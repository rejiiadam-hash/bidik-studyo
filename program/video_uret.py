"""
Senaryo (JSON) -> 1080x1920 Shorts videosu.

Kullanim:
    python video_uret.py senaryo.json [cikti.mp4]

Senaryo formati (senaryo_motoru.py bunu uretir):
{
  "baslik": "Ahtapotun 3 kalbi var!",
  "alan": "hayvanlar",
  "konu": "ahtapot kalpleri",
  "aciklama": "...", "etiketler": ["ahtapot", "bilgi", ...],
  "dogrulama_notu": "Bilginin dayanagi (onay icin)",
  "sahneler": [
    {"sure": 2.5, "ifade": "saskin", "kol": "kollar_havada", "ziplama": 60,
     "replik": "Bir ahtapotun kac kalbi var?", "konusuyor": true,
     "kart": {"buyuk": "3", "alt": "KALP", "ikon": "kalp", "adet": 3, "renk": "mavi"}}
  ]
}
edge-tts kuruluysa (pip install edge-tts) replikler seslendirilir ve agiz sese
gore oynar; kurulu degilse video sessiz + altyazili uretilir.
"""
import json, math, os, shutil, subprocess, sys, tempfile, wave, struct, asyncio
from PIL import Image, ImageDraw, ImageFont
from karakter import ciz_bidik, IFADELER, KOL_POZLARI
from kostumler import KOSTUMLER, ust_boy
import arka_planlar
from ortak import FONT, ffmpeg, komut, KOK

FPS = 30
W, H, SS = 1080, 1920, 2
ARKA = (250, 244, 230)
ZEMIN = (232, 220, 196)
LACI = (35, 37, 58)
SES = "tr-TR-AhmetNeural"   # Bidik'in sabit sesi
RENKLER = {"mavi": (70, 140, 230), "kirmizi": (230, 57, 70), "yesil": (60, 170, 100),
           "mor": (150, 90, 200), "turuncu": (245, 140, 30), "pembe": (240, 110, 160)}
IKONLAR = ["kalp", "yildiz", "soru", "unlem", "damla"]
SINIR_SURE = (10.0, 20.0)


# --- dogrulama ---------------------------------------------------------------
def dogrula(sen):
    hatalar = []
    sahneler = sen.get("sahneler") or []
    if not 3 <= len(sahneler) <= 8:
        hatalar.append("3-8 sahne olmali")
    toplam = 0
    for i, s in enumerate(sahneler):
        if s.get("ifade") not in IFADELER:
            hatalar.append(f"sahne {i+1}: gecersiz ifade {s.get('ifade')}")
        if s.get("kol", "serbest") not in KOL_POZLARI:
            hatalar.append(f"sahne {i+1}: gecersiz kol {s.get('kol')}")
        if len(s.get("replik", "")) > 70:
            hatalar.append(f"sahne {i+1}: replik 70 karakterden uzun")
        k = s.get("kart")
        if k and k.get("ikon") and k["ikon"] not in IKONLAR:
            hatalar.append(f"sahne {i+1}: gecersiz ikon {k['ikon']}")
        toplam += float(s.get("sure", 0))
    if not SINIR_SURE[0] <= toplam <= SINIR_SURE[1]:
        hatalar.append(f"toplam sure {toplam:.1f} sn ({SINIR_SURE[0]:.0f}-{SINIR_SURE[1]:.0f} olmali)")
    if sen.get("kostum") and sen["kostum"] not in KOSTUMLER:
        hatalar.append(f"gecersiz kostum {sen['kostum']}")
    return hatalar


SON_URETIM = {}       # son videonun ek bilgileri (arka plan adi...) - panel meta'ya yazar
ALTYAZI_ALT = 410      # altyazi kutusunun alt siniri (px): Bidik'in tepesi bunun altinda kalmali
KART_ALT = 805         # bilgi karti / son cagri kartinin alt siniri


def sigan_olcek(istenen, ust_px, ziplama, alt_sinir):
    """Bidik'i (kostum + percem + ziplama dahil) verilen cizginin altina sigdiran en buyuk olcek."""
    zemin = H * 0.80
    return min(istenen, (zemin - alt_sinir) / (435 + ust_px + max(0.0, ziplama)))


# --- ses ---------------------------------------------------------------------
def ses_var_mi():
    try:
        import edge_tts  # noqa
        ffmpeg()
        return True
    except Exception:
        return False


