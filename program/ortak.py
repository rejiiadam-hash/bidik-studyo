"""Ortak yollar ve araclar. Tum veriler BIDIK klasorunun kendisinde durur."""
import os, shutil, json

PROGRAM = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(PROGRAM)                      # .../Desktop/BIDIK
AYAR = os.path.join(KOK, "ayarlar.json")
HAFIZA = os.path.join(KOK, "hafiza.json")
SENARYO = os.path.join(KOK, "senaryolar")           # bekleyen / onaylanan / reddedilen
VIDEO = os.path.join(KOK, "videolar")               # <tarih>/<ad>.mp4 + _yayin.txt
FONT = os.path.join(PROGRAM, "font", "DejaVuSans-Bold.ttf")

VARSAYILAN_AYAR = {
    "gemini_api_key": "",
    "gemini_sohbet_anahtari": "",   # Bidik sohbeti icin AYRI anahtar (baska Google hesabi); senaryolari etkilemez
    "gunluk_video": 3,
    "aday_sayisi": 9,
    "model": "",
    "alanlar": ["hayvanlar", "bilim", "uzay", "insan vucudu", "tarih", "psikoloji",
                "yemek ve mutfak bilimi", "teknoloji", "dunya cografyasi",
                "burclar ve gokyuzu", "cocuklarin neden sorulari"],
    "uslup": "Aile dostu, kufursuz, kimseyi asagilamayan; zeki ve absurt mizah.",
    "youtube_gizlilik": "private",
    "son_cagri": True,   # videonun son 2 sn'sinde Begen + Abone ol animasyonu
    "tema": "koyu",
    "imza_acik": True,               # acilista seri etiketi + kapanista yorum sorusu / yarin vaadi
    "seri_adi": "BIDIK BİLİR Mİ?",
    "paylasim_saatleri": ["11:00", "15:00", "19:00"],
    "youtube_kanal": "",
    "github_depo": "rejiiadam-hash/bidik-studyo",     # "kullanici/depo": bos ise GitHub guncelleme kanali kapali
    "github_dal": "main",
}


def ayarlar():
    veri = {}
    if os.path.exists(AYAR):
        with open(AYAR, encoding="utf-8") as f:
            veri = json.load(f)
    return {**VARSAYILAN_AYAR, **veri}


def ayar_kaydet(yeni):
    a = ayarlar()
    a.update(yeni)
    with open(AYAR, "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=2)
    return a


KANAL_SATIRI = "Bıdık her gün yeni bir ilginç bilgiyle burada. Kaçırmamak için abone ol! 💛"


def _etiket_temizle(e):
    import re
    e = re.sub(r"[^\w\s'-]", "", str(e).replace("#", ""), flags=re.UNICODE).strip().lower()
    return re.sub(r"\s+", " ", e)


def hashtagler(s):
    """Aciklamanin sonuna eklenecek 3 hashtag (ilk 3'u basligin ustunde gorunur)."""
    import re
    ham = s.get("hashtagler") or [f"#{e}" for e in (s.get("etiketler") or [])[:2]] + ["#ilginçbilgiler"]
    sonuc = []
    for h in ham:
        h = "#" + re.sub(r"[^\w]", "", str(h).replace("#", ""), flags=re.UNICODE).lower()
        if len(h) > 2 and h not in sonuc:
            sonuc.append(h)
    if "#bıdık" not in sonuc and len(sonuc) < 4:
        sonuc.append("#bıdık")
    return sonuc[:4]


def aciklama_tam(s):
    """YouTube aciklamasi: metin + kanal satiri + hashtag'ler."""
    govde = (s.get("aciklama") or "").strip()
    if "#" in govde:   # zaten tam aciklama (kullanici duzenlemis)
        return govde
    return f"{govde}\n\n{KANAL_SATIRI}\n\n{' '.join(hashtagler(s))}".strip()


def etiket_listesi(s):
    """YouTube etiket alani: tekrarsiz, toplam 480 karakteri gecmez."""
    sonuc, toplam = [], 0
    for e in list(s.get("etiketler") or []) + [s.get("konu", ""), "ilginç bilgiler", "bıdık", "komik animasyon"]:
        e = _etiket_temizle(e)[:30]
        if not e or e in sonuc:
            continue
        if toplam + len(e) + 2 > 480:
            break
        sonuc.append(e)
        toplam += len(e) + 2
    return sonuc[:15]


# Windows'ta yardimci programlar (ffmpeg, pip) siyah konsol penceresi acmasin
PENCERESIZ = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW


def komut(args):
    """Bir komutu pencere acmadan calistirir; hata olursa anlasilir mesaj verir."""
    import subprocess
    sonuc = subprocess.run(args, capture_output=True, text=True, creationflags=PENCERESIZ)
    if sonuc.returncode != 0:
        raise RuntimeError(f"{os.path.basename(args[0])} hatasi: {(sonuc.stderr or '').strip()[-400:]}")
    return sonuc


def ffmpeg():
    """Bilgisayarda ffmpeg yoksa pip ile gelen imageio-ffmpeg kullanilir."""
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("ffmpeg bulunamadi. BASLAT.bat'i tekrar calistir (gerekenleri kurar).")


# --- uretimi durdurma ------------------------------------------------------------------------
import threading as _threading
IPTAL = _threading.Event()


class Iptal(BaseException):   # BaseException: genel "except Exception" bloklari durdurmayi yutmasin
    """Kullanici 'Durdur'a basti."""


def iptal_kontrol():
    if IPTAL.is_set():
        raise Iptal("Durduruldu")


def uyu(sn):
    """Durdur'a basilirsa hemen uyanan bekleme."""
    import time
    son = time.time() + sn
    while time.time() < son:
        iptal_kontrol()
        time.sleep(min(0.5, max(0.0, son - time.time())))
    iptal_kontrol()
