"""
Konuya gore arka planlar: 11 konu x 4 sahne, tamamen kodla cizilir.

- Her sahne 1080x1920 tabanli koordinatlarla cizilir (k = olcek carpani; video SS=2 ile 2160x3840).
- Zemin cizgisi her zaman y=1536'da (Bidik'in bastigi yer).
- Motifler yumusak renkli ve hafif bulanik cizilir: Bidik, altyazi ve bilgi karti hep one cikar.
- secim(): ayni konuda son kullanilanlari tekrar etmez (BIDIK/arka_gecmis.json).
"""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
ZEMIN_Y = int(H * 0.80)
LACI = (35, 37, 58)


# --- yardimcilar ------------------------------------------------------------------
def _karis(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradyan(img, ust, alt, y0=0, y1=None, k=1):
    y1 = H if y1 is None else y1
    d = ImageDraw.Draw(img)
    adim = 4
    for y in range(int(y0 * k), int(y1 * k), adim):
        t = (y / k - y0) / max(1, (y1 - y0))
        d.rectangle([0, y, W * k, y + adim], fill=_karis(ust, alt, t))


def _P(k, pts):
    return [(x * k, y * k) for x, y in pts]


def _daire(d, k, x, y, r, renk, kontur=None, w=0):
    d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=renk, outline=kontur, width=int(w * k))


def _bulut(d, k, x, y, r, renk):
    for dx, dy, rr in ((0, 0, 1), (-0.9, 0.25, 0.7), (0.9, 0.25, 0.75), (-0.4, -0.35, 0.75), (0.45, -0.3, 0.7)):
        _daire(d, k, x + dx * r, y + dy * r, rr * r, renk)
    d.rectangle([(x - 1.5 * r) * k, (y + 0.2 * r) * k, (x + 1.55 * r) * k, (y + 0.95 * r) * k], fill=renk)


def _yildiz5(d, k, x, y, r, renk):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(_P(k, pts), fill=renk)


def _yildizlar(d, k, rng, n, renk, y_max=ZEMIN_Y, buyuk=False):
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, y_max)
        r = rng.choice((2, 2, 3, 3, 4, 5)) * (1.4 if buyuk else 1)
        _daire(d, k, x, y, r, renk)


def _zemin(d, k, renk, cizgi=None):
    d.rectangle([0, ZEMIN_Y * k, W * k, H * k], fill=renk)
    d.line([(0, ZEMIN_Y * k), (W * k, ZEMIN_Y * k)], fill=cizgi or _karis(renk, (0, 0, 0), 0.35), width=int(6 * k))


def _dag(d, k, tepeler, taban, renk):
    pts = [(0, taban)] + tepeler + [(W, taban)]
    d.polygon(_P(k, pts), fill=renk)


def _dalga(d, k, y, genlik, dalga_boyu, renk, alt=H, faz=0):
    pts = [(0, alt)]
    for x in range(0, W + 20, 20):
        pts.append((x, y + genlik * math.sin(x / dalga_boyu * 2 * math.pi + faz)))
    pts.append((W, alt))
    d.polygon(_P(k, pts), fill=renk)


def _desen(d, k, rng, cizici, n, y_max=ZEMIN_Y - 40):
    for _ in range(n):
        cizici(rng.uniform(40, W - 40), rng.uniform(60, y_max), rng)


# ==================================================================================
# SAHNELER: her fonksiyon (img, d, k, rng) -> zemin dahil tum sahneyi cizer
# ==================================================================================

# ---- UZAY ----------------------------------------------------------------------------
def uzay_derin(img, d, k, rng):
    _gradyan(img, (16, 20, 52), (44, 36, 92), k=k)
    _yildizlar(d, k, rng, 160, (220, 225, 255))
    _daire(d, k, 840, 560, 120, (226, 140, 90))
    d.ellipse([(840 - 210) * k, (560 - 34) * k, (840 + 210) * k, (560 + 34) * k], outline=(250, 210, 160), width=int(14 * k))
    d.chord([(840 - 120) * k, (560 - 120) * k, (840 + 120) * k, (560 + 120) * k], 200, 340, fill=(226, 140, 90))
    _daire(d, k, 170, 1050, 46, (150, 190, 255))
    _zemin(d, k, (52, 48, 96))


def uzay_ay(img, d, k, rng):
    _gradyan(img, (8, 10, 30), (30, 32, 70), k=k)
    _yildizlar(d, k, rng, 140, (230, 230, 255))
    _daire(d, k, 820, 620, 110, (70, 130, 220))
    for x, y, r in ((790, 590, 40), (860, 650, 32), (820, 690, 22)):
        _daire(d, k, x, y, r, (90, 180, 110))
    _zemin(d, k, (170, 170, 182), (120, 120, 134))
    for _ in range(9):
        x, y, r = rng.uniform(40, W - 40), rng.uniform(ZEMIN_Y + 50, H - 40), rng.uniform(22, 60)
        d.ellipse([(x - r) * k, (y - r * 0.35) * k, (x + r) * k, (y + r * 0.35) * k], fill=(148, 148, 162))
    _dalga(d, k, ZEMIN_Y - 20, 18, 520, (170, 170, 182), alt=ZEMIN_Y + 4)


def uzay_bulutsu(img, d, k, rng):
    _gradyan(img, (30, 14, 60), (12, 30, 70), k=k)
    for _ in range(14):
        x, y, r = rng.uniform(0, W), rng.uniform(250, 1300), rng.uniform(120, 260)
        renk = rng.choice([(110, 50, 140), (60, 70, 160), (150, 60, 120)])
        _daire(d, k, x, y, r, renk)
    img.paste(img.filter(ImageFilter.GaussianBlur(60 * k)))
    d = ImageDraw.Draw(img)
    _yildizlar(d, k, rng, 150, (255, 255, 255))
    d.line(_P(k, [(120, 380), (420, 520)]), fill=(255, 255, 255), width=int(5 * k))
    _daire(d, k, 420, 520, 8, (255, 255, 255))
    _zemin(d, k, (40, 30, 70))