class SesHatasi(RuntimeError):
    """Bir replik tum denemelere ragmen seslendirilemedi."""
    pass


SES_ONBELLEK = os.path.join(KOK, "ses_onbellek")
PROSODI = {"rate": "+8%", "pitch": "+25Hz"}
# prosodi'siz (duz) uretimde Bidik'in sesini taklit etmek icin: sesi incelt + hafif hizlandir
DUZ_SESE_FILTRE = "asetrate=24000*1.15,aresample=24000,atempo=0.94"
KIRP = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse")


def _tts_mp3(metin, mp3, prosodi=True):
    import edge_tts
    if os.path.exists(mp3):
        os.remove(mp3)
    ayar = PROSODI if prosodi else {}
    asyncio.run(edge_tts.Communicate(metin, SES, **ayar).save(mp3))
    if not os.path.exists(mp3) or os.path.getsize(mp3) < 1000:
        raise RuntimeError("bos ses dosyasi geldi")


def _wav_yap(mp3, wav, ek_filtre=None):
    filtre = (ek_filtre + "," if ek_filtre else "") + KIRP
    komut([ffmpeg(), "-y", "-loglevel", "error", "-i", mp3, "-af", filtre, "-ac", "1", "-ar", "24000", wav])


def _cumleler(metin):
    import re
    parca = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", metin) if p.strip()]
    return parca if len(parca) > 1 else [p.strip() for p in re.split(r"[,;:]\s*", metin) if p.strip()]


def _ses_uret(metin, wav):
    """
    Sirayla dener (her basarisizlikta biraz daha uzun bekleyerek):
      1-2: normal (Bidik'in sesi)
      3-4: prosodi'siz istek + sesi bilgisayarda Bidik'e benzetme
      5-6: cumle cumle ayri istekler, sonra birlestirme
    """
    import time
    mp3 = wav + ".mp3"
    son_hata = None
    for deneme in range(6):
        try:
            if deneme < 2:
                _tts_mp3(metin, mp3, prosodi=True)
                _wav_yap(mp3, wav)
            elif deneme < 4:
                _tts_mp3(metin, mp3, prosodi=False)
                _wav_yap(mp3, wav, DUZ_SESE_FILTRE)
            else:
                parcalar = _cumleler(metin)
                if len(parcalar) < 2:
                    _tts_mp3(metin, mp3, prosodi=(deneme == 4))
                    _wav_yap(mp3, wav, None if deneme == 4 else DUZ_SESE_FILTRE)
                else:
                    liste = wav + ".liste.txt"
                    yollar = []
                    for k, p in enumerate(parcalar):
                        pm, pw = f"{wav}.{k}.mp3", f"{wav}.{k}.wav"
                        _tts_mp3(p, pm, prosodi=True)
                        _wav_yap(pm, pw)
                        os.remove(pm)
                        yollar.append(pw)
                        time.sleep(0.6)
                    with open(liste, "w", encoding="utf-8") as f:
                        f.writelines("file '" + y.replace(os.sep, "/") + "'\n" for y in yollar)
                    komut([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste, wav])
            if os.path.exists(mp3):
                os.remove(mp3)
            if deneme:
                print(f"Seslendirme {deneme + 1}. denemede basarili: {metin[:40]}")
            return
        except Exception as e:
            son_hata = e
            bekle = (2, 4, 6, 8, 10, 0)[deneme]
            print(f"Seslendirme denemesi {deneme + 1}/6 basarisiz ({e}); {bekle} sn sonra tekrar")
            time.sleep(bekle)
    raise SesHatasi(f"'{metin[:40]}' 6 denemede seslendirilemedi: {son_hata}")


def seslendir(metin, hedef_wav):
    """Onbellekte varsa oradan alir (tekrar istek yok); yoksa uretip onbellege koyar."""
    import hashlib
    os.makedirs(SES_ONBELLEK, exist_ok=True)
    anahtar = hashlib.sha1(f"{SES}|{PROSODI}|{KIRP}|{metin}".encode("utf-8")).hexdigest()[:20]
    onb = os.path.join(SES_ONBELLEK, anahtar + ".wav")
    if os.path.exists(onb) and os.path.getsize(onb) > 2000:
        shutil.copyfile(onb, hedef_wav)
        return
    _ses_uret(metin, hedef_wav)
    shutil.copyfile(hedef_wav, onb)


