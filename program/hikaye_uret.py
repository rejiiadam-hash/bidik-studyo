"""
Bidik Hikayeleri: 2-3 dakikalik, yatay (1920x1080) ogretici cizgi film bolumleri.

Bolum (JSON) formati (hikaye_motoru.py uretir):
{
  "baslik": "Ay Neden Sekil Degistirir?", "alan": "uzay", "konu": "ay evreleri", "kostum": "astronot" (istege bagli),
  "bolumler": [
    {"ad": "Kaybolan Ay", "tema": "burclar", "arka_no": 3,
     "satirlar": [
        {"kim": "bidik" | "bilge", "metin": "...", "ifade": "saskin", "kol": "kollar_havada",
         "kart": {"buyuk": "29,5", "alt": "GÜN", "renk": "mavi"}}       # kart istege bagli
     ]}
  ],
  "soru": {"metin": "Ay'in isigi nereden gelir?", "secenekler": ["...", "...", "..."], "dogru": 1},
  "ozet": ["...", "...", "..."],
  "aciklama": "...", "hashtagler": [...], "etiketler": [...]
}
Bidik'in sesi Ahmet, Bilge'nin sesi Emel. Ses yoksa (sesli=False) sessiz + altyazili uretilir.
"""
import json, math, os, shutil, subprocess, tempfile, wave, struct

from PIL import Image, ImageDraw, ImageFont

import arka_planlar
from bilge import ciz_bilge, TEMA_AKSESUAR
from karakter import ciz_bidik, IFADELER, KOL_POZLARI
from kostumler import KOSTUMLER, kostum_sec
from ortak import FONT, ffmpeg

W, H, SS, FPS = 1920, 1080, 2, 24
LACI = (35, 37, 58)
SARI = (255, 196, 30)
MOR = (120, 98, 178)
YESIL = (60, 170, 100)
KIRMIZI = (230, 57, 70)
RENKLER = {"mavi": (70, 140, 230), "kirmizi": KIRMIZI, "yesil": YESIL, "mor": (150, 90, 200),
           "turuncu": (245, 140, 30), "pembe": (240, 110, 160)}
SES_BIDIK = "tr-TR-AhmetNeural"
SES_BILGE = "tr-TR-EmelNeural"
SERI_ADI = "BIDIK HİKÂYELERİ"

BIDIK_X, BILGE_X, AYAK_Y = 350, 1570, 1015
OLCEK = 1.12
ALTYAZI_Y = 955


def _font(px):
    return ImageFont.truetype(FONT, max(8, int(px * SS)))