def uzay_mars(img, d, k, rng):
    _gradyan(img, (230, 170, 140), (200, 120, 90), k=k)
    _daire(d, k, 230, 420, 46, (245, 225, 210))
    _daire(d, k, 850, 300, 26, (240, 215, 200))
    _dag(d, k, [(180, 1300), (380, 1180), (560, 1330), (760, 1200), (980, 1340)], ZEMIN_Y, (190, 100, 70))
    _zemin(d, k, (176, 92, 62))
    for _ in range(14):
        x, y, r = rng.uniform(30, W - 30), rng.uniform(ZEMIN_Y + 40, H - 30), rng.uniform(8, 22)
        _daire(d, k, x, y, r, (150, 74, 50))


# ---- HAYVANLAR ------------------------------------------------------------------------
def _akasya(d, k, x, y, s, renk=(86, 110, 64)):
    d.polygon(_P(k, [(x - 10 * s, y), (x + 10 * s, y), (x + 6 * s, y - 180 * s), (x - 6 * s, y - 180 * s)]), fill=(110, 82, 58))
    d.ellipse([(x - 150 * s) * k, (y - 240 * s) * k, (x + 150 * s) * k, (y - 170 * s) * k], fill=renk)
    d.ellipse([(x - 90 * s) * k, (y - 270 * s) * k, (x + 110 * s) * k, (y - 210 * s) * k], fill=renk)


def hayvan_savan(img, d, k, rng):
    _gradyan(img, (170, 215, 225), (245, 225, 180), 0, ZEMIN_Y, k)
    _daire(d, k, 780, 520, 110, (255, 238, 190))
    _dag(d, k, [(0, 1350), (300, 1290), (600, 1360), (900, 1300), (1080, 1340)], ZEMIN_Y, (200, 190, 140))
    _akasya(d, k, 190, ZEMIN_Y, 1.1)
    _akasya(d, k, 900, ZEMIN_Y - 30, 0.75)
    _zemin(d, k, (206, 180, 110))
    for _ in range(40):
        x, y = rng.uniform(0, W), rng.uniform(ZEMIN_Y + 30, H - 20)
        d.line(_P(k, [(x, y), (x + 6, y - 22)]), fill=(170, 145, 80), width=int(4 * k))


def hayvan_orman(img, d, k, rng):
    _gradyan(img, (200, 232, 210), (150, 200, 160), 0, ZEMIN_Y, k)
    for kat, renk in ((0, (120, 175, 130)), (1, (90, 150, 105))):
        for i in range(7):
            x = i * 170 + (60 if kat else 0) + rng.uniform(-30, 30)
            h = rng.uniform(380, 560) + kat * 80
            d.polygon(_P(k, [(x, ZEMIN_Y - h), (x - 110, ZEMIN_Y), (x + 110, ZEMIN_Y)]), fill=renk)
    _zemin(d, k, (96, 140, 80))
    for _ in range(12):
        x, y = rng.uniform(30, W - 30), rng.uniform(ZEMIN_Y + 40, H - 40)
        _daire(d, k, x, y, 10, rng.choice([(255, 230, 120), (255, 170, 190), (255, 255, 255)]))


def hayvan_deniz(img, d, k, rng):
    _gradyan(img, (120, 200, 230), (30, 90, 150), 0, H, k)
    for i in range(6):
        x = 100 + i * 180
        d.polygon(_P(k, [(x - 40, 0), (x + 40, 0), (x + 160, 1200), (x + 80, 1200)]), fill=(140, 210, 235))
    img.paste(img.filter(ImageFilter.GaussianBlur(30 * k)))
    d = ImageDraw.Draw(img)
    for _ in range(30):
        x, y, r = rng.uniform(0, W), rng.uniform(450, ZEMIN_Y), rng.uniform(6, 18)
        _daire(d, k, x, y, r, None, (210, 240, 255), 3)
    for x in (90, 260, 880, 1000):
        for j in range(5):
            _daire(d, k, x + 18 * math.sin(j), ZEMIN_Y - 40 - j * 60, 26, (60, 150, 110))
    _zemin(d, k, (226, 205, 160))


def hayvan_kutup(img, d, k, rng):
    _gradyan(img, (190, 225, 245), (235, 245, 252), 0, ZEMIN_Y, k)
    _dag(d, k, [(0, 1100), (260, 980), (420, 1200), (700, 1050), (900, 1230), (1080, 1120)], ZEMIN_Y, (205, 228, 245))
    d.polygon(_P(k, [(620, ZEMIN_Y), (720, 1240), (800, 1300), (900, ZEMIN_Y)]), fill=(225, 240, 252))
    _zemin(d, k, (240, 246, 252), (170, 200, 225))
    for _ in range(70):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        _daire(d, k, x, y, rng.uniform(3, 7), (255, 255, 255))


# ---- YEMEK ----------------------------------------------------------------------------
def yemek_mutfak(img, d, k, rng):
    _gradyan(img, (236, 246, 244), (220, 236, 232), 0, ZEMIN_Y, k)
    for y in range(820, ZEMIN_Y, 90):
        for x in range(0, W, 90):
            d.rectangle([(x + 3) * k, (y + 3) * k, (x + 87) * k, (y + 87) * k], fill=(205, 228, 224))
    for raf_y in (560, 760):
        d.rectangle([60 * k, raf_y * k, 420 * k, (raf_y + 14) * k], fill=(170, 130, 95))
    for i, renk in enumerate([(230, 120, 110), (240, 200, 110), (130, 190, 150), (140, 170, 220)]):
        x = 90 + i * 85
        d.rounded_rectangle([x * k, 470 * k, (x + 60) * k, 560 * k], radius=int(10 * k), fill=renk)
    _daire(d, k, 860, 450, 70, (250, 250, 250), (180, 190, 200), 6)
    d.line(_P(k, [(860, 450), (860, 405)]), fill=(120, 120, 140), width=int(6 * k))
    d.line(_P(k, [(860, 450), (895, 470)]), fill=(120, 120, 140), width=int(6 * k))
    _zemin(d, k, (190, 150, 115))


