"""
Bidik'in video basi giris hareketleri (ilk ~0.75 sn).

Her giris uc parcadan olusur:
  durum(ad, t)            -> Bidik'in o andaki konumu: dx/dy (piksel, olcek 1'de), olcek carpani, egilme,
                             gizli (henuz gorunmuyor), kirp_zemin (zeminin altinda kalan kisim cizilmez)
  arka(ad, img, d, t, c)  -> Bidik'ten ONCE cizilenler (or. tava)
  on(ad, img, d, t, c)    -> Bidik'ten SONRA cizilenler (alev, duman, cali, perde, yildizlar...)
t: 0..1 ilerleme. c: {"x","y","s","W","H"} (x,y: ayak noktasi; s: Bidik'in o anki olcegi, piksel/birim)
secim(tema): konuya ozel + genel girislerden, son 2 kullanilani atlayarak secer (giris_gecmis.json).
"""
import json, math, os, random
from PIL import Image, ImageDraw

SURE_SN = 0.75
LACI = (35, 37, 58)


# --- yumusatma egrileri ------------------------------------------------------------------
def _cik(t):          # ease-out cubic
    return 1 - (1 - t) ** 3


def _tas(t, c=1.6):   # ease-out back (hafif tasma)
    t -= 1
    return 1 + (c + 1) * t ** 3 + c * t ** 2


def _sek(t):          # ease-out bounce
    n, dd = 7.5625, 2.75
    if t < 1 / dd:
        return n * t * t
    if t < 2 / dd:
        t -= 1.5 / dd
        return n * t * t + 0.75
    if t < 2.5 / dd:
        t -= 2.25 / dd
        return n * t * t + 0.9375
    t -= 2.625 / dd
    return n * t * t + 0.984375


def _yildiz(d, cx, cy, r, renk):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=renk)


def _duman(img, cx, cy, r, alfa):
    if alfa <= 0.02:
        return
    katman = Image.new("RGBA", (int(r * 5), int(r * 4)), (0, 0, 0, 0))
    kd = ImageDraw.Draw(katman)
    ox, oy = r * 2.5, r * 2.2
    for dx, dy, rr in ((-1.2, 0.3, 0.8), (-0.4, -0.3, 1.0), (0.5, -0.1, 0.9), (1.2, 0.4, 0.75), (0, 0.6, 0.9)):
        R = r * rr
        kd.ellipse([ox + dx * r - R, oy + dy * r - R, ox + dx * r + R, oy + dy * r + R],
                   fill=(245, 245, 250, int(235 * alfa)), outline=(190, 192, 205, int(255 * alfa)), width=max(2, int(r * 0.06)))
    img.paste(katman, (int(cx - ox), int(cy - oy)), katman)


# --- girisler ------------------------------------------------------------------------------
def durum(ad, t):
    """Bidik'in giris boyuncaki konumu (dy: yukari eksi)."""
    t = max(0.0, min(1.0, t))
    o = {"dx": 0.0, "dy": 0.0, "olcek": 1.0, "egilme": 0.0, "gizli": False, "kirp_zemin": False, "ziplama": None}
    if ad == "zipla":                        # klasik: yere dusup sekme
        o["dy"] = -abs(math.sin(math.pi * t * 2)) * (1 - t * 0.55) * 170   # iki kez sekme
    elif ad in ("yandan_kay", "kaydir"):     # sagdan kayarak gelir, durunca dogrulur
        e = _tas(t, 1.2)
        o["dx"] = (1 - e) * 900
        o["egilme"] = -0.8 * (1 - _cik(t))
    elif ad == "dus":                        # yukaridan duser, seker
        o["dy"] = -(1 - _sek(t)) * 1100
    elif ad in ("buyu", "soru"):             # 'pop' diye belirir
        o["olcek"] = max(0.02, _tas(t, 2.2))
    elif ad == "roket":                      # roketle yavasca iner
        o["dy"] = -(1 - _cik(t)) * 1200
    elif ad == "tava":                       # tavadan firlar, havada buyur, yere iner
        o["olcek"] = 0.45 + 0.55 * _cik(min(1, t * 1.4))
        o["dy"] = -math.sin(math.pi * t) * 520
        o["dx"] = (1 - t) * -60
    elif ad == "duman":                      # duman bulutunun icinden cikar
        o["gizli"] = t < 0.22
        o["olcek"] = max(0.02, _tas(max(0.0, (t - 0.22) / 0.78), 2.0))
    elif ad == "perde":                      # perde aralanir, Bidik zaten sahnede
        pass
    elif ad == "pervane":                    # pervaneyle suzulerek iner
        o["dy"] = -(1 - _cik(t)) * 1250
        o["dx"] = math.sin(t * math.pi * 3) * 45 * (1 - t)
    elif ad == "cali":                       # calinin arkasindan firlar
        o["dy"] = (1 - _tas(t, 1.8)) * 560
        o["kirp_zemin"] = True
    elif ad == "piksel":                     # piksel piksel belirir (on() bulaniklastirir)
        pass
    elif ad == "yildiz":                     # yildizlar etrafinda doner, sonra 'pop'
        o["olcek"] = max(0.02, _tas(max(0.0, (t - 0.35) / 0.65), 2.0))
        o["gizli"] = t < 0.35
    elif ad == "kalp":                       # kalp atisi gibi iki vurusla buyur
        if t < 0.45:
            o["olcek"] = max(0.02, _tas(t / 0.45, 2.4))
        else:
            u = (t - 0.45) / 0.55
            o["olcek"] = 1 + 0.10 * math.sin(u * math.pi * 2) * (1 - u)
    return o


