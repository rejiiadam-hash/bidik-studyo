"""
Bidik'in kostum dolabi: konuya uygun kiyafetler, tamamen kodla cizilir.

Her kostum en fazla uc katman cizer:
  govde(img, d, g)  : govdenin ustune, agiz/kollarin ALTINA (onluk, stetoskop)
  kafa(img, d, g)   : yuzden sonra (sapka, kulaklik, gozluk). Donus: percemin cikacagi
                      tepe noktasi (x, y); None = normal yer; False = percem gizli
  on(img, d, g)     : en onde (astronot fanusu)
g: {"gx","gy","rx","ry","s","c","w","faz"} - govde merkezi, yaricaplar, olcek, kontur rengi/kalinligi, animasyon fazi.
Kimlik korunur: sari govde, kirmizi ayakkabi, yuz ifadeleri ve (cogu kostumde) percem hep gorunur.
"""
import math
from PIL import Image, ImageDraw

BEYAZ = (255, 255, 255)
SARI = (255, 214, 64)


def _yarim_kubbe(d, cx, taban_y, yr, yy, renk, c, w):
    """Tabani duz yarim elips (sapka kubbesi)."""
    d.chord([cx - yr, taban_y - yy, cx + yr, taban_y + yy], 180, 360, fill=renk, outline=c, width=w)
    d.line([(cx - yr, taban_y), (cx + yr, taban_y)], fill=c, width=w)


def _yildiz(d, cx, cy, r, renk, c=None, w=0):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=renk, outline=c, width=w)


def _kalin(d, pts, w, renk):
    d.line(pts, fill=renk, width=int(w), joint="curve")
    r = w / 2
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=renk)


def _bez(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
            for t in (i / n for i in range(n + 1))]


def _brim(g):
    return g["gy"] - 155 * g["s"]


# --- 1. YEMEK: asci sapkasi -------------------------------------------------------
def asci(img, d, g):
    gx, s, c, w = g["gx"], g["s"], g["c"], g["w"]
    by = _brim(g)
    puflar = [(gx - 62 * s, by - 95 * s, 58 * s), (gx + 62 * s, by - 95 * s, 58 * s), (gx, by - 118 * s, 66 * s)]
    for px, py, r in puflar:
        d.ellipse([px - r, py - r, px + r, py + r], fill=c)
    for px, py, r in puflar:
        r2 = r - w
        d.ellipse([px - r2, py - r2, px + r2, py + r2], fill=BEYAZ)
    d.rounded_rectangle([gx - 100 * s, by - 62 * s, gx + 100 * s, by + 10 * s], radius=int(14 * s),
                        fill=BEYAZ, outline=c, width=w)
    for i in (-2, -1, 0, 1, 2):
        d.line([(gx + i * 34 * s, by - 50 * s), (gx + i * 34 * s, by - 4 * s)], fill=(215, 215, 222), width=int(5 * s))
    return (gx, by - 178 * s)


# --- 2. HAYVANLAR: safari sapkasi ---------------------------------------------------
def safari(img, d, g):
    gx, s, c, w = g["gx"], g["s"], g["c"], g["w"]
    by = _brim(g)
    haki, koyu = (205, 176, 120), (120, 88, 52)
    _yarim_kubbe(d, gx, by + 2 * s, 102 * s, 104 * s, haki, c, w)
    _kalin(d, [(gx - 96 * s, by - 16 * s), (gx + 96 * s, by - 16 * s)], 18 * s, koyu)
    d.ellipse([gx - 158 * s, by - 18 * s, gx + 158 * s, by + 24 * s], fill=haki, outline=c, width=w)
    d.ellipse([gx - 128 * s, by - 8 * s, gx + 128 * s, by + 12 * s], fill=(185, 156, 102))
    return (gx, by - 100 * s)