def yemek_piknik(img, d, k, rng):
    _gradyan(img, (175, 220, 245), (225, 242, 250), 0, ZEMIN_Y, k)
    _daire(d, k, 880, 300, 80, (255, 240, 170))
    _bulut(d, k, 230, 360, 70, (255, 255, 255))
    _dag(d, k, [(0, 1320), (400, 1220), (800, 1330), (1080, 1260)], ZEMIN_Y, (150, 205, 130))
    _zemin(d, k, (130, 190, 110))
    kare = 70
    for j, y in enumerate(range(ZEMIN_Y + 20, H, kare)):
        for i, x in enumerate(range(-20, W, kare)):
            if (i + j) % 2 == 0:
                d.rectangle([x * k, y * k, (x + kare) * k, (y + kare) * k], fill=(228, 110, 110))
            else:
                d.rectangle([x * k, y * k, (x + kare) * k, (y + kare) * k], fill=(250, 238, 230))


def yemek_meyve(img, d, k, rng):
    _gradyan(img, (255, 236, 222), (255, 220, 210), 0, ZEMIN_Y, k)

    def meyve(x, y, rng):
        tur = rng.randrange(4)
        if tur == 0:      # elma
            _daire(d, k, x, y, 34, (235, 110, 100)); d.line(_P(k, [(x, y - 34), (x + 6, y - 52)]), fill=(110, 80, 50), width=int(5 * k))
        elif tur == 1:    # portakal
            _daire(d, k, x, y, 32, (250, 175, 80)); _daire(d, k, x + 8, y - 8, 6, (255, 210, 140))
        elif tur == 2:    # uzum
            for dx, dy in ((0, 0), (-14, -12), (14, -12), (0, -24), (-7, 12), (7, 12)):
                _daire(d, k, x + dx, y + dy, 11, (160, 110, 190))
        else:             # limon
            d.ellipse([(x - 36) * k, (y - 24) * k, (x + 36) * k, (y + 24) * k], fill=(245, 225, 110))
    _desen(d, k, rng, meyve, 26)
    _zemin(d, k, (240, 190, 170))


def yemek_firin(img, d, k, rng):
    _gradyan(img, (214, 160, 130), (196, 140, 112), 0, ZEMIN_Y, k)
    for j, y in enumerate(range(0, ZEMIN_Y, 60)):
        ofs = 0 if j % 2 == 0 else 70
        for x in range(-ofs, W, 140):
            d.rectangle([(x + 4) * k, (y + 4) * k, (x + 136) * k, (y + 56) * k], fill=(200, 128, 100))
    d.chord([270 * k, 760 * k, 810 * k, 1300 * k], 180, 360, fill=(120, 74, 60))
    d.chord([340 * k, 840 * k, 740 * k, 1240 * k], 180, 360, fill=(60, 36, 32))
    for i in range(6):
        _daire(d, k, 420 + i * 48, 1035, 22, (255, 170, 70))
    _zemin(d, k, (150, 105, 80))


# ---- BILIM ----------------------------------------------------------------------------
def bilim_lab(img, d, k, rng):
    _gradyan(img, (222, 236, 250), (205, 222, 240), 0, ZEMIN_Y, k)
    for raf_y in (600, 860):
        d.rectangle([0, raf_y * k, W * k, (raf_y + 16) * k], fill=(160, 175, 200))
        for x in range(40, W, 120):
            renk = rng.choice([(120, 210, 170), (240, 150, 170), (130, 170, 240), (250, 210, 110)])
            if rng.random() < 0.5:
                d.rounded_rectangle([x * k, (raf_y - 110) * k, (x + 34) * k, raf_y * k], radius=int(14 * k), fill=(240, 246, 252), outline=(150, 165, 190), width=int(4 * k))
                d.rounded_rectangle([(x + 4) * k, (raf_y - 60) * k, (x + 30) * k, (raf_y - 4) * k], radius=int(10 * k), fill=renk)
            else:
                d.polygon(_P(k, [(x + 10, raf_y - 110), (x + 30, raf_y - 110), (x + 30, raf_y - 70), (x + 62, raf_y), (x - 22, raf_y), (x + 10, raf_y - 70)]),
                          fill=(240, 246, 252), outline=(150, 165, 190))
                d.polygon(_P(k, [(x - 12, raf_y - 4), (x + 52, raf_y - 4), (x + 38, raf_y - 34), (x + 2, raf_y - 34)]), fill=renk)
    _zemin(d, k, (200, 210, 225))


def bilim_tahta(img, d, k, rng):
    _gradyan(img, (226, 214, 192), (214, 200, 176), 0, ZEMIN_Y, k)
    d.rounded_rectangle([60 * k, 440 * k, 1020 * k, 1240 * k], radius=int(18 * k), fill=(48, 84, 70), outline=(150, 110, 70), width=int(22 * k))
    tebesir = (225, 235, 228)
    for _ in range(10):
        x, y = rng.uniform(130, 760), rng.uniform(500, 1160)
        n = rng.randrange(3, 7)
        for i in range(n):
            d.line(_P(k, [(x + i * 34, y), (x + i * 34 + 22, y - 18)]), fill=tebesir, width=int(4 * k))
        d.line(_P(k, [(x, y + 16), (x + n * 34, y + 16)]), fill=tebesir, width=int(3 * k))
    d.ellipse([780 * k, 560 * k, 940 * k, 720 * k], outline=tebesir, width=int(5 * k))
    d.line(_P(k, [(860, 560), (860, 720)]), fill=tebesir, width=int(3 * k))
    _zemin(d, k, (170, 135, 100))


def bilim_atom(img, d, k, rng):
    _gradyan(img, (214, 232, 252), (190, 214, 245), 0, ZEMIN_Y, k)

    def atom(x, y, rng):
        r = rng.uniform(40, 80)
        for a in (0, 60, 120):
            katman = Image.new("L", (int(2.4 * r * k), int(2.4 * r * k)), 0)
            ImageDraw.Draw(katman).ellipse([0.2 * r * k, 0.85 * r * k, 2.2 * r * k, 1.55 * r * k], outline=255, width=int(4 * k))
            katman = katman.rotate(a, resample=Image.BICUBIC)
            img.paste((150, 180, 230), (int((x - 1.2 * r) * k), int((y - 1.2 * r) * k)), katman)
        _daire(ImageDraw.Draw(img), k, x, y, r * 0.16, (110, 140, 220))
    _desen(d, k, rng, atom, 9)
    d = ImageDraw.Draw(img)
    _zemin(d, k, (170, 195, 235))