def arka(ad, img, d, t, c):
    s, x, y = c["s"], c["x"], c["y"]
    if ad == "tava":   # yerde tava (Bidik'in arkasinda kalan sap)
        kay = max(0.0, (t - 0.65) / 0.35) * -900 * s
        cx, cy = x + kay, y - 6 * s
        d.line([(cx + 120 * s, cy - 10 * s), (cx + 300 * s, cy - 60 * s)], fill=(60, 50, 50), width=int(26 * s))
        d.ellipse([cx - 150 * s, cy - 40 * s, cx + 150 * s, cy + 30 * s], fill=(70, 74, 92), outline=LACI, width=int(8 * s))
        d.ellipse([cx - 120 * s, cy - 28 * s, cx + 120 * s, cy + 14 * s], fill=(110, 116, 138))


def on(ad, img, d, t, c):
    s, x, y, W, H = c["s"], c["x"], c["y"], c["W"], c["H"]
    if ad == "roket":   # ayaklarin altinda alev + inince toz
        if t < 0.9:
            fy = c["ayak_y"]
            boy = (110 + 30 * math.sin(t * 60)) * s * (1 - t * 0.6)
            for yon in (-1, 1):
                fx = x + yon * 65 * s
                d.polygon([(fx - 28 * s, fy), (fx + 28 * s, fy), (fx, fy + boy)], fill=(255, 150, 40))
                d.polygon([(fx - 15 * s, fy), (fx + 15 * s, fy), (fx, fy + boy * 0.6)], fill=(255, 235, 120))
        if t > 0.75:
            _duman(img, x, y - 20 * s, 95 * s * (0.6 + t), (1 - t) / 0.25)
    elif ad == "duman":
        r = 150 * s * (0.6 + t * 0.9)
        _duman(img, x, y - 260 * s, r, 1.0 if t < 0.35 else max(0.0, 1 - (t - 0.35) / 0.5))
    elif ad in ("dus", "yandan_kay", "kaydir") and t > 0.55:
        _duman(img, x, y - 10 * s, 60 * s * (0.5 + t), max(0.0, 1 - (t - 0.55) / 0.45) * 0.9)
    elif ad == "perde":
        acik = _cik(t)
        gen = (W / 2) * (1 - acik) + 40
        for taraf in (0, 1):
            x0 = 0 if taraf == 0 else W - gen
            d.rectangle([x0, 0, x0 + gen, H], fill=(190, 30, 45))
            for i in range(7):
                fx = x0 + gen * (i + 0.5) / 7
                d.line([(fx, 0), (fx, H)], fill=(150, 20, 35), width=max(3, int(W / 160)))
        d.rectangle([0, 0, W, H * 0.07], fill=(160, 22, 38))
        for i in range(12):
            d.ellipse([i * W / 12, H * 0.05, (i + 1) * W / 12, H * 0.09], fill=(160, 22, 38))
        d.line([(0, H * 0.075), (W, H * 0.075)], fill=(240, 190, 60), width=max(4, int(W / 120)))
    elif ad == "cali":
        by = y + 8 * s + max(0.0, (t - 0.72) / 0.28) ** 2 * 420 * s   # sonda calı yere cekilir
        renkler = [(70, 150, 80), (90, 170, 90), (60, 135, 75)]
        for i, (dx, dy, r) in enumerate(((-190, -60, 120), (-60, -120, 150), (90, -100, 140), (210, -50, 115), (0, -30, 160))):
            d.ellipse([x + (dx - r) * s, by + (dy - r) * s, x + (dx + r) * s, by + (dy + r * 0.8) * s],
                      fill=renkler[i % 3], outline=LACI, width=int(6 * s))
        if t > 0.5:   # firlarken yapraklar
            for i in range(5):
                a = i * 1.3 + t * 4
                px, py = x + math.cos(a) * 200 * s * t, by - 250 * s * t - i * 30 * s
                d.ellipse([px - 14 * s, py - 8 * s, px + 14 * s, py + 8 * s], fill=(90, 170, 90))
    elif ad == "piksel" and t < 0.95:
        blok = max(1, int((1 - _cik(t)) * 70 * c["SS"]))
        if blok > 1:
            x0, y0 = int(max(0, x - 420 * s)), int(max(0, y - 900 * s))
            x1, y1 = int(min(W, x + 420 * s)), int(min(H, y + 10 * s))
            bolge = img.crop((x0, y0, x1, y1))
            kucuk = bolge.resize((max(1, (x1 - x0) // blok), max(1, (y1 - y0) // blok)), Image.BILINEAR)
            img.paste(kucuk.resize(bolge.size, Image.NEAREST), (x0, y0))
            rnd = random.Random(int(t * 100))
            for _ in range(5):   # parazit seritleri
                yy = rnd.uniform(y0, y1)
                d.rectangle([x0, yy, x1, yy + rnd.uniform(4, 14) * c["SS"]], fill=rnd.choice([(0, 220, 255), (255, 60, 200), (120, 255, 160)]))
    elif ad == "yildiz":
        for i in range(8):
            a = i * math.pi / 4 + t * 7
            r = (1 - _cik(t)) * 520 * s + 160 * s
            px, py = x + math.cos(a) * r, y - 260 * s + math.sin(a) * r * 0.8
            _yildiz(d, px, py, (26 - 10 * t) * s, (255, 220, 90) if i % 2 else (255, 255, 255))
    elif ad == "kalp" and t > 0.2:
        r = 200 * s + t * 260 * s
        alfa = max(0.0, 1 - t)
        katman = Image.new("RGBA", (int(r * 2.2), int(r * 2.2)), (0, 0, 0, 0))
        kd = ImageDraw.Draw(katman)
        o = r * 1.1
        cx, cy = o, o
        w = max(3, int(16 * s))
        kd.arc([cx - r, cy - r * 0.9, cx, cy + r * 0.1], 135, 360, fill=(240, 80, 110, int(255 * alfa)), width=w)
        kd.arc([cx, cy - r * 0.9, cx + r, cy + r * 0.1], 180, 45, fill=(240, 80, 110, int(255 * alfa)), width=w)
        kd.line([(cx - r * 0.85, cy - r * 0.05), (cx, cy + r), (cx + r * 0.85, cy - r * 0.05)], fill=(240, 80, 110, int(255 * alfa)), width=w)
        img.paste(katman, (int(x - o), int(y - 260 * s - o)), katman)
    elif ad == "soru" and t > 0.15:
        from ortak import FONT
        from PIL import ImageFont
        olc = _tas(min(1, (t - 0.15) / 0.5), 2.0)
        alfa = 1.0 if t < 0.8 else max(0.0, 1 - (t - 0.8) / 0.2)
        if olc > 0.05 and alfa > 0.02:
            px, py, r = x + 165 * s, y - 590 * s, 52 * s * olc
            katman = Image.new("RGBA", (int(r * 3) + 4, int(r * 3) + 4), (0, 0, 0, 0))
            kd = ImageDraw.Draw(katman)
            kd.ellipse([2, 2, 2 * r, 2 * r], fill=(255, 255, 255, int(255 * alfa)), outline=(35, 37, 58, int(255 * alfa)), width=max(2, int(6 * s)))
            kd.text((r + 2, r + 2), "?", font=ImageFont.truetype(FONT, max(8, int(r * 1.3))), fill=(150, 100, 230, int(255 * alfa)), anchor="mm")
            img.paste(katman, (int(px - r), int(py - r)), katman)


# --- konu -> girisler -------------------------------------------------------------------------
GENEL = ["zipla", "yandan_kay", "dus", "buyu"]
TEMA_GIRIS = {
    "uzay": ["roket"], "yemek": ["tava"], "bilim": ["duman"], "tarih": ["perde"], "cocuk": ["pervane"],
    "hayvanlar": ["cali"], "teknoloji": ["piksel"], "burclar": ["yildiz"], "insan": ["kalp"],
    "psikoloji": ["soru"], "cografya": ["kaydir"], "genel": [],
}
ADLAR = {"zipla": "Zıplayarak", "yandan_kay": "Yandan kayarak", "dus": "Yukarıdan düşerek", "buyu": "'Pop' diye belirerek",
         "roket": "Roketle inerek", "tava": "Tavadan fırlayarak", "duman": "Duman bulutundan çıkarak", "perde": "Perde aralanarak",
         "pervane": "Pervaneyle süzülerek", "cali": "Çalının arkasından fırlayarak", "piksel": "Piksel piksel belirerek",
         "yildiz": "Yıldız dansıyla", "kalp": "Kalp atışıyla", "soru": "Soru işaretiyle", "kaydir": "Kayarak gelip toz kaldırarak"}


def _gecmis_yolu():
    from ortak import KOK
    return os.path.join(KOK, "giris_gecmis.json")


def secim(tema):
    """Konuya ozel girislere iki kat agirlik; son 2 kullanilan giris tekrar edilmez (tum konular boyunca)."""
    try:
        with open(_gecmis_yolu(), encoding="utf-8") as f:
            son = json.load(f)
    except (OSError, ValueError):
        son = []
    ozel = TEMA_GIRIS.get(tema, [])
    havuz = [g for g in ozel * 2 + GENEL if g not in son[-2:]] or GENEL
    ad = random.choice(havuz)
    try:
        with open(_gecmis_yolu(), "w", encoding="utf-8") as f:
            json.dump((son + [ad])[-6:], f)
    except OSError:
        pass
    return ad