# --- 3. PSIKOLOJI: dedektif sapkasi -------------------------------------------------
def dedektif(img, d, g):
    gx, s, c, w = g["gx"], g["s"], g["c"], g["w"]
    by = _brim(g)
    kahve, koyu = (164, 120, 78), (118, 82, 50)
    yr, yy = 108 * s, 100 * s
    # kareli kubbe: once kubbe, sonra kubbe maskesiyle karo cizgileri
    x0, y0 = int(gx - yr), int(by - yy)
    katman = Image.new("RGB", (int(2 * yr) + 2, int(yy) + 2), kahve)
    kd = ImageDraw.Draw(katman)
    adim = 26 * s
    for i in range(-6, 7):
        kd.line([(yr + i * adim, 0), (yr + i * adim, yy)], fill=koyu, width=int(5 * s))
    for j in range(1, 5):
        kd.line([(0, yy - j * adim), (2 * yr, yy - j * adim)], fill=koyu, width=int(5 * s))
    maske = Image.new("L", katman.size, 0)
    ImageDraw.Draw(maske).chord([0, 0, 2 * yr, 2 * yy], 180, 360, fill=255)
    img.paste(katman, (x0, y0), maske)
    d.chord([gx - yr, by - yy, gx + yr, by + yy], 180, 360, outline=c, width=w)
    d.line([(gx - yr, by), (gx + yr, by)], fill=c, width=w)
    # on siper
    d.chord([gx - 78 * s, by - 16 * s, gx + 78 * s, by + 24 * s], 0, 180, fill=koyu, outline=c, width=w)
    # tepede fiyonk (kulakliklar yukari baglanmis)
    t = by - yy + 6 * s
    for yon in (-1, 1):
        d.polygon([(gx, t), (gx + yon * 34 * s, t - 18 * s), (gx + yon * 34 * s, t + 16 * s)], fill=koyu, outline=c)
    d.ellipse([gx - 9 * s, t - 9 * s, gx + 9 * s, t + 9 * s], fill=koyu, outline=c, width=int(4 * s))
    return (gx - 6 * s, t - 6 * s)


# --- 4. BURCLAR: yildizli buyucu sapkasi --------------------------------------------
def buyucu(img, d, g):
    gx, s, c, w = g["gx"], g["s"], g["c"], g["w"]
    by = _brim(g)
    lac = (58, 62, 150)
    uc = (gx + 50 * s, by - 205 * s)
    sol = _bez((gx - 105 * s, by), (gx - 35 * s, by - 120 * s), uc)
    sag = _bez(uc, (gx + 30 * s, by - 100 * s), (gx + 105 * s, by))
    d.polygon(sol + sag[1:], fill=lac, outline=c)
    _kalin(d, sol, w, c)
    _kalin(d, sag, w, c)
    _yildiz(d, gx - 30 * s, by - 70 * s, 22 * s, SARI)
    _yildiz(d, gx + 30 * s, by - 112 * s, 14 * s, SARI)
    _yildiz(d, gx + 8 * s, by - 30 * s, 11 * s, SARI)
    # hilal
    hx, hy, hr = gx + 50 * s, by - 50 * s, 17 * s
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=SARI)
    d.ellipse([hx - hr + 9 * s, hy - hr - 4 * s, hx + hr + 9 * s, hy + hr - 4 * s], fill=lac)
    d.ellipse([gx - 165 * s, by - 20 * s, gx + 165 * s, by + 22 * s], fill=lac, outline=c, width=w)
    return (uc[0] - 6 * s, uc[1] + 6 * s)


