"""
Konuya gore arka planlar (tamamen kodla cizilir, Bidik'in cizgi tarzina uygun).

- Her konu (tema) icin 5 sahne var; renkler yumusak tutulur ki Bidik, altyazi ve bilgi karti one ciksin.
- secim(tema): son kullanilanlari BIDIK\\arka_gecmis.json'da tutar, art arda aynisini SECMEZ.
- ciz(tema, no, genislik, yukseklik): bir kere cizilir, videonun her karesinde kopyasi kullanilir.
Zemin cizgisi her zaman yuksekligin %80'inde (Bidik'in bastigi yer).
"""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFilter

LACI = (35, 37, 58)
ZEMIN_ORAN = 0.80


# --- yardimcilar -------------------------------------------------------------------
def _karis(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _dikey_gecis(d, w, y0, y1, ust, alt):
    for y in range(int(y0), int(y1)):
        d.line([(0, y), (w, y)], fill=_karis(ust, alt, (y - y0) / max(1, y1 - y0)))


def _zemin(d, w, h, renk, cizgi=True):
    zy = int(h * ZEMIN_ORAN)
    d.rectangle([0, zy, w, h], fill=renk)
    if cizgi:
        d.line([(0, zy), (w, zy)], fill=LACI, width=max(2, int(w / 180)))
    return zy


def _yildiz(d, cx, cy, r, renk):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=renk)


def _bulut(d, cx, cy, r, renk):
    for dx, dy, rr in ((-1.0, 0.25, 0.75), (-0.35, -0.2, 1.0), (0.45, -0.05, 0.85), (1.05, 0.3, 0.6)):
        R = r * rr
        d.ellipse([cx + dx * r - R, cy + dy * r - R, cx + dx * r + R, cy + dy * r + R], fill=renk)
    d.rounded_rectangle([cx - r * 1.5, cy + r * 0.05, cx + r * 1.6, cy + r * 0.85], radius=int(r * 0.4), fill=renk)


def _tepeler(d, w, taban, yukseklik, renk, dalga=2.0, faz=0.0):
    pts = [(0, taban)]
    for i in range(0, 41):
        x = w * i / 40
        pts.append((x, taban - yukseklik * (0.55 + 0.45 * math.sin(i / 40 * math.pi * dalga + faz))))
    pts.append((w, taban))
    d.polygon(pts, fill=renk)


def _isiltilar(d, w, ust, alt, adet, renk, rnd, rmin, rmax):
    for _ in range(adet):
        x, y, r = rnd.uniform(0, w), rnd.uniform(ust, alt), rnd.uniform(rmin, rmax)
        d.ellipse([x - r, y - r, x + r, y + r], fill=renk)


def _hilal(img, cx, cy, r, ox, oy, renk):
    """Arka plani boyamadan hilal: dolu daireden kaydirilmis daire maskeyle cikarilir."""
    maske = Image.new("L", (int(2 * r) + 2, int(2 * r) + 2), 0)
    md = ImageDraw.Draw(maske)
    md.ellipse([0, 0, 2 * r, 2 * r], fill=255)
    md.ellipse([ox, oy, 2 * r + ox, 2 * r + oy], fill=0)
    img.paste(Image.new("RGB", maske.size, renk), (int(cx - r), int(cy - r)), maske)


def _bulanik_daireler(img, w, ust, alt, adet, renkler, rnd, rmin, rmax, bulanik):
    """Yumusak 'bokeh' daireleri (derinlik hissi)."""
    katman = Image.new("RGBA", img.size, (0, 0, 0, 0))
    kd = ImageDraw.Draw(katman)
    for _ in range(adet):
        x, y, r = rnd.uniform(0, w), rnd.uniform(ust, alt), rnd.uniform(rmin, rmax)
        kd.ellipse([x - r, y - r, x + r, y + r], fill=rnd.choice(renkler))
    katman = katman.filter(ImageFilter.GaussianBlur(bulanik))
    img.paste(katman, (0, 0), katman)


# --- UZAY -------------------------------------------------------------------------
def uzay(img, d, w, h, k, no, rnd):
    paletler = [((18, 22, 60), (52, 40, 110)), ((10, 18, 44), (30, 70, 120)), ((40, 20, 70), (110, 50, 120)),
                ((14, 16, 36), (40, 44, 80)), ((20, 30, 70), (60, 30, 90))]
    ust, alt = paletler[no]
    zy = int(h * ZEMIN_ORAN)
    _dikey_gecis(d, w, 0, zy, ust, alt)
    if no == 2:   # bulutsu
        _bulanik_daireler(img, w, 0, zy, 9, [(255, 120, 200, 70), (120, 160, 255, 70), (180, 120, 255, 60)], rnd, 120 * k, 260 * k, 70 * k)
    for _ in range(140):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, zy), rnd.uniform(1.2, 3.4) * k
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255) if rnd.random() < 0.7 else (255, 230, 150))
    for _ in range(6):
        _yildiz(d, rnd.uniform(40 * k, w - 40 * k), rnd.uniform(60 * k, zy * 0.75), rnd.uniform(9, 16) * k, (255, 236, 160))
    if no in (0, 4):   # halkali gezegen
        px, py, pr = w * (0.80 if no == 0 else 0.22), h * 0.36, 95 * k
        d.ellipse([px - pr * 1.9, py - pr * 0.45, px + pr * 1.9, py + pr * 0.45], outline=(255, 210, 140), width=int(10 * k))
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(240, 150, 90), outline=LACI, width=int(5 * k))
        d.chord([px - pr, py - pr, px + pr, py + pr], 20, 160, fill=(215, 115, 70))
        d.arc([px - pr * 1.9, py - pr * 0.45, px + pr * 1.9, py + pr * 0.45], 0, 180, fill=(255, 210, 140), width=int(10 * k))
    if no == 1:   # uzaktan Dunya
        px, py, pr = w * 0.78, h * 0.33, 120 * k
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(70, 140, 230), outline=LACI, width=int(5 * k))
        for dx, dy, r in ((-0.3, -0.2, 0.42), (0.35, 0.25, 0.32), (0.1, 0.55, 0.2)):
            d.ellipse([px + dx * pr - r * pr, py + dy * pr - r * pr * 0.7, px + dx * pr + r * pr, py + dy * pr + r * pr * 0.7], fill=(80, 180, 110))
        d.arc([px - pr * 0.8, py - pr * 0.8, px + pr * 0.8, py + pr * 0.8], 200, 250, fill=(255, 255, 255), width=int(8 * k))
    if no == 3:   # buyuk ay
        px, py, pr = w * 0.24, h * 0.30, 130 * k
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(236, 232, 214), outline=LACI, width=int(5 * k))
        for dx, dy, r in ((-0.3, -0.25, 0.22), (0.35, 0.1, 0.16), (-0.05, 0.45, 0.12), (0.4, -0.45, 0.1)):
            d.ellipse([px + dx * pr - r * pr, py + dy * pr - r * pr, px + dx * pr + r * pr, py + dy * pr + r * pr], fill=(208, 202, 182))
    if no == 4:   # kayan yildizlar
        for _ in range(3):
            x, y = rnd.uniform(w * 0.4, w), rnd.uniform(60 * k, zy * 0.5)
            d.line([(x, y), (x - 160 * k, y + 70 * k)], fill=(255, 255, 255), width=int(4 * k))
            _yildiz(d, x, y, 12 * k, (255, 255, 255))
    # zemin: ay yuzeyi
    _zemin(d, w, h, (150, 146, 170) if no != 1 else (120, 124, 150))
    for _ in range(9):
        x, y, r = rnd.uniform(0, w), rnd.uniform(zy + 30 * k, h - 20 * k), rnd.uniform(18, 46) * k
        d.ellipse([x - r, y - r * 0.4, x + r, y + r * 0.4], fill=(128, 124, 150))