def bilim_dna(img, d, k, rng):
    _gradyan(img, (236, 224, 250), (214, 200, 240), 0, ZEMIN_Y, k)
    for cx in (170, 910):
        for i in range(0, 34):
            y = 120 + i * 40
            a = i * 0.45
            x1, x2 = cx + 90 * math.sin(a), cx - 90 * math.sin(a)
            d.line(_P(k, [(x1, y), (x2, y)]), fill=(200, 180, 230), width=int(6 * k))
            _daire(d, k, x1, y, 13, (170, 120, 220))
            _daire(d, k, x2, y, 13, (240, 140, 180))
    _zemin(d, k, (190, 170, 225))


# ---- TARIH ----------------------------------------------------------------------------
def tarih_sutun(img, d, k, rng):
    _gradyan(img, (200, 225, 245), (250, 236, 210), 0, ZEMIN_Y, k)
    tas = (236, 226, 204)
    d.polygon(_P(k, [(60, 520), (540, 330), (1020, 520)]), fill=tas)
    d.rectangle([60 * k, 520 * k, 1020 * k, 580 * k], fill=(222, 210, 186))
    for x in (110, 300, 690, 880):
        d.rectangle([x * k, 580 * k, (x + 90) * k, ZEMIN_Y * k], fill=tas)
        for j in range(1, 4):
            d.line(_P(k, [(x + j * 22, 600), (x + j * 22, ZEMIN_Y - 20)]), fill=(214, 202, 178), width=int(4 * k))
        d.rectangle([(x - 14) * k, 580 * k, (x + 104) * k, 612 * k], fill=(222, 210, 186))
    _zemin(d, k, (214, 200, 170))


def tarih_piramit(img, d, k, rng):
    _gradyan(img, (160, 210, 240), (250, 225, 180), 0, ZEMIN_Y, k)
    _daire(d, k, 200, 350, 70, (255, 245, 200))
    for x, s, renk in ((780, 1.0, (225, 185, 120)), (430, 0.7, (215, 175, 115)), (980, 0.5, (210, 170, 110))):
        d.polygon(_P(k, [(x - 300 * s, ZEMIN_Y), (x, ZEMIN_Y - 360 * s), (x + 300 * s, ZEMIN_Y)]), fill=renk)
        d.polygon(_P(k, [(x, ZEMIN_Y - 360 * s), (x + 300 * s, ZEMIN_Y), (x + 60 * s, ZEMIN_Y)]), fill=_karis(renk, (0, 0, 0), 0.12))
    _zemin(d, k, (232, 205, 150))


def tarih_kale(img, d, k, rng):
    _gradyan(img, (190, 215, 235), (215, 230, 240), 0, ZEMIN_Y, k)
    _bulut(d, k, 820, 380, 60, (245, 250, 255))
    tas = (170, 168, 175)
    d.rectangle([0, 900 * k, W * k, ZEMIN_Y * k], fill=tas)
    for x in range(0, W, 120):
        d.rectangle([x * k, 840 * k, (x + 70) * k, 900 * k], fill=tas)
    for j, y in enumerate(range(920, ZEMIN_Y, 60)):
        for x in range(-60 if j % 2 else 0, W, 120):
            d.rectangle([(x + 4) * k, (y + 4) * k, (x + 116) * k, (y + 56) * k], outline=(150, 148, 156), width=int(3 * k))
    for x in (150, 930):
        d.rectangle([(x - 70) * k, 640 * k, (x + 70) * k, 900 * k], fill=(160, 158, 166))
        d.polygon(_P(k, [(x - 80, 640), (x, 520), (x + 80, 640)]), fill=(180, 90, 90))
    _zemin(d, k, (150, 140, 120))


def tarih_harita(img, d, k, rng):
    _gradyan(img, (240, 226, 196), (226, 206, 170), 0, ZEMIN_Y, k)
    for _ in range(9):
        x, y = rng.uniform(80, W - 80), rng.uniform(450, ZEMIN_Y - 80)
        pts = [(x + rng.uniform(60, 150) * math.cos(a), y + rng.uniform(40, 110) * math.sin(a)) for a in [i * math.pi / 5 for i in range(10)]]
        d.polygon(_P(k, pts), fill=(214, 190, 150))
    for _ in range(5):
        pts = [(rng.uniform(80, W - 80), rng.uniform(450, ZEMIN_Y - 80)) for _ in range(5)]
        for a, b in zip(pts, pts[1:]):
            d.line(_P(k, [a, b]), fill=(170, 80, 70), width=int(4 * k))
    _daire(d, k, 900, 560, 70, None, (150, 110, 80), 5)
    d.polygon(_P(k, [(900, 500), (912, 560), (900, 620), (888, 560)]), fill=(170, 80, 70))
    _zemin(d, k, (196, 160, 115))


# ---- INSAN VUCUDU ---------------------------------------------------------------------
def vucut_hastane(img, d, k, rng):
    _gradyan(img, (226, 244, 246), (210, 236, 240), 0, ZEMIN_Y, k)
    for x in (120, 960):   # pencere
        d.rounded_rectangle([(x - 90) * k, 520 * k, (x + 90) * k, 780 * k], radius=int(12 * k), fill=(200, 232, 245), outline=(250, 252, 255), width=int(14 * k))
    for _ in range(22):
        x, y, s = rng.uniform(60, W - 60), rng.uniform(450, ZEMIN_Y - 80), rng.uniform(18, 34)
        d.rectangle([(x - s / 3) * k, (y - s) * k, (x + s / 3) * k, (y + s) * k], fill=(160, 215, 220))
        d.rectangle([(x - s) * k, (y - s / 3) * k, (x + s) * k, (y + s / 3) * k], fill=(160, 215, 220))
    _zemin(d, k, (180, 215, 220))