# --- 5. COCUK SORULARI: pervaneli sapka ---------------------------------------------
def pervane(img, d, g):
    gx, s, c, w, faz = g["gx"], g["s"], g["c"], g["w"], g["faz"]
    by = _brim(g)
    yr, yy = 108 * s, 100 * s
    kutu = [gx - yr, by - yy, gx + yr, by + yy]
    for i, renk in enumerate([(230, 57, 70), (255, 196, 0), (60, 170, 100), (61, 127, 217)]):
        d.pieslice(kutu, 180 + i * 45, 225 + i * 45, fill=renk, outline=c, width=int(5 * s))
    d.chord(kutu, 180, 360, outline=c, width=w)
    d.line([(gx - yr, by), (gx + yr, by)], fill=c, width=w)
    d.chord([gx - 80 * s, by - 14 * s, gx + 80 * s, by + 26 * s], 0, 180, fill=(61, 127, 217), outline=c, width=w)
    # pervane: kendi etrafinda doner (genislik cos ile degisir)
    tepe = by - yy
    _kalin(d, [(gx, tepe + 4 * s), (gx, tepe - 30 * s)], 9 * s, c)
    aci = faz * 2 * math.pi * 2.5
    L = 92 * s * max(0.12, abs(math.cos(aci)))
    py = tepe - 34 * s
    yon = 1 if math.cos(aci) >= 0 else -1
    d.ellipse([gx - L, py - 11 * s, gx, py + 11 * s], fill=(230, 57, 70) if yon > 0 else (61, 127, 217), outline=c, width=int(5 * s))
    d.ellipse([gx, py - 11 * s, gx + L, py + 11 * s], fill=(61, 127, 217) if yon > 0 else (230, 57, 70), outline=c, width=int(5 * s))
    d.ellipse([gx - 10 * s, py - 10 * s, gx + 10 * s, py + 10 * s], fill=SARI, outline=c, width=int(4 * s))
    return (gx - 50 * s, tepe + 18 * s)


# --- 6. TARIH: miğfer (sorguclu) -------------------------------------------------------
def migfer(img, d, g):
    gx, gy, s, c, w = g["gx"], g["gy"], g["s"], g["c"], g["w"]
    by = _brim(g)
    altin, koyu = (222, 168, 48), (176, 124, 24)
    # sorguc (kirmizi tuy)
    sy = by - 70 * s                      # sorgucun tabani kubbenin icinde kalir
    d.chord([gx - 104 * s, sy - 112 * s, gx + 104 * s, sy + 112 * s], 180, 360, fill=(214, 40, 54), outline=c, width=w)
    for i in range(-4, 5):
        aci = math.pi * (0.5 + i / 10)
        d.line([(gx + math.cos(aci) * 30 * s, sy - math.sin(aci) * 30 * s),
                (gx + math.cos(aci) * 98 * s, sy - math.sin(aci) * 104 * s)], fill=(160, 24, 40), width=int(4 * s))
    _yarim_kubbe(d, gx, by + 6 * s, 114 * s, 96 * s, altin, c, w)
    # yanak korumalari
    for yon in (-1, 1):
        x1, x2 = sorted((gx + yon * 100 * s, gx + yon * 140 * s))
        d.rounded_rectangle([x1, by - 4 * s, x2, by + 92 * s], radius=int(16 * s), fill=altin, outline=c, width=w)
    d.rounded_rectangle([gx - 124 * s, by - 8 * s, gx + 124 * s, by + 14 * s], radius=int(8 * s), fill=koyu, outline=c, width=w)
    return False   # sorguc percemin yerini alir


# --- 7. UZAY: astronot fanusu ---------------------------------------------------------
def astronot_govde(img, d, g):
    gx, gy, s, c = g["gx"], g["gy"], g["s"], g["c"]
    # gogus armasi
    ax, ay, r = gx + 78 * s, gy + 98 * s, 26 * s
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(61, 127, 217), outline=c, width=int(5 * s))
    _yildiz(d, ax, ay, 15 * s, BEYAZ)