def wav_zarf(yol):
    """Her video karesi icin 0..1 ses siddeti (agiz acikligi)."""
    with wave.open(yol) as w:
        sr, n = w.getframerate(), w.getnframes()
        veri = struct.unpack(f"<{n}h", w.readframes(n))
    adim = sr // FPS
    zarf = []
    for i in range(0, n, adim):
        parca = veri[i:i + adim]
        if not parca:
            break
        rms = math.sqrt(sum(x * x for x in parca) / len(parca))
        zarf.append(rms)
    tepe = max(zarf) or 1
    return [min(1.0, (z / tepe) * 1.4) for z in zarf], n / sr


# --- cizim yardimcilari -------------------------------------------------------
def _font(px):
    return ImageFont.truetype(FONT, int(px * SS))


def satirlara_bol(d, metin, font, maks):
    satirlar, mevcut = [], ""
    for kelime in metin.split():
        deneme = (mevcut + " " + kelime).strip()
        if d.textlength(deneme, font=font) <= maks or not mevcut:
            mevcut = deneme
        else:
            satirlar.append(mevcut)
            mevcut = kelime
    satirlar.append(mevcut)
    return satirlar


def altyazi(d, metin, y=300, boyut=66):
    if not metin:
        return
    fb = _font(boyut)
    satirlar = satirlara_bol(d, metin, fb, (W - 160) * SS)
    sat_h, pad = boyut * 1.27 * SS, 36 * SS
    tw = max(d.textlength(s, font=fb) for s in satirlar)
    ust = y * SS - len(satirlar) * sat_h / 2
    d.rounded_rectangle([W * SS / 2 - tw / 2 - pad, ust - 26 * SS,
                         W * SS / 2 + tw / 2 + pad, ust + len(satirlar) * sat_h + 26 * SS],
                        radius=40 * SS, fill=LACI)
    for i, s in enumerate(satirlar):
        d.text((W * SS / 2, ust + sat_h * (i + 0.5)), s, font=fb, fill=(255, 255, 255), anchor="mm")


def ikon(d, tur, cx, cy, r, renk):
    if tur == "kalp":
        d.ellipse([cx - r, cy - r * 0.9, cx, cy + r * 0.1], fill=renk, outline=LACI, width=int(r * 0.12))
        d.ellipse([cx, cy - r * 0.9, cx + r, cy + r * 0.1], fill=renk, outline=LACI, width=int(r * 0.12))
        d.polygon([(cx - r * 0.97, cy - r * 0.25), (cx + r * 0.97, cy - r * 0.25), (cx, cy + r)], fill=renk)
        d.line([(cx - r * 0.97, cy - r * 0.25), (cx, cy + r), (cx + r * 0.97, cy - r * 0.25)],
               fill=LACI, width=int(r * 0.12), joint="curve")
    elif tur == "yildiz":
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=renk, outline=LACI, width=int(r * 0.1))
    elif tur == "damla":
        d.polygon([(cx, cy - r), (cx - r * 0.7, cy + r * 0.2), (cx + r * 0.7, cy + r * 0.2)], fill=renk)
        d.ellipse([cx - r * 0.7, cy - r * 0.3, cx + r * 0.7, cy + r * 0.9], fill=renk, outline=LACI, width=int(r * 0.1))
    else:  # soru / unlem
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=renk, outline=LACI, width=int(r * 0.1))
        d.text((cx, cy), "?" if tur == "soru" else "!", font=ImageFont.truetype(FONT, int(r * 1.4)),
               fill=(255, 255, 255), anchor="mm")