def vucut_ekg(img, d, k, rng):
    _gradyan(img, (255, 232, 236), (252, 214, 222), 0, ZEMIN_Y, k)
    for y in range(0, ZEMIN_Y, 60):
        d.line(_P(k, [(0, y), (W, y)]), fill=(250, 205, 214), width=int(2 * k))
    for x in range(0, W, 60):
        d.line(_P(k, [(x, 0), (x, ZEMIN_Y)]), fill=(250, 205, 214), width=int(2 * k))
    for y0 in (620, 1060):
        pts, x = [], 0
        while x < W:
            pts += [(x, y0), (x + 80, y0), (x + 100, y0 - 30), (x + 120, y0), (x + 140, y0 + 20), (x + 160, y0 - 120), (x + 180, y0 + 50), (x + 200, y0), (x + 260, y0)]
            x += 260
        d.line(_P(k, pts), fill=(232, 110, 130), width=int(7 * k), joint="curve")
    _zemin(d, k, (236, 180, 190))


def vucut_hucre(img, d, k, rng):
    _gradyan(img, (255, 228, 222), (250, 210, 205), 0, ZEMIN_Y, k)

    def hucre(x, y, rng):
        r = rng.uniform(34, 62)
        _daire(d, k, x, y, r, (236, 130, 130))
        _daire(d, k, x, y, r * 0.5, (222, 110, 112))
    _desen(d, k, rng, hucre, 22)
    _zemin(d, k, (226, 160, 160))


def vucut_noron(img, d, k, rng):
    _gradyan(img, (226, 230, 252), (208, 214, 246), 0, ZEMIN_Y, k)
    noktalar = [(rng.uniform(40, W - 40), rng.uniform(420, ZEMIN_Y - 60)) for _ in range(20)]
    for a in noktalar:
        yakinlar = sorted(noktalar, key=lambda b: (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)[1:3]
        for b in yakinlar:
            d.line(_P(k, [a, b]), fill=(170, 175, 235), width=int(5 * k))
    for x, y in noktalar:
        _daire(d, k, x, y, 16, (140, 150, 230))
    _zemin(d, k, (180, 186, 235))


# ---- PSIKOLOJI ------------------------------------------------------------------------
def psiko_oda(img, d, k, rng):
    _gradyan(img, (226, 214, 196), (212, 198, 178), 0, ZEMIN_Y, k)
    for x in range(0, W, 54):
        d.rectangle([x * k, 0, (x + 22) * k, ZEMIN_Y * k], fill=(218, 204, 184))
    for x, y, w, h in ((110, 520, 220, 170), (420, 470, 160, 200), (700, 560, 250, 160)):
        d.rectangle([x * k, y * k, (x + w) * k, (y + h) * k], fill=(240, 232, 216), outline=(150, 112, 80), width=int(12 * k))
    for a, b in (((220, 605), (500, 570)), ((500, 570), (825, 640))):
        d.line(_P(k, [a, b]), fill=(200, 70, 70), width=int(4 * k))
    _zemin(d, k, (150, 108, 76))


def psiko_soru(img, d, k, rng):
    _gradyan(img, (236, 230, 252), (220, 212, 246), 0, ZEMIN_Y, k)
    from PIL import ImageFont
    font_yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "DejaVuSans-Bold.ttf")
    for _ in range(22):
        x, y = rng.uniform(40, W - 40), rng.uniform(420, ZEMIN_Y - 40)
        boy = int(rng.uniform(60, 140) * k)
        d.text((x * k, y * k), "?", font=ImageFont.truetype(font_yol, boy), fill=rng.choice([(200, 186, 240), (186, 200, 245), (230, 190, 230)]), anchor="mm")
    _zemin(d, k, (196, 184, 236))


def psiko_dusunce(img, d, k, rng):
    _gradyan(img, (220, 238, 250), (236, 244, 252), 0, ZEMIN_Y, k)
    for x, y, r in ((250, 620, 120), (800, 760, 100), (520, 1080, 80)):
        _bulut(d, k, x, y, r, (255, 255, 255))
        _daire(d, k, x - r * 0.4, y + r * 1.4, r * 0.18, (255, 255, 255))
        _daire(d, k, x - r * 0.6, y + r * 1.8, r * 0.1, (255, 255, 255))
    _zemin(d, k, (190, 214, 236))


def psiko_gece(img, d, k, rng):
    _gradyan(img, (40, 46, 84), (90, 90, 140), 0, ZEMIN_Y, k)
    _daire(d, k, 820, 380, 80, (250, 240, 200))
    _yildizlar(d, k, rng, 60, (220, 220, 250), y_max=900)
    x = 0
    while x < W:
        w, h = rng.uniform(80, 150), rng.uniform(260, 620)
        d.rectangle([x * k, (ZEMIN_Y - h) * k, (x + w) * k, ZEMIN_Y * k], fill=(60, 62, 100))
        for wy in range(int(ZEMIN_Y - h + 30), ZEMIN_Y - 30, 50):
            for wx in range(int(x + 16), int(x + w - 20), 34):
                if rng.random() < 0.35:
                    d.rectangle([wx * k, wy * k, (wx + 14) * k, (wy + 20) * k], fill=(250, 220, 140))
        x += w + rng.uniform(4, 20)
    _zemin(d, k, (70, 70, 104))


# ---- TEKNOLOJI ------------------------------------------------------------------------
def tek_devre(img, d, k, rng):
    _gradyan(img, (210, 238, 222), (190, 226, 206), 0, ZEMIN_Y, k)
    for _ in range(26):
        x, y = rng.uniform(0, W), rng.uniform(400, ZEMIN_Y)
        x2 = x + rng.choice((-1, 1)) * rng.uniform(80, 240)
        y2 = y + rng.uniform(60, 160)
        d.line(_P(k, [(x, y), (x2, y), (x2, y2)]), fill=(140, 200, 165), width=int(6 * k))
        _daire(d, k, x, y, 10, (110, 180, 140))
        _daire(d, k, x2, y2, 10, (110, 180, 140))
    for x, y in ((180, 700), (820, 980)):
        d.rounded_rectangle([x * k, y * k, (x + 130) * k, (y + 130) * k], radius=int(10 * k), fill=(90, 110, 100))
    _zemin(d, k, (150, 200, 170))