def astronot_on(img, d, g):
    gx, gy, s, c, w = g["gx"], g["gy"], g["s"], g["c"], g["w"]
    r = 218 * s
    cx, cy = gx, gy - 52 * s
    kutu = [int(cx - r - w), int(cy - r - w), int(cx + r + w), int(cy + r + w)]
    katman = Image.new("RGBA", (kutu[2] - kutu[0], kutu[3] - kutu[1]), (0, 0, 0, 0))
    kd = ImageDraw.Draw(katman)
    o = w
    kd.ellipse([o, o, o + 2 * r, o + 2 * r], fill=(140, 200, 255, 20), outline=(35, 37, 58, 255), width=w)
    # koyu arka planlarda da secilsin: ic tarafta acik renkli ince kenar
    kd.ellipse([o + w * 0.8, o + w * 0.8, o + 2 * r - w * 0.8, o + 2 * r - w * 0.8], outline=(215, 230, 255, 230), width=int(w * 0.55))
    # parlama
    kd.arc([o + r * 0.25, o + r * 0.2, o + r * 1.4, o + r * 1.35], 195, 250, fill=(255, 255, 255, 230), width=int(14 * s))
    kd.arc([o + r * 0.25, o + r * 0.2, o + r * 1.4, o + r * 1.35], 258, 270, fill=(255, 255, 255, 230), width=int(14 * s))
    img.paste(katman.convert("RGB"), (kutu[0], kutu[1]), katman)


# --- 8. COGRAFYA: kaptan sapkasi -------------------------------------------------------
def kaptan(img, d, g):
    gx, s, c, w = g["gx"], g["s"], g["c"], g["w"]
    by = _brim(g)
    lac = (34, 44, 82)
    d.rounded_rectangle([gx - 98 * s, by - 58 * s, gx + 98 * s, by + 4 * s], radius=int(10 * s), fill=lac, outline=c, width=w)
    d.ellipse([gx - 132 * s, by - 112 * s, gx + 132 * s, by - 40 * s], fill=BEYAZ, outline=c, width=w)
    d.chord([gx - 104 * s, by - 18 * s, gx + 104 * s, by + 26 * s], 0, 180, fill=(20, 22, 34), outline=c, width=w)
    # altin capa armasi
    ax, ay = gx, by - 30 * s
    d.ellipse([ax - 20 * s, ay - 20 * s, ax + 20 * s, ay + 20 * s], fill=(222, 168, 48), outline=c, width=int(4 * s))
    _kalin(d, [(ax, ay - 12 * s), (ax, ay + 12 * s)], 5 * s, lac)
    d.arc([ax - 11 * s, ay - 4 * s, ax + 11 * s, ay + 14 * s], 0, 180, fill=lac, width=int(5 * s))
    _kalin(d, [(ax - 7 * s, ay - 6 * s), (ax + 7 * s, ay - 6 * s)], 4 * s, lac)
    return (gx, by - 108 * s)


# --- 9. TEKNOLOJI: oyuncu kulakligi ----------------------------------------------------
def kulaklik(img, d, g):
    gx, gy, s, c, w = g["gx"], g["gy"], g["s"], g["c"], g["w"]
    gri, mavi = (62, 64, 84), (0, 200, 255)
    band = _bez((gx - 140 * s, gy - 92 * s), (gx, gy - 272 * s), (gx + 140 * s, gy - 92 * s))
    _kalin(d, band, 30 * s, c)
    _kalin(d, band, 18 * s, gri)
    # mikrofon kolu (sol kulaktan agza dogru)
    kol = _bez((gx - 150 * s, gy - 40 * s), (gx - 150 * s, gy + 40 * s), (gx - 82 * s, gy + 36 * s))
    _kalin(d, kol, 14 * s, c)
    _kalin(d, kol, 6 * s, gri)
    d.ellipse([gx - 96 * s, gy + 24 * s, gx - 70 * s, gy + 48 * s], fill=gri, outline=c, width=int(4 * s))
    for yon in (-1, 1):
        x1, x2 = sorted((gx + yon * 122 * s, gx + yon * 172 * s))
        d.rounded_rectangle([x1, gy - 128 * s, x2, gy - 30 * s], radius=int(22 * s), fill=gri, outline=c, width=w)
        d.rounded_rectangle([x1 + 12 * s, gy - 110 * s, x2 - 12 * s, gy - 48 * s], radius=int(12 * s), fill=mavi)
    return None


