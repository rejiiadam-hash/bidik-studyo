"""
BIDIK - kanalin sabit cizgi karakteri.

Karakter tamamen kodla cizilir; bu yuzden her videoda birebir ayni gorunur.
Degisen tek sey parametrelerdir: ifade, agiz acikligi, goz kirpma, bakis yonu,
kol pozu, egilme/ziplama. Yeni video hazirlarken sadece bu parametreler verilir.

Kullanim:
    from karakter import ciz_bidik
    ciz_bidik(img, x=540, y=1300, olcek=1.0, ifade="mutlu", agiz=0.6)
"""
import math
from PIL import Image, ImageDraw

# --- Sabit kimlik: bunlar degismez -------------------------------------------
RENK = {
    "govde": (255, 183, 3),       # sicak sari-turuncu
    "govde_golge": (240, 150, 0),
    "cizgi": (35, 37, 58),        # koyu lacivert kontur
    "goz_beyaz": (255, 255, 255),
    "gozbebek": (35, 37, 58),
    "yanak": (255, 120, 120),
    "agiz_ic": (150, 30, 50),
    "dil": (255, 110, 120),
    "perçem": (35, 37, 58),
    "ayakkabi": (230, 57, 70),    # imza kirmizi ayakkabilar
}
KONTUR = 9  # olcek 1.0'da cizgi kalinligi (px)

IFADELER = ["normal", "mutlu", "saskin", "kizgin", "uzgun", "sinsi", "utangac"]
KOL_POZLARI = ["serbest", "el_salla", "isaret", "kollar_havada", "bel", "yuz_avuc"]


def _bezier(p0, p1, p2, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _kalin_cizgi(d, pts, w, renk):
    d.line(pts, fill=renk, width=int(w), joint="curve")
    r = w / 2
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=renk)