def bilgi_karti(d, kart, giris):
    """Ust-orta bolgede buyuk bilgi karti; giris 0..1 animasyon."""
    renk = RENKLER.get(kart.get("renk", "mavi"), RENKLER["mavi"])
    olc = 0.6 + 0.4 * min(1, giris) + 0.06 * math.sin(min(1, giris) * math.pi)
    cx, cy = W / 2 * SS, 640 * SS
    kw, kh = 760 * SS * olc, 300 * SS * olc
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2, cx + kw / 2, cy + kh / 2], radius=int(46 * SS * olc),
                        fill=(255, 255, 255), outline=LACI, width=int(8 * SS))
    adet = int(kart.get("adet", 0) or 0)
    tur = kart.get("ikon")
    buyuk = str(kart.get("buyuk", ""))
    alt = str(kart.get("alt", ""))
    if tur and adet:
        adet = min(adet, 6)
        r = 46 * SS * olc
        for i in range(adet):
            ix = cx + (i - (adet - 1) / 2) * r * 2.4
            ikon(d, tur, ix, cy - kh * 0.12, r, renk)
        d.text((cx, cy + kh * 0.30), (buyuk + " " + alt).strip(), font=_sigdir(d, (buyuk + " " + alt).strip(), 54 * olc, kw * 0.9), fill=LACI, anchor="mm")
    else:
        d.text((cx, cy - kh * 0.10), buyuk, font=_sigdir(d, buyuk, 120 * olc, kw * 0.88), fill=renk, anchor="mm")
        d.text((cx, cy + kh * 0.30), alt, font=_sigdir(d, alt, 48 * olc, kw * 0.9), fill=LACI, anchor="mm")


def _sigdir(d, metin, px, maks):
    """Metni kart genisligine sigana kadar kucultur."""
    while px > 18:
        f = _font(px)
        if d.textlength(metin, font=f) <= maks:
            return f
        px *= 0.92
    return _font(px)


# --- video sonu: Begen + Abone ol (son 2 sn) ----------------------------------
SON_CAGRI_SN = 2.0
MAVI_BEGEN = (62, 128, 235)
KIRMIZI_YT = (230, 33, 23)


def _yay(t):
    """0..1 -> hafif tasan 'pop' egrisi."""
    t = max(0.0, min(1.0, t))
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def _kapsul(d, p1, p2, kalinlik, renk):
    d.line([p1, p2], fill=renk, width=int(kalinlik))
    r = kalinlik / 2
    for p in (p1, p2):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=renk)


def _basparmak(d, cx, cy, r, dolu, renk):
    """Klasik 'begen' eli: bilek + avuc + yukari bakan bas parmak."""
    cizgi = LACI
    w = max(2, int(r * 0.14))
    ic = renk if dolu else (255, 255, 255)
    # bas parmak (avucun arkasinda kalir)
    a, b = (cx - 0.22 * r, cy - 0.05 * r), (cx - 0.02 * r, cy - 0.78 * r)
    _kapsul(d, a, b, 0.44 * r + 2 * w, cizgi)
    _kapsul(d, a, b, 0.44 * r, ic)
    # bilek
    d.rounded_rectangle([cx - 0.98 * r, cy - 0.12 * r, cx - 0.62 * r, cy + 0.86 * r], radius=int(0.08 * r),
                        fill=ic, outline=cizgi, width=w)
    # avuc
    d.rounded_rectangle([cx - 0.50 * r, cy - 0.16 * r, cx + 0.72 * r, cy + 0.86 * r], radius=int(0.24 * r),
                        fill=ic, outline=cizgi, width=w)
    # parmak cizgileri
    for y in (0.16, 0.42, 0.64):
        d.line([(cx + 0.22 * r, cy + y * r), (cx + 0.70 * r, cy + y * r)], fill=cizgi, width=max(1, int(w * 0.8)))