# --- 10. BILIM: koruyucu gozluk + laboratuvar onlugu ----------------------------------
def onluk(img, d, g):
    """On tarafi acik beyaz laboratuvar onlugu: govdenin iki yaninda, ortada sari karin gorunur."""
    gx, gy, rx, ry, s, c, w = g["gx"], g["gy"], g["rx"], g["ry"], g["s"], g["c"], g["w"]
    ust, alt = gy + 22 * s, gy + ry
    kutu = [int(gx - rx), int(gy - ry), int(gx + rx), int(alt)]
    katman = Image.new("RGB", (kutu[2] - kutu[0], kutu[3] - kutu[1]), BEYAZ)
    maske = Image.new("L", katman.size, 0)
    md = ImageDraw.Draw(maske)
    o = w * 0.55
    md.ellipse([o, o, 2 * rx - o, 2 * ry - o], fill=255)
    oy = ust - (gy - ry)
    md.rectangle([0, 0, 2 * rx, oy], fill=0)                          # ust kisim acik (yuz)
    md.polygon([(rx - 58 * s, oy), (rx + 58 * s, oy), (rx + 40 * s, 2 * ry), (rx - 40 * s, 2 * ry)], fill=0)
    img.paste(katman, (kutu[0], kutu[1]), maske)
    for yon in (-1, 1):
        # on kenar + yaka kivrimi
        d.line([(gx + yon * 58 * s, ust), (gx + yon * 40 * s, alt - 4 * s)], fill=c, width=int(6 * s))
        d.line([(gx + yon * 58 * s, ust), (gx + yon * 96 * s, ust + 58 * s)], fill=(200, 202, 214), width=int(5 * s))
        d.line([(gx + yon * (rx * 0.93), ust), (gx + yon * 58 * s, ust)], fill=c, width=int(5 * s))
    # cep + kalem
    d.rounded_rectangle([gx + 66 * s, gy + 100 * s, gx + 110 * s, gy + 136 * s], radius=int(6 * s), outline=c, width=int(5 * s))
    _kalin(d, [(gx + 80 * s, gy + 90 * s), (gx + 80 * s, gy + 112 * s)], 7 * s, (61, 127, 217))


def bilimci(img, d, g):
    gx, gy, s, c, w = g["gx"], g["gy"], g["s"], g["c"], g["w"]
    kayis = _bez((gx - 110 * s, gy - 126 * s), (gx, gy - 168 * s), (gx + 110 * s, gy - 126 * s))
    _kalin(d, kayis, 16 * s, (40, 160, 120))
    for yon in (-1, 1):
        lx, ly, r = gx + yon * 44 * s, gy - 160 * s, 30 * s
        d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(40, 160, 120), outline=c, width=w)
        d.ellipse([lx - r + 9 * s, ly - r + 9 * s, lx + r - 9 * s, ly + r - 9 * s], fill=(190, 235, 255))
        d.arc([lx - r + 14 * s, ly - r + 14 * s, lx + r - 14 * s, ly + r - 14 * s], 200, 260, fill=BEYAZ, width=int(5 * s))
    return (gx, gy - 182 * s)


# --- 11. INSAN VUCUDU: doktor (kafa aynasi + stetoskop) -------------------------------
def stetoskop(img, d, g):
    gx, gy, s, c = g["gx"], g["gy"], g["s"], g["c"]
    gri = (90, 96, 120)
    hortum = _bez((gx - 128 * s, gy + 30 * s), (gx - 70 * s, gy + 150 * s), (gx, gy + 132 * s)) + \
        _bez((gx, gy + 132 * s), (gx + 70 * s, gy + 150 * s), (gx + 128 * s, gy + 30 * s))[1:]
    _kalin(d, hortum, 14 * s, c)
    _kalin(d, hortum, 7 * s, gri)
    sarkan = _bez((gx, gy + 132 * s), (gx + 10 * s, gy + 160 * s), (gx + 46 * s, gy + 150 * s))
    _kalin(d, sarkan, 12 * s, c)
    _kalin(d, sarkan, 5 * s, gri)
    ux, uy, r = gx + 58 * s, gy + 148 * s, 18 * s
    d.ellipse([ux - r, uy - r, ux + r, uy + r], fill=(205, 210, 222), outline=c, width=int(5 * s))