def _yay(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _satirlar(d, metin, font, maks):
    satir, mevcut = [], ""
    for k in metin.split():
        dene = (mevcut + " " + k).strip()
        if d.textlength(dene, font=font) <= maks or not mevcut:
            mevcut = dene
        else:
            satir.append(mevcut)
            mevcut = k
    satir.append(mevcut)
    return satir


def _sigdir(d, metin, px, maks):
    while px > 14 and d.textlength(metin, font=_font(px)) > maks:
        px -= 2
    return _font(px)


# --- dogrulama --------------------------------------------------------------------------------
def dogrula(b):
    h = []
    bol = b.get("bolumler") or []
    if not 2 <= len(bol) <= 7:
        h.append("2-7 bolum olmali")
    satir_sayisi = 0
    for i, bo in enumerate(bol):
        if not bo.get("ad"):
            h.append(f"bolum {i + 1}: ad yok")
        for j, s in enumerate(bo.get("satirlar") or []):
            satir_sayisi += 1
            if s.get("kim") not in ("bidik", "bilge"):
                h.append(f"bolum {i + 1} satir {j + 1}: kim bidik/bilge olmali")
            if not s.get("metin") or len(s["metin"]) > 160:
                h.append(f"bolum {i + 1} satir {j + 1}: metin bos ya da 160 karakterden uzun")
    if not 12 <= satir_sayisi <= 60:
        h.append(f"toplam {satir_sayisi} satir (12-60 olmali)")
    q = b.get("soru") or {}
    if q and (len(q.get("secenekler") or []) != 3 or q.get("dogru") not in (0, 1, 2)):
        h.append("soru: 3 secenek ve 0-2 arasi dogru olmali")
    if b.get("kostum") and b["kostum"] not in KOSTUMLER:
        h.append("gecersiz kostum")
    return h


# --- zaman cizelgesi --------------------------------------------------------------------------
def _parca(tur, **k):
    k["tur"] = tur
    return k


TEMA_KOSTUM = {v: k for k, v in arka_planlar.KOSTUM_TEMA.items()}   # uzay -> astronot ...


def giyim(b):
    """Her kisim icin (Bidik'in kostumu, Bilge'nin aksesuari): kismin arka plan temasina gore degisir.
    Kisimda "kostum" yazilmissa o kullanilir; 'genel' temada bolumun konusuna uygun kostum."""
    ana = b.get("kostum") if b.get("kostum") in KOSTUMLER else kostum_sec(b.get("alan", ""), b.get("konu", ""))
    sonuc = []
    for bo in b["bolumler"]:
        tema = bo.get("tema") if bo.get("tema") in arka_planlar.TEMALAR else "genel"
        kos = bo.get("kostum") if bo.get("kostum") in KOSTUMLER else (TEMA_KOSTUM.get(tema) or ana)
        sonuc.append((kos, TEMA_AKSESUAR.get(tema, "mezuniyet")))
    return sonuc


def cizelge(b):
    """Bolumu sirali parcalara cevirir; her parcanin konusmacisi ve metni (seslendirilecekse) olur."""
    p = [_parca("kapak", kim="bidik", metin=f"Bıdık Hikâyeleri! Bugün: {b['baslik']}", sure=3.6, bolum=0)]
    for i, bo in enumerate(b["bolumler"]):
        p.append(_parca("bolum", ad=bo["ad"], no=i + 1, sure=1.7, bolum=i))
        for s in bo["satirlar"]:
            p.append(_parca("satir", kim=s["kim"], metin=s["metin"], ifade=s.get("ifade"), kol=s.get("kol"),
                            kart=s.get("kart"), bolum=i, sure=None))
    son_bolum = len(b["bolumler"]) - 1
    q = b.get("soru")
    if q:
        p.append(_parca("soru", kim="bilge", metin="Hadi bakalım bir soru: " + q["metin"], soru=q, bolum=son_bolum))
        p.append(_parca("sayac", soru=q, sure=4.0, bolum=son_bolum))
        p.append(_parca("cevap", kim="bidik", metin=f"Doğru cevap: {q['secenekler'][q['dogru']]}!", soru=q, bolum=son_bolum))
    if b.get("ozet"):
        p.append(_parca("ozet", kim="bilge", metin="Bugün öğrendiklerimiz: " + " ".join(b["ozet"]), ozet=b["ozet"], bolum=son_bolum))
    p.append(_parca("kapanis", kim="bidik", metin="Bir sonraki hikâyede görüşmek üzere! Abone olmayı unutma!",
                    bolum=son_bolum))
    return p


def _zarf(yol):
    with wave.open(yol) as w:
        sr, n = w.getframerate(), w.getnframes()
        veri = struct.unpack(f"<{n}h", w.readframes(n))
    adim = max(1, sr // FPS)
    z = []
    for i in range(0, n, adim):
        parca = veri[i:i + adim]
        if parca:
            z.append(math.sqrt(sum(x * x for x in parca) / len(parca)))
    tepe = max(z) if z else 1
    return [min(1.0, v / (tepe or 1) * 1.4) for v in z], n / sr


# --- cizim parcalari -------------------------------------------------------------------------
def _altyazi(d, metin, kim, giris):
    if not metin:
        return
    f = _font(40)
    maks = 760 * SS
    sat = _satirlar(d, metin, f, maks)[:3]
    sh = 40 * 1.3 * SS
    tw = max(d.textlength(s, font=f) for s in sat)
    cx = W / 2 * SS
    alt = (ALTYAZI_Y + 50) * SS
    ust = alt - len(sat) * sh - 34 * SS
    kenar = SARI if kim == "bidik" else MOR
    a = _yay(giris)
    dy = (1 - a) * 20 * SS
    d.rounded_rectangle([cx - tw / 2 - 34 * SS, ust + dy, cx + tw / 2 + 34 * SS, alt + dy], radius=30 * SS,
                        fill=LACI, outline=kenar, width=6 * SS)
    ad = "Bıdık" if kim == "bidik" else "Bilge"
    fa = _font(26)
    aw = d.textlength(ad, font=fa) + 30 * SS
    d.rounded_rectangle([cx - tw / 2 - 20 * SS, ust - 22 * SS + dy, cx - tw / 2 - 20 * SS + aw, ust + 18 * SS + dy],
                        radius=18 * SS, fill=kenar)
    d.text((cx - tw / 2 - 20 * SS + aw / 2, ust - 2 * SS + dy), ad, font=fa, fill=LACI, anchor="mm")
    for i, s in enumerate(sat):
        d.text((cx, ust + 17 * SS + sh * (i + 0.5) + dy), s, font=f, fill=(255, 255, 255), anchor="mm")


def _kart(d, kart, giris):
    renk = RENKLER.get(kart.get("renk", "mavi"), RENKLER["mavi"])
    o = 0.6 + 0.4 * _yay(giris)
    cx, cy = W / 2 * SS, 330 * SS
    kw, kh = 640 * SS * o, 270 * SS * o
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2 + 10 * SS, cx + kw / 2, cy + kh / 2 + 10 * SS], radius=int(40 * SS * o), fill=(0, 0, 0, 60))
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2, cx + kw / 2, cy + kh / 2], radius=int(40 * SS * o),
                        fill=(255, 255, 255), outline=LACI, width=7 * SS)
    buyuk, alt = str(kart.get("buyuk", "")), str(kart.get("alt", ""))
    d.text((cx, cy - kh * 0.12), buyuk, font=_sigdir(d, buyuk, 110 * o, kw * 0.86), fill=renk, anchor="mm")
    d.text((cx, cy + kh * 0.30), alt, font=_sigdir(d, alt, 44 * o, kw * 0.9), fill=LACI, anchor="mm")


