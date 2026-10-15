"""
Yedek ses motoru (DENEME): Piper - internetsiz calisan Turkce erkek sesi (tr_TR-dfki-medium).

Simdilik sadece ORNEK uretir: Deniz Ahmet (Bidik'in normal sesi) ile Piper'i karsilastirip
karar verecek. Begenirse video uretiminde yedek olarak baglanacak.

Ilk kullanimda: piper-tts paketi pip ile kurulur, ses modeli (~60 MB) Hugging Face'ten
BIDIK\\sesler\\piper\\ klasorune indirilir. Sonrasi tamamen internetsiz.
"""
import os, subprocess, sys, urllib.request, wave

from ortak import KOK, PENCERESIZ, ffmpeg, komut

PIPER_DIR = os.path.join(KOK, "sesler", "piper")
ORNEK_DIR = os.path.join(KOK, "sesler", "ornek")
MODEL = "tr_TR-dfki-medium"
MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/"
ORNEK_METIN = "Merhaba! Ben Bıdık. Bugün sana çok ilginç bir bilgi anlatacağım, hazır mısın?"
# Bidik'e benzetme: sesi incelt (+%18), hizi koru
BIDIK_FILTRE = "asetrate=22050*1.18,aresample=24000,atempo=0.92"
_SES = {}


def _python():
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):
        py = py[:-len("pythonw.exe")] + "python.exe"
    return py


def _paket_hazirla(ilerle):
    try:
        import piper  # noqa: F401
        return
    except ImportError:
        pass
    ilerle(10, "Piper kuruluyor (bir kerelik, internet gerekir)")
    s = subprocess.run([_python(), "-m", "pip", "install", "-q", "piper-tts"],
                       capture_output=True, text=True, creationflags=PENCERESIZ)
    if s.returncode != 0:
        raise RuntimeError("Piper kurulamadi (bu Python surumu desteklenmiyor olabilir): "
                           + (s.stderr or s.stdout or "")[-300:])
    import importlib
    importlib.invalidate_caches()


def _model_hazirla(ilerle):
    os.makedirs(PIPER_DIR, exist_ok=True)
    for uzanti in (".onnx.json", ".onnx"):
        hedef = os.path.join(PIPER_DIR, MODEL + uzanti)
        if os.path.exists(hedef) and os.path.getsize(hedef) > 1000:
            continue
        ilerle(30, f"Ses modeli indiriliyor ({MODEL}{uzanti}, bir kerelik)")
        gecici = hedef + ".indiriliyor"
        req = urllib.request.Request(MODEL_URL + MODEL + uzanti + "?download=true",
                                     headers={"User-Agent": "BidikStudyo"})
        with urllib.request.urlopen(req, timeout=120) as r, open(gecici, "wb") as f:
            while True:
                parca = r.read(1 << 16)
                if not parca:
                    break
                f.write(parca)
        os.replace(gecici, hedef)


def _ses():
    if "v" not in _SES:
        from piper import PiperVoice
        _SES["v"] = PiperVoice.load(os.path.join(PIPER_DIR, MODEL + ".onnx"))
    return _SES["v"]


def piper_wav(metin, wav, bidik=True):
    """Metni Piper ile seslendirir; bidik=True ise Bidik tonuna yaklastirir."""
    ham = wav + ".ham.wav"
    with wave.open(ham, "wb") as f:
        try:
            from piper import SynthesisConfig
            _ses().synthesize_wav(metin, f, syn_config=SynthesisConfig(length_scale=0.95))
        except ImportError:   # eski piper surumu
            _ses().synthesize(metin, f)
    with wave.open(ham) as f:
        sr = f.getframerate()
    filtre = (BIDIK_FILTRE.replace("22050", str(sr)) + "," if bidik else "") + "loudnorm=I=-16:TP=-1.5"
    komut([ffmpeg(), "-y", "-loglevel", "error", "-i", ham, "-af", filtre, "-ac", "1", "-ar", "24000", wav])
    os.remove(ham)


def ornek_uret(ilerle):
    os.makedirs(ORNEK_DIR, exist_ok=True)
    notlar = []
    ilerle(5, "Ahmet (Bidik'in normal sesi) ile ornek")
    try:
        from video_uret import seslendir
        seslendir(ORNEK_METIN, os.path.join(ORNEK_DIR, "1_ahmet.wav"))
    except Exception as e:
        notlar.append("Ahmet sesi su an cevap vermedi (karsilastirma icin sonra tekrar dene)")
        print("ornek ahmet:", e)
    _paket_hazirla(ilerle)
    _model_hazirla(ilerle)
    ilerle(80, "Piper ornekleri uretiliyor")
    piper_wav(ORNEK_METIN, os.path.join(ORNEK_DIR, "2_piper_bidik.wav"), bidik=True)
    piper_wav(ORNEK_METIN, os.path.join(ORNEK_DIR, "3_piper_dogal.wav"), bidik=False)
    ilerle(100, "Hazir")
    return "Ses ornekleri hazir: Ayarlar > Yedek ses bolumunden dinle." + (" " + notlar[0] if notlar else "")


def ornekler():
    if not os.path.isdir(ORNEK_DIR):
        return []
    return sorted(f for f in os.listdir(ORNEK_DIR) if f.endswith(".wav"))
