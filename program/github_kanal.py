"""
GitHub guncelleme kanali.

Herkese acik depodaki surum.json'a bakar:
  {"surum": "1.5.1", "tarih": "...", "notlar": ["..."],
   "dosyalar": {"program/panel.py": "<sha256>", "kok/OKUBENI.txt": "<sha256>", ...}}
Surum, kurulu surumden buyukse SADECE parmak izi farkli olan dosyalari indirir, sha256 ile dogrular
ve BIDIK\\guncelleme\\ klasorune koyar (surum.json en son). Gerisini mevcut guncelleyici yapar:
panelde "Yeni guncelleme var" bandi cikar, Deniz "Simdi guncelle"ye basar.

Ayar: ayarlar.json -> "github_depo": "kullanici/depo", "github_dal": "main" (bos ise kanal kapali).
Sadece Python standart kutuphanesi kullanir. Hicbir anahtar/sifre gondermez.
"""
import hashlib, json, os, re, shutil, threading, time, urllib.request, urllib.error

from ortak import KOK, PROGRAM, ayarlar

GUNCELLEME = os.path.join(KOK, "guncelleme")
KONTROL_ARALIGI = 30 * 60        # sn
ILK_BEKLEME = 20                 # uygulama acildiktan sonra
DURUM = {"son_kontrol": "", "sonuc": "henuz kontrol edilmedi", "hata": ""}
_KILIT = threading.Lock()
_GECERLI_YOL = re.compile(r"^(program|kok)/[A-Za-z0-9_./ -]+$")


def _sayi(s):
    return tuple(int(x) for x in re.findall(r"\d+", str(s))) or (0,)


def _kurulu_surum():
    try:
        with open(os.path.join(PROGRAM, "surum.txt"), encoding="utf-8") as f:
            return f.read().strip() or "1.0.0"
    except OSError:
        return "1.0.0"


def _bekleyen_surum():
    try:
        with open(os.path.join(GUNCELLEME, "surum.json"), encoding="utf-8") as f:
            return json.load(f).get("surum", "0")
    except (OSError, ValueError):
        return "0"


def _indir(url):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + f"t={int(time.time())}",
                                 headers={"User-Agent": "BidikStudyo", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def _sha(veri):
    return hashlib.sha256(veri).hexdigest()


def _yerel_yol(goreli):
    """'program/x.py' -> PROGRAM/x.py, 'kok/y.txt' -> KOK/y.txt"""
    alan, _, geri = goreli.partition("/")
    return os.path.join(PROGRAM if alan == "program" else KOK, *geri.split("/"))


def _yerel_sha(goreli):
    try:
        with open(_yerel_yol(goreli), "rb") as f:
            return _sha(f.read())
    except OSError:
        return ""


def kontrol_et():
    """Bir kez kontrol eder. Donus: kisa durum metni."""
    a = ayarlar()
    depo = (a.get("github_depo") or "").strip().strip("/")
    dal = (a.get("github_dal") or "main").strip()
    if not depo:
        return "kapali (github_depo ayari bos)"
    if not re.match(r"^[\w.-]+/[\w.-]+$", depo):
        raise ValueError(f"github_depo gecersiz: {depo}")
    # raw.githubusercontent.com dal adresini ~5 dk onbellekte tutar (yeni surum gec gorunur).
    # Dalin en son commit'ini GitHub API'den alip o commit'e sabitlenmis adresten indiririz: hep en guncel.
    ref = dal
    try:
        istek = urllib.request.Request(f"https://api.github.com/repos/{depo}/commits/{dal}",
                                       headers={"User-Agent": "BidikStudyo", "Accept": "application/vnd.github.sha"})
        with urllib.request.urlopen(istek, timeout=20) as r:
            sha = r.read().decode().strip()
        if re.fullmatch(r"[0-9a-f]{40}", sha):
            ref = sha
    except Exception as e:   # API sinirina takilirsa dal adresiyle devam
        print("GitHub API'den son commit alinamadi:", str(e)[:120])
    taban = f"https://raw.githubusercontent.com/{depo}/{ref}/"
    with _KILIT:
        man = json.loads(_indir(taban + "surum.json").decode("utf-8"))
        uzak = str(man.get("surum", "0"))
        if _sayi(uzak) <= _sayi(_kurulu_surum()):
            return f"guncel (v{_kurulu_surum()})"
        if _sayi(uzak) <= _sayi(_bekleyen_surum()):
            return f"v{uzak} indirildi, 'Simdi guncelle' bekleniyor"
        dosyalar = man.get("dosyalar") or {}
        if not isinstance(dosyalar, dict):
            raise ValueError("surum.json 'dosyalar' alani bozuk")
        gecici = GUNCELLEME + ".indiriliyor"
        shutil.rmtree(gecici, ignore_errors=True)
        adet = 0
        for goreli, beklenen in sorted(dosyalar.items()):
            if (not _GECERLI_YOL.match(goreli) or ".." in goreli or goreli == "program/surum.txt"
                    or "__pycache__" in goreli):
                print("GitHub kanali: atlanan yol", goreli)
                continue
            if _yerel_sha(goreli) == beklenen:
                continue   # zaten ayni
            veri = _indir(taban + "/".join(urllib.request.quote(p) for p in goreli.split("/")))
            if _sha(veri) != beklenen:
                shutil.rmtree(gecici, ignore_errors=True)
                raise ValueError(f"{goreli} dogrulanamadi (dosya yarim inmis olabilir); sonra tekrar denenecek")
            hedef = os.path.join(gecici, *goreli.split("/"))
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            with open(hedef, "wb") as f:
                f.write(veri)
            adet += 1
        os.makedirs(gecici, exist_ok=True)
        shutil.rmtree(GUNCELLEME, ignore_errors=True)
        os.replace(gecici, GUNCELLEME)
        bilgi = {"surum": uzak, "tarih": man.get("tarih", ""), "notlar": man.get("notlar", []),
                 "kaynak": "github"}
        with open(os.path.join(GUNCELLEME, "surum.json"), "w", encoding="utf-8") as f:   # EN SON
            json.dump(bilgi, f, ensure_ascii=False, indent=2)
        print(f"GitHub kanali: v{uzak} indirildi ({adet} dosya)")
        return f"v{uzak} indirildi ({adet} dosya), 'Simdi guncelle' bekleniyor"


def _dongu():
    time.sleep(ILK_BEKLEME)
    while True:
        try:
            DURUM["sonuc"] = kontrol_et()
            DURUM["hata"] = ""
        except urllib.error.HTTPError as e:
            DURUM["hata"] = f"GitHub {e.code}" + (" (depo/dal bulunamadi ya da surum.json yok)" if e.code == 404 else "")
        except Exception as e:   # internet yok vb.: sessizce sonra tekrar dene
            DURUM["hata"] = str(e)[:200]
        DURUM["son_kontrol"] = time.strftime("%Y-%m-%d %H:%M")
        if DURUM["hata"]:
            print("GitHub kanali:", DURUM["hata"])
        time.sleep(KONTROL_ARALIGI)


def baslat():
    threading.Thread(target=_dongu, daemon=True, name="github_kanal").start()


def durum_metni():
    a = ayarlar()
    return (f"GitHub kanali: {a.get('github_depo') or 'kapali'} | son kontrol: {DURUM['son_kontrol'] or '-'}"
            f" | {DURUM['sonuc']}" + (f" | hata: {DURUM['hata']}" if DURUM["hata"] else ""))