# --- BURCLAR / GOKYUZU --------------------------------------------------------------
TAKIMYILDIZLAR = [
    [(0, 0), (1, 0.4), (2, 0.2), (2.8, 0.9), (3.6, 0.5)],
    [(0, 1), (0.8, 0.2), (1.6, 0.8), (2.4, 0), (3.2, 0.7)],
    [(0, 0.5), (1, 0), (1.2, 1), (2.2, 1.3), (2.6, 0.4)],
]


def burclar(img, d, w, h, k, no, rnd):
    paletler = [((34, 26, 80), (110, 70, 150)), ((20, 30, 70), (90, 60, 140)), ((50, 30, 90), (170, 90, 140)),
                ((24, 22, 60), (70, 80, 150)), ((40, 24, 70), (120, 60, 120))]
    ust, alt = paletler[no]
    zy = int(h * ZEMIN_ORAN)
    _dikey_gecis(d, w, 0, zy, ust, alt)
    _bulanik_daireler(img, w, 0, zy, 6, [(255, 200, 255, 50), (180, 200, 255, 50)], rnd, 140 * k, 260 * k, 80 * k)
    for _ in range(110):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, zy), rnd.uniform(1.2, 3.0) * k
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    # takimyildizlar (noktalar + ince cizgiler)
    for j in range(3):
        sekil = TAKIMYILDIZLAR[(no + j) % 3]
        ox, oy, olc = rnd.uniform(60 * k, w - 360 * k), rnd.uniform(80 * k, zy * 0.62), rnd.uniform(70, 95) * k
        pts = [(ox + a * olc, oy + b * olc) for a, b in sekil]
        d.line(pts, fill=(200, 200, 255), width=int(3 * k))
        for p in pts:
            _yildiz(d, p[0], p[1], 11 * k, (255, 236, 160))
    if no in (0, 2, 4):   # hilal
        px, py, pr = w * (0.82 if no != 2 else 0.18), h * 0.12, 70 * k
        _hilal(img, px, py, pr, 30 * k, -12 * k, (255, 226, 140))
    if no in (1, 3):   # burc carki (12 dilimli halka)
        cx, cy, r = w * 0.5, h * 0.40, 330 * k
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(200, 190, 255), width=int(5 * k))
        d.ellipse([cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8], outline=(160, 150, 230), width=int(3 * k))
        for i in range(12):
            a = i * math.pi / 6
            d.line([(cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8), (cx + math.cos(a) * r, cy + math.sin(a) * r)],
                   fill=(200, 190, 255), width=int(3 * k))
            am = a + math.pi / 12
            _yildiz(d, cx + math.cos(am) * r * 0.9, cy + math.sin(am) * r * 0.9, 9 * k, (255, 236, 160))
    _zemin(d, w, h, (64, 52, 110))
    _tepeler(d, w, zy, 30 * k, (52, 42, 96), 3, no)


# --- HAYVANLAR -------------------------------------------------------------------------
def _agac_akasya(d, x, taban, k, renk_govde=(110, 80, 50), renk_yaprak=(80, 140, 70)):
    d.line([(x, taban), (x - 10 * k, taban - 170 * k)], fill=renk_govde, width=int(16 * k))
    d.line([(x - 6 * k, taban - 120 * k), (x + 50 * k, taban - 190 * k)], fill=renk_govde, width=int(10 * k))
    d.ellipse([x - 140 * k, taban - 250 * k, x + 120 * k, taban - 170 * k], fill=renk_yaprak)