def son_cagri(d, k):
    """k: son 2 saniyedeki kare no (0..59)."""
    n = SON_CAGRI_SN * FPS
    giris = _yay(k / 9)
    cikis = 1.0 if k < n - 5 else max(0.0, (n - k) / 5)
    olc = giris * (0.85 + 0.15 * cikis)
    if olc <= 0.01:
        return
    cx, cy = W / 2 * SS, 625 * SS
    kw, kh = 820 * SS * olc, 210 * SS * olc
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2 + 10 * SS, cx + kw / 2, cy + kh / 2 + 10 * SS],
                        radius=int(52 * SS * olc), fill=(225, 214, 190))
    d.rounded_rectangle([cx - kw / 2, cy - kh / 2, cx + kw / 2, cy + kh / 2], radius=int(52 * SS * olc),
                        fill=(255, 255, 255), outline=LACI, width=int(7 * SS))

    begen_an, abone_an = 18, 36                     # tiklama kareleri
    begenildi, abone = k >= begen_an, k >= abone_an
    bw, bh = 300 * SS * olc, 120 * SS * olc
    # Begen
    bx = cx - kw / 2 + 40 * SS * olc + bw / 2
    basma = 0.92 if begen_an <= k < begen_an + 3 else 1.0
    bb = [bx - bw / 2 * basma, cy - bh / 2 * basma, bx + bw / 2 * basma, cy + bh / 2 * basma]
    d.rounded_rectangle(bb, radius=int(bh / 2), fill=(232, 240, 255) if begenildi else (255, 255, 255),
                        outline=MAVI_BEGEN if begenildi else LACI, width=int(6 * SS))
    _basparmak(d, bx - bw * 0.26, cy - 2 * SS * olc, 40 * SS * olc * basma, begenildi, MAVI_BEGEN)
    d.text((bx + bw * 0.15, cy), "BEĞEN", font=_font(44 * olc), fill=MAVI_BEGEN if begenildi else LACI, anchor="mm")
    # Abone ol
    aw = kw - bw - 120 * SS * olc
    ax = cx + kw / 2 - 40 * SS * olc - aw / 2
    basma = 0.92 if abone_an <= k < abone_an + 3 else 1.0
    ab = [ax - aw / 2 * basma, cy - bh / 2 * basma, ax + aw / 2 * basma, cy + bh / 2 * basma]
    d.rounded_rectangle(ab, radius=int(bh / 2), fill=(225, 225, 228) if abone else KIRMIZI_YT)
    metin = "ABONE OLUNDU ✓" if abone else "ABONE OL"
    d.text((ax, cy), metin, font=_sigdir(d, metin, 46 * olc * basma, aw * 0.85),
           fill=(90, 90, 98) if abone else (255, 255, 255), anchor="mm")
    # dokunma halkasi
    for an, (px, py) in ((begen_an, (bx, cy)), (abone_an, (ax, cy))):
        if an - 4 <= k < an + 8:
            t = (k - (an - 4)) / 12
            r = (30 + 70 * t) * SS
            a = int(255 * (1 - t))
            d.ellipse([px - r, py - r, px + r, py + r], outline=(255, 183, 3), width=int(12 * SS * (1 - t) + 2))