def _serit(d, ust_yazi, alt_yazi, giris, cikis=1.0):
    """Kapak / bolum basligi seridi (ortada)."""
    a = _yay(giris) * cikis
    if a <= 0.01:
        return
    cx, cy = W / 2 * SS, 300 * SS
    f1, f2 = _font(34), _sigdir(d, alt_yazi, 76, 1300 * SS)
    tw = max(d.textlength(alt_yazi, font=f2), d.textlength(ust_yazi, font=f1)) + 120 * SS
    kw = tw * (0.7 + 0.3 * a)
    d.rounded_rectangle([cx - kw / 2, cy - 105 * SS + 12 * SS, cx + kw / 2, cy + 105 * SS + 12 * SS], radius=50 * SS, fill=(210, 150, 10))
    d.rounded_rectangle([cx - kw / 2, cy - 105 * SS, cx + kw / 2, cy + 105 * SS], radius=50 * SS, fill=SARI, outline=LACI, width=7 * SS)
    d.text((cx, cy - 45 * SS), ust_yazi, font=f1, fill=(120, 60, 20), anchor="mm")
    d.text((cx, cy + 25 * SS), alt_yazi, font=f2, fill=LACI, anchor="mm")


def _soru_kutusu(d, q, kalan=None, cevap=False):
    cx = W / 2 * SS
    f = _sigdir(d, q["metin"], 50, 1200 * SS)
    d.rounded_rectangle([cx - 680 * SS, 90 * SS, cx + 680 * SS, 210 * SS], radius=40 * SS, fill=LACI, outline=MOR, width=6 * SS)
    d.text((cx, 150 * SS), q["metin"], font=f, fill=(255, 255, 255), anchor="mm")
    for i, sec in enumerate(q["secenekler"]):
        y = (290 + i * 120) * SS
        dogru = cevap and i == q["dogru"]
        soluk = cevap and not dogru
        dolgu = (205, 240, 215) if dogru else ((235, 232, 226) if soluk else (255, 255, 255))
        d.rounded_rectangle([cx - 390 * SS, y - 46 * SS, cx + 390 * SS, y + 46 * SS], radius=46 * SS, fill=dolgu,
                            outline=YESIL if dogru else LACI, width=(9 if dogru else 6) * SS)
        harf = "ABC"[i]
        d.ellipse([cx - 375 * SS, y - 36 * SS, cx - 303 * SS, y + 36 * SS], fill=MOR if not dogru else YESIL)
        d.text((cx - 339 * SS, y), harf, font=_font(40), fill=(255, 255, 255), anchor="mm")
        d.text((cx + 30 * SS, y), sec, font=_sigdir(d, sec, 44, 600 * SS), fill=(150, 150, 150) if soluk else LACI, anchor="mm")
        if dogru:
            d.text((cx + 345 * SS, y), "✓", font=_font(56), fill=YESIL, anchor="mm")
    if kalan is not None:
        r = 52 * SS
        x0, y0 = cx + 500 * SS, 410 * SS
        d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=(255, 255, 255), outline=LACI, width=6 * SS)
        d.arc([x0 - r + 8 * SS, y0 - r + 8 * SS, x0 + r - 8 * SS, y0 + r - 8 * SS], -90, -90 + 360 * (kalan % 1 or 1),
              fill=KIRMIZI, width=10 * SS)
        d.text((x0, y0), str(math.ceil(kalan)), font=_font(52), fill=LACI, anchor="mm")