def hayvanlar(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no == 0:   # savan
        _dikey_gecis(d, w, 0, zy, (255, 214, 150), (255, 240, 200))
        d.ellipse([w * 0.62, h * 0.18, w * 0.62 + 260 * k, h * 0.18 + 260 * k], fill=(255, 170, 90))
        _tepeler(d, w, zy, 120 * k, (226, 196, 130), 1.4, 0.5)
        _agac_akasya(d, w * 0.15, zy - 10 * k, k * 1.1, (110, 80, 50), (120, 150, 70))
        _agac_akasya(d, w * 0.86, zy - 30 * k, k * 0.8, (110, 80, 50), (120, 150, 70))
        _zemin(d, w, h, (214, 180, 110))
    elif no == 1:   # orman
        _dikey_gecis(d, w, 0, zy, (190, 230, 200), (230, 245, 220))
        for i in range(9):
            x = w * (i / 8) + rnd.uniform(-30, 30) * k
            r = rnd.uniform(120, 190) * k
            d.ellipse([x - r, zy - r * 2.2, x + r, zy - r * 0.3], fill=rnd.choice([(90, 160, 100), (110, 175, 110), (75, 145, 95)]))
        for i in range(6):
            x = rnd.uniform(0, w)
            d.rectangle([x - 12 * k, zy - 260 * k, x + 12 * k, zy], fill=(120, 90, 60))
        _zemin(d, w, h, (120, 170, 90))
    elif no == 2:   # su alti
        _dikey_gecis(d, w, 0, zy, (110, 200, 230), (40, 120, 190))
        for i in range(5):   # isik huzmeleri
            x = w * (0.1 + i * 0.22)
            d.polygon([(x, 0), (x + 70 * k, 0), (x + 200 * k, zy), (x + 80 * k, zy)], fill=(150, 220, 240))
        _isiltilar(d, w, 0, zy, 30, (200, 240, 255), rnd, 5 * k, 14 * k)
        for i in range(4):   # baliklar
            x, y, r = rnd.uniform(80 * k, w - 80 * k), rnd.uniform(zy * 0.2, zy * 0.7), rnd.uniform(26, 40) * k
            renk = rnd.choice([(255, 150, 80), (255, 210, 80), (240, 110, 140)])
            d.ellipse([x - r * 1.4, y - r * 0.8, x + r * 1.4, y + r * 0.8], fill=renk)
            d.polygon([(x + r * 1.2, y), (x + r * 2.2, y - r * 0.8), (x + r * 2.2, y + r * 0.8)], fill=renk)
            d.ellipse([x - r * 0.9, y - r * 0.25, x - r * 0.5, y + r * 0.15], fill=LACI)
        for i in range(7):   # yosun
            x = rnd.uniform(0, w)
            d.line([(x, zy), (x + 20 * k, zy - 160 * k), (x - 10 * k, zy - 260 * k)], fill=(60, 160, 110), width=int(14 * k), joint="curve")
        _zemin(d, w, h, (230, 210, 160))
    elif no == 3:   # ciftlik
        _dikey_gecis(d, w, 0, zy, (150, 210, 255), (220, 240, 255))
        _bulut(d, w * 0.25, h * 0.14, 70 * k, (255, 255, 255))
        _bulut(d, w * 0.78, h * 0.22, 55 * k, (255, 255, 255))
        _tepeler(d, w, zy, 160 * k, (140, 200, 110), 1.2, 1.0)
        bx, by = w * 0.78, zy - 40 * k   # ahir
        d.rectangle([bx - 110 * k, by - 160 * k, bx + 110 * k, by], fill=(210, 70, 60), outline=LACI, width=int(5 * k))
        d.polygon([(bx - 130 * k, by - 160 * k), (bx, by - 250 * k), (bx + 130 * k, by - 160 * k)], fill=(170, 50, 50), outline=LACI)
        d.rectangle([bx - 40 * k, by - 90 * k, bx + 40 * k, by], fill=(255, 255, 255), outline=LACI, width=int(4 * k))
        for i in range(12):   # cit
            x = i * w / 11
            d.rectangle([x - 8 * k, zy - 70 * k, x + 8 * k, zy], fill=(250, 240, 220), outline=LACI, width=int(3 * k))
        d.rectangle([0, zy - 55 * k, w, zy - 43 * k], fill=(250, 240, 220))
        _zemin(d, w, h, (120, 180, 90))
    else:   # kutup
        _dikey_gecis(d, w, 0, zy, (190, 225, 255), (235, 245, 255))
        for i in range(3):
            x = w * (0.1 + i * 0.4)
            d.polygon([(x - 220 * k, zy), (x, zy - rnd.uniform(260, 380) * k), (x + 220 * k, zy)], fill=(220, 236, 250), outline=(170, 200, 230))
        _isiltilar(d, w, 0, zy, 60, (255, 255, 255), rnd, 4 * k, 9 * k)
        _zemin(d, w, h, (240, 248, 255))


# --- YEMEK / MUTFAK ------------------------------------------------------------------
def yemek(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    duvarlar = [(255, 236, 214), (220, 240, 230), (255, 226, 226), (230, 236, 255), (255, 244, 200)]
    karolar = [(250, 210, 170), (180, 220, 200), (250, 190, 190), (200, 210, 250), (250, 225, 150)]
    d.rectangle([0, 0, w, zy], fill=duvarlar[no])
    if no in (0, 2, 4):   # fayans
        a = 90 * k
        for y in range(0, zy, int(a)):
            for x in range(0, w, int(a)):
                if ((x // int(a)) + (y // int(a))) % 2 == 0:
                    d.rectangle([x, y, x + a, y + a], fill=karolar[no])
    else:   # cizgili duvar kagidi
        for x in range(0, w, int(60 * k)):
            d.rectangle([x, 0, x + 26 * k, zy], fill=karolar[no])
    # raf + kavanozlar
    ry = h * (0.30 if no % 2 == 0 else 0.42)
    d.rectangle([w * 0.05, ry, w * 0.95, ry + 18 * k], fill=(170, 120, 80), outline=LACI, width=int(4 * k))
    for i in range(5):
        x = w * (0.12 + i * 0.18)
        kh = rnd.uniform(90, 140) * k
        renk = rnd.choice([(255, 180, 80), (230, 90, 80), (120, 190, 120), (240, 220, 120), (200, 140, 220)])
        d.rounded_rectangle([x - 45 * k, ry - kh, x + 45 * k, ry], radius=int(16 * k), fill=(255, 255, 255), outline=LACI, width=int(4 * k))
        d.rounded_rectangle([x - 38 * k, ry - kh * 0.7, x + 38 * k, ry - 6 * k], radius=int(12 * k), fill=renk)
        d.rectangle([x - 50 * k, ry - kh - 16 * k, x + 50 * k, ry - kh + 4 * k], fill=(200, 80, 70), outline=LACI, width=int(3 * k))
    if no in (1, 3):   # asili tavalar
        for i, x in enumerate((w * 0.2, w * 0.8)):
            d.line([(x, h * 0.08), (x, h * 0.13)], fill=LACI, width=int(5 * k))
            d.ellipse([x - 70 * k, h * 0.13, x + 70 * k, h * 0.13 + 140 * k], fill=(90, 96, 120), outline=LACI, width=int(5 * k))
    # zemin: kareli masa ortusu
    _zemin(d, w, h, (255, 255, 255))
    renk = [(230, 80, 80), (80, 150, 220), (240, 150, 60), (90, 170, 110), (220, 90, 140)][no]
    a = 70 * k
    for y in range(zy, h, int(a)):
        for x in range(0, w, int(a)):
            if ((x // int(a)) + ((y - zy) // int(a))) % 2 == 0:
                d.rectangle([x, y, x + a, y + a], fill=renk)
    d.line([(0, zy), (w, zy)], fill=LACI, width=max(2, int(w / 180)))


# --- BILIM -------------------------------------------------------------------------------
def bilim(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no in (0, 3):   # kara tahta
        d.rectangle([0, 0, w, zy], fill=(220, 232, 240) if no == 0 else (240, 230, 214))
        bx0, by0, bx1, by1 = w * 0.06, h * 0.06, w * 0.94, h * 0.45
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(16 * k), fill=(40, 80, 64), outline=(150, 100, 60), width=int(18 * k))
        tebesir = (235, 240, 230)
        for j, (x, y) in enumerate([(0.12, 0.11), (0.55, 0.14), (0.15, 0.26), (0.58, 0.30), (0.2, 0.38)]):
            yy = h * y
            xx = w * x
            for i in range(rnd.randint(4, 7)):   # formul benzeri karalamalar
                d.line([(xx + i * 34 * k, yy), (xx + i * 34 * k + 22 * k, yy - 18 * k)], fill=tebesir, width=int(4 * k))
            d.line([(xx, yy + 14 * k), (xx + 240 * k, yy + 14 * k)], fill=tebesir, width=int(3 * k))
        cx, cy, r = w * 0.78, h * 0.32, 70 * k   # atom
        for a in (0, 60, 120):
            katman = Image.new("RGBA", (int(r * 3), int(r * 3)), (0, 0, 0, 0))
            ImageDraw.Draw(katman).ellipse([r * 0.2, r * 1.1, r * 2.8, r * 1.9], outline=tebesir + (255,), width=int(4 * k))
            katman = katman.rotate(a, resample=Image.BICUBIC)
            img.paste(katman, (int(cx - r * 1.5), int(cy - r * 1.5)), katman)
        d.ellipse([cx - 12 * k, cy - 12 * k, cx + 12 * k, cy + 12 * k], fill=(255, 200, 80))
    elif no in (1, 4):   # laboratuvar rafi + erlenler
        _dikey_gecis(d, w, 0, zy, (214, 240, 250) if no == 1 else (236, 226, 255), (245, 250, 255))
        for ry in (h * 0.22, h * 0.42):
            d.rectangle([w * 0.04, ry, w * 0.96, ry + 16 * k], fill=(160, 170, 190), outline=LACI, width=int(4 * k))
            for i in range(5):
                x = w * (0.12 + i * 0.19) + rnd.uniform(-10, 10) * k
                renk = rnd.choice([(120, 220, 160), (255, 140, 160), (140, 180, 255), (255, 210, 100)])
                if i % 2 == 0:   # erlen
                    d.polygon([(x - 18 * k, ry - 120 * k), (x + 18 * k, ry - 120 * k), (x + 60 * k, ry), (x - 60 * k, ry)], fill=(255, 255, 255), outline=LACI)
                    d.polygon([(x - 38 * k, ry - 50 * k), (x + 38 * k, ry - 50 * k), (x + 58 * k, ry - 3 * k), (x - 58 * k, ry - 3 * k)], fill=renk)
                else:   # deney tupu
                    d.rounded_rectangle([x - 20 * k, ry - 130 * k, x + 20 * k, ry], radius=int(20 * k), fill=(255, 255, 255), outline=LACI, width=int(4 * k))
                    d.rounded_rectangle([x - 16 * k, ry - 70 * k, x + 16 * k, ry - 4 * k], radius=int(16 * k), fill=renk)
        _isiltilar(d, w, 0, zy, 18, (255, 255, 255), rnd, 6 * k, 16 * k)
    else:   # mavi baski (blueprint) + DNA
        d.rectangle([0, 0, w, zy], fill=(40, 90, 160))
        for x in range(0, w, int(60 * k)):
            d.line([(x, 0), (x, zy)], fill=(70, 120, 190), width=int(2 * k))
        for y in range(0, zy, int(60 * k)):
            d.line([(0, y), (w, y)], fill=(70, 120, 190), width=int(2 * k))
        for side in (0.12, 0.88):   # DNA sarmali
            cx = w * side
            for i in range(28):
                y = h * 0.04 + i * 34 * k
                a = i * 0.5
                x1, x2 = cx + math.sin(a) * 60 * k, cx - math.sin(a) * 60 * k
                d.line([(x1, y), (x2, y)], fill=(160, 200, 255), width=int(3 * k))
                d.ellipse([x1 - 9 * k, y - 9 * k, x1 + 9 * k, y + 9 * k], fill=(255, 210, 100))
                d.ellipse([x2 - 9 * k, y - 9 * k, x2 + 9 * k, y + 9 * k], fill=(120, 230, 200))
    _zemin(d, w, h, (200, 206, 222) if no != 2 else (60, 100, 160))


# --- INSAN VUCUDU ----------------------------------------------------------------------
def _kalp(d, cx, cy, r, renk):
    d.ellipse([cx - r, cy - r * 0.9, cx, cy + r * 0.1], fill=renk)
    d.ellipse([cx, cy - r * 0.9, cx + r, cy + r * 0.1], fill=renk)
    d.polygon([(cx - r * 0.97, cy - r * 0.25), (cx + r * 0.97, cy - r * 0.25), (cx, cy + r)], fill=renk)


def insan(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    paletler = [((220, 245, 240), (245, 252, 250)), ((255, 228, 232), (255, 245, 247)), ((226, 236, 255), (245, 248, 255)),
                ((235, 250, 230), (250, 255, 248)), ((250, 238, 220), (255, 250, 242))]
    _dikey_gecis(d, w, 0, zy, *paletler[no])
    if no == 0:   # kalp ritmi (EKG)
        y = h * 0.30
        pts, x = [], 0
        while x < w:
            pts += [(x, y), (x + 80 * k, y), (x + 100 * k, y - 30 * k), (x + 120 * k, y + 20 * k), (x + 140 * k, y - 140 * k),
                    (x + 165 * k, y + 70 * k), (x + 185 * k, y), (x + 300 * k, y)]
            x += 300 * k
        d.line(pts, fill=(60, 190, 160), width=int(8 * k), joint="curve")
        for _ in range(8):
            _kalp(d, rnd.uniform(0, w), rnd.uniform(h * 0.42, zy * 0.95), rnd.uniform(16, 30) * k, (255, 170, 180))
    elif no == 1:   # kalpler + hucreler
        _bulanik_daireler(img, w, 0, zy, 12, [(255, 160, 180, 90), (255, 200, 210, 90)], rnd, 60 * k, 140 * k, 20 * k)
        for _ in range(10):
            _kalp(d, rnd.uniform(0, w), rnd.uniform(40 * k, zy * 0.9), rnd.uniform(18, 40) * k, (240, 100, 130))
    elif no == 2:   # rontgen panosu
        bx0, by0, bx1, by1 = w * 0.18, h * 0.07, w * 0.82, h * 0.42
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(18 * k), fill=(30, 40, 60), outline=(160, 170, 190), width=int(12 * k))
        cx = (bx0 + bx1) / 2
        for i in range(6):   # kaburgalar
            y = by0 + 90 * k + i * 55 * k
            d.arc([cx - 200 * k, y - 40 * k, cx - 10 * k, y + 60 * k], 180, 300, fill=(200, 220, 240), width=int(9 * k))
            d.arc([cx + 10 * k, y - 40 * k, cx + 200 * k, y + 60 * k], 240, 360, fill=(200, 220, 240), width=int(9 * k))
        d.line([(cx, by0 + 60 * k), (cx, by1 - 40 * k)], fill=(200, 220, 240), width=int(14 * k))
    elif no == 3:   # hucreler (mikroskop)
        for _ in range(14):
            x, y, r = rnd.uniform(0, w), rnd.uniform(0, zy), rnd.uniform(50, 110) * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 240, 200), outline=(140, 200, 150), width=int(5 * k))
            d.ellipse([x - r * 0.3, y - r * 0.3, x + r * 0.3, y + r * 0.3], fill=(150, 200, 230))
    else:   # DNA + arti isaretleri
        for i in range(30):
            y = i * 32 * k
            a = i * 0.45
            for cx in (w * 0.15, w * 0.85):
                x1, x2 = cx + math.sin(a) * 55 * k, cx - math.sin(a) * 55 * k
                d.line([(x1, y), (x2, y)], fill=(230, 200, 170), width=int(3 * k))
                d.ellipse([x1 - 8 * k, y - 8 * k, x1 + 8 * k, y + 8 * k], fill=(240, 130, 110))
                d.ellipse([x2 - 8 * k, y - 8 * k, x2 + 8 * k, y + 8 * k], fill=(100, 180, 220))
        for _ in range(6):
            x, y, r = rnd.uniform(w * 0.3, w * 0.7), rnd.uniform(40 * k, zy * 0.6), 20 * k
            d.rectangle([x - r, y - r * 0.32, x + r, y + r * 0.32], fill=(120, 210, 170))
            d.rectangle([x - r * 0.32, y - r, x + r * 0.32, y + r], fill=(120, 210, 170))
    _zemin(d, w, h, (205, 230, 225) if no != 1 else (250, 215, 222))


# --- TARIH ---------------------------------------------------------------------------------
def _sutun(d, x, taban, yuk, gen, k, renk=(240, 230, 205), golge=(215, 200, 170)):
    d.rectangle([x - gen / 2, taban - yuk, x + gen / 2, taban], fill=renk, outline=LACI, width=int(4 * k))
    for i in (-1, 0, 1):
        d.line([(x + i * gen * 0.25, taban - yuk + 30 * k), (x + i * gen * 0.25, taban - 20 * k)], fill=golge, width=int(5 * k))
    d.rectangle([x - gen * 0.7, taban - yuk - 26 * k, x + gen * 0.7, taban - yuk], fill=renk, outline=LACI, width=int(4 * k))
    d.rectangle([x - gen * 0.65, taban - 20 * k, x + gen * 0.65, taban], fill=renk, outline=LACI, width=int(4 * k))


def tarih(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no == 0:   # antik tapinak
        _dikey_gecis(d, w, 0, zy, (255, 220, 170), (255, 242, 220))
        for x in (w * 0.08, w * 0.92):
            _sutun(d, x, zy, 900 * k, 90 * k, k)
        d.polygon([(0, h * 0.16), (w / 2, h * 0.04), (w, h * 0.16)], fill=(240, 230, 205), outline=LACI)
        _zemin(d, w, h, (220, 200, 160))
    elif no == 1:   # piramitler
        _dikey_gecis(d, w, 0, zy, (255, 200, 140), (255, 236, 200))
        d.ellipse([w * 0.66, h * 0.10, w * 0.66 + 200 * k, h * 0.10 + 200 * k], fill=(255, 245, 210))
        for x, s in ((w * 0.2, 1.0), (w * 0.62, 1.35), (w * 0.95, 0.8)):
            b = 330 * k * s
            d.polygon([(x - b, zy), (x, zy - b * 0.95), (x + b, zy)], fill=(225, 180, 110), outline=LACI)
            d.polygon([(x, zy - b * 0.95), (x + b, zy), (x + b * 0.35, zy)], fill=(200, 155, 90))
        _zemin(d, w, h, (232, 200, 140))
    elif no == 2:   # parsomen + harita cizgileri
        d.rectangle([0, 0, w, zy], fill=(244, 228, 190))
        _bulanik_daireler(img, w, 0, zy, 10, [(210, 180, 130, 80), (230, 200, 150, 80)], rnd, 80 * k, 200 * k, 40 * k)
        for _ in range(5):   # kesikli rota
            x0, y0 = rnd.uniform(0, w), rnd.uniform(0, zy * 0.7)
            for i in range(10):
                d.line([(x0 + i * 40 * k, y0 + math.sin(i) * 20 * k), (x0 + i * 40 * k + 20 * k, y0 + math.sin(i + 0.5) * 20 * k)],
                       fill=(170, 120, 80), width=int(5 * k))
        cx, cy, r = w * 0.8, h * 0.14, 80 * k   # pusula gulu
        d.polygon([(cx, cy - r), (cx + r * 0.2, cy), (cx, cy + r), (cx - r * 0.2, cy)], fill=(170, 60, 50))
        d.polygon([(cx - r, cy), (cx, cy - r * 0.2), (cx + r, cy), (cx, cy + r * 0.2)], fill=(120, 90, 60))
        _zemin(d, w, h, (200, 170, 120))
    elif no == 3:   # kale duvari
        _dikey_gecis(d, w, 0, zy, (170, 210, 250), (225, 240, 255))
        _bulut(d, w * 0.7, h * 0.12, 60 * k, (255, 255, 255))
        top = h * 0.40
        d.rectangle([0, top, w, zy], fill=(170, 160, 150), outline=LACI, width=int(4 * k))
        for x in range(0, w, int(120 * k)):
            d.rectangle([x, top - 60 * k, x + 70 * k, top], fill=(170, 160, 150), outline=LACI, width=int(4 * k))
        for y in range(int(top + 20 * k), zy, int(60 * k)):
            ofs = (y // int(60 * k)) % 2 * 60 * k
            for x in range(int(-ofs), w, int(120 * k)):
                d.rectangle([x, y, x + 120 * k, y + 60 * k], outline=(140, 130, 120), width=int(3 * k))
        d.line([(w * 0.5, h * 0.06), (w * 0.5, top - 60 * k)], fill=LACI, width=int(6 * k))   # sancak
        d.polygon([(w * 0.5, h * 0.06), (w * 0.5 + 120 * k, h * 0.08), (w * 0.5, h * 0.11)], fill=(214, 40, 54))
        _zemin(d, w, h, (150, 140, 130))
    else:   # muze: cerceveli tablolar
        d.rectangle([0, 0, w, zy], fill=(150, 40, 50))
        d.rectangle([0, zy - 120 * k, w, zy], fill=(120, 30, 40))
        for x, y, gw, gh in ((w * 0.08, h * 0.08, 340 * k, 260 * k), (w * 0.58, h * 0.10, 300 * k, 380 * k), (w * 0.2, h * 0.36, 260 * k, 200 * k)):
            d.rectangle([x, y, x + gw, y + gh], fill=(212, 170, 60), outline=LACI, width=int(4 * k))
            d.rectangle([x + 22 * k, y + 22 * k, x + gw - 22 * k, y + gh - 22 * k], fill=rnd.choice([(120, 160, 200), (200, 180, 120), (140, 180, 130)]))
        _zemin(d, w, h, (190, 150, 110))


# --- PSIKOLOJI -------------------------------------------------------------------------------
def psikoloji(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    paletler = [((230, 220, 255), (248, 244, 255)), ((220, 240, 255), (245, 250, 255)), ((255, 230, 240), (255, 246, 250)),
                ((236, 230, 220), (250, 246, 240)), ((225, 250, 240), (245, 255, 250))]
    _dikey_gecis(d, w, 0, zy, *paletler[no])
    if no in (0, 2):   # dusunce balonlari + soru isaretleri
        from PIL import ImageFont
        for _ in range(7):
            x, y, r = rnd.uniform(60 * k, w - 60 * k), rnd.uniform(40 * k, zy * 0.85), rnd.uniform(40, 80) * k
            _bulut(d, x, y, r, (255, 255, 255))
        for _ in range(9):
            x, y = rnd.uniform(40 * k, w - 40 * k), rnd.uniform(40 * k, zy * 0.9)
            d.text((x, y), "?", fill=rnd.choice([(170, 140, 240), (240, 140, 180), (120, 170, 240)]),
                   font=_font(int(rnd.uniform(50, 90) * k)), anchor="mm")
    elif no == 1:   # spiral (hipnoz) - soluk
        cx, cy = w / 2, h * 0.40
        pts = [(cx + math.cos(a / 10) * a * 1.9 * k, cy + math.sin(a / 10) * a * 1.9 * k) for a in range(0, 330)]
        d.line(pts, fill=(190, 215, 250), width=int(18 * k), joint="curve")
    elif no == 3:   # dedektif panosu
        bx0, by0, bx1, by1 = w * 0.06, h * 0.06, w * 0.94, h * 0.46
        d.rectangle([bx0, by0, bx1, by1], fill=(200, 160, 110), outline=(120, 90, 60), width=int(14 * k))
        notlar = []
        for _ in range(6):
            x, y = rnd.uniform(bx0 + 60 * k, bx1 - 160 * k), rnd.uniform(by0 + 50 * k, by1 - 170 * k)
            d.rectangle([x, y, x + 130 * k, y + 120 * k], fill=rnd.choice([(255, 250, 200), (255, 255, 255), (220, 240, 255)]), outline=(150, 120, 90))
            notlar.append((x + 65 * k, y + 10 * k))
        d.line(notlar, fill=(214, 40, 54), width=int(4 * k))
        for p in notlar:
            d.ellipse([p[0] - 9 * k, p[1] - 9 * k, p[0] + 9 * k, p[1] + 9 * k], fill=(214, 40, 54))
    else:   # beyin dalgalari
        for i in range(6):
            y = h * (0.08 + i * 0.11)
            pts = [(x, y + math.sin(x / (60 * k) + i) * 26 * k) for x in range(0, w + 10, 10)]
            d.line(pts, fill=rnd.choice([(150, 220, 200), (180, 200, 250), (250, 190, 210)]), width=int(7 * k))
    _zemin(d, w, h, (215, 205, 240) if no != 3 else (190, 170, 150))


# --- TEKNOLOJI --------------------------------------------------------------------------------
def teknoloji(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no in (0, 3):   # devre karti
        taban = (20, 70, 60) if no == 0 else (30, 40, 90)
        hat = (60, 200, 150) if no == 0 else (90, 160, 255)
        d.rectangle([0, 0, w, zy], fill=taban)
        for _ in range(26):
            x, y = rnd.uniform(0, w), rnd.uniform(0, zy)
            pts = [(x, y)]
            for _ in range(3):
                if rnd.random() < 0.5:
                    x += rnd.choice([-1, 1]) * rnd.uniform(60, 180) * k
                else:
                    y += rnd.choice([-1, 1]) * rnd.uniform(60, 180) * k
                pts.append((x, y))
            d.line(pts, fill=hat, width=int(5 * k))
            for p in (pts[0], pts[-1]):
                d.ellipse([p[0] - 11 * k, p[1] - 11 * k, p[0] + 11 * k, p[1] + 11 * k], fill=taban, outline=hat, width=int(4 * k))
        for _ in range(4):   # cipler
            x, y = rnd.uniform(60 * k, w - 220 * k), rnd.uniform(60 * k, zy * 0.6)
            d.rectangle([x, y, x + 160 * k, y + 110 * k], fill=(30, 32, 40), outline=hat, width=int(4 * k))
    elif no == 1:   # piksel / retro oyun
        _dikey_gecis(d, w, 0, zy, (60, 40, 120), (200, 90, 160))
        a = int(40 * k)
        for _ in range(60):
            x, y = rnd.randrange(0, w, a), rnd.randrange(0, zy, a)
            d.rectangle([x, y, x + a, y + a], fill=rnd.choice([(120, 220, 255), (255, 220, 100), (255, 120, 200), (140, 255, 170)]))
    elif no == 2:   # kod ekrani
        d.rectangle([0, 0, w, zy], fill=(28, 30, 44))
        for i in range(34):
            y = 30 * k + i * 44 * k
            if y > zy - 20 * k:
                break
            x = 40 * k + rnd.choice([0, 1, 2]) * 50 * k
            for _ in range(rnd.randint(2, 5)):
                ln = rnd.uniform(60, 220) * k
                d.rounded_rectangle([x, y, x + ln, y + 16 * k], radius=int(8 * k),
                                    fill=rnd.choice([(120, 200, 255), (255, 180, 100), (180, 140, 255), (120, 220, 160), (90, 96, 120)]))
                x += ln + 20 * k
    else:   # neon izgara (retro ufuk)
        _dikey_gecis(d, w, 0, zy, (30, 10, 60), (150, 40, 130))
        cx = w / 2
        d.ellipse([cx - 220 * k, zy - 380 * k, cx + 220 * k, zy + 60 * k], fill=(255, 140, 80))
        for i in range(6):
            y = zy - 340 * k + i * 60 * k
            d.rectangle([cx - 230 * k, y, cx + 230 * k, y + 14 * k], fill=_karis((30, 10, 60), (150, 40, 130), y / zy))
        for i in range(-8, 9):
            d.line([(cx + i * 40 * k, zy * 0.62), (cx + i * 220 * k, zy)], fill=(255, 100, 220), width=int(3 * k))
    _zemin(d, w, h, (60, 64, 90) if no != 4 else (90, 30, 110))


# --- COGRAFYA ----------------------------------------------------------------------------------
def cografya(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no == 0:   # daglar
        _dikey_gecis(d, w, 0, zy, (150, 200, 255), (230, 245, 255))
        _bulut(d, w * 0.2, h * 0.12, 60 * k, (255, 255, 255))
        for x, b, renk in ((w * 0.2, 420, (120, 140, 190)), (w * 0.75, 520, (100, 120, 170)), (w * 0.45, 340, (140, 160, 200))):
            bb = b * k
            d.polygon([(x - bb, zy), (x, zy - bb * 1.1), (x + bb, zy)], fill=renk, outline=LACI)
            d.polygon([(x - bb * 0.25, zy - bb * 0.82), (x, zy - bb * 1.1), (x + bb * 0.25, zy - bb * 0.82), (x, zy - bb * 0.74)], fill=(255, 255, 255))
        _zemin(d, w, h, (130, 190, 110))
    elif no == 1:   # deniz feneri
        _dikey_gecis(d, w, 0, zy, (255, 200, 160), (200, 225, 255))
        d.rectangle([0, zy - 200 * k, w, zy], fill=(70, 150, 210))
        for i in range(8):
            y = zy - 180 * k + i * 22 * k
            d.line([(rnd.uniform(0, w * 0.5), y), (rnd.uniform(w * 0.5, w), y)], fill=(130, 190, 240), width=int(4 * k))
        x = w * 0.84
        d.polygon([(x - 50 * k, zy - 200 * k), (x - 34 * k, zy - 620 * k), (x + 34 * k, zy - 620 * k), (x + 50 * k, zy - 200 * k)], fill=(255, 255, 255), outline=LACI)
        for i in range(3):
            y = zy - 260 * k - i * 130 * k
            d.rectangle([x - 46 * k + i * 4 * k, y - 50 * k, x + 46 * k - i * 4 * k, y], fill=(220, 60, 60))
        d.rectangle([x - 40 * k, zy - 690 * k, x + 40 * k, zy - 620 * k], fill=(255, 230, 120), outline=LACI, width=int(4 * k))
        d.polygon([(x - 40 * k, zy - 690 * k), (x, zy - 740 * k), (x + 40 * k, zy - 690 * k)], fill=(60, 60, 80))
        _zemin(d, w, h, (232, 214, 170))
    elif no == 2:   # nokta dunya haritasi hissi + meridyenler
        d.rectangle([0, 0, w, zy], fill=(200, 230, 250))
        cx, cy, r = w / 2, h * 0.36, 420 * k
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(160, 210, 245), outline=(120, 180, 230), width=int(6 * k))
        for i in range(1, 6):
            rr = r * i / 6
            d.ellipse([cx - rr, cy - r, cx + rr, cy + r], outline=(130, 190, 235), width=int(3 * k))
            yy = cy - r + 2 * r * i / 6
            ww = math.sqrt(max(0, r * r - (yy - cy) ** 2))
            d.line([(cx - ww, yy), (cx + ww, yy)], fill=(130, 190, 235), width=int(3 * k))
        for _ in range(7):   # kita lekeleri
            x, y = rnd.uniform(cx - r * 0.7, cx + r * 0.7), rnd.uniform(cy - r * 0.7, cy + r * 0.7)
            rr = rnd.uniform(50, 120) * k
            d.ellipse([x - rr, y - rr * 0.7, x + rr, y + rr * 0.7], fill=(120, 190, 120))
        _zemin(d, w, h, (150, 200, 140))
    elif no == 3:   # col + kaktus
        _dikey_gecis(d, w, 0, zy, (255, 190, 120), (255, 230, 180))
        d.ellipse([w * 0.12, h * 0.12, w * 0.12 + 220 * k, h * 0.12 + 220 * k], fill=(255, 250, 220))
        _tepeler(d, w, zy, 140 * k, (240, 200, 130), 1.6, 2.0)
        for x in (w * 0.12, w * 0.9):
            d.rounded_rectangle([x - 26 * k, zy - 280 * k, x + 26 * k, zy], radius=int(26 * k), fill=(90, 160, 90), outline=LACI, width=int(4 * k))
            d.rounded_rectangle([x - 90 * k, zy - 220 * k, x - 50 * k, zy - 120 * k], radius=int(20 * k), fill=(90, 160, 90), outline=LACI, width=int(4 * k))
            d.rectangle([x - 70 * k, zy - 140 * k, x - 20 * k, zy - 110 * k], fill=(90, 160, 90))
        _zemin(d, w, h, (236, 196, 130))
    else:   # tropikal ada
        _dikey_gecis(d, w, 0, zy, (120, 210, 250), (210, 245, 255))
        d.rectangle([0, zy - 160 * k, w, zy], fill=(60, 190, 210))
        for i in range(6):
            y = zy - 140 * k + i * 24 * k
            d.line([(rnd.uniform(0, w * 0.5), y), (rnd.uniform(w * 0.5, w), y)], fill=(150, 230, 240), width=int(4 * k))
        x = w * 0.15
        d.line([(x, zy), (x + 40 * k, zy - 420 * k)], fill=(150, 100, 60), width=int(22 * k))
        for a in range(0, 360, 60):
            r = math.radians(a)
            d.line([(x + 40 * k, zy - 420 * k), (x + 40 * k + math.cos(r) * 170 * k, zy - 420 * k + math.sin(r) * 70 * k + 40 * k)],
                   fill=(60, 160, 80), width=int(26 * k))
        _zemin(d, w, h, (245, 225, 170))


# --- COCUK SORULARI ------------------------------------------------------------------------------
def cocuk(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    if no == 0:   # gokkusagi + bulutlar
        _dikey_gecis(d, w, 0, zy, (170, 220, 255), (230, 245, 255))
        cx, cy = w / 2, zy + 60 * k
        for i, renk in enumerate([(240, 80, 80), (255, 160, 60), (255, 220, 70), (90, 200, 110), (80, 150, 240), (150, 100, 220)]):
            r = (720 - i * 45) * k
            d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=renk, width=int(46 * k))
        _bulut(d, w * 0.12, zy - 60 * k, 80 * k, (255, 255, 255))
        _bulut(d, w * 0.88, zy - 60 * k, 80 * k, (255, 255, 255))
        _zemin(d, w, h, (140, 210, 120))
    elif no == 1:   # balonlar
        _dikey_gecis(d, w, 0, zy, (255, 230, 200), (255, 248, 235))
        for _ in range(9):
            x, y, r = rnd.uniform(60 * k, w - 60 * k), rnd.uniform(80 * k, zy * 0.6), rnd.uniform(44, 70) * k
            renk = rnd.choice([(255, 110, 120), (255, 200, 80), (120, 200, 255), (160, 230, 140), (210, 150, 255)])
            d.line([(x, y + r * 1.2), (x + 20 * k, y + r * 3.4)], fill=(150, 150, 160), width=int(3 * k))
            d.ellipse([x - r, y - r * 1.2, x + r, y + r * 1.2], fill=renk, outline=LACI, width=int(4 * k))
            d.ellipse([x - r * 0.5, y - r * 0.8, x - r * 0.15, y - r * 0.35], fill=(255, 255, 255))
        _zemin(d, w, h, (250, 210, 150))
    elif no == 2:   # oyun odasi: bloklar
        d.rectangle([0, 0, w, zy], fill=(255, 240, 220))
        for x in range(0, w, int(80 * k)):
            d.line([(x, 0), (x, zy)], fill=(255, 225, 200), width=int(30 * k))
        harfler = "ABCNE?"
        for i in range(6):
            x, y, a = w * (0.08 + (i % 3) * 0.32), h * (0.12 + (i // 3) * 0.2), 120 * k
            renk = [(240, 90, 90), (90, 160, 240), (100, 200, 120), (255, 190, 60), (180, 120, 230), (255, 140, 180)][i]
            d.rounded_rectangle([x, y, x + a, y + a], radius=int(14 * k), fill=renk, outline=LACI, width=int(5 * k))
            d.text((x + a / 2, y + a / 2), harfler[i], fill=(255, 255, 255), font=_font(int(70 * k)), anchor="mm")
        _zemin(d, w, h, (190, 150, 110))
    elif no == 3:   # konfeti + yildizlar
        _dikey_gecis(d, w, 0, zy, (255, 236, 250), (240, 248, 255))
        for _ in range(70):
            x, y = rnd.uniform(0, w), rnd.uniform(0, zy)
            renk = rnd.choice([(255, 120, 150), (255, 200, 80), (120, 200, 255), (150, 230, 150), (200, 150, 255)])
            if rnd.random() < 0.3:
                _yildiz(d, x, y, rnd.uniform(10, 20) * k, renk)
            else:
                d.rounded_rectangle([x, y, x + 26 * k, y + 12 * k], radius=int(5 * k), fill=renk)
        _zemin(d, w, h, (200, 220, 250))
    else:   # gunesli tepeler
        _dikey_gecis(d, w, 0, zy, (130, 205, 255), (215, 240, 255))
        sx, sy, sr = w * 0.80, h * 0.13, 90 * k
        for a in range(0, 360, 30):
            r = math.radians(a)
            d.line([(sx + math.cos(r) * sr * 1.2, sy + math.sin(r) * sr * 1.2), (sx + math.cos(r) * sr * 1.7, sy + math.sin(r) * sr * 1.7)],
                   fill=(255, 210, 80), width=int(12 * k))
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 220, 90), outline=LACI, width=int(5 * k))
        _bulut(d, w * 0.25, h * 0.18, 65 * k, (255, 255, 255))
        _tepeler(d, w, zy, 220 * k, (150, 215, 120), 1.3, 0.3)
        _tepeler(d, w, zy, 120 * k, (120, 195, 100), 2.0, 1.2)
        for _ in range(12):   # cicekler
            x, y = rnd.uniform(0, w), rnd.uniform(zy - 90 * k, zy - 10 * k)
            renk = rnd.choice([(255, 120, 150), (255, 220, 80), (255, 255, 255)])
            for a in range(0, 360, 72):
                r = math.radians(a)
                d.ellipse([x + math.cos(r) * 10 * k - 8 * k, y + math.sin(r) * 10 * k - 8 * k, x + math.cos(r) * 10 * k + 8 * k, y + math.sin(r) * 10 * k + 8 * k], fill=renk)
            d.ellipse([x - 6 * k, y - 6 * k, x + 6 * k, y + 6 * k], fill=(255, 190, 40))
        _zemin(d, w, h, (120, 190, 100))


# --- GENEL (kostumsuz / bilinmeyen konu) ------------------------------------------------------------
def genel(img, d, w, h, k, no, rnd):
    zy = int(h * ZEMIN_ORAN)
    paletler = [((255, 236, 200), (255, 248, 232)), ((220, 236, 255), (246, 250, 255)), ((236, 226, 255), (250, 246, 255)),
                ((220, 245, 230), (246, 253, 248)), ((255, 226, 230), (255, 246, 247))]
    _dikey_gecis(d, w, 0, zy, *paletler[no])
    renkler = [(255, 200, 120, 90), (140, 190, 255, 90), (200, 160, 255, 90), (140, 220, 170, 90), (255, 160, 180, 90)]
    _bulanik_daireler(img, w, 0, zy, 14, [renkler[no], renkler[(no + 2) % 5]], rnd, 50 * k, 150 * k, 18 * k)
    _isiltilar(d, w, 0, zy, 20, (255, 255, 255), rnd, 4 * k, 10 * k)
    _zemin(d, w, h, _karis(paletler[no][0], (200, 180, 150), 0.45))


def _font(px):
    from PIL import ImageFont
    from ortak import FONT
    return ImageFont.truetype(FONT, max(8, px))


# --- tema tablosu ------------------------------------------------------------------------------------
TEMALAR = {
    "uzay": ("Uzay", uzay), "burclar": ("Burçlar ve gökyüzü", burclar), "hayvanlar": ("Hayvanlar", hayvanlar),
    "yemek": ("Yemek / mutfak", yemek), "bilim": ("Bilim", bilim), "insan": ("İnsan vücudu", insan),
    "tarih": ("Tarih", tarih), "psikoloji": ("Psikoloji", psikoloji), "teknoloji": ("Teknoloji", teknoloji),
    "cografya": ("Coğrafya", cografya), "cocuk": ("Çocuk soruları", cocuk), "genel": ("Genel", genel),
}
SAHNE_SAYISI = 5
KOSTUM_TEMA = {"astronot": "uzay", "buyucu": "burclar", "safari": "hayvanlar", "asci": "yemek", "bilimci": "bilim",
               "doktor": "insan", "migfer": "tarih", "dedektif": "psikoloji", "kulaklik": "teknoloji",
               "kaptan": "cografya", "pervane": "cocuk"}


def tema_bul(alan="", konu="", kostum=""):
    """Once konu alanina gore; bulunamazsa kostume gore; o da yoksa 'genel'."""
    from kostumler import kostum_sec
    return KOSTUM_TEMA.get(kostum_sec(alan, konu)) or KOSTUM_TEMA.get(kostum or "") or "genel"


def ciz(tema, no, genislik, yukseklik, k=None):
    tema = tema if tema in TEMALAR else "genel"
    no = int(no) % SAHNE_SAYISI
    img = Image.new("RGB", (int(genislik), int(yukseklik)), (250, 244, 230))
    d = ImageDraw.Draw(img)
    k = k or genislik / 1080      # yatay (hikaye) videolarda olcek disaridan verilir
    TEMALAR[tema][1](img, d, int(genislik), int(yukseklik), k, no, random.Random(f"{tema}-{no}"))
    return img


# --- tekrar etmeyen secim ----------------------------------------------------------------------------
# --- sahne katalogu: her sahnenin adi; bazilari sadece konusu uyunca kullanilir (kopek konusunda balik olmasin) ---
SAHNE_ADLARI = {
    "uzay": ["halkali gezegen", "uzaktan Dunya", "renkli bulutsu", "buyuk Ay", "kayan yildizlar"],
    "burclar": ["takimyildizlar ve hilal", "burc cemberi", "gece gokyuzu ve hilal", "burc cemberi (mavi)", "takimyildizlar"],
    "hayvanlar": ["savana (Afrika)", "orman", "deniz alti", "ciftlik", "kutup / kar"],
    "yemek": ["mutfak rafi", "mutfak (lambali)", "mutfak rafi (pembe)", "mutfak (mavi)", "mutfak rafi (sari)"],
    "bilim": ["kara tahta", "laboratuvar rafi", "DNA ve hucre", "kara tahta (krem)", "laboratuvar (mor)"],
    "insan": ["kalp ritmi", "kalpler", "beyin/kitap panosu", "hucreler", "DNA"],
    "tarih": ["antik tapinak (sutunlar)", "piramitler (Misir)", "eski harita", "kale surlari", "muze"],
    "psikoloji": ["bulutlar ve soru isaretleri", "hipnoz sarmali", "pembe bulutlar", "dedektif panosu", "dalgalar"],
    "teknoloji": ["devre karti (yesil)", "piksel yagmuru", "kod ekrani", "devre karti (mavi)", "retro gun batimi"],
    "cografya": ["karli daglar", "deniz feneri ve kiyi", "dunya haritasi", "col", "tropik plaj"],
    "cocuk": ["gokkusagi", "balonlar", "harf kupleri", "konfeti", "gunesli cayir"],
    "genel": ["renkli isiltilar"] * 5,
}
# yalnizca konu/metin bu kelimelerden birini icerirse secilebilen sahneler
OZEL_SAHNE = {
    ("hayvanlar", 0): ["savan", "afrika", "aslan", "zürafa", "zurafa", "fil ", "filler", "zebra", "çita", "cita", "gergedan", "sırtlan"],
    ("hayvanlar", 2): ["deniz", "okyanus", "balık", "balik", "ahtapot", "köpekbalı", "kopekbali", "balina", "yunus", "mercan",
                       "denizanası", "denizanasi", "kaplumbağa", "su alt", "mürekkep", "istakoz", "yengeç", "fok"],
    ("hayvanlar", 4): ["kutup", "penguen", "kar ", "karlı", "buz", "fok", "antarktika", "arktik", "kutup ayısı", "mors", "eskimo"],
    ("bilim", 2): ["dna", "gen ", "genetik", "hücre", "hucre", "kalıtım", "kalitim"],
    ("tarih", 0): ["antik", "yunan", "roma", "tapınak", "tapinak", "olimpos", "sokrat", "atina"],
    ("tarih", 1): ["mısır", "misir", "piramit", "firavun", "mumya", "nil ", "kleopatra"],
    ("cografya", 3): ["çöl", "col ", "sahra", "kum ", "kumul", "deve", "vaha", "kurak"],
    ("cografya", 4): ["ada ", "adası", "adalar", "plaj", "tropik", "okyanus", "mercan", "palmiye", "hawaii", "kumsal"],
}


def _kucuk(metin):
    return " " + (metin or "").replace("İ", "i").replace("I", "ı").lower() + " "


def _eslesir(m, kelimeler):
    """Kelime BASINDAN eslesme ('fil' -> 'filler' evet, 'film' hayir icin 'fil ' yazilir)."""
    import re
    m = re.sub(r"[^\w\s]", " ", m)
    return any((" " + k) in m for k in kelimeler)


def uygun_sahneler(tema, metin=""):
    """Bu metne uyan sahneler. Metin ozel bir sahneyle eslesiyorsa SADECE onlar (or. penguen -> kutup)."""
    m = _kucuk(metin)
    eslesen = [no for no in range(SAHNE_SAYISI)
               if (tema, no) in OZEL_SAHNE and _eslesir(m, OZEL_SAHNE[(tema, no)])]
    if eslesen:
        return eslesen
    return [no for no in range(SAHNE_SAYISI) if (tema, no) not in OZEL_SAHNE]


def sahne_uygun_mu(tema, no, metin=""):
    return no in uygun_sahneler(tema, metin) or (
        (tema, no) in OZEL_SAHNE and _eslesir(_kucuk(metin), OZEL_SAHNE[(tema, no)]))


def _gecmis_yolu():
    from ortak import KOK
    return os.path.join(KOK, "arka_gecmis.json")


def secim(tema, metin=""):
    """Konuya uyan sahneler arasindan, son 2 kullanilani atlayarak rastgele secer ve kaydeder."""
    try:
        with open(_gecmis_yolu(), encoding="utf-8") as f:
            gecmis = json.load(f)
    except (OSError, ValueError):
        gecmis = {}
    son = gecmis.get(tema, [])
    uygun = uygun_sahneler(tema, metin) or list(range(SAHNE_SAYISI))
    adaylar = [i for i in uygun if i not in son[-2:]] or uygun
    no = random.choice(adaylar)
    gecmis[tema] = (son + [no])[-4:]
    try:
        with open(_gecmis_yolu(), "w", encoding="utf-8") as f:
            json.dump(gecmis, f)
    except OSError:
        pass
    return no