def doktor(img, d, g):
    gx, gy, s, c, w = g["gx"], g["gy"], g["s"], g["c"], g["w"]
    kayis = _bez((gx - 112 * s, gy - 122 * s), (gx, gy - 164 * s), (gx + 112 * s, gy - 122 * s))
    _kalin(d, kayis, 14 * s, (230, 230, 236))
    _kalin(d, kayis, 5 * s, (180, 182, 196))
    mx, my, r = gx, gy - 160 * s, 34 * s
    d.ellipse([mx - r, my - r, mx + r, my + r], fill=(205, 210, 222), outline=c, width=w)
    d.ellipse([mx - 10 * s, my - 10 * s, mx + 10 * s, my + 10 * s], fill=c)
    d.arc([mx - r + 8 * s, my - r + 8 * s, mx + r - 8 * s, my + r - 8 * s], 200, 250, fill=BEYAZ, width=int(5 * s))
    return (gx, gy - 182 * s)


# "ust": bas tepesinin USTUNE cikan yukseklik (percem dahil, olcek 1'de px).
# Video uretimi bunu kullanarak Bidik'i altyaziya / bilgi kartina carpmayacak kadar kucultur.
KOSTUMLER = {
    "asci":      {"ad": "Aşçı şapkası",       "ust": 235, "kafa": asci},
    "safari":    {"ad": "Safari şapkası",     "ust": 160, "kafa": safari},
    "dedektif":  {"ad": "Dedektif şapkası",   "ust": 160, "kafa": dedektif},
    "buyucu":    {"ad": "Yıldızlı büyücü",    "ust": 262, "kafa": buyucu},
    "pervane":   {"ad": "Pervaneli şapka",    "ust": 140, "kafa": pervane},
    "migfer":    {"ad": "Miğfer",             "ust": 160, "kafa": migfer},
    "astronot":  {"ad": "Astronot",           "ust": 95,  "govde": astronot_govde, "on": astronot_on},
    "kaptan":    {"ad": "Kaptan şapkası",     "ust": 165, "kafa": kaptan},
    "kulaklik":  {"ad": "Oyuncu kulaklığı",   "ust": 80,  "kafa": kulaklik},
    "bilimci":   {"ad": "Bilimci",            "ust": 85,  "govde": onluk, "kafa": bilimci},
    "doktor":    {"ad": "Doktor",             "ust": 85,  "govde": stetoskop, "kafa": doktor},
}
PERCEM_UST = 80   # kostumsuz halde percemin bas ustune cikan yuksekligi


def ust_boy(kostum):
    return (KOSTUMLER.get(kostum) or {}).get("ust", PERCEM_UST)


def _sade(m):
    m = str(m or "").lower()
    for a, b in zip("çğıöşüâî", "cgiosuai"):
        m = m.replace(a, b)
    return m


# konu alani -> kostum (sirayla ilk eslesen; "mutfak bilimi" "bilim"den once gelmeli)
ESLESME = [
    (("yemek", "mutfak"), "asci"), (("burc", "gokyuzu", "astroloji", "zodyak"), "buyucu"),
    (("cocuk", "neden"), "pervane"), (("uzay", "gezegen", "astronomi"), "astronot"),
    (("hayvan",), "safari"), (("insan vucud", "saglik", "beden"), "doktor"),
    (("tarih",), "migfer"), (("psikoloji", "beyin", "zihin"), "dedektif"),
    (("teknoloji", "bilgisayar", "internet"), "kulaklik"), (("cografya", "dunya"), "kaptan"),
    (("bilim",), "bilimci"),
]


def kostum_sec(alan, konu=""):
    a = _sade(alan)
    for anahtarlar, kostum in ESLESME:
        if any(k in a for k in anahtarlar):
            return kostum
    k = _sade(konu)
    for anahtarlar, kostum in ESLESME:
        if any(x in k for x in anahtarlar):
            return kostum
    return ""