def tek_neon(img, d, k, rng):
    _gradyan(img, (40, 24, 80), (120, 50, 130), 0, ZEMIN_Y, k)
    _daire(d, k, 540, 900, 230, (255, 150, 120))
    for i in range(6):
        y = 790 + i * 50
        d.rectangle([300 * k, y * k, 780 * k, (y + 14 + i * 3) * k], fill=(120, 50, 130))
    d.rectangle([0, ZEMIN_Y * k, W * k, H * k], fill=(30, 18, 60))
    for i in range(-10, 11):
        d.line(_P(k, [(540 + i * 40, ZEMIN_Y), (540 + i * 180, H)]), fill=(240, 90, 200), width=int(4 * k))
    for j in range(8):
        y = ZEMIN_Y + (j ** 1.6) * 14
        d.line(_P(k, [(0, y), (W, y)]), fill=(240, 90, 200), width=int(4 * k))


def tek_piksel(img, d, k, rng):
    _gradyan(img, (150, 200, 250), (190, 225, 252), 0, ZEMIN_Y, k)
    p = 40
    for bx, by in ((160, 360), (760, 460)):
        for dx, dy in ((0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (3, 1), (-1, 1)):
            d.rectangle([(bx + dx * p) * k, (by + dy * p) * k, (bx + dx * p + p) * k, (by + dy * p + p) * k], fill=(250, 252, 255))
    for x in range(0, W, p * 2):
        h = rng.choice((2, 3, 4, 5))
        for j in range(h):
            d.rectangle([x * k, (ZEMIN_Y - (j + 1) * p) * k, (x + p * 2 - 4) * k, (ZEMIN_Y - j * p - 4) * k], fill=(110, 190, 110))
    for x, y in ((300, 900), (360, 900), (330, 840), (780, 800)):
        d.rectangle([x * k, y * k, (x + 36) * k, (y + 36) * k], fill=(250, 200, 70), outline=(200, 140, 40), width=int(4 * k))
    _zemin(d, k, (170, 120, 80))


def tek_kod(img, d, k, rng):
    _gradyan(img, (30, 40, 70), (40, 52, 90), 0, ZEMIN_Y, k)
    renkler = [_karis(r, (35, 46, 80), 0.45) for r in [(120, 200, 255), (250, 190, 110), (170, 230, 150), (230, 140, 200), (150, 160, 200)]]
    y = 440
    while y < ZEMIN_Y - 40:
        x = 60 + rng.choice((0, 0, 40, 80))
        for _ in range(rng.randrange(2, 6)):
            w = rng.uniform(40, 170)
            d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + 18) * k], radius=int(9 * k), fill=rng.choice(renkler))
            x += w + 20
            if x > W - 100:
                break
        y += 44
    _zemin(d, k, (50, 62, 100))


# ---- COGRAFYA -------------------------------------------------------------------------
def cog_deniz(img, d, k, rng):
    _gradyan(img, (170, 215, 245), (225, 240, 250), 0, 1150, k)
    _bulut(d, k, 240, 360, 70, (255, 255, 255))
    _bulut(d, k, 820, 520, 50, (255, 255, 255))
    _gradyan(img, (90, 160, 210), (60, 120, 180), 1150, ZEMIN_Y, k)
    d = ImageDraw.Draw(img)
    d.polygon(_P(k, [(760, 1140), (900, 1140), (880, 1170), (780, 1170)]), fill=(150, 90, 70))
    d.polygon(_P(k, [(826, 1140), (826, 990), (890, 1130)]), fill=(250, 250, 250))
    for y in (1220, 1320, 1420):
        _dalga(d, k, y, 10, 160, _karis((90, 160, 210), (60, 120, 180), (y - 1150) / 400), alt=y + 40, faz=y)
    _zemin(d, k, (236, 214, 166))


def cog_dag(img, d, k, rng):
    _gradyan(img, (180, 220, 245), (230, 242, 250), 0, ZEMIN_Y, k)
    _bulut(d, k, 780, 380, 64, (255, 255, 255))
    _dag(d, k, [(0, 1050), (250, 760), (480, 1080), (760, 700), (1080, 1000)], ZEMIN_Y, (150, 175, 200))
    for x, y in ((250, 760), (760, 700)):
        d.polygon(_P(k, [(x, y), (x - 70, y + 90), (x + 70, y + 90)]), fill=(250, 252, 255))
    _dag(d, k, [(0, 1300), (300, 1200), (650, 1310), (1080, 1220)], ZEMIN_Y, (130, 180, 120))
    _zemin(d, k, (120, 170, 105))


def cog_harita(img, d, k, rng):
    _gradyan(img, (190, 225, 245), (170, 212, 240), 0, ZEMIN_Y, k)
    for y in range(440, ZEMIN_Y, 110):
        d.line(_P(k, [(0, y), (W, y)]), fill=(205, 232, 248), width=int(3 * k))
    for x in range(0, W, 110):
        d.line(_P(k, [(x, 400), (x, ZEMIN_Y)]), fill=(205, 232, 248), width=int(3 * k))
    for _ in range(7):
        x, y = rng.uniform(100, W - 100), rng.uniform(480, ZEMIN_Y - 120)
        pts = [(x + rng.uniform(60, 170) * math.cos(a), y + rng.uniform(40, 120) * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]]
        d.polygon(_P(k, pts), fill=(170, 210, 150))
    _zemin(d, k, (130, 180, 215))


def cog_ada(img, d, k, rng):
    _gradyan(img, (150, 215, 240), (240, 230, 200), 0, 1250, k)
    _daire(d, k, 820, 400, 90, (255, 240, 190))
    _gradyan(img, (80, 190, 200), (60, 160, 190), 1250, ZEMIN_Y, k)
    d = ImageDraw.Draw(img)
    for x0 in (140, 930):
        d.line(_P(k, [(x0, ZEMIN_Y), (x0 + 30, 1000)]), fill=(140, 100, 70), width=int(26 * k))
        for a in range(5):
            ang = math.pi * (0.95 + a * 0.28)
            d.line(_P(k, [(x0 + 30, 1000), (x0 + 30 + 170 * math.cos(ang), 1000 + 90 * math.sin(ang) + 60)]), fill=(80, 160, 90), width=int(30 * k))
    _zemin(d, k, (240, 220, 170))


