"""
BILGE - Bidik Hikayeleri'nin yardimci karakteri: gozluklu, bilge bir baykus.
Bidik ile ayni cizgi dili (koyu lacivert kontur, yumusak renkler). Sesi: tr-TR-EmelNeural.

    ciz_bilge(img, x, y, olcek=1.0, ifade="normal", agiz=0.0, kirp=0.0, bakis=(0,0), kanat=0.0, ziplama=0.0)
x, y: ayaklarin orta noktasi (yere bastigi yer). Boyu olcek 1'de yaklasik 470 px.
"""
import math
from PIL import Image, ImageDraw

RENK = {
    "govde": (120, 98, 178), "govde_koyu": (92, 72, 148), "karin": (214, 204, 240), "tuy": (186, 172, 226),
    "cizgi": (35, 37, 58), "goz": (255, 255, 255), "gaga": (255, 166, 40), "ayak": (255, 150, 30),
    "gozluk": (35, 37, 58), "yanak": (255, 140, 160),
}
KONTUR = 9
IFADELER = ["normal", "mutlu", "saskin", "dusunceli"]


def ciz_bilge(img, x, y, olcek=1.0, ifade="normal", agiz=0.0, kirp=0.0, bakis=(0.0, 0.0), kanat=0.0, ziplama=0.0,
              aksesuar=None):
    s = olcek
    d = ImageDraw.Draw(img)
    c, w = RENK["cizgi"], max(1, int(KONTUR * s))
    # --- ayaklar ---
    for yon in (-1, 1):
        ax = x + yon * 48 * s
        for p in (-1, 0, 1):
            d.ellipse([ax + p * 16 * s - 12 * s, y - 20 * s, ax + p * 16 * s + 12 * s, y + 4 * s],
                      fill=RENK["ayak"], outline=c, width=max(1, int(5 * s)))
    gx, gy = x, y - 215 * s - ziplama * s
    rx, ry = 150 * s, 195 * s
    # --- kanatlar (govdenin arkasinda) ---
    for yon in (-1, 1):
        acik = kanat * 38
        kx = gx + yon * (rx * 0.78)
        uc = (kx + yon * (70 + acik * 0.6) * s, gy + (40 - acik * 2.2) * s)
        pts = [(kx, gy - 60 * s), (kx + yon * 58 * s, gy - 20 * s), uc, (kx + yon * 40 * s, gy + 120 * s), (kx, gy + 130 * s)]
        d.polygon(pts, fill=RENK["govde_koyu"], outline=c)
        d.line(pts + [pts[0]], fill=c, width=w, joint="curve")
    # --- kulak tuyleri ---
    for yon in (-1, 1):
        pts = [(gx + yon * 70 * s, gy - ry * 0.80), (gx + yon * 132 * s, gy - ry * 1.12), (gx + yon * 122 * s, gy - ry * 0.62)]
        d.polygon(pts, fill=RENK["govde_koyu"], outline=c)
        d.line(pts + [pts[0]], fill=c, width=w, joint="curve")
    # --- govde ---
    d.ellipse([gx - rx, gy - ry, gx + rx, gy + ry], fill=RENK["govde"], outline=c, width=w)
    # karin + tuy desenleri
    kb = [gx - rx * 0.62, gy + ry * 0.05, gx + rx * 0.62, gy + ry * 0.92]
    d.ellipse(kb, fill=RENK["karin"])
    for sira, (yy, adet) in enumerate(((0.32, 3), (0.52, 4), (0.72, 3))):
        for i in range(adet):
            px = gx + (i - (adet - 1) / 2) * 34 * s
            py = gy + ry * yy
            d.arc([px - 13 * s, py - 10 * s, px + 13 * s, py + 12 * s], 20, 160, fill=RENK["tuy"], width=max(1, int(5 * s)))
    d.ellipse([gx - rx, gy - ry, gx + rx, gy + ry], outline=c, width=w)
    g = {"gx": gx, "gy": gy, "rx": rx, "ry": ry, "s": s, "c": c, "w": w}
    ak = AKSESUARLAR.get(aksesuar) if aksesuar else None
    if ak and ak.get("govde"):
        ak["govde"](img, d, g)
    # --- gozler + gozluk ---
    gr = 52 * s
    gozler = [(gx - 62 * s, gy - ry * 0.38), (gx + 62 * s, gy - ry * 0.38)]
    for ex, ey in gozler:
        d.ellipse([ex - gr - 8 * s, ey - gr - 8 * s, ex + gr + 8 * s, ey + gr + 8 * s], fill=RENK["tuy"])
        d.ellipse([ex - gr, ey - gr, ex + gr, ey + gr], fill=RENK["goz"])
        if ifade == "mutlu" and kirp < 0.5:
            d.arc([ex - gr * 0.6, ey - gr * 0.35, ex + gr * 0.6, ey + gr * 0.55], 200, 340, fill=c, width=max(1, int(10 * s)))
        elif kirp >= 0.5:
            d.line([(ex - gr * 0.6, ey + 4 * s), (ex + gr * 0.6, ey + 4 * s)], fill=c, width=max(1, int(9 * s)))
        else:
            pr = (30 if ifade == "saskin" else 24) * s
            bx, by = ex + bakis[0] * 16 * s, ey + bakis[1] * 12 * s - (8 * s if ifade == "dusunceli" else 0)
            d.ellipse([bx - pr, by - pr, bx + pr, by + pr], fill=c)
            d.ellipse([bx - pr * 0.25 + pr * 0.35, by - pr * 0.65, bx + pr * 0.35 + pr * 0.25, by - pr * 0.05], fill=(255, 255, 255))
        d.ellipse([ex - gr - 8 * s, ey - gr - 8 * s, ex + gr + 8 * s, ey + gr + 8 * s], outline=RENK["gozluk"], width=max(1, int(8 * s)))
    d.line([(gozler[0][0] + gr + 6 * s, gozler[0][1] - 6 * s), (gozler[1][0] - gr - 6 * s, gozler[1][1] - 6 * s)],
           fill=RENK["gozluk"], width=max(1, int(8 * s)))
    # kaslar
    if ifade in ("saskin", "dusunceli"):
        for i, (ex, ey) in enumerate(gozler):
            yuk = 0 if ifade == "saskin" else (6 if i == 0 else -10)
            d.arc([ex - 40 * s, ey - gr - 42 * s + yuk * s, ex + 40 * s, ey - gr - 2 * s + yuk * s], 210, 330, fill=c, width=max(1, int(7 * s)))
    # yanaklar
    for ex, ey in gozler:
        d.ellipse([ex - 26 * s, ey + gr + 6 * s, ex + 26 * s, ey + gr + 26 * s], fill=RENK["yanak"])
    # --- gaga: konusurken alt gaga asagi iner, ici gorunur ---
    bx, by = gx, gy - ry * 0.12
    ac = max(0.0, min(1.0, agiz)) * 30 * s
    ust = [(bx - 26 * s, by - 8 * s), (bx + 26 * s, by - 8 * s), (bx, by + 22 * s)]
    if ac > 2:
        ic = [(bx - 22 * s, by + 2 * s), (bx + 22 * s, by + 2 * s), (bx + 10 * s, by + 18 * s + ac), (bx - 10 * s, by + 18 * s + ac)]
        d.polygon(ic, fill=(150, 30, 50), outline=c)
        alt = [(bx - 16 * s, by + 12 * s + ac), (bx + 16 * s, by + 12 * s + ac), (bx, by + 30 * s + ac)]
        d.polygon(alt, fill=RENK["gaga"], outline=c)
    d.polygon(ust, fill=RENK["gaga"], outline=c)
    d.line(ust + [ust[0]], fill=c, width=max(1, int(5 * s)), joint="curve")
    if ak and ak.get("kafa"):
        ak["kafa"](img, d, g)
    if ak and ak.get("on"):
        ak["on"](img, d, g)


