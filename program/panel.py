"""
Bidik Kontrol Paneli: http://127.0.0.1:8765
Senaryo uret -> onayla / duzenle / reddet -> video onizle -> YouTube'a yukle.
"""
import datetime, glob, json, os, re, shutil, subprocess, sys, threading, time, traceback, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

from ortak import KOK, PROGRAM, SENARYO, VIDEO, ayarlar, ayar_kaydet, aciklama_tam, etiket_listesi
from karakter import IFADELER, KOL_POZLARI
from video_uret import uret, dogrula, IKONLAR, RENKLER
import senaryo_motoru as motor
import youtube_yukle as yt
import github_kanal
import telefon

PORT = 8765
GUNCELLEME = os.path.join(KOK, "guncelleme")
YEDEK = os.path.join(KOK, "yedek")
NABIZ = {"son": None}           # Edge uygulama modunda pencere kapandi mi anlamak icin
KAPAT = {"fonk": None}          # uygulama.py pencereyi kapatma fonksiyonunu buraya koyar
ARKA = {"acik": False}       # uygulama.py --arka: pencere olmadan arka planda calisiyor
IS = {"calisiyor": False, "baslik": "", "yuzde": 0, "mesaj": "", "hata": "", "bitti": "", "no": 0}
KILIT = threading.Lock()


# --- yardimcilar --------------------------------------------------------------
def guvenli(yol_rel):
    """Panelden gelen goreli yolu BIDIK klasoru icinde tutar."""
    tam = os.path.normpath(os.path.join(KOK, yol_rel))
    if not tam.startswith(os.path.normpath(KOK) + os.sep):
        raise ValueError("gecersiz yol")
    return tam


def rel(tam):
    return os.path.relpath(tam, KOK).replace(os.sep, "/")


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def tasi(yol, hedef_tur):
    hedef = os.path.join(SENARYO, hedef_tur, os.path.basename(os.path.dirname(yol)))
    os.makedirs(hedef, exist_ok=True)
    yeni = os.path.join(hedef, os.path.basename(yol))
    if os.path.exists(yeni):
        yeni = yeni.replace(".json", f"_{datetime.datetime.now():%H%M%S}.json")
    shutil.move(yol, yeni)
    return yeni


def is_baslat(baslik, fonk):
    with KILIT:
        if IS["calisiyor"]:
            raise RuntimeError("Zaten bir islem suruyor: " + IS["baslik"])
        IS.update(calisiyor=True, baslik=baslik, yuzde=0, mesaj="Basliyor", hata="", bitti="", no=IS["no"] + 1)

    def ilerle(y, m):
        IS.update(yuzde=int(y), mesaj=m)

    def kos():
        try:
            sonuc = fonk(ilerle)
            IS.update(bitti=sonuc or "Tamamlandi")
        except Exception as e:
            traceback.print_exc()
            IS.update(hata=str(e))
        finally:
            IS["calisiyor"] = False
    threading.Thread(target=kos, daemon=True).start()


def durum():
    a = ayarlar()
    bekleyen = []
    for p in motor.bekleyen_dosyalar():
        s = oku(p)
        s["_id"] = rel(p)
        s["_hatalar"] = dogrula(s)
        bekleyen.append(s)
    videolar = []
    for mp4 in sorted(glob.glob(os.path.join(VIDEO, "*", "*.mp4")), reverse=True):
        meta_yol = mp4[:-4] + ".json"
        meta = oku(meta_yol) if os.path.exists(meta_yol) else {}
        videolar.append({"_id": rel(mp4), "baslik": meta.get("baslik", os.path.basename(mp4)),
                         "aciklama": aciklama_tam(meta), "etiketler": etiket_listesi(meta),
                         "tarih": os.path.basename(os.path.dirname(mp4)),
                         "sure": meta.get("_video_sure"), "sesli": meta.get("_sesli"),
                         "youtube_url": meta.get("youtube_url", ""), "yayin_zamani": meta.get("yayin_zamani", ""),
                         "zamanli": meta.get("zamanli", False), "kisitli": meta.get("kisitli", False),
                         "sessiz_sahneler": meta.get("_sessiz_sahneler", [])})
    return {
        "is": IS,
        "bekleyen": bekleyen,
        "videolar": videolar[:30],
        "ayar": {"gemini_var": bool(a.get("gemini_api_key")), "gunluk_video": a["gunluk_video"],
                 "alanlar": a["alanlar"], "son_cagri": a.get("son_cagri", True), "tema": a.get("tema", "koyu"),
                 "paylasim_saatleri": a.get("paylasim_saatleri") or ["11:00", "15:00", "19:00"],
                 "youtube_hazir": yt.hazir_mi(), "youtube_bagli": yt.bagli_mi(),
                 "youtube_kanal": a.get("youtube_kanal", ""), "youtube_silme": yt.silme_izni_var(),
                 "sifre_var": sifre_var(), "arka": ARKA["acik"]},
        "secenek": {"ifade": IFADELER, "kol": KOL_POZLARI, "ikon": IKONLAR, "renk": list(RENKLER)},
        "toplam_islenen": len(motor.hafiza()["konular"]),
        "surum": surum(),
        "guncelleme": bekleyen_guncelleme(),
    }