# ---- BURCLAR --------------------------------------------------------------------------
def burc_takim(img, d, k, rng):
    _gradyan(img, (18, 22, 60), (52, 40, 100), 0, ZEMIN_Y, k)
    _yildizlar(d, k, rng, 120, (200, 205, 240))
    for _ in range(4):
        cx, cy = rng.uniform(150, W - 150), rng.uniform(450, 1250)
        pts = [(cx + rng.uniform(-150, 150), cy + rng.uniform(-110, 110)) for _ in range(5)]
        d.line(_P(k, pts), fill=(140, 150, 220), width=int(3 * k))
        for x, y in pts:
            _yildiz5(d, k, x, y, 13, (255, 230, 150))
    _zemin(d, k, (44, 36, 90))


def burc_hilal(img, d, k, rng):
    _gradyan(img, (70, 40, 110), (190, 110, 160), 0, ZEMIN_Y, k)
    _yildizlar(d, k, rng, 90, (250, 230, 250))
    maske = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(maske)
    md.ellipse([(780 - 120) * k, (520 - 120) * k, (780 + 120) * k, (520 + 120) * k], fill=255)
    md.ellipse([(830 - 112) * k, (480 - 112) * k, (830 + 112) * k, (480 + 112) * k], fill=0)
    img.paste((255, 240, 200), (0, 0), maske)
    for x, y in ((200, 700), (420, 420), (900, 1050)):
        _yildiz5(d, k, x, y, 26, (255, 225, 150))
    _zemin(d, k, (120, 70, 130))


def burc_cember(img, d, k, rng):
    _gradyan(img, (30, 30, 70), (60, 50, 110), 0, ZEMIN_Y, k)
    _yildizlar(d, k, rng, 80, (200, 200, 240))
    cx, cy = 540, 900
    for r in (360, 300):
        d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], outline=(120, 110, 190), width=int(5 * k))
    for i in range(12):
        a = i * math.pi / 6
        d.line(_P(k, [(cx + 300 * math.cos(a), cy + 300 * math.sin(a)), (cx + 360 * math.cos(a), cy + 360 * math.sin(a))]), fill=(120, 110, 190), width=int(5 * k))
        b = a + math.pi / 12
        _yildiz5(d, k, cx + 330 * math.cos(b), cy + 330 * math.sin(b), 12, (240, 210, 140))
    _zemin(d, k, (50, 42, 96))


def burc_gozlem(img, d, k, rng):
    _gradyan(img, (24, 30, 72), (70, 70, 130), 0, ZEMIN_Y, k)
    _yildizlar(d, k, rng, 130, (220, 225, 255))
    d.rectangle([660 * k, 1180 * k, 1000 * k, ZEMIN_Y * k], fill=(90, 92, 140))
    d.chord([640 * k, 1020 * k, 1020 * k, 1340 * k], 180, 360, fill=(120, 124, 175))
    d.line(_P(k, [(830, 1110), (930, 960)]), fill=(70, 72, 120), width=int(34 * k))
    _dag(d, k, [(0, 1380), (300, 1300), (560, 1400)], ZEMIN_Y, (60, 62, 110))
    _zemin(d, k, (60, 58, 104))


# ---- COCUK SORULARI -------------------------------------------------------------------
def cocuk_gokkusagi(img, d, k, rng):
    _gradyan(img, (190, 230, 252), (230, 245, 252), 0, ZEMIN_Y, k)
    for i, renk in enumerate([(240, 120, 120), (250, 180, 100), (250, 225, 110), (140, 210, 130), (120, 180, 240), (170, 140, 220)]):
        r = 520 - i * 38
        d.arc([(540 - r) * k, (1250 - r) * k, (540 + r) * k, (1250 + r) * k], 180, 360, fill=renk, width=int(38 * k))
    _bulut(d, k, 130, 1180, 90, (255, 255, 255))
    _bulut(d, k, 950, 1180, 90, (255, 255, 255))
    _zemin(d, k, (150, 210, 130))


def cocuk_konfeti(img, d, k, rng):
    _gradyan(img, (255, 244, 230), (255, 236, 240), 0, ZEMIN_Y, k)
    renkler = [(240, 120, 130), (250, 190, 90), (120, 200, 150), (110, 170, 240), (190, 140, 230)]
    for _ in range(90):
        x, y, s = rng.uniform(0, W), rng.uniform(380, ZEMIN_Y), rng.uniform(8, 16)
        a = rng.uniform(0, math.pi)
        d.polygon(_P(k, [(x + s * math.cos(a) * 1.8, y + s * math.sin(a)), (x - s * math.sin(a), y + s * math.cos(a)),
                        (x - s * math.cos(a) * 1.8, y - s * math.sin(a)), (x + s * math.sin(a), y - s * math.cos(a))]), fill=rng.choice(renkler))
    for i, (x, renk) in enumerate(((120, (240, 120, 130)), (230, (110, 170, 240)), (175, (250, 190, 90)), (900, (120, 200, 150)), (1010, (190, 140, 230)))):
        y = ZEMIN_Y - 110 - (220 if i in (2,) else 0)
        d.rounded_rectangle([(x - 55) * k, y * k, (x + 55) * k, (y + 110) * k], radius=int(14 * k), fill=renk)
    _zemin(d, k, (240, 200, 170))


def cocuk_oda(img, d, k, rng):
    _gradyan(img, (214, 236, 252), (230, 222, 250), 0, ZEMIN_Y, k)
    for _ in range(26):
        _yildiz5(d, k, rng.uniform(40, W - 40), rng.uniform(420, ZEMIN_Y - 100), rng.uniform(14, 28), (255, 236, 160))
    d.rounded_rectangle([90 * k, 520 * k, 330 * k, 780 * k], radius=int(16 * k), fill=(190, 225, 250), outline=(250, 250, 255), width=int(16 * k))
    d.line(_P(k, [(210, 520), (210, 780)]), fill=(250, 250, 255), width=int(10 * k))
    _bulut(d, k, 200, 640, 40, (255, 255, 255))
    _zemin(d, k, (200, 170, 140))
    for x in range(0, W, 120):
        d.line(_P(k, [(x, ZEMIN_Y), (x - 60, H)]), fill=(185, 155, 125), width=int(4 * k))


