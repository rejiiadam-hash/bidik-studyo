"""Kanal kimlik paketi: profil resmi, banner ve aciklama metni (BIDIK/kimlik klasorune)."""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "program"))
from PIL import Image, ImageDraw, ImageFont
from karakter import ciz_bidik
from ortak import FONT, KOK

SS = 2
LACI = (35, 37, 58)
SARI = (255, 205, 40)


def _font(px):
    return ImageFont.truetype(FONT, int(px * SS))


def _zemin(w, h, ust, alt):
    img = Image.new("RGB", (w * SS, h * SS))
    d = ImageDraw.Draw(img)
    for y in range(h * SS):
        t = y / (h * SS)
        d.line([(0, y), (w * SS, y)], fill=tuple(int(ust[i] + (alt[i] - ust[i]) * t) for i in range(3)))
    return img, d


def _isiltilar(d, w, h, adet, rnd):
    for _ in range(adet):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(6, 22)
        d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=(255, 255, 255))


def profil(yol):
    import random
    img, d = _zemin(800, 800, (255, 236, 160), (255, 196, 90))
    _isiltilar(d, 800, 800, 14, random.Random(5))
    ciz_bidik(img, x=400 * SS, y=745 * SS, olcek=1.15 * SS, ifade="mutlu", agiz=0.2)
    img.resize((800, 800), Image.LANCZOS).save(yol)


def banner(yol):
    import random
    W, H = 2560, 1440
    img, d = _zemin(W, H, (255, 236, 160), (255, 190, 80))
    _isiltilar(d, W, H, 60, random.Random(9))
    # guvenli alan (tum cihazlarda gorunen): 1546x423, ortada
    cx, cy = W // 2, H // 2
    ciz_bidik(img, x=(cx - 585) * SS, y=(cy + 205) * SS, olcek=0.85 * SS, ifade="mutlu", agiz=0.3, kol="el_salla", kol_faz=0.2)
    d = ImageDraw.Draw(img)
    f1, f2 = _font(122), _font(50)
    d.text(((cx + 175) * SS, (cy - 45) * SS), "BIDIK BİLİR Mİ?", font=f1, fill=LACI, anchor="mm")
    d.text(((cx + 175) * SS, (cy + 80) * SS), "Her gün yeni bir bilgi, 20 saniyede!", font=f2, fill=(120, 60, 20), anchor="mm")
    img.resize((W, H), Image.LANCZOS).save(yol)


ACIKLAMA = """Merhaba, ben Bıdık! 🥚
Her gün birkaç saniyede aklına takılan şeyleri öğreniyoruz: hayvanlar, uzay, tarih, bilim ve daha fazlası.

Hangi konuyu anlatacağımı tahmin edebilir misin? Yorumlara yaz, yarın yenisi geliyor!
Beğen, abone ol, Bıdık'la her gün bir şey öğren. 💛

Bıdık Bilir mi? · Günde 3 yeni Shorts
"""


if __name__ == "__main__":
    kl = os.path.join(KOK, "kimlik")
    os.makedirs(kl, exist_ok=True)
    profil(os.path.join(kl, "bidik_profil_800.png"))
    banner(os.path.join(kl, "bidik_banner_2560x1440.png"))
    with open(os.path.join(kl, "KANAL_ACIKLAMASI.txt"), "w", encoding="utf-8") as f:
        f.write(ACIKLAMA)
    print("Hazir:", kl)