def _ozet_karti(d, maddeler, t):
    cx = W / 2 * SS
    d.rounded_rectangle([cx - 470 * SS, 60 * SS, cx + 470 * SS, (140 + 92 * len(maddeler)) * SS], radius=40 * SS,
                        fill=(255, 255, 255), outline=LACI, width=7 * SS)
    d.text((cx, 108 * SS), "Bugün öğrendiklerimiz", font=_font(46), fill=MOR, anchor="mm")
    for i, m in enumerate(maddeler):
        a = _yay((t - 0.6 - i * 0.9) / 0.4)
        if a <= 0:
            continue
        y = (185 + i * 92) * SS
        d.ellipse([cx - 440 * SS, y - 24 * SS, cx - 392 * SS, y + 24 * SS], fill=SARI, outline=LACI, width=4 * SS)
        d.text((cx - 416 * SS, y), str(i + 1), font=_font(30), fill=LACI, anchor="mm")
        d.text((cx - 370 * SS + (1 - a) * 40 * SS, y), m, font=_sigdir(d, m, 36, 820 * SS), fill=LACI, anchor="lm")


def _abone(d, t):
    a = _yay(t / 0.5)
    if a <= 0.01:
        return
    cx, cy = W / 2 * SS, 330 * SS
    kw, kh = 620 * SS * a, 150 * SS * a
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2, cx + kw / 2, cy + kh / 2], radius=int(75 * SS * a),
                        fill=(230, 33, 23) if t < 1.6 else (225, 225, 228))
    yazi = "ABONE OL" if t < 1.6 else "ABONE OLUNDU ✓"
    d.text((cx, cy), yazi, font=_sigdir(d, yazi, 60 * a, kw * 0.85), fill=(255, 255, 255) if t < 1.6 else (90, 90, 98), anchor="mm")