def cocuk_balon(img, d, k, rng):
    _gradyan(img, (160, 215, 250), (220, 240, 252), 0, ZEMIN_Y, k)
    _bulut(d, k, 820, 1250, 80, (255, 255, 255))
    for _ in range(14):
        x, y = rng.uniform(60, W - 60), rng.uniform(420, 1300)
        r = rng.uniform(40, 62)
        renk = rng.choice([(240, 120, 130), (250, 190, 90), (120, 200, 150), (110, 170, 240), (190, 140, 230)])
        d.line(_P(k, [(x, y + r * 1.2), (x + 10, y + r * 1.2 + 120)]), fill=(150, 150, 170), width=int(3 * k))
        d.ellipse([(x - r) * k, (y - r * 1.2) * k, (x + r) * k, (y + r * 1.2) * k], fill=renk)
        _daire(d, k, x - r * 0.35, y - r * 0.5, r * 0.18, _karis(renk, (255, 255, 255), 0.6))
    _zemin(d, k, (140, 200, 120))


# ---- GENEL (konu eslesmezse) ---------------------------------------------------------------
def genel_krem(img, d, k, rng):
    img.paste((250, 244, 230), [0, 0, W * k, H * k])
    _zemin(d, k, (232, 220, 196), LACI)


def genel_noktali(img, d, k, rng):
    _gradyan(img, (252, 246, 232), (246, 236, 214), 0, ZEMIN_Y, k)
    for y in range(420, ZEMIN_Y, 70):
        for x in range(35 if (y // 70) % 2 else 0, W, 70):
            _daire(d, k, x, y, 6, (240, 222, 190))
    _zemin(d, k, (232, 214, 182))


TEMALAR = {
    "uzay": [uzay_derin, uzay_ay, uzay_bulutsu, uzay_mars],
    "hayvanlar": [hayvan_savan, hayvan_orman, hayvan_deniz, hayvan_kutup],
    "yemek": [yemek_mutfak, yemek_piknik, yemek_meyve, yemek_firin],
    "bilim": [bilim_lab, bilim_tahta, bilim_atom, bilim_dna],
    "tarih": [tarih_sutun, tarih_piramit, tarih_kale, tarih_harita],
    "vucut": [vucut_hastane, vucut_ekg, vucut_hucre, vucut_noron],
    "psikoloji": [psiko_oda, psiko_soru, psiko_dusunce, psiko_gece],
    "teknoloji": [tek_devre, tek_neon, tek_piksel, tek_kod],
    "cografya": [cog_deniz, cog_dag, cog_harita, cog_ada],
    "burclar": [burc_takim, burc_hilal, burc_cember, burc_gozlem],
    "cocuk": [cocuk_gokkusagi, cocuk_konfeti, cocuk_oda, cocuk_balon],
    "genel": [genel_krem, genel_noktali],
}
SAHNELER = {f.__name__: f for liste in TEMALAR.values() for f in liste}


def _sade(m):
    m = str(m or "").lower()
    for a, b in zip("çğıöşüâî", "cgiosuai"):
        m = m.replace(a, b)
    return m


ESLESME = [
    (("yemek", "mutfak"), "yemek"), (("burc", "gokyuzu", "astroloji", "zodyak"), "burclar"),
    (("cocuk", "neden"), "cocuk"), (("uzay", "gezegen", "astronomi"), "uzay"),
    (("hayvan",), "hayvanlar"), (("insan vucud", "saglik", "beden"), "vucut"),
    (("tarih",), "tarih"), (("psikoloji", "beyin", "zihin"), "psikoloji"),
    (("teknoloji", "bilgisayar", "internet"), "teknoloji"), (("cografya", "dunya"), "cografya"),
    (("bilim",), "bilim"),
]


def tema_bul(alan):
    a = _sade(alan)
    for anahtarlar, tema in ESLESME:
        if any(x in a for x in anahtarlar):
            return tema
    return "genel"


# --- secim: ayni konuda tekrar etme --------------------------------------------------------
def _gecmis_yolu():
    from ortak import KOK
    return os.path.join(KOK, "arka_gecmis.json")


def gecmis():
    try:
        with open(_gecmis_yolu(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, ImportError):
        return []


def secim(alan, kaydet=True):
    """Konuya uygun, son kullanilanlardan farkli bir sahne adi secer ve gecmise yazar."""
    tema = tema_bul(alan)
    adaylar = [f.__name__ for f in TEMALAR[tema]]
    son = gecmis()
    yasak = set([x for x in reversed(son) if x in adaylar][:max(0, len(adaylar) - 2)])  # 4 sahnede son 2'si tekrar edilmez
    secilebilir = [a for a in adaylar if a not in yasak] or adaylar
    ad = random.choice(secilebilir)
    if kaydet:
        try:
            with open(_gecmis_yolu(), "w", encoding="utf-8") as f:
                json.dump((son + [ad])[-60:], f)
        except (OSError, ImportError):
            pass
    return ad


def ciz(ad, k=2, bulanik=True):
    """Sahneyi W*k x H*k boyutunda cizer. bulanik: zemin ustundeki motifler hafif yumusatilir."""
    f = SAHNELER.get(ad) or genel_krem
    img = Image.new("RGB", (W * k, H * k), (250, 244, 230))
    rng = random.Random(ad)
    f(img, ImageDraw.Draw(img), k, rng)
    if bulanik:
        ust = img.crop((0, 0, W * k, ZEMIN_Y * k)).filter(ImageFilter.GaussianBlur(2.2 * k))
        img.paste(ust, (0, 0))
        ImageDraw.Draw(img).line([(0, ZEMIN_Y * k), (W * k, ZEMIN_Y * k)], fill=_karis(img.getpixel((5, ZEMIN_Y * k + 30)), (0, 0, 0), 0.35), width=int(6 * k))
    return img


def golge_ekle(img, x, k=2, olcek=1.0):
    """Bidik'in ayaklarinin altina yumusak golge (zemine 'bassin'). x: piksel (k dahil), olcek: Bidik olcegi."""
    gw, gh = int(250 * olcek * k), int(26 * olcek * k)
    pay = int(24 * k)
    katman = Image.new("L", (gw + 2 * pay, gh + 2 * pay), 0)
    ImageDraw.Draw(katman).ellipse([pay, pay, pay + gw, pay + gh], fill=80)
    katman = katman.filter(ImageFilter.GaussianBlur(8 * k))
    img.paste((0, 0, 0), (int(x - katman.width / 2), int(ZEMIN_Y * k - katman.height / 2)), katman)
