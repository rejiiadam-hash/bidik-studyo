"""
Ana sayfadaki "Bidik ile sohbet". Senaryo motorundan TAMAMEN AYRI bir Gemini anahtari kullanir
(ayarlar.json -> gemini_sohbet_anahtari; baska bir Google hesabindan alinir), boylece sohbet
senaryo yazma kotasini hic etkilemez. Anahtar yoksa ana anahtara DUSMEZ.
"""
import json, re, threading, urllib.error, urllib.request

from ortak import ayarlar, ayar_kaydet

API = "https://generativelanguage.googleapis.com/v1beta"
KILIT = threading.Lock()

KISILIK = (
    "Sen Bidik'sin: bir YouTube Shorts kanalinin neseli, merakli, cocuksu, sevimli sari yumurta karakterisin. "
    "Karsindaki kisi kanalin sahibi Deniz; ona 'Deniz' diye hitap et, samimi ve sicak ol. "
    "Turkce konus. Cevaplarin KISA olsun (en fazla 2-3 cumle), eglenceli ve naif; ara sira bir emoji kullanabilirsin. "
    "Markdown, liste, baslik KULLANMA, duz konusma dili kullan. "
    "Bilmedigin bir seyi uydurma: 'Bunu bilmiyorum ama ogrenmek isterim' de. "
    "Kufur, siyaset, yetiskin icerik yok; aile dostu kal. Hep Bidik karakterinde kal."
)


class SohbetHatasi(Exception):
    pass


def _istek(url, anahtar, veri=None):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "key=" + anahtar,
                                 data=json.dumps(veri).encode() if veri else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        govde = e.read().decode(errors="ignore")[:300]
        if e.code in (400, 401, 403) and ("API key" in govde or "API_KEY" in govde or e.code in (401, 403)):
            raise SohbetHatasi("anahtar", "Sohbet anahtari gecersiz gorunuyor. Ayarlar'dan yenisini gir.")
        if e.code == 429:
            raise SohbetHatasi("limit", "Bidik biraz yoruldu (Gemini limiti doldu). Biraz sonra tekrar dene.")
        raise SohbetHatasi("gecici", f"Gemini {e.code}")
    except TimeoutError:
        raise SohbetHatasi("gecici", "Gemini cevap vermedi")
    except urllib.error.URLError as e:
        raise SohbetHatasi("net", "Internete baglanilamadi")


def _modeller(anahtar):
    liste = _istek(f"{API}/models?pageSize=200", anahtar).get("models", [])
    uygun = [m["name"].split("/")[-1] for m in liste
             if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
             and not any(x in m["name"] for x in ("tts", "image", "live", "audio", "thinking"))]
    anah = lambda n: (("preview" in n) or ("exp" in n), "lite" not in n, [-int(x) for x in re.findall(r"\d+", n)])
    return sorted(uygun, key=anah)[:5]


def cevapla(mesaj, gecmis=None):
    anahtar = (ayarlar().get("gemini_sohbet_anahtari") or "").strip()
    if not anahtar:
        raise SohbetHatasi("yok", "Sohbet icin ayri bir Gemini anahtari gerekli (Ayarlar > Bidik sohbet anahtari).")
    mesaj = (mesaj or "").strip()[:600]
    if not mesaj:
        raise SohbetHatasi("bos", "Bir sey yaz :)")
    icerik = []
    for g in (gecmis or [])[-12:]:
        metin = str(g.get("metin", ""))[:600]
        if metin:
            icerik.append({"role": "model" if g.get("rol") == "bidik" else "user", "parts": [{"text": metin}]})
    icerik.append({"role": "user", "parts": [{"text": mesaj}]})
    govde = {"systemInstruction": {"parts": [{"text": KISILIK}]}, "contents": icerik,
             "generationConfig": {"temperature": 1.0, "maxOutputTokens": 1024}}
    with KILIT:
        a = ayarlar()
        modeller = [a["sohbet_model"]] if a.get("sohbet_model") else []
        son = None
        for tur in range(2):
            if tur == 1 or not modeller:
                modeller = _modeller(anahtar)
            for m in modeller:
                try:
                    c = _istek(f"{API}/models/{m}:generateContent", anahtar, govde)
                    parcalar = (c.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
                    metin = "".join(p.get("text", "") for p in parcalar if not p.get("thought")).strip()
                    if metin:
                        if a.get("sohbet_model") != m:
                            ayar_kaydet({"sohbet_model": m})
                        return metin
                    son = SohbetHatasi("bos", "Bidik bir sey diyemedi, tekrar dene.")
                except SohbetHatasi as e:
                    if e.args[0] in ("anahtar", "limit", "net"):
                        raise
                    son = e
        raise son or SohbetHatasi("gecici", "Bidik su an cevap veremiyor.")