# --- uretim -----------------------------------------------------------------------------------
def uret(bolum_yolu, cikti=None, sesli=None, ilerleme=None):
    ilerle = ilerleme or (lambda y, m: None)
    with open(bolum_yolu, encoding="utf-8") as f:
        b = json.load(f)
    h = dogrula(b)
    if h:
        raise ValueError("Bolum gecersiz: " + "; ".join(h))
    from video_uret import ses_var_mi, seslendir, SesHatasi
    sesli = ses_var_mi() if sesli is None else sesli
    cikti = cikti or os.path.splitext(bolum_yolu)[0] + ".mp4"
    kostum = b.get("kostum") if b.get("kostum") in KOSTUMLER else kostum_sec(b.get("alan", ""), b.get("konu", ""))
    parcalar = cizelge(b)
    gecici = tempfile.mkdtemp(prefix="hikaye_")
    try:
        # 1) sesler: basarisiz olanlar icin bekleyip tekrar turlari (ses servisi bazen gecici olarak cevap vermez)
        konusan = [p for p in parcalar if p.get("metin") and p.get("kim")]
        if not sesli:
            for p in konusan:
                p["sure"] = p.get("sure") or max(2.2, len(p["metin"]) / 14 + 0.8)
        else:
            import time
            from ortak import ayarlar as _ayar
            bekleyen = list(range(len(konusan)))
            for tur, bekle in enumerate([0] + [45, 90, 150][:max(0, int(_ayar().get("ses_ek_tur", 2)))]):
                if not bekleyen:
                    break
                if bekle:
                    ilerle(None, f"Ses servisi cevap vermiyor; {bekle} sn sonra eksik {len(bekleyen)} satır tekrar denenecek")
                    time.sleep(bekle)
                kalan, ust_uste = [], 0
                for sira, n in enumerate(bekleyen):
                    p = konusan[n]
                    if ust_uste >= 2:          # servis kapali gorunuyor: bu turu bitir, sonra tekrar dene
                        kalan += bekleyen[sira:]
                        break
                    ilerle(2 + int(28 * (len(konusan) - len(bekleyen) + sira) / max(1, len(konusan))),
                           f"Seslendirme {n + 1}/{len(konusan)}" + (f" (tekrar turu {tur})" if tur else ""))
                    wav = os.path.join(gecici, f"s{n}.wav")
                    try:
                        if seslendir(p["metin"], wav, ses=SES_BIDIK if p["kim"] == "bidik" else SES_BILGE) == "yeni":
                            time.sleep(1.5)   # ses servisini art arda istekle bogmamak icin kisa ara
                    except SesHatasi as e:
                        print("Hikaye seslendirme basarisiz:", e)
                        kalan.append(n)
                        ust_uste += 1
                        continue
                    ust_uste = 0
                    p["wav"] = wav
                    p["zarf"], uzunluk = _zarf(wav)
                    p["sure"] = max(p.get("sure") or 0, uzunluk + 0.45)
                bekleyen = kalan
            if bekleyen:
                raise SesHatasi(f"Ses servisi {len(bekleyen)} satıra cevap vermedi. Başarılı sesler kaydedildi; "
                                "birkaç dakika sonra 'Videoyu üret'e tekrar basınca sadece eksikler istenecek.")
        for p in parcalar:
            if p["tur"] == "ozet":
                p["sure"] = max(p["sure"], 0.9 * len(p["ozet"]) + 2.2)
            if p["tur"] == "kapanis":
                p["sure"] = max(p["sure"], 3.2)
        # 2) arka planlar (her bolum icin bir kez)
        arkalar = {}
        for i, bo in enumerate(b["bolumler"]):
            tema = bo.get("tema") if bo.get("tema") in arka_planlar.TEMALAR else arka_planlar.tema_bul(b.get("alan", ""), b.get("konu", ""), kostum)
            no = bo.get("arka_no") if isinstance(bo.get("arka_no"), int) else i
            arkalar[i] = arka_planlar.ciz(tema, no, W * SS, H * SS, k=SS)
        # 3) kareler -> ffmpeg (ara dosya yok)
        toplam = sum(int(round(p["sure"] * FPS)) for p in parcalar)
        sessiz_mp4 = os.path.join(gecici, "goruntu.mp4")
        ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "20", "-pix_fmt", "yuv420p", sessiz_mp4], stdin=subprocess.PIPE)
        giy = giyim(b)
        n, onceki_bolum = 0, 0
        zamanlar = [(0.0, "Giriş")]
        for pi, p in enumerate(parcalar):
            kare_sayisi = int(round(p["sure"] * FPS))
            if p["tur"] == "bolum":
                zamanlar.append((n / FPS, p["ad"]))
            elif p["tur"] == "soru":
                zamanlar.append((n / FPS, "Soru zamanı"))
            bolum = p.get("bolum", 0)
            for k in range(kare_sayisi):
                t = k / FPS
                if bolum != onceki_bolum and p["tur"] == "bolum" and k < 12:
                    img = Image.blend(arkalar[onceki_bolum], arkalar[bolum], k / 12)
                else:
                    img = arkalar[bolum].copy()
                d = ImageDraw.Draw(img, "RGBA")
                degisim = p["tur"] == "bolum" and bolum != onceki_bolum and giy[bolum] != giy[onceki_bolum]
                simdiki = giy[onceki_bolum] if (degisim and k < 6) else giy[bolum]
                duman = max(0.0, 1 - abs(k - 6) / 6) if (degisim and k < 12) else 0.0
                _kare(img, d, p, k, t, n, simdiki, duman)
                ff.stdin.write(img.reduce(SS).tobytes())
                n += 1
                if n % 24 == 0:
                    ilerle(30 + int(62 * n / toplam), f"Çizim: {n}/{toplam} kare")
            if p["tur"] == "bolum":
                onceki_bolum = bolum
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg goruntuyu yazamadi")
        # 4) ses izi
        ilerle(94, "Ses ve görüntü birleştiriliyor")
        if sesli:
            ses_wav = os.path.join(gecici, "ses.wav")
            _ses_izi(parcalar, ses_wav)
            subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", sessiz_mp4, "-i", ses_wav, "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "160k", "-shortest", cikti], check=True)
        else:
            shutil.copyfile(sessiz_mp4, cikti)
        ilerle(100, "Hikâye videosu hazır")
        return cikti, n / FPS, zamanlar
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _ses_izi(parcalar, hedef):
    sr = 24000
    with wave.open(hedef, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sr)
        for p in parcalar:
            kare = int(round(p["sure"] * FPS))
            ornek = int(kare / FPS * sr)
            veri = b""
            if p.get("wav"):
                with wave.open(p["wav"]) as w:
                    veri = w.readframes(w.getnframes())[:ornek * 2]
            out.writeframes(veri + b"\x00\x00" * (ornek - len(veri) // 2))


def _kare(img, d, p, k, t, n, giy, duman=0.0):
    kostum, aksesuar = giy
    tur = p["tur"]
    konusan = p.get("kim") if p.get("metin") else None
    zarf = p.get("zarf")
    agiz = 0.0
    if konusan:
        if zarf:
            agiz = zarf[k] if k < len(zarf) else 0.0
        elif t < p["sure"] - 0.5:
            agiz = (0.5 + 0.5 * math.sin(t * 2 * math.pi * 4.2)) * 0.85
    kirp_bidik = 1.0 if (n % 70) in (0, 1) else 0.0
    kirp_bilge = 1.0 if ((n + 33) % 85) in (0, 1) else 0.0
    # karakterler
    b_ifade = p.get("ifade") if (konusan == "bidik" and p.get("ifade") in IFADELER) else "mutlu" if tur in ("kapak", "cevap", "kapanis") else "normal"
    b_kol = p.get("kol") if (konusan == "bidik" and p.get("kol") in KOL_POZLARI) else ("el_salla" if tur in ("kapak", "kapanis") else ("kollar_havada" if tur == "cevap" else "serbest"))
    b_zip = (8 + 6 * math.sin(t * 7)) if konusan == "bidik" else 0
    if tur == "cevap":
        b_zip = abs(math.sin(t * 6)) * 40
    ciz_bidik(img, x=BIDIK_X * SS, y=AYAK_Y * SS, olcek=OLCEK * SS, ifade=b_ifade, kol=b_kol,
              agiz=agiz if konusan == "bidik" else 0.0, kirp=kirp_bidik, ziplama=b_zip + 3 * math.sin(t * 2.4),
              bakis=(0.8, 0.0) if konusan == "bilge" else (0.3, -0.1), kol_faz=t * 1.4, kostum=kostum)
    g_ifade = p.get("ifade") if (konusan == "bilge" and p.get("ifade") in ("normal", "mutlu", "saskin", "dusunceli")) else ("mutlu" if tur in ("kapak", "cevap", "kapanis", "ozet") else "normal")
    ciz_bilge(img, BILGE_X * SS, AYAK_Y * SS, OLCEK * SS, ifade=g_ifade,
              agiz=agiz if konusan == "bilge" else 0.0, kirp=kirp_bilge,
              bakis=(-0.9, 0.0) if konusan == "bidik" else (-0.3, 0.1),
              kanat=(0.5 + 0.5 * math.sin(t * 5)) * (0.6 if konusan == "bilge" else 0.0),
              ziplama=(6 + 5 * math.sin(t * 6)) if konusan == "bilge" else 2 * math.sin(t * 2), aksesuar=aksesuar)
    if duman > 0:   # kisim degisince kiyafet degisimi: "puf" dumani
        from girisler import _duman
        for cx in (BIDIK_X, BILGE_X):
            _duman(img, cx * SS, (AYAK_Y - 260) * SS, 150 * SS * OLCEK, duman)
        d = ImageDraw.Draw(img, "RGBA")
    # ust katman
    if tur == "kapak":
        _serit(d, SERI_ADI, p["metin"].split("Bugün: ", 1)[-1], t / 0.6, min(1.0, (p["sure"] - t) / 0.4))
    elif tur == "bolum":
        _serit(d, f"{p['no']}. BÖLÜM", p["ad"], t / 0.5, min(1.0, (p["sure"] - t) / 0.3))
    elif tur == "satir" and p.get("kart"):
        _kart(d, p["kart"], t / 0.35)
    elif tur in ("soru", "sayac"):
        _soru_kutusu(d, p["soru"], kalan=(p["sure"] - t) if tur == "sayac" else None)
    elif tur == "cevap":
        _soru_kutusu(d, p["soru"], cevap=True)
    elif tur == "ozet":
        _ozet_karti(d, p["ozet"], t)
    elif tur == "kapanis":
        _abone(d, t)
    if p.get("metin") and tur not in ("kapak",):
        _altyazi(d, p["metin"] if tur != "ozet" else "Bugün öğrendiklerimiz…", konusan, t / 0.25)


def bolum_listesi(zamanlar):
    """YouTube aciklamasi icin bolum (chapter) satirlari: ilk 0:00, her biri en az 10 sn."""
    satirlar, son = [], -100.0
    for t, ad in zamanlar:
        if t - son < 10 and satirlar:
            continue
        satirlar.append(f"{int(t) // 60}:{int(t) % 60:02d} {ad}")
        son = t
    return satirlar if len(satirlar) >= 3 else []


def kapak_resmi(b, yol):
    """1280x720 YouTube kapak gorseli: ilk kismin arka plani, iki karakter, buyuk baslik."""
    kostum, aksesuar = giyim(b)[0]
    bo = b["bolumler"][0]
    tema = bo.get("tema") if bo.get("tema") in arka_planlar.TEMALAR else "genel"
    img = arka_planlar.ciz(tema, bo.get("arka_no", 0) or 0, W * SS, H * SS, k=SS)
    ciz_bidik(img, x=330 * SS, y=1060 * SS, olcek=1.45 * SS, ifade="saskin", kol="kollar_havada", kostum=kostum)
    ciz_bilge(img, 1600 * SS, 1060 * SS, 1.35 * SS, ifade="mutlu", agiz=0.5, kanat=0.6, aksesuar=aksesuar)
    d = ImageDraw.Draw(img)
    baslik = b.get("baslik", "")
    f = _font(96)
    sat = _satirlar(d, baslik, f, 1150 * SS)[:3]
    while len(_satirlar(d, baslik, f, 1150 * SS)) > 3 and f.size > 50 * SS:
        f = ImageFont.truetype(FONT, f.size - 6 * SS)
        sat = _satirlar(d, baslik, f, 1150 * SS)[:3]
    sh = f.size * 1.18
    ust = 420 * SS - len(sat) * sh / 2
    for i, s in enumerate(sat):
        d.text((W / 2 * SS, ust + sh * (i + 0.5)), s, font=f, fill=(255, 255, 255), anchor="mm",
               stroke_width=12 * SS, stroke_fill=LACI)
    fs = _font(40)
    tw = d.textlength(SERI_ADI, font=fs)
    d.rounded_rectangle([W / 2 * SS - tw / 2 - 30 * SS, 70 * SS, W / 2 * SS + tw / 2 + 30 * SS, 140 * SS], radius=35 * SS,
                        fill=SARI, outline=LACI, width=6 * SS)
    d.text((W / 2 * SS, 105 * SS), SERI_ADI, font=fs, fill=LACI, anchor="mm")
    img.resize((1280, 720), Image.LANCZOS).save(yol, "PNG")


if __name__ == "__main__":
    import sys
    print(uret(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sesli=False))
