"""
BILGE - Bidik Hikayeleri'nin yardimci karakteri: gozluklu, bilge bir baykus.
Bidik ile ayni cizgi dili (koyu lacivert kontur, yumusak renkler). Sesi: tr-TR-EmelNeural.

    ciz_bilge(img, x, y, olcek=1.0, ifade="normal", agiz=0.0, kirp=0.0, bakis=(0,0), kanat=0.0, ziplama=0.0)
x, y: ayaklarin orta noktasi (yere bastigi yer). Boyu olcek 1'de yaklasik 470 px.
"""
import math
from PIL import ImageDraw

RENK = {
    "govde": (120, 98, 178), "govde_koyu": (92, 72, 148), "karin": (214, 204, 240), "tuy": (186, 172, 226),
    "cizgi": (35, 37, 58), "goz": (255, 255, 255), "gaga": (255, 166, 40), "ayak": (255, 150, 30),
    "gozluk": (35, 37, 58), "yanak": (255, 140, 160),
}
KONTUR = 9
IFADELER = ["normal", "mutlu", "saskin", "dusunceli"]


def ciz_bilge(img, x, y, olcek=1.0, ifade="normal", agiz=0.0, kirp=0.0, bakis=(0.0, 0.0), kanat=0.0, ziplama=0.0):
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