# --- telefondan erisim: sifre ve oturum ------------------------------------------
import hashlib, hmac, secrets
from http.cookies import SimpleCookie

OTURUM_DOSYA = os.path.join(KOK, "oturumlar.json")
OTURUM_SURE = 30 * 24 * 3600
GIRIS = {"hata": 0, "kilit": 0.0}
YEREL_HOSTLAR = {"127.0.0.1", "localhost"}
SADECE_YEREL = {"/api/sifre", "/api/telefon", "/api/klasor", "/api/youtube-istemci", "/api/kapat"}


def _ozet(sifre, tuz, tur=200_000):
    return hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(tuz), tur).hex()


def sifre_var():
    return bool((ayarlar().get("panel_sifre") or {}).get("ozet"))


def _sifre_dogru(sifre):
    k = ayarlar().get("panel_sifre") or {}
    if not k.get("ozet"):
        return False
    return hmac.compare_digest(_ozet(sifre, k["tuz"], int(k.get("tur", 200_000))), k["ozet"])


def _oturumlar():
    try:
        with open(OTURUM_DOSYA, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return {}
    simdi = time.time()
    return {k: v for k, v in veri.items() if v > simdi}


def _oturumlari_yaz(o):
    with open(OTURUM_DOSYA, "w", encoding="utf-8") as f:
        json.dump(o, f)


def _oturum_ac():
    jeton = secrets.token_urlsafe(32)
    o = _oturumlar()
    o[hashlib.sha256(jeton.encode()).hexdigest()] = time.time() + OTURUM_SURE
    _oturumlari_yaz(o)
    return jeton


def _jeton(h):
    try:
        c = SimpleCookie(h.headers.get("Cookie") or "")
        return c["bidik_oturum"].value if "bidik_oturum" in c else ""
    except Exception:
        return ""


def _oturum_gecerli(h):
    j = _jeton(h)
    return bool(j) and hashlib.sha256(j.encode()).hexdigest() in _oturumlar()


def uzak_mi(h):
    """Istek bu bilgisayarin kendisinden degilse (telefon / Tailscale) True."""
    host = (h.headers.get("Host") or "").strip().lower()
    host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    ip = h.client_address[0]
    # Tailscale serve istegi 127.0.0.1'den iletir ama yonlendirme basliklari ekler
    yonlendirildi = any(h.headers.get(k) for k in ("X-Forwarded-For", "X-Forwarded-Host", "Forwarded",
                                                     "Tailscale-User-Login", "Tailscale-User-Name"))
    return ip not in ("127.0.0.1", "::1") or host not in YEREL_HOSTLAR or yonlendirildi


def sifre_ayarla(v):
    sifre = str(v.get("sifre") or "")
    if len(sifre) < 6:
        raise ValueError("Sifre en az 6 karakter olmali.")
    tuz = secrets.token_hex(16)
    ayar_kaydet({"panel_sifre": {"tuz": tuz, "ozet": _ozet(sifre, tuz), "tur": 200_000}})
    _oturumlari_yaz({})   # eski telefon oturumlari kapanir
    return {"mesaj": "Sifre kaydedildi. Telefonda yeniden giris yapman gerekecek."}


GIRIS_HTML = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#14151d">
<link rel="manifest" href="/manifest.json"><link rel="apple-touch-icon" href="/bidik.png">
<meta name="apple-mobile-web-app-capable" content="yes"><title>Bıdık Stüdyo</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#14151d;color:#ecebf3;
font:16px system-ui,-apple-system,"Segoe UI",sans-serif}form{width:min(340px,90vw);text-align:center}
img{width:96px}h1{font-size:22px;margin:10px 0 18px}input{width:100%;box-sizing:border-box;font:inherit;padding:14px;
border-radius:12px;border:1.5px solid #2e3144;background:#151722;color:#ecebf3;margin-bottom:12px}
button{width:100%;font:inherit;font-weight:700;padding:14px;border-radius:12px;border:none;background:#ffb703;color:#23253a}
p{color:#e63946;min-height:22px;font-size:14px}</style></head><body>
<form onsubmit="gir(event)"><img src="/bidik.png" alt=""><h1>Bıdık Stüdyo</h1>
<input id="s" type="password" placeholder="Şifre" autocomplete="current-password" autofocus>
<button>Giriş</button><p id="h">__MESAJ__</p></form>
<script>async function gir(e){e.preventDefault();const r=await fetch("/api/giris",{method:"POST",
headers:{"Content-Type":"application/json"},body:JSON.stringify({sifre:document.getElementById("s").value})});
const j=await r.json();if(j.ok)location.replace("/");else document.getElementById("h").textContent=j.hata||"Hata";}</script>
</body></html>"""

MANIFEST = {"name": "Bıdık Stüdyo", "short_name": "Bıdık", "start_url": "/", "display": "standalone",
            "background_color": "#14151d", "theme_color": "#14151d",
            "icons": [{"src": "/bidik.png", "sizes": "192x192", "type": "image/png"}]}


# --- surum / guncelleme --------------------------------------------------------
def surum():
    try:
        with open(os.path.join(PROGRAM, "surum.txt"), encoding="utf-8") as f:
            return f.read().strip() or "1.0.0"
    except OSError:
        return "1.0.0"


def _sayi(s):
    return tuple(int(x) for x in re.findall(r"\d+", s)) or (0,)


def bekleyen_guncelleme():
    yol = os.path.join(GUNCELLEME, "surum.json")
    if not os.path.exists(yol):
        return None
    try:
        g = oku(yol)
    except (OSError, ValueError):
        return None
    if _sayi(g.get("surum", "0")) <= _sayi(surum()):
        return None
    return {"surum": g["surum"], "notlar": g.get("notlar", []), "tarih": g.get("tarih", "")}


def _kopyala_agac(kaynak, hedef):
    adet = 0
    for kok, _, dosyalar in os.walk(kaynak):
        for d in dosyalar:
            k = os.path.join(kok, d)
            h = os.path.join(hedef, os.path.relpath(k, kaynak))
            os.makedirs(os.path.dirname(h), exist_ok=True)
            shutil.copy2(k, h)
            adet += 1
    return adet


def guncelleme_uygula(ilerle):
    g = bekleyen_guncelleme()
    if not g:
        raise RuntimeError("Uygulanacak guncelleme yok.")
    eski = surum()
    ilerle(10, f"Yedek aliniyor (v{eski})")
    os.makedirs(YEDEK, exist_ok=True)
    shutil.copytree(PROGRAM, os.path.join(YEDEK, f"program_v{eski}_{datetime.datetime.now():%Y%m%d%H%M%S}"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    for eski_yedek in sorted(glob.glob(os.path.join(YEDEK, "program_v*")))[:-3]:   # son 3 yedek kalsin
        shutil.rmtree(eski_yedek, ignore_errors=True)
    ger_yol = os.path.join(PROGRAM, "gereksinimler.txt")
    eski_ger = open(ger_yol, encoding="utf-8").read() if os.path.exists(ger_yol) else ""

    ilerle(35, "Yeni dosyalar kopyalaniyor")
    adet = 0
    if os.path.isdir(os.path.join(GUNCELLEME, "program")):
        adet += _kopyala_agac(os.path.join(GUNCELLEME, "program"), PROGRAM)
    if os.path.isdir(os.path.join(GUNCELLEME, "kok")):
        adet += _kopyala_agac(os.path.join(GUNCELLEME, "kok"), KOK)

    yeni_ger = open(ger_yol, encoding="utf-8").read() if os.path.exists(ger_yol) else ""
    if yeni_ger != eski_ger:
        ilerle(60, "Yeni bilesenler kuruluyor (internet gerekir)")
        py = sys.executable
        if py.lower().endswith("pythonw.exe"):
            py = py[:-len("pythonw.exe")] + "python.exe"
        bayrak = 0x08000000 if sys.platform.startswith("win") else 0   # CREATE_NO_WINDOW
        sonuc = subprocess.run([py, "-m", "pip", "install", "-q", "-r", ger_yol],
                               capture_output=True, text=True, creationflags=bayrak)
        if sonuc.returncode != 0:
            raise RuntimeError("Bilesenler kurulamadi: " + (sonuc.stderr or "")[-300:])

    with open(os.path.join(PROGRAM, "surum.txt"), "w", encoding="utf-8") as f:
        f.write(g["surum"])
    shutil.rmtree(GUNCELLEME, ignore_errors=True)
    ilerle(95, "Uygulama yeniden baslatiliyor")
    threading.Timer(1.0, yeniden_baslat).start()
    return f"v{g['surum']} kuruldu ({adet} dosya). Uygulama yeniden aciliyor..."


def yeniden_baslat():
    """Yeni bir uygulama sureci baslatir, bu sureci kapatir."""
    hedef = os.path.join(PROGRAM, "uygulama.py")
    bayrak = 0
    if sys.platform.startswith("win"):
        bayrak = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    argumanlar = [sys.executable, hedef, "--yeniden"] + (["--arka"] if ARKA["acik"] else [])
    subprocess.Popen(argumanlar, cwd=KOK, creationflags=bayrak, close_fds=True)
    time.sleep(0.3)
    try:
        if KAPAT["fonk"]:
            KAPAT["fonk"]()
    finally:
        os._exit(0)


def guncelle(_):
    is_baslat("Guncelleniyor", guncelleme_uygula)


def nabiz(_):
    NABIZ["son"] = time.time()


# --- islemler -----------------------------------------------------------------
def senaryo_uret(_):
    def f(ilerle):
        secilen = motor.calistir(ilerle)
        return f"{len(secilen)} yeni senaryo onayini bekliyor"
    is_baslat("Senaryolar yaziliyor", f)


def kaydet(v):
    yol = guvenli(v["id"])
    s = v["senaryo"]
    for k in [k for k in s if k.startswith("_")]:
        s.pop(k)
    yaz(yol, s)
    return {"hatalar": dogrula(s)}


def siradaki_no(gun):
    """Ayni gunde kullanilmis en buyuk numaranin bir fazlasi (silinenler dahil): dosyalar asla ezilmez."""
    kullanilan = [0]
    for klasor in (os.path.join(VIDEO, gun), os.path.join(KOK, "silinenler", gun)):
        for yol in glob.glob(os.path.join(klasor, f"bidik_{gun}_*")):
            m = re.match(rf"bidik_{re.escape(gun)}_(\d+)", os.path.basename(yol))
            if m:
                kullanilan.append(int(m.group(1)))
    no = max(kullanilan) + 1
    while os.path.exists(os.path.join(VIDEO, gun, f"bidik_{gun}_{no}.mp4")):
        no += 1
    return no


def _video_yap(senaryo_yolu, s, mp4, ilerle):
    """Videoyu uretir, meta + yayin metnini yazar; sessiz kalan sahne numaralarini dondurur."""
    _, sure, sesli, sessiz = uret(senaryo_yolu, mp4, ilerleme=ilerle)
    meta = dict(s, _video_sure=round(sure, 1), _sesli=sesli, _sessiz_sahneler=sessiz)
    yaz(mp4[:-4] + ".json", meta)
    with open(mp4[:-4] + "_yayin.txt", "w", encoding="utf-8") as fp:
        fp.write(f"BASLIK:\n{s['baslik']} #shorts\n\nACIKLAMA:\n{aciklama_tam(s)}\n\n"
                 f"ETIKETLER (YouTube etiket alanina):\n{', '.join(etiket_listesi(s))}\n")
    return sessiz


def yeniden_uret(v):
    """
    Bir videoyu ayni senaryodan bastan uretir (ornegin sesi eksik ciktiysa).
    Paylasilmamis video: eskisi silinenler'e tasinir, yenisi yerine gelir.
    Paylasilmis video: YouTube'daki dosya degistirilemedigi icin yeni (paylasilmamis) bir kopya olusturulur.
    """
    eski_mp4 = guvenli(v["id"])
    eski_meta_yol = eski_mp4[:-4] + ".json"
    if not os.path.exists(eski_meta_yol):
        raise ValueError("Bu videonun senaryo kaydi bulunamadi.")
    meta = oku(eski_meta_yol)
    paylasildi = bool(meta.get("youtube_url"))
    s = {k: val for k, val in meta.items() if not k.startswith("_") and k not in
         ("youtube_url", "youtube_id", "yayin_zamani", "zamanli", "kisitli", "paylasildi")}

    def f(ilerle):
        import tempfile
        gecici = os.path.join(tempfile.mkdtemp(prefix="bidik_yeniden_"), "senaryo.json")
        yaz(gecici, s)
        gun = datetime.datetime.now().strftime("%Y-%m-%d")
        os.makedirs(os.path.join(VIDEO, gun), exist_ok=True)
        mp4 = os.path.join(VIDEO, gun, f"bidik_{gun}_{siradaki_no(gun)}.mp4")
        sessiz = _video_yap(gecici, s, mp4, ilerle)
        if not paylasildi:
            video_sil({"id": v["id"]})
        if sessiz:
            return f"Yeniden uretildi ama {len(sessiz)} sahnede ses yine olusmadi. Internet baglantini kontrol edip tekrar dene."
        return ("Duzeltilmis kopya hazir. YouTube'daki eski videoyu Studio'dan silip bunu paylasabilirsin."
                if paylasildi else "Video yeniden uretildi, tum sahneler sesli.")
    is_baslat(f"Yeniden uretiliyor: {s.get('baslik', '')}", f)


def _yazim_kapisi(yol, ilerle):
    """
    Video uretilmeden once metinler yazim + bilgi acisindan denetlenir (metin degismediyse tekrar sorulmaz).
    Hata bulunursa duzeltmeler dosyaya yazilir ve islem DURUR: Deniz duzeltilmis metni gorup tekrar onaylar.
    Denetlenemezse (internet/Gemini) yine durur: denetlenmemis metin yayina girmez.
    """
    if not ayarlar().get("yazim_denetimi", True):
        return
    s = oku(yol)
    if motor.denetim_gecerli(s):
        return
    son = {"y": 3}

    def ilerle2(y, m):
        if y is not None:
            son["y"] = y
        ilerle(son["y"], m)
    ilerle2(3, "Yazim ve bilgi denetimi yapiliyor")
    try:
        r = motor.denetle(motor.model_sec(ayarlar()["model"]), [s], ilerle2)[0]
    except motor.MotorHatasi as e:
        raise ValueError(f"Yazim denetimi yapilamadi ({str(e)[:150]}). Birkac dakika sonra tekrar onayla; "
                         "denetlenmemis metin yayina girmez.")
    if not r["tamam"]:
        raise ValueError("Yazim denetimi cevabi okunamadi. Tekrar onayla; denetlenmemis metin yayina girmez.")
    motor.denetim_isle(s, r)
    if r["duzeltmeler"] or not r["bilgi_dogru"]:
        yaz(yol, s)
        mesaj = []
        if not r["bilgi_dogru"]:
            mesaj.append("BILGI SUPHELI: " + (r["bilgi_sorunu"] or "denetim bu bilgiye guvenmedi")
                         + " Metni duzenle ya da reddet.")
        if r["duzeltmeler"]:
            mesaj.append("Yazim duzeltildi (senaryo guncellendi, kontrol edip tekrar onayla): "
                         + " | ".join(r["duzeltmeler"]))
        raise ValueError(" ".join(mesaj))
    yaz(yol, s)   # imza kaydedildi


def onayla(v):
    yol = guvenli(v["id"])
    s = oku(yol)
    h = dogrula(s)
    if h:
        raise ValueError("Once duzelt: " + "; ".join(h))

    def f(ilerle):
        nonlocal s
        _yazim_kapisi(yol, ilerle)
        s = oku(yol)
        gun =datetime.datetime.now().strftime("%Y-%m-%d")
        klasor = os.path.join(VIDEO, gun)
        os.makedirs(klasor, exist_ok=True)
        no = siradaki_no(gun)
        mp4 = os.path.join(klasor, f"bidik_{gun}_{no}.mp4")
        sessiz = _video_yap(yol, s, mp4, ilerle)
        motor.hafizaya_ekle(s.get("konu", s["baslik"]), s.get("alan", ""), s["baslik"], "onaylandi")
        tasi(yol, "onaylanan")
        if sessiz:
            return (f"Video hazir ama {len(sessiz)} sahnede ses uretilemedi (sahne {', '.join(map(str, sessiz))}). "
                    "Videolar sekmesinde 'Yeniden uret'e bas.")
        return f"Video hazir: {os.path.basename(mp4)}"
    is_baslat(f"Video uretiliyor: {s['baslik']}", f)


def reddet(v):
    yol = guvenli(v["id"])
    s = oku(yol)
    motor.hafizaya_ekle(s.get("konu", s.get("baslik", "")), s.get("alan", ""), s.get("baslik", ""), "reddedildi")
    tasi(yol, "reddedilen")


def _meta(mp4):
    yol = mp4[:-4] + ".json"
    return yol, (oku(yol) if os.path.exists(yol) else {})


def paylas(v):
    """Videoyu secilen tarih/saatte otomatik yayinlanacak sekilde YouTube'a yukler."""
    mp4 = guvenli(v["id"])
    meta_yol, meta = _meta(mp4)
    if meta.get("youtube_url"):
        raise ValueError("Bu video zaten paylasildi: " + meta["youtube_url"])
    if not yt.bagli_mi():
        raise ValueError("Once YouTube sekmesinden hesabini bagla.")
    try:
        yerel = datetime.datetime.strptime(f"{v['tarih']} {v['saat']}", "%Y-%m-%d %H:%M")
    except (KeyError, ValueError):
        raise ValueError("Tarih ve saati sec.")
    zaman = yerel.astimezone()   # bilgisayarin saat dilimi (Turkiye: UTC+3)
    if zaman < datetime.datetime.now().astimezone() - datetime.timedelta(minutes=5):
        raise ValueError("Gecmis bir saat secildi. Simdi ya da ileri bir zaman sec.")
    if v.get("baslik"):
        meta["baslik"] = v["baslik"].strip()
    if v.get("aciklama"):
        meta["aciklama"] = v["aciklama"].strip()

    def f(ilerle):
        sonuc = yt.yukle(mp4, meta.get("baslik", "Bidik"), aciklama_tam(meta), etiket_listesi(meta),
                         yayin_zamani=zaman, ilerleme=ilerle)
        meta.update(youtube_url=sonuc["url"], youtube_id=sonuc["id"], yayin_zamani=zaman.isoformat(),
                    zamanli=sonuc["zamanli"], kisitli=sonuc["kisitli"],
                    paylasildi=datetime.datetime.now().astimezone().isoformat())
        yaz(meta_yol, meta)
        if sonuc["kisitli"]:
            return ("Video yuklendi ama YouTube onu OZEL olarak kisitladi (Google denetimi gerekiyor). "
                    "YouTube sekmesindeki aciklamaya bak.")
        if sonuc["zamanli"]:
            return f"Zamanlandi: {zaman:%d.%m.%Y %H:%M}'da otomatik yayinlanacak."
        return f"Yayinlandi: {sonuc['url']}"
    is_baslat(f"Paylasiliyor: {meta.get('baslik', '')}", f)


def video_sil(v):
    """
    Videoyu bilgisayardan kalici silmez: BIDIK/silinenler klasorune tasir.
    youtube_da_sil=True ise once YouTube'dan kalici olarak siler (basarisizsa hicbir sey tasinmaz).
    """
    mp4 = guvenli(v["id"])
    if v.get("youtube_da_sil"):
        meta_yol = mp4[:-4] + ".json"
        meta = oku(meta_yol) if os.path.exists(meta_yol) else {}
        vid = meta.get("youtube_id") or (meta.get("youtube_url", "").rstrip("/").split("/")[-1] or None)
        if not vid:
            raise ValueError("Bu videonun YouTube kaydi bulunamadi; sadece uygulamadan kaldirabilirsin.")
        sonuc = yt.sil(vid)
        meta.update(youtube_silindi=datetime.datetime.now().astimezone().isoformat(), youtube_silme_sonucu=sonuc)
        yaz(meta_yol, meta)
    hedef = os.path.join(KOK, "silinenler", os.path.basename(os.path.dirname(mp4)))
    os.makedirs(hedef, exist_ok=True)
    taban = mp4[:-4]
    for ek in (".mp4", ".json", "_yayin.txt"):
        if os.path.exists(taban + ek):
            hedef_yol = os.path.join(hedef, os.path.basename(taban + ek))
            if os.path.exists(hedef_yol):
                hedef_yol = hedef_yol.replace(os.path.basename(taban), os.path.basename(taban) + f"_{time.time():.0f}")
            shutil.move(taban + ek, hedef_yol)


def _paket_surumu(ad):
    try:
        from importlib.metadata import version
        return version(ad)
    except Exception:
        return "kurulu degil"


def destek(_):
    """Claude'a yapistirilacak teshis bilgisi (anahtarlar dahil edilmez)."""
    import platform
    a = ayarlar()
    satirlar = [
        "BIDIK STUDYO DESTEK BILGISI",
        f"Surum: {surum()} | Windows: {platform.platform()} | Python: {platform.python_version()}",
        f"Gemini anahtari: {'var' if a.get('gemini_api_key') else 'yok'} | son model: {a.get('son_model', '-')}",
        f"Ses kutuphanesi (edge-tts): {_paket_surumu('edge-tts')}",
        f"YouTube: {'bagli (' + a.get('youtube_kanal', '') + ')' if yt.bagli_mi() else 'bagli degil'}",
        github_kanal.durum_metni(),
        f"Arka plan: {'evet' if ARKA['acik'] else 'hayir'} | telefon sifresi: {'var' if sifre_var() else 'yok'}",
        f"Son is: {IS.get('baslik')} | durum: {'calisiyor' if IS.get('calisiyor') else 'bitti'} | hata: {IS.get('hata') or '-'}",
    ]
    log = os.path.join(KOK, "bidik.log")
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="ignore") as f:
            son = f.readlines()[-40:]
        satirlar += ["", "--- bidik.log (son 40 satir) ---"] + [x.rstrip() for x in son]
    return {"metin": "\n".join(satirlar)}


def github_kontrol(_):
    """GitHub'da yeni surum var mi, hemen bak (normalde 30 dk'da bir kendisi bakar)."""
    try:
        github_kanal.DURUM["sonuc"] = github_kanal.kontrol_et()
        github_kanal.DURUM["hata"] = ""
    except Exception as e:
        github_kanal.DURUM["hata"] = str(e)[:200]
    return {"metin": github_kanal.durum_metni()}


def telefon_islem(v):
    """Ayarlar > Telefondan erisim karti (sadece bu bilgisayardan)."""
    islem = v.get("islem", "durum")
    if islem == "otomatik":
        acik = bool(v.get("acik"))
        telefon.otomatik_baslat(acik)
        ayar_kaydet({"arka_plan": acik})
        ts = {}
    elif islem == "ac":
        ts = telefon.tailscale_ac()
    elif islem == "kapat":
        ts = telefon.tailscale_kapat()
    else:
        ts = telefon.tailscale_durum()
    return {"tailscale": ts, "sifre_var": sifre_var(), "otomatik": telefon.otomatik_baslat_var(),
            "arka": ARKA["acik"]}


def kapat(_):
    """Uygulamayi (arka plan dahil) tamamen kapatir."""
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"mesaj": "Uygulama kapaniyor"}


def youtube_istemci(v):
    yt.istemci_kaydet(v.get("icerik", ""))


def youtube_bagla(_):
    is_baslat("YouTube hesabi baglaniyor", yt.bagla)


def youtube_kes(_):
    yt.baglantiyi_kes()


def ayar(v):
    yeni = {}
    if v.get("gemini_api_key"):
        yeni["gemini_api_key"] = v["gemini_api_key"].strip()
    if v.get("gunluk_video"):
        yeni["gunluk_video"] = max(1, min(10, int(v["gunluk_video"])))
        yeni["aday_sayisi"] = max(6, yeni["gunluk_video"] * 3)
    if v.get("alanlar"):
        yeni["alanlar"] = [a.strip() for a in v["alanlar"].split(",") if a.strip()]
    if v.get("paylasim_saatleri"):
        saatler = []
        for p in str(v["paylasim_saatleri"]).replace(";", ",").split(","):
            p = p.strip().replace(".", ":")
            try:
                t = datetime.datetime.strptime(p, "%H:%M")
            except ValueError:
                try:
                    t = datetime.datetime.strptime(p, "%H")
                except ValueError:
                    raise ValueError(f"Gecersiz saat: '{p}'. Ornek: 11:00, 15:00, 19:00")
            if f"{t:%H:%M}" not in saatler:
                saatler.append(f"{t:%H:%M}")
        yeni["paylasim_saatleri"] = sorted(saatler)[:8]
    if "son_cagri" in v:
        yeni["son_cagri"] = bool(v["son_cagri"])
    if v.get("tema") in ("koyu", "acik"):
        yeni["tema"] = v["tema"]
    ayar_kaydet(yeni)


def klasor_ac(v):
    hedef = guvenli(v["id"]) if v.get("id") else KOK
    if sys.platform.startswith("win"):
        if os.path.isfile(hedef):
            subprocess.Popen(["explorer", "/select,", hedef])
        else:
            os.startfile(hedef)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R" if os.path.isfile(hedef) else "", hedef])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(hedef) if os.path.isfile(hedef) else hedef])


ISLEMLER = {"/api/senaryo-uret": senaryo_uret, "/api/kaydet": kaydet, "/api/onayla": onayla,
            "/api/reddet": reddet, "/api/ayar": ayar, "/api/klasor": klasor_ac,
            "/api/guncelle": guncelle, "/api/nabiz": nabiz,
            "/api/paylas": paylas, "/api/video-sil": video_sil, "/api/youtube-istemci": youtube_istemci,
            "/api/youtube-bagla": youtube_bagla, "/api/youtube-kes": youtube_kes, "/api/destek": destek, "/api/github-kontrol": github_kontrol, "/api/sifre": sifre_ayarla, "/api/telefon": telefon_islem, "/api/kapat": kapat, "/api/yeniden-uret": yeniden_uret}


# --- sunucu -------------------------------------------------------------------
class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, veri, kod=200):
        b = json.dumps(veri, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, metin, kod=200):
        b = metin.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _kapi(self, yol):
        """Uzak istekte oturum yoksa cevabi verir ve False dondurur."""
        if not uzak_mi(self) or yol in ("/bidik.png", "/manifest.json", "/api/giris"):
            return True
        if not sifre_var():
            self._html(GIRIS_HTML.replace("__MESAJ__", "Telefon erişimi kapalı: önce bilgisayardaki uygulamada "
                                          "Ayarlar &gt; Telefondan erişim bölümünden şifre belirle."), 403)
            return False
        if _oturum_gecerli(self):
            if yol in SADECE_YEREL:
                self._json({"ok": False, "hata": "Bu islem sadece bilgisayardan yapilabilir."}, 403)
                return False
            return True
        if yol.startswith("/api/") or yol.startswith("/dosya/"):
            self._json({"ok": False, "hata": "Oturum kapali, yeniden giris yap.", "giris": True}, 401)
        else:
            self._html(GIRIS_HTML.replace("__MESAJ__", ""))
        return False

    def _giris(self, v):
        simdi = time.time()
        if simdi < GIRIS["kilit"]:
            return self._json({"ok": False, "hata": f"Cok fazla hatali deneme. {int(GIRIS['kilit'] - simdi) + 1} sn bekle."}, 429)
        if not _sifre_dogru(str(v.get("sifre") or "")):
            GIRIS["hata"] += 1
            if GIRIS["hata"] >= 5:
                GIRIS["kilit"] = simdi + min(900, 60 * 2 ** (GIRIS["hata"] - 5))
            time.sleep(1)
            return self._json({"ok": False, "hata": "Sifre yanlis."}, 401)
        GIRIS.update(hata=0, kilit=0.0)
        jeton = _oturum_ac()
        https = (self.headers.get("X-Forwarded-Proto") or "").lower() == "https" or \
            (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "").lower().split(":")[0].endswith(".ts.net")
        guvenli_cerez = "; Secure" if https else ""
        b = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", f"bidik_oturum={jeton}; Path=/; Max-Age={OTURUM_SURE}; HttpOnly; SameSite=Strict{guvenli_cerez}")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _cikis(self):
        j = _jeton(self)
        if j:
            o = _oturumlar()
            o.pop(hashlib.sha256(j.encode()).hexdigest(), None)
            _oturumlari_yaz(o)
        b = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", "bidik_oturum=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        yol = urlparse(self.path).path
        if not self._kapi(yol):
            return
        if yol == "/manifest.json":
            self._json(MANIFEST)
        elif yol == "/":
            b = open(os.path.join(os.path.dirname(__file__), "panel.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif yol == "/api/durum":
            self._json(durum())
        elif yol.startswith("/dosya/"):
            self._dosya(unquote(yol[len("/dosya/"):]))
        elif yol == "/bidik.png":
            self._dosya("program/bidik.png")
        else:
            self.send_error(404)

    def _dosya(self, r):
        try:
            tam = guvenli(r)
        except ValueError:
            return self.send_error(403)
        if not os.path.isfile(tam):
            return self.send_error(404)
        boyut = os.path.getsize(tam)
        tur = {"mp4": "video/mp4", "png": "image/png"}.get(tam.rsplit(".", 1)[-1], "application/octet-stream")
        bas, son = 0, boyut - 1
        aralik = self.headers.get("Range")
        if aralik and aralik.startswith("bytes="):
            a, _, b = aralik[6:].partition("-")
            bas = int(a) if a else 0
            son = min(int(b), boyut - 1) if b else boyut - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {bas}-{son}/{boyut}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tur)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(son - bas + 1))
        self.end_headers()
        with open(tam, "rb") as f:
            f.seek(bas)
            kalan = son - bas + 1
            try:
                while kalan > 0:
                    parca = f.read(min(65536, kalan))
                    if not parca:
                        break
                    self.wfile.write(parca)
                    kalan -= len(parca)
            except (ConnectionResetError, BrokenPipeError):
                pass

    def do_POST(self):
        yol = urlparse(self.path).path
        if not self._kapi(yol):
            return
        uzunluk = int(self.headers.get("Content-Length") or 0)
        if uzunluk > 5_000_000:
            return self.send_error(413)
        if yol == "/api/giris":
            try:
                return self._giris(json.loads(self.rfile.read(uzunluk) or b"{}"))
            except ValueError:
                return self._json({"ok": False, "hata": "gecersiz istek"}, 400)
        if yol == "/api/cikis":
            return self._cikis()
        fonk = ISLEMLER.get(yol)
        if not fonk:
            return self.send_error(404)
        try:
            v = json.loads(self.rfile.read(uzunluk) or b"{}")
            sonuc = fonk(v) or {}
            self._json({"ok": True, **sonuc})
        except Exception as e:
            traceback.print_exc()
            self._json({"ok": False, "hata": str(e)}, 400)