# --- aksesuarlar (konuya gore; Bidik'in kostumleriyle uyumlu) ------------------------------
def _ust(g):
    return g["gy"] - g["ry"]          # kafanin tepesi


def _cizgi(d, pts, g, kalin=None):
    d.line(pts + [pts[0]], fill=g["c"], width=kalin or g["w"], joint="curve")


def mezuniyet(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    d.rounded_rectangle([gx - 62 * s, ty - 28 * s, gx + 62 * s, ty + 26 * s], radius=int(12 * s), fill=(40, 42, 64), outline=c, width=w)
    ust = [(gx - 125 * s, ty - 40 * s), (gx, ty - 82 * s), (gx + 125 * s, ty - 40 * s), (gx, ty + 2 * s)]
    d.polygon(ust, fill=(52, 54, 80))
    _cizgi(d, ust, g)
    d.ellipse([gx - 9 * s, ty - 50 * s, gx + 9 * s, ty - 32 * s], fill=(255, 196, 30), outline=c, width=max(1, int(4 * s)))
    d.line([(gx, ty - 41 * s), (gx + 92 * s, ty - 30 * s), (gx + 96 * s, ty + 40 * s)], fill=(255, 196, 30), width=int(7 * s))
    d.rounded_rectangle([gx + 86 * s, ty + 34 * s, gx + 106 * s, ty + 72 * s], radius=int(6 * s), fill=(255, 196, 30), outline=c, width=max(1, int(4 * s)))


def astronot(img, d, g):
    gx, gy, ry, s, c = g["gx"], g["gy"], g["ry"], g["s"], g["c"]
    cx, cy, r = gx, gy - ry * 0.30, 205 * s
    kat = Image.new("RGBA", img.size, (0, 0, 0, 0))
    kd = ImageDraw.Draw(kat)
    kd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(190, 225, 255, 60))
    kd.arc([cx - r * 0.82, cy - r * 0.82, cx + r * 0.82, cy + r * 0.82], 200, 250, fill=(255, 255, 255, 220), width=int(14 * s))
    img.paste(Image.alpha_composite(img.convert("RGBA"), kat).convert(img.mode))
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=g["w"])
    d.ellipse([cx - r + 7 * s, cy - r + 7 * s, cx + r - 7 * s, cy + r - 7 * s], outline=(225, 235, 250), width=int(5 * s))
    d.line([(cx + r * 0.55, cy - r * 0.83), (cx + r * 0.75, cy - r * 1.12)], fill=c, width=int(7 * s))
    d.ellipse([cx + r * 0.75 - 13 * s, cy - r * 1.12 - 13 * s, cx + r * 0.75 + 13 * s, cy - r * 1.12 + 13 * s], fill=(230, 57, 70), outline=c, width=max(1, int(4 * s)))
    # yaka halkasi
    d.rounded_rectangle([gx - 150 * s, cy + r - 26 * s, gx + 150 * s, cy + r + 10 * s], radius=int(16 * s), fill=(220, 224, 236), outline=c, width=g["w"])