# --- uretim -------------------------------------------------------------------
def uret(senaryo_yolu, cikti=None, sesli=None, ilerleme=None, izin_sessiz=False):
    """ilerleme: istege bagli fonksiyon(yuzde:int, mesaj:str)"""
    ilerle = ilerleme or (lambda y, m: None)
    with open(senaryo_yolu, encoding="utf-8") as f:
        sen = json.load(f)
    hatalar = dogrula(sen)
    if hatalar:
        raise ValueError("Senaryo gecersiz: " + "; ".join(hatalar))
    cikti = cikti or os.path.splitext(senaryo_yolu)[0] + ".mp4"
    sesli = ses_var_mi() if sesli is None else sesli
    gecici = tempfile.mkdtemp(prefix="bidik_")
    kare_dir = os.path.join(gecici, "k")
    os.makedirs(kare_dir)

    # her sahnenin sesi ve suresi
    # 1) once TUM replikleri seslendir; biri bile olmazsa video uretme (sessiz video asla cikmasin)
    import time as _t
    from ortak import ayarlar as _ayar
    hazir_sesler = {}
    konusan = [i for i, s in enumerate(sen["sahneler"]) if sesli and s.get("replik") and s.get("konusuyor", True)]
    bekleyen = list(konusan)
    # Ses servisi takilirsa: art arda 2 replik tamamen basarisiz olunca tur biter (servis kapali demektir),
    # biraz beklenip SADECE eksikler tekrar istenir. Ek tur sayisi ayarlar.json "ses_ek_tur" (varsayilan 2).
    ek_tur = max(0, int(_ayar().get("ses_ek_tur", 2)))
    bekleme = (45, 90, 150)
    for tur in range(1 + ek_tur):
        if tur and bekleyen:
            sn = bekleme[min(tur - 1, len(bekleme) - 1)]
            while sn > 0:
                ilerle(10, f"Ses servisi yanit vermiyor; {sn} sn sonra {tur + 1}. tur ({len(bekleyen)} replik eksik)")
                _t.sleep(5)
                sn -= 5
        kalan, ust_uste = [], 0
        for sira, i in enumerate(bekleyen):
            if ust_uste >= 2:           # servis kapali gorunuyor: bu turu bosuna uzatma
                kalan.append(i)
                continue
            wav = os.path.join(gecici, f"s{i}.wav")
            yapilan = len(konusan) - len(bekleyen) + sira
            ilerle(2 + int(8 * yapilan / max(1, len(konusan))),
                   f"Seslendiriliyor ({yapilan + 1}/{len(konusan)})" + (f" - {tur + 1}. tur" if tur else ""))
            try:
                seslendir(sen["sahneler"][i]["replik"], wav)
                hazir_sesler[i] = wav
                ust_uste = 0
            except SesHatasi as e:
                print("Seslendirme basarisiz:", e)
                kalan.append(i)
                ust_uste += 1
            _t.sleep(0.8)   # ses servisine art arda yuklenmemek icin kisa ara
        bekleyen = kalan
        if not bekleyen:
            break
    basarisiz = [i + 1 for i in bekleyen]
    if basarisiz:
        try:
            import importlib.metadata as _im
            print("edge-tts surumu:", _im.version("edge-tts"))
        except Exception:
            pass
    if basarisiz and not izin_sessiz:
        shutil.rmtree(gecici, ignore_errors=True)
        raise SesHatasi(
            f"Ses servisi su an {len(basarisiz)} replige cevap vermedi (sahne {', '.join(map(str, basarisiz))}). "
            "Sessiz video uretilmedi. Basarili sesler kaydedildi; birkac dakika sonra tekrar denediginde "
            "sadece eksikler istenecek.")

    sahne_sesleri, sessiz_sahneler = [], []
    for i, s in enumerate(sen["sahneler"]):
        zarf, sure = None, float(s["sure"])
        if sesli and s.get("replik") and s.get("konusuyor", True):
            wav = hazir_sesler.get(i)
            try:
                if not wav:
                    raise SesHatasi("ses yok")
                zarf, ses_sure = wav_zarf(wav)
                # sahne konusma bitince hemen gecsin: olu sessizlik izleyiciyi kaydirtir
                sure = max(ses_sure + 0.35, 2.4 if s.get("kart") else 1.3)
                sahne_sesleri.append((wav, sure))
            except Exception as e:  # tum denemeler basarisiz: sahne sessiz kalir, kullaniciya bildirilir
                print("Seslendirme basarisiz, sahne sessiz:", e)
                zarf = None
                sessiz_sahneler.append(i + 1)
                sahne_sesleri.append((None, sure))
        else:
            if sesli:   # bilerek sessiz tepki sahnesi: kisa tut
                sure = min(sure, 2.0)
            sahne_sesleri.append((None, sure))
        s["_sure"], s["_zarf"] = sure, zarf
    # son sahnede "Begen + Abone ol" karti son replikle cakismasin diye biraz pay birak
    from ortak import ayarlar as _ayarlar
    if sesli and _ayarlar().get("son_cagri", True) and sahne_sesleri:
        son = sen["sahneler"][-1]
        son["_sure"] += 0.8
        sahne_sesleri[-1] = (sahne_sesleri[-1][0], son["_sure"])

    toplam_kare = sum(int(round(s["_sure"] * FPS)) for s in sen["sahneler"])
    from ortak import ayarlar
    cagri_acik = ayarlar().get("son_cagri", True)
    cagri_basla = toplam_kare - int(SON_CAGRI_SN * FPS) if cagri_acik else 10 ** 9
    kostum = sen.get("kostum") or None
    ust = ust_boy(kostum)
    # konuya uygun arka plan (senaryoda sabitlenmediyse otomatik, art arda tekrar etmeyen)
    arka_ad = sen.get("arka_plan") if sen.get("arka_plan") in arka_planlar.SAHNELER else arka_planlar.secim(sen.get("alan", ""))
    SON_URETIM["arka_plan"] = arka_ad
    arka_taban = arka_planlar.ciz(arka_ad, SS)
    golgeli = {}
    # tum video icin tek buyuk-sahne olcegi (sahneler arasi "buyume/kuculme" sicramasi olmasin)
    zmax = max([float(x.get("ziplama", 0)) for x in sen["sahneler"] if not x.get("kart")] or [0])
    buyuk_olcek = sigan_olcek(1.95, ust, zmax + 30, ALTYAZI_ALT)
    kart_olcek = sigan_olcek(1.3, ust, 10, KART_ALT)
    n = 0
    for si, s in enumerate(sen["sahneler"]):
        toplam = int(round(s["_sure"] * FPS))
        p = {k: s[k] for k in ("ifade", "kol", "bakis", "egilme") if k in s}
        if "bakis" in p:
            p["bakis"] = tuple(p["bakis"])
        hedef_zip = float(s.get("ziplama", 0))
        kaydir = -150 if p.get("kol") == "isaret" else 0
        kart = s.get("kart")
        # sahne boyunca sabit olcek: kostum/percem altyaziya ya da karta carpmasin
        sahne_olcek = kart_olcek if kart else buyuk_olcek
        cagri_olcek = sigan_olcek(1.3, ust, 10, KART_ALT - 60)
        for k in range(toplam):
            t = k / FPS
            anahtar = (kaydir, round(sahne_olcek, 3))
            if anahtar not in golgeli:            # golge sahnenin konumuna gore bir kez cizilir
                g = arka_taban.copy()
                arka_planlar.golge_ekle(g, (W / 2 + kaydir) * SS, SS, sahne_olcek)
                golgeli[anahtar] = g
            img = golgeli[anahtar].copy()
            d = ImageDraw.Draw(img)
            cagri_k = n - cagri_basla          # >= 0 ise son 2 saniyedeyiz
            if kart and cagri_k < 0:
                bilgi_karti(d, kart, k / 8)
            giris = max(0.0, 1 - k / 6)
            zip_ = hedef_zip * math.sin(min(1, k / 8) * math.pi / 2) + giris * 25
            zip_ += 4 * math.sin(t * 2 * math.pi * 0.9)
            if s["_zarf"]:
                agiz = s["_zarf"][k] if k < len(s["_zarf"]) else 0.0
            elif s.get("konusuyor", True) and s.get("replik"):
                agiz = (0.5 + 0.5 * math.sin(t * 2 * math.pi * 4.5)) * 0.9 if t < s["_sure"] - 0.3 else 0.0
            else:
                agiz = 0.0
            kirp = 1.0 if (n % 75) in (0, 1, 2) else 0.0
            olcek = sahne_olcek
            if kart:  # kartli sahnede Bidik kucuk ve yerde durur, kartla cakismaz
                zip_ = min(zip_, 10)
            if cagri_k >= 0:  # video sonu kartina yer ac: Bidik yumusakca kuculur
                hedef = cagri_olcek
                gecis = min(1.0, cagri_k / 8)
                olcek = olcek + (hedef - olcek) * (gecis * gecis * (3 - 2 * gecis))
                zip_ = min(zip_, 10)
            ciz_bidik(img, x=(W / 2 + kaydir) * SS, y=H * 0.80 * SS, olcek=olcek * SS,
                      agiz=agiz, kirp=kirp, ziplama=zip_, kol_faz=t * 1.6, kostum=kostum, **p)
            altyazi(d, s.get("replik", ""))
            if cagri_k >= 0:
                son_cagri(d, cagri_k)
            img.resize((W, H), Image.LANCZOS).save(os.path.join(kare_dir, f"{n:05d}.png"))
            n += 1
            if n % 15 == 0:
                ilerle(10 + int(80 * n / toplam_kare), f"Cizim: kare {n}/{toplam_kare}")

    # ses izi: sahne seslerini sirayla birlestir (sessiz sahneler bosluk)
    ilerle(92, "Ses ve video birlestiriliyor")
    ses_izi = os.path.join(gecici, "ses.wav")
    parcalar = []
    for i, (wav, sure) in enumerate(sahne_sesleri):
        hedef = os.path.join(gecici, f"p{i}.wav")
        if wav:
            komut([ffmpeg(), "-y", "-loglevel", "error", "-i", wav, "-af", f"apad=whole_dur={sure}",
                            "-ar", "24000", "-ac", "1", hedef])
        else:
            komut([ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=24000:cl=mono", "-t", str(sure), hedef])
        parcalar.append(hedef)
    liste = os.path.join(gecici, "liste.txt")
    with open(liste, "w", encoding="utf-8") as f:
        f.writelines("file '" + p.replace(os.sep, "/") + "'\n" for p in parcalar)
    komut([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                    ses_izi])

    komut([ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(kare_dir, "%05d.png"), "-i", ses_izi,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", cikti])
    shutil.rmtree(gecici, ignore_errors=True)
    ilerle(100, "Hazir")
    return cikti, n / FPS, sesli, sessiz_sahneler


if __name__ == "__main__":
    yol, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    c, sure, sesli, sessiz = uret(yol, out)
    print(f"{c} hazir ({sure:.1f} sn, {'sesli' if sesli else 'sessiz'})")