def hazirla():
    for d in ("bekleyen", "onaylanan", "reddedilen"):
        os.makedirs(os.path.join(SENARYO, d), exist_ok=True)
    os.makedirs(VIDEO, exist_ok=True)
    if not os.path.exists(os.path.join(KOK, "ayarlar.json")):
        ayar_kaydet({})
    github_kanal.baslat()   # bilgisayar kapaliyken GitHub'a konan guncellemeleri acilinca indirir


class SessizSunucu(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # Sayfa yenilenirken yarida kalan istekler (pencere iptal etti) zararsizdir; log'u kirletmesin.
        hata = sys.exc_info()[1]
        if isinstance(hata, (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def sunucu_olustur():
    hazirla()
    # Linux/macOS: kapanan eski baglantilar (TIME_WAIT) yeniden acilisi engellemesin.
    # Windows'ta SO_REUSEADDR portu baska surecle paylastirabildigi icin kullanilmaz.
    ThreadingHTTPServer.allow_reuse_address = not sys.platform.startswith("win")
    SessizSunucu.allow_reuse_address = ThreadingHTTPServer.allow_reuse_address
    return SessizSunucu(("127.0.0.1", PORT), Isleyici)


def main():
    sunucu = sunucu_olustur()
    adres = f"http://127.0.0.1:{PORT}"
    print(f"Bidik paneli calisiyor: {adres}\nKapatmak icin bu pencereyi kapat.")
    if "--tarayicisiz" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(adres)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