def buyucu(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    d.ellipse([gx - 110 * s, ty - 8 * s, gx + 110 * s, ty + 30 * s], fill=(60, 50, 130), outline=c, width=w)
    kon = [(gx - 72 * s, ty + 8 * s), (gx + 18 * s, ty - 200 * s), (gx + 78 * s, ty + 8 * s)]
    d.polygon(kon, fill=(76, 62, 160))
    _cizgi(d, kon, g)
    for (dx, dy, r) in ((-20, -40, 13), (22, -95, 10), (10, -150, 8)):
        _yildiz(d, gx + dx * s, ty + dy * s, r * s)


def _yildiz(d, cx, cy, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(pts, fill=(255, 214, 80))


def safari(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    d.ellipse([gx - 150 * s, ty - 4 * s, gx + 150 * s, ty + 36 * s], fill=(196, 168, 112), outline=c, width=w)
    d.chord([gx - 92 * s, ty - 92 * s, gx + 92 * s, ty + 70 * s], 180, 360, fill=(214, 186, 128), outline=c, width=w)
    d.rectangle([gx - 90 * s, ty - 6 * s, gx + 90 * s, ty + 12 * s], fill=(120, 92, 52))
    d.line([(gx - 90 * s, ty - 6 * s), (gx + 90 * s, ty - 6 * s)], fill=c, width=max(1, int(4 * s)))


def asci(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    for dx, dy, r in ((-58, -78, 52), (0, -104, 60), (58, -78, 52)):
        d.ellipse([gx + (dx - r) * s, ty + (dy - r) * s, gx + (dx + r) * s, ty + (dy + r) * s], fill=(255, 255, 255), outline=c, width=w)
    d.rectangle([gx - 92 * s, ty - 80 * s, gx + 92 * s, ty - 30 * s], fill=(255, 255, 255))
    d.rounded_rectangle([gx - 96 * s, ty - 40 * s, gx + 96 * s, ty + 22 * s], radius=int(12 * s), fill=(245, 245, 248), outline=c, width=w)


def laboratuvar(img, d, g):
    gx, gy, rx, ry, s, c, w = g["gx"], g["gy"], g["rx"], g["ry"], g["s"], g["c"], g["w"]
    for yon in (-1, 1):
        pts = [(gx + yon * 30 * s, gy + ry * 0.02), (gx + yon * rx * 0.98, gy + ry * 0.05), (gx + yon * rx * 0.86, gy + ry * 0.62),
               (gx + yon * rx * 0.58, gy + ry * 0.95), (gx + yon * 62 * s, gy + ry * 0.98), (gx + yon * 70 * s, gy + ry * 0.35)]
        d.polygon(pts, fill=(250, 250, 252))
        d.line(pts, fill=c, width=w, joint="curve")
    # cep + kalemler
    px, py = gx + rx * 0.55, gy + ry * 0.45
    d.line([(px - 4 * s, py - 30 * s), (px - 4 * s, py)], fill=(70, 140, 230), width=int(8 * s))
    d.line([(px + 14 * s, py - 24 * s), (px + 14 * s, py)], fill=(230, 57, 70), width=int(8 * s))
    d.rounded_rectangle([px - 26 * s, py - 4 * s, px + 32 * s, py + 46 * s], radius=int(6 * s), fill=(235, 238, 244), outline=c, width=max(1, int(5 * s)))


def doktor(img, d, g):
    gx, gy, rx, ry, s, c, w = g["gx"], g["gy"], g["rx"], g["ry"], g["s"], g["c"], g["w"]
    boru = (60, 64, 84)
    d.arc([gx - rx * 0.62, gy - ry * 0.05, gx + rx * 0.62, gy + ry * 0.55], 0, 180, fill=boru, width=int(10 * s))
    d.line([(gx + rx * 0.3, gy + ry * 0.47), (gx + rx * 0.36, gy + ry * 0.72)], fill=boru, width=int(10 * s))
    cx, cy, r = gx + rx * 0.36, gy + ry * 0.76, 24 * s
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 205, 215), outline=c, width=max(1, int(6 * s)))
    # kafa aynasi
    ty = _ust(g)
    d.arc([gx - rx * 0.9, ty - 8 * s, gx + rx * 0.9, ty + ry * 0.5], 200, 340, fill=(60, 64, 84), width=int(9 * s))
    d.ellipse([gx - 30 * s, ty - 22 * s, gx + 30 * s, ty + 38 * s], fill=(235, 240, 248), outline=c, width=w)
    d.ellipse([gx - 9 * s, ty - 1 * s, gx + 9 * s, ty + 17 * s], fill=(255, 255, 255))


def defne(img, d, g):
    gx, s, c, ty = g["gx"], g["s"], g["c"], _ust(g)
    for yon in (-1, 1):
        for i in range(6):
            a = math.radians(200 + i * 14) if yon < 0 else math.radians(340 - i * 14)
            px, py = gx + math.cos(a) * 118 * s, ty + 50 * s + math.sin(a) * 70 * s
            d.ellipse([px - 22 * s, py - 11 * s, px + 22 * s, py + 11 * s], fill=(96, 170, 80), outline=c, width=max(1, int(4 * s)))
    d.ellipse([gx - 12 * s, ty - 30 * s, gx + 12 * s, ty - 6 * s], fill=(230, 57, 70), outline=c, width=max(1, int(4 * s)))


def papyon(img, d, g):
    gx, gy, ry, s, c, w = g["gx"], g["gy"], g["ry"], g["s"], g["c"], g["w"]
    cy = gy + ry * 0.10
    for yon in (-1, 1):
        pts = [(gx, cy), (gx + yon * 58 * s, cy - 30 * s), (gx + yon * 58 * s, cy + 30 * s)]
        d.polygon(pts, fill=(200, 40, 60))
        _cizgi(d, pts, g)
    d.rounded_rectangle([gx - 14 * s, cy - 16 * s, gx + 14 * s, cy + 16 * s], radius=int(6 * s), fill=(170, 30, 50), outline=c, width=max(1, int(5 * s)))


def kulaklik(img, d, g):
    gx, gy, rx, ry, s, c, w = g["gx"], g["gy"], g["rx"], g["ry"], g["s"], g["c"], g["w"]
    ty = _ust(g)
    d.arc([gx - rx * 1.0, ty - 30 * s, gx + rx * 1.0, ty + ry * 1.2], 192, 348, fill=(60, 64, 84), width=int(18 * s))
    for yon in (-1, 1):
        cx, cy = gx + yon * rx * 0.97, gy - ry * 0.32
        d.rounded_rectangle([cx - 26 * s, cy - 44 * s, cx + 26 * s, cy + 44 * s], radius=int(20 * s), fill=(70, 140, 230), outline=c, width=w)
    d.line([(gx - rx * 0.97, gy - ry * 0.1), (gx - rx * 0.5, gy + ry * 0.12)], fill=(60, 64, 84), width=int(8 * s))
    d.ellipse([gx - rx * 0.5 - 13 * s, gy + ry * 0.12 - 13 * s, gx - rx * 0.5 + 13 * s, gy + ry * 0.12 + 13 * s], fill=(60, 64, 84))


def kaptan(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    d.chord([gx - 120 * s, ty - 34 * s, gx + 120 * s, ty + 44 * s], 180, 360, fill=(30, 34, 52), outline=c, width=w)   # siper
    d.rounded_rectangle([gx - 98 * s, ty - 76 * s, gx + 98 * s, ty + 2 * s], radius=int(28 * s), fill=(255, 255, 255), outline=c, width=w)
    d.rectangle([gx - 92 * s, ty - 16 * s, gx + 92 * s, ty + 2 * s], fill=(30, 34, 52))
    # capa
    ax, ay = gx, ty - 46 * s
    d.ellipse([ax - 8 * s, ay - 22 * s, ax + 8 * s, ay - 6 * s], outline=(222, 168, 48), width=max(1, int(4 * s)))
    d.line([(ax, ay - 6 * s), (ax, ay + 16 * s)], fill=(222, 168, 48), width=int(5 * s))
    d.arc([ax - 18 * s, ay - 4 * s, ax + 18 * s, ay + 20 * s], 20, 160, fill=(222, 168, 48), width=int(5 * s))


def pervane(img, d, g):
    gx, s, c, w, ty = g["gx"], g["s"], g["c"], g["w"], _ust(g)
    d.chord([gx - 100 * s, ty - 70 * s, gx + 100 * s, ty + 60 * s], 180, 360, fill=(255, 196, 30), outline=c, width=w)
    d.pieslice([gx - 100 * s, ty - 70 * s, gx + 100 * s, ty + 60 * s], 180, 240, fill=(230, 57, 70))
    d.pieslice([gx - 100 * s, ty - 70 * s, gx + 100 * s, ty + 60 * s], 300, 360, fill=(70, 140, 230))
    d.chord([gx - 100 * s, ty - 70 * s, gx + 100 * s, ty + 60 * s], 180, 360, outline=c, width=w)
    d.line([(gx, ty - 70 * s), (gx, ty - 92 * s)], fill=c, width=int(6 * s))
    for yon, renk in ((-1, (230, 57, 70)), (1, (70, 140, 230))):
        pts = [(gx, ty - 96 * s), (gx + yon * 74 * s, ty - 110 * s), (gx + yon * 74 * s, ty - 86 * s)]
        d.polygon(pts, fill=renk)
        _cizgi(d, pts, g, max(1, int(5 * s)))


AKSESUARLAR = {
    "mezuniyet": {"kafa": mezuniyet}, "astronot": {"on": astronot}, "buyucu": {"kafa": buyucu},
    "safari": {"kafa": safari}, "asci": {"kafa": asci}, "laboratuvar": {"govde": laboratuvar},
    "doktor": {"govde": doktor}, "defne": {"kafa": defne}, "papyon": {"on": papyon}, "kulaklik": {"kafa": kulaklik},
    "kaptan": {"kafa": kaptan}, "pervane": {"kafa": pervane},
}
# arka plan temasi -> Bilge'nin aksesuari
TEMA_AKSESUAR = {"uzay": "astronot", "burclar": "buyucu", "hayvanlar": "safari", "yemek": "asci", "bilim": "laboratuvar",
                 "insan": "doktor", "tarih": "defne", "psikoloji": "papyon", "teknoloji": "kulaklik",
                 "cografya": "kaptan", "cocuk": "pervane", "genel": "mezuniyet"}