def _kol(d, omuz, el, s, renk_cizgi, dirsek_bukum=0.0, el_ac=False):
    mx, my = (omuz[0] + el[0]) / 2, (omuz[1] + el[1]) / 2
    dx, dy = el[0] - omuz[0], el[1] - omuz[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    kontrol = (mx + nx * dirsek_bukum * s, my + ny * dirsek_bukum * s)
    pts = _bezier(omuz, kontrol, el)
    _kalin_cizgi(d, pts, 22 * s, renk_cizgi)
    _kalin_cizgi(d, pts, 11 * s, RENK["govde"])
    r = 19 * s
    d.ellipse([el[0] - r, el[1] - r, el[0] + r, el[1] + r],
              fill=RENK["govde"], outline=renk_cizgi, width=int(KONTUR * s * 0.8))


def ciz_bidik(img, x, y, olcek=1.0, ifade="normal", agiz=0.0, kirp=0.0,
              bakis=(0.0, 0.0), kol="serbest", ziplama=0.0, egilme=0.0,
              kol_faz=0.0):
    """
    x, y     : ayaklarin orta noktasi (yere bastigi yer)
    agiz     : 0 kapali ... 1 tamamen acik (konusma icin)
    kirp     : 0 acik goz ... 1 kapali goz (goz kirpma)
    bakis    : (-1..1, -1..1) gozbebeklerinin yonu
    kol      : KOL_POZLARI'ndan biri
    ziplama  : govdenin yukari kalkmasi (px, olcek 1'de)
    egilme   : -1..1 govde sag/sol egilmesi
    kol_faz  : el sallama gibi hareketler icin 0..1 dongu fazi
    """
    s = olcek
    d = ImageDraw.Draw(img)
    c = RENK["cizgi"]
    w = int(KONTUR * s)

    # --- ayaklar (yerde sabit) -------------------------------------------------
    for yon in (-1, 1):
        ax = x + yon * 55 * s
        bacak_ust = (ax + egilme * 10 * s, y - 70 * s - ziplama * s)
        bacak_alt = (ax, y - 18 * s)
        _kalin_cizgi(d, [bacak_ust, bacak_alt], 22 * s, c)
        _kalin_cizgi(d, [bacak_ust, bacak_alt], 11 * s, RENK["govde"])
        d.rounded_rectangle([ax - 34 * s + yon * 10 * s, y - 34 * s,
                             ax + 34 * s + yon * 10 * s, y],
                            radius=int(17 * s), fill=RENK["ayakkabi"],
                            outline=c, width=w)

    # --- govde: armut/yumurta formu -------------------------------------------
    gx = x + egilme * 25 * s
    gy = y - 255 * s - ziplama * s          # govde merkezi
    rx, ry = 150 * s, 180 * s
    govde_bbox = [gx - rx, gy - ry, gx + rx, gy + ry]
    d.ellipse(govde_bbox, fill=RENK["govde"], outline=c, width=w)
    # karin golgesi
    d.chord([gx - rx * 0.78, gy + ry * 0.15, gx + rx * 0.78, gy + ry * 0.92],
            start=10, end=170, fill=RENK["govde_golge"])
    d.ellipse(govde_bbox, outline=c, width=w)

    # --- imza percem (kafadaki kivrik tutam) ----------------------------------
    tepe = (gx, gy - ry + 4 * s)
    p1 = _bezier(tepe, (gx + 10 * s, tepe[1] - 80 * s), (gx + 60 * s, tepe[1] - 60 * s))
    p2 = _bezier(p1[-1], (gx + 85 * s, tepe[1] - 40 * s), (gx + 55 * s, tepe[1] - 25 * s), 12)
    _kalin_cizgi(d, p1 + p2[1:], 13 * s, RENK["perçem"])

    # --- kollar ----------------------------------------------------------------
    omuz_sol = (gx - rx * 0.92, gy + 10 * s)
    omuz_sag = (gx + rx * 0.92, gy + 10 * s)
    sal = math.sin(kol_faz * 2 * math.pi)
    if kol == "serbest":
        _kol(d, omuz_sol, (gx - rx - 40 * s, gy + 120 * s + sal * 6 * s), s, c, -25)
        _kol(d, omuz_sag, (gx + rx + 40 * s, gy + 120 * s - sal * 6 * s), s, c, 25)
    elif kol == "el_salla":
        _kol(d, omuz_sol, (gx - rx - 40 * s, gy + 120 * s), s, c, -25)
        _kol(d, omuz_sag, (gx + rx + 70 * s + sal * 30 * s, gy - 120 * s), s, c, -40)
    elif kol == "isaret":
        _kol(d, omuz_sol, (gx - rx - 40 * s, gy + 120 * s), s, c, -25)
        el = (gx + rx + 140 * s, gy - 20 * s + sal * 5 * s)
        _kol(d, omuz_sag, el, s, c, 0)
        _kalin_cizgi(d, [el, (el[0] + 38 * s, el[1] - 6 * s)], 15 * s, c)
        _kalin_cizgi(d, [el, (el[0] + 36 * s, el[1] - 6 * s)], 6 * s, RENK["govde"])
    elif kol == "kollar_havada":
        _kol(d, omuz_sol, (gx - rx - 70 * s - sal * 15 * s, gy - 170 * s), s, c, 35)
        _kol(d, omuz_sag, (gx + rx + 70 * s + sal * 15 * s, gy - 170 * s), s, c, -35)
    elif kol == "bel":
        _kol(d, omuz_sol, (gx - rx + 10 * s, gy + 95 * s), s, c, 70)
        _kol(d, omuz_sag, (gx + rx - 10 * s, gy + 95 * s), s, c, -70)
    elif kol == "yuz_avuc":
        _kol(d, omuz_sol, (gx - rx - 40 * s, gy + 120 * s), s, c, -25)

    # --- yuz -------------------------------------------------------------------
    yx, yy = gx + bakis[0] * 8 * s, gy - 55 * s + bakis[1] * 5 * s
    goz_ara = 58 * s
    gw, gh = 36 * s, 46 * s
    if ifade == "saskin":
        gw, gh = 42 * s, 56 * s
    kirp_eff = kirp
    if ifade == "mutlu":
        kirp_eff = max(kirp, 0.0)

    for yon in (-1, 1):
        ex = yx + yon * goz_ara
        if ifade == "mutlu" and kirp < 0.5:
            # mutlu: ters U goz (^^)
            pts = _bezier((ex - gw, yy + 8 * s), (ex, yy - 45 * s), (ex + gw, yy + 8 * s))
            _kalin_cizgi(d, pts, 11 * s, c)
            continue
        acik = gh * (1 - kirp_eff)
        if ifade == "sinsi":
            acik *= 0.45
        if acik < 5 * s:
            pts = _bezier((ex - gw, yy), (ex, yy + 12 * s), (ex + gw, yy))
            _kalin_cizgi(d, pts, 10 * s, c)
            continue
        ust = yy - acik
        alt = yy + gh if ifade != "sinsi" else yy + acik
        d.ellipse([ex - gw, ust, ex + gw, alt], fill=RENK["goz_beyaz"], outline=c, width=int(7 * s))
        pr = 15 * s if ifade != "saskin" else 11 * s
        px = ex + bakis[0] * 12 * s
        py = (ust + alt) / 2 + bakis[1] * 10 * s
        py = min(max(py, ust + pr), alt - pr)
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=RENK["gozbebek"])
        d.ellipse([px - pr * 0.2, py - pr * 0.75, px + pr * 0.35, py - pr * 0.2], fill=(255, 255, 255))

    # kaslar
    kas_y = yy - gh - 22 * s
    for yon in (-1, 1):
        ex = yx + yon * goz_ara
        ic, dis = ex - yon * 28 * s, ex + yon * 28 * s
        if ifade == "kizgin":
            p = [(dis, kas_y - 14 * s), (ic, kas_y + 14 * s)]
        elif ifade in ("uzgun", "utangac"):
            p = [(dis, kas_y + 10 * s), (ic, kas_y - 12 * s)]
        elif ifade == "saskin":
            p = _bezier((dis, kas_y - 10 * s), (ex, kas_y - 34 * s), (ic, kas_y - 10 * s))
        elif ifade == "sinsi":
            p = [(dis, kas_y + (8 if yon < 0 else -14) * s), (ic, kas_y + (4 if yon < 0 else 0) * s)]
            p = [(p[0][0], p[0][1] + gh * 0.5), (p[1][0], p[1][1] + gh * 0.5)]
        else:
            p = _bezier((dis, kas_y), (ex, kas_y - 12 * s), (ic, kas_y))
        _kalin_cizgi(d, p, 10 * s, c)

    # yanaklar
    if ifade in ("mutlu", "utangac", "normal"):
        alfa = 1.0 if ifade == "utangac" else 0.6
        for yon in (-1, 1):
            cx, cy = yx + yon * 100 * s, yy + 50 * s
            r = 22 * s
            renk = tuple(int(RENK["govde"][i] * (1 - alfa) + RENK["yanak"][i] * alfa) for i in range(3))
            d.ellipse([cx - r * 1.3, cy - r * 0.8, cx + r * 1.3, cy + r * 0.8], fill=renk)

    # agiz
    mx, my = yx, yy + 75 * s
    acik = max(0.0, min(1.0, agiz))
    genis = 46 * s
    if ifade in ("uzgun",):
        egri = -22 * s
    elif ifade == "kizgin":
        egri = -10 * s
    elif ifade == "saskin":
        egri = 0
        genis = 26 * s
        acik = max(acik, 0.55)
    elif ifade == "sinsi":
        egri = 18 * s
    elif ifade == "utangac":
        egri = 8 * s
        genis = 24 * s
    elif ifade == "mutlu":
        egri = 30 * s
        acik = max(acik, 0.35)
    else:
        egri = 16 * s

    if acik < 0.08:
        if ifade == "sinsi":
            pts = _bezier((mx - genis, my), (mx + 5 * s, my + egri), (mx + genis, my - 18 * s))
        else:
            pts = _bezier((mx - genis, my - egri * 0.4), (mx, my + egri), (mx + genis, my - egri * 0.4))
        _kalin_cizgi(d, pts, 10 * s, c)
    else:
        h = 70 * s * acik
        if ifade == "saskin":
            d.ellipse([mx - genis, my - h * 0.5, mx + genis, my + h * 0.7],
                      fill=RENK["agiz_ic"], outline=c, width=int(8 * s))
        else:
            ust_egri = egri * 0.4
            ust = _bezier((mx - genis, my - ust_egri), (mx, my + egri * 0.3 - 4 * s), (mx + genis, my - ust_egri))
            alt = _bezier((mx + genis, my - ust_egri), (mx, my + egri * 0.3 + h * 1.6), (mx - genis, my - ust_egri))
            poly = ust + alt[1:]
            # agiz ici + dil, agiz sekline kirpilarak
            maske = Image.new("L", img.size, 0)
            ImageDraw.Draw(maske).polygon(poly, fill=255)
            katman = Image.new("RGB", img.size, RENK["agiz_ic"])
            dil_y = my + egri * 0.3 + h * 0.75
            ImageDraw.Draw(katman).ellipse([mx - genis * 0.6, dil_y, mx + genis * 0.6, dil_y + h * 1.2],
                                            fill=RENK["dil"])
            img.paste(katman, (0, 0), maske)
            _kalin_cizgi(d, poly + [poly[0]], 8 * s, c)

    # yuz avuc: el yuzu kapatir (en ustte cizilir)
    if kol == "yuz_avuc":
        el = (yx + 5 * s, yy - 20 * s)
        _kol(d, omuz_sag, el, s, c, 70)
        d.ellipse([el[0] - 75 * s, el[1] - 34 * s, el[0] + 75 * s, el[1] + 34 * s],
                  fill=RENK["govde"], outline=c, width=int(KONTUR * s * 0.8))
        for i in (-1, 0, 1):
            fx = el[0] + i * 34 * s
            _kalin_cizgi(d, [(fx, el[1] - 22 * s), (fx, el[1] + 10 * s)], 5 * s, c)

    # utangac/sinsi ter damlasi yok; saskin icin ter damlasi
    if ifade == "saskin":
        tx, ty = gx + rx * 0.72, gy - ry * 0.55
        d.polygon([(tx, ty - 26 * s), (tx - 14 * s, ty + 4 * s), (tx + 14 * s, ty + 4 * s)],
                  fill=(120, 200, 255), outline=c)
        d.ellipse([tx - 14 * s, ty - 10 * s, tx + 14 * s, ty + 16 * s],
                  fill=(120, 200, 255), outline=c, width=int(5 * s))


def kare(genislik=1080, yukseklik=1920, arka=(250, 244, 230), ss=2, **params):
    """Tek bir kare uretir (ss: kenar yumusatma icin superornekleme)."""
    img = Image.new("RGB", (genislik * ss, yukseklik * ss), arka)
    p = dict(params)
    p["x"] = p.get("x", genislik / 2) * ss
    p["y"] = p.get("y", yukseklik * 0.78) * ss
    p["olcek"] = p.get("olcek", 1.6) * ss
    p["ziplama"] = p.get("ziplama", 0.0)
    ciz_bidik(img, **p)
    return img.resize((genislik, yukseklik), Image.LANCZOS)
