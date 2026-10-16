"""
Bidik Hikayeleri motoru: Gemini ile 2-3 dakikalik bolum yazar, yazim + bilgi denetiminden gecirir,
BIDIK\\hikayeler\\<id>\\bolum.json olarak kaydeder. Video: hikaye_uret.uret().
Senaryo motorunun Gemini baglantisini (ana anahtar) kullanir; haftada bir bolum oldugu icin kota yuku kucuktur.
"""
import datetime, hashlib, json, os, re, time

import arka_planlar
from hikaye_uret import dogrula
from kostumler import KOSTUMLER
from ortak import KOK, ayarlar
from senaryo_motoru import MotorHatasi, gemini_json, model_sec

KLASOR = os.path.join(KOK, "hikayeler")
IFADE_BIDIK = ["normal", "mutlu", "saskin", "kizgin", "uzgun", "sinsi", "utangac"]
IFADE_BILGE = ["normal", "mutlu", "saskin", "dusunceli"]
KOLLAR = ["serbest", "el_salla", "isaret", "kollar_havada", "bel", "yuz_avuc"]


def liste():
    os.makedirs(KLASOR, exist_ok=True)
    sonuc = []
    for ad in sorted(os.listdir(KLASOR), reverse=True):
        yol = os.path.join(KLASOR, ad, "bolum.json")
        try:
            with open(yol, encoding="utf-8") as f:
                b = json.load(f)
        except (OSError, ValueError):
            continue
        b["id"] = ad
        sonuc.append(b)
    return sonuc


def kaydet(b):
    klasor = os.path.join(KLASOR, b["id"])
    os.makedirs(klasor, exist_ok=True)
    veri = {k: v for k, v in b.items() if k != "id"}
    gecici = os.path.join(klasor, "bolum.json.yaziliyor")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, os.path.join(klasor, "bolum.json"))


def _slug(metin):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜâÂ", "cgiosuCGIOSUaA")
    s = re.sub(r"[^a-z0-9]+", "-", (metin or "").translate(tr).lower()).strip("-")
    return s[:40] or "bolum"


# --- metinler ve imza (denetimden sonra degisirse yeniden denetlenir) -----------------------
def metinler(b):
    m = [b.get("baslik", ""), b.get("aciklama", "")]
    for bo in b.get("bolumler", []):
        m.append(bo.get("ad", ""))
        for s in bo.get("satirlar", []):
            m.append(s.get("metin", ""))
            k = s.get("kart") or {}
            m += [str(k.get("buyuk", "")), str(k.get("alt", ""))]
    q = b.get("soru") or {}
    m += [q.get("metin", "")] + list(q.get("secenekler") or [])
    m += list(b.get("ozet") or [])
    return m


def imza(b):
    return hashlib.sha1(json.dumps(metinler(b), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def denetim_gecerli(b):
    return (b.get("denetim") or {}).get("imza") == imza(b)


# --- istemler ------------------------------------------------------------------------------
def yazar_istemi(konu, alan, onceki):
    temalar = ", ".join(arka_planlar.TEMALAR)
    sahneler = "\n".join(f"    {t}: " + ", ".join(f"{i}={ad}" for i, ad in enumerate(adlar))
                         for t, adlar in arka_planlar.SAHNE_ADLARI.items() if t != "genel")
    return f"""Sen Turkce cocuk ve aile egitim cizgi filmi yazarisin. Dizinin adi "BIDIK HIKAYELERI".
Karakterler:
- BIDIK: sari, yumurta seklinde, merakli, biraz sakar, komik ve sevimli. Sorular sorar, yanlis tahminler yapar, saskinlikla ogrenir.
- BILGE: gozluklu, sakin ve sevecen bir baykus. Konuyu basit, dogru ve hikayelestirerek anlatir.

GOREV: "{konu}" konusunda ({alan} alani) 2-3 dakikalik bir bolum yaz. Izleyici kisa bir cizgi film izler gibi eglenirken
konuyu gercekten ogrenmeli. Bolum bir YOLCULUK/OLAY uzerinden ilerlesin (or. Bidik bir seyi merak eder, Bilge onu
konunun gectigi yerlere goturur, olaylar adim adim anlatilir).

KURALLAR
- 4 veya 5 bolum (kisim). Her kismin kisa bir adi ve konusuna uyan bir arka plan temasi olsun. Temalar: {temalar}.
  "arka_no": temanin sahnesi (0-4), ICERIGE UYGUN olani sec (kopek anlatilirken deniz alti SECME):
{sahneler}
- Her kisimda 5-7 satir; toplam 24-32 satir. Her satir en fazla 140 karakter, gunluk konusma dili, dogal diyalog.
- Ilk satirlar merak uyandiran bir sorun/soru ile baslasin. Bidik espri yapsin ama bilgi her zaman one ciksin.
- BILGI KESINLIKLE DOGRU OLMALI. Supheli, tartismali, efsane bilgileri KULLANMA. Sayilar dogru ve yuvarlanmis olsun.
- "kart": en onemli 3-5 bilgi icin (sayi ya da kisa kavram). "buyuk" en fazla 12 karakter, "alt" en fazla 26 karakter,
  EMOJI KULLANMA. "renk": mavi, kirmizi, yesil, mor, turuncu, pembe.
- Her kismin "tema"si Bidik'in kiyafetini ve Bilge'nin aksesuarini da belirler (uzay: astronot, tarih: migfer, yemek: asci...).
  Hikaye bir yerden baska yere gidiyorsa temayi ona gore sec; ayni yerde kalan kisimlarda ayni temayi kullan ki kiyafet
  gereksiz yere degismesin. Istersen kisma "kostum" da yazabilirsin: {list(KOSTUMLER)}.
- "ifade": bidik icin {IFADE_BIDIK}, bilge icin {IFADE_BILGE}. "kol" (sadece bidik): {KOLLAR}.
- Sonunda "soru": konuyla ilgili 3 secenekli bir soru (tek dogru cevap, "dogru": 0-2).
- "ozet": ogrenilen 3 ana bilgi, her biri en fazla 60 karakter.
- Daha once islenen hikaye konulari (TEKRARLAMA): {", ".join(onceki) or "yok"}

YAYIN METINLERI
- "baslik": merak uyandiran, konunun anahtar kelimesini iceren, en fazla 70 karakter, en fazla 1 emoji.
- "aciklama": 2-3 cumle; bolumde ne ogrenilecegi + izleyiciye bir soru. Hashtag YAZMA.
- "hashtagler": TAM 3 hashtag (#konu, #kategori, #bidikhikayeleri).
- "etiketler": 10-12 arama ifadesi, kucuk harf, # yok.

CIKTI yalnizca su JSON:
{{"baslik": "...", "alan": "{alan}", "konu": "{konu}", "aciklama": "...", "hashtagler": ["#...", "#...", "#bidikhikayeleri"],
  "etiketler": ["..."], "dogrulama_notu": "bilgilerin dayanagi, 1-2 cumle",
  "bolumler": [{{"ad": "...", "tema": "...", "arka_no": 0,
     "satirlar": [{{"kim": "bidik", "metin": "...", "ifade": "saskin", "kol": "kollar_havada"}},
                  {{"kim": "bilge", "metin": "...", "ifade": "normal", "kart": {{"buyuk": "...", "alt": "...", "renk": "mavi"}}}}]}}],
  "soru": {{"metin": "...", "secenekler": ["...", "...", "..."], "dogru": 1}},
  "ozet": ["...", "...", "..."]}}"""


def konu_istemi(alanlar, onceki, kisa_basliklar):
    return f"""Turkce aile/cocuk egitim cizgi filmi "BIDIK HIKAYELERI" icin 2-3 dakikada anlatilabilecek, hikayelestirilmeye uygun
ve merak uyandiran 1 konu sec. Alanlar: {", ".join(alanlar)}.
Konu genis ama tek bolumde islenebilir olsun (or. "Ay neden sekil degistirir?", "Arilar bal nasil yapar?").
Daha once islenen hikaye konulari (TEKRARLAMA): {", ".join(onceki) or "yok"}
Kanalda kisa videolarda en cok ilgi goren basliklar (ilham icin): {" | ".join(kisa_basliklar) or "-"}
CIKTI yalnizca JSON: {{"konu": "...", "alan": "..."}}"""


def denetim_istemi(b):
    ozet = {"baslik": b.get("baslik", ""), "aciklama": b.get("aciklama", ""),
            "bolumler": [{"ad": bo.get("ad", ""), "satirlar": [s.get("metin", "") for s in bo.get("satirlar", [])],
                          "kartlar": [{"satir": j, "buyuk": (s.get("kart") or {}).get("buyuk", ""), "alt": (s.get("kart") or {}).get("alt", "")}
                                      for j, s in enumerate(bo.get("satirlar", [])) if s.get("kart")]}
                         for bo in b.get("bolumler", [])],
            "soru": b.get("soru"), "ozet": b.get("ozet"), "dogrulama_notu": b.get("dogrulama_notu", "")}
    return f"""Sen titiz bir Turkce dil editoru ve bilgi dogrulayicisisin. Asagidaki cizgi film bolumu yayina girmeden son kez denetleniyor.

1) YAZIM/DILBILGISI: yazim, noktalama, Turkce karakter (ı/i, ş, ğ, ü, ö, ç), "de/da", "ki", "mi" hatalarini duzelt.
   Anlami, uslubu ve espriyi DEGISTIRME; hata yoksa metni AYNEN geri ver. Satir sayilari ve sirasi ayni kalsin.
   Ozel adlari (Bıdık, Bilge) koru. Satirlar en fazla 150 karakter.
2) BILGI DOGRULUGU: tum olgusal iddialari ve sorunun dogru cevabini kontrol et. Yanlis, supheli ya da yaniltici bir
   iddia varsa bilgi_dogru=false yap ve bilgi_sorunu alanina neyin sorunlu oldugunu yaz. Emin degilsen false yap.

Metin: {json.dumps(ozet, ensure_ascii=False)}

CIKTI yalnizca JSON, ayni yapida duzeltilmis metinler + karar:
{{"baslik": "...", "aciklama": "...", "bolumler": [{{"ad": "...", "satirlar": ["..."], "kartlar": [{{"satir": 0, "buyuk": "...", "alt": "..."}}]}}],
  "soru": {{"metin": "...", "secenekler": ["...", "...", "..."], "dogru": 1}}, "ozet": ["..."],
  "bilgi_dogru": true, "bilgi_sorunu": ""}}"""


def denetle(modeller, b, ilerle=None):
    """Yazim duzeltmelerini uygular. Donus: (bilgi_dogru, sorun, duzeltmeler). Cevap bozuksa MotorHatasi."""
    r = gemini_json(modeller, denetim_istemi(b), 0.1, ilerle)
    if not isinstance(r, dict) or not isinstance(r.get("bilgi_dogru"), bool) or \
            len(r.get("bolumler") or []) != len(b["bolumler"]):
        raise MotorHatasi("Denetim cevabi okunamadi")
    duz = []

    def uygula(etiket, eski, yeni, ayarla, maks):
        if isinstance(yeni, str) and yeni.strip() and yeni.strip() != (eski or "").strip() and len(yeni.strip()) <= maks:
            duz.append(f"{etiket}: '{eski}' -> '{yeni.strip()}'")
            ayarla(yeni.strip())

    uygula("Baslik", b.get("baslik"), r.get("baslik"), lambda v: b.__setitem__("baslik", v), 100)
    uygula("Aciklama", b.get("aciklama"), r.get("aciklama"), lambda v: b.__setitem__("aciklama", v), 3000)
    for i, (bo, rb) in enumerate(zip(b["bolumler"], r["bolumler"])):
        uygula(f"Kisim {i + 1} adi", bo.get("ad"), rb.get("ad"), lambda v, bo=bo: bo.__setitem__("ad", v), 60)
        rs = rb.get("satirlar") or []
        if len(rs) == len(bo["satirlar"]):
            for j, (s, yeni) in enumerate(zip(bo["satirlar"], rs)):
                uygula(f"Kisim {i + 1} satir {j + 1}", s.get("metin"), yeni, lambda v, s=s: s.__setitem__("metin", v), 160)
        for k in rb.get("kartlar") or []:
            try:
                kart = bo["satirlar"][int(k.get("satir"))].get("kart")
            except (TypeError, ValueError, IndexError):
                continue
            if kart:
                for alan, maks in (("buyuk", 14), ("alt", 30)):
                    uygula("Kart", str(kart.get(alan, "")), k.get(alan), lambda v, kart=kart, alan=alan: kart.__setitem__(alan, v), maks)
    q, rq = b.get("soru") or {}, r.get("soru") or {}
    if q and isinstance(rq, dict):
        uygula("Soru", q.get("metin"), rq.get("metin"), lambda v: q.__setitem__("metin", v), 120)
        if len(rq.get("secenekler") or []) == 3:
            for j in range(3):
                uygula("Secenek", q["secenekler"][j], rq["secenekler"][j], lambda v, j=j: q["secenekler"].__setitem__(j, v), 50)
        if rq.get("dogru") in (0, 1, 2) and rq["dogru"] != q.get("dogru"):
            return False, "Sorunun dogru cevabi denetimde farkli bulundu.", duz
    if len(r.get("ozet") or []) == len(b.get("ozet") or []):
        for j, yeni in enumerate(r["ozet"]):
            uygula("Ozet", b["ozet"][j], yeni, lambda v, j=j: b["ozet"].__setitem__(j, v), 70)
    return r["bilgi_dogru"], str(r.get("bilgi_sorunu") or ""), duz


def _temizle(b):
    """Modelin atlayabilecegi alanlari duzeltir, gecersiz secimleri varsayilana ceker."""
    for bo in b.get("bolumler", []):
        if bo.get("tema") not in arka_planlar.TEMALAR:
            bo["tema"] = arka_planlar.tema_bul(b.get("alan", ""), b.get("konu", ""))
        if not isinstance(bo.get("arka_no"), int):
            bo["arka_no"] = 0
        for s in bo.get("satirlar", []):
            s["kim"] = "bilge" if str(s.get("kim", "")).lower().startswith("bil") else "bidik"
            gecerli = IFADE_BIDIK if s["kim"] == "bidik" else IFADE_BILGE
            if s.get("ifade") not in gecerli:
                s["ifade"] = "normal"
            if s["kim"] == "bilge" or s.get("kol") not in KOLLAR:
                s.pop("kol", None)
            k = s.get("kart")
            if k and not (str(k.get("buyuk", "")).strip()):
                s.pop("kart", None)
    if b.get("kostum") not in KOSTUMLER:
        b.pop("kostum", None)


def yaz(konu=None, ilerle=None):
    ilerle = ilerle or (lambda y, m: None)
    a = ayarlar()
    ilerle(5, "Model seçiliyor")
    modeller = model_sec(a.get("model"))
    onceki = [x.get("konu", "") for x in liste()][:40]
    alan = ""
    if not konu:
        try:
            import analiz
            kisa = analiz.en_iyi_basliklar(5)
        except Exception:
            kisa = []
        ilerle(10, "Konu seçiliyor")
        k = gemini_json(modeller, konu_istemi(a["alanlar"], onceki, kisa), 1.0, ilerle)
        konu, alan = str(k.get("konu", "")).strip(), str(k.get("alan", "")).strip()
        if not konu:
            raise MotorHatasi("Konu seçilemedi, tekrar dene.")
    son_hata = ""
    for deneme in range(3):
        ilerle(20 + deneme * 25, f"Bölüm yazılıyor: {konu}" + (f" (deneme {deneme + 1})" if deneme else ""))
        b = gemini_json(modeller, yazar_istemi(konu, alan or "genel", onceki), 0.9, ilerle)
        if not isinstance(b, dict):
            son_hata = "cevap okunamadi"
            continue
        b.setdefault("konu", konu)
        b.setdefault("alan", alan or "genel")
        _temizle(b)
        h = dogrula(b)
        if h:
            son_hata = "; ".join(h[:3])
            print("Hikaye formati gecersiz:", son_hata)
            continue
        ilerle(35 + deneme * 25, "Yazım ve bilgi denetimi")
        sonuc = None
        for dd in range(2):   # Gemini mesgulse bolumu bastan yazmak yerine sadece denetimi tekrar dene
            try:
                sonuc = denetle(modeller, b, ilerle)
                break
            except MotorHatasi as e:
                son_hata = str(e)
                if dd == 0:
                    ilerle(None, "Gemini meşgul, denetim 20 sn sonra tekrar denenecek")
                    time.sleep(20)
        if sonuc is None:
            # yazilan bolum bosa gitmesin: denetimsiz taslak olarak kaydedilir; video uretilirken denetim yapilir
            b["durum"] = "taslak"
            b["yazildi"] = datetime.datetime.now().isoformat(timespec="minutes")
            b["id"] = f"{datetime.date.today():%Y-%m-%d}-{_slug(b.get('baslik') or konu)}"
            kaydet(b)
            ilerle(100, "Bölüm yazıldı, denetim videodan önce yapılacak")
            return b
        dogru, sorun, duz = sonuc
        if not dogru:
            son_hata = "bilgi şüpheli: " + sorun
            print("Hikaye elendi:", sorun)
            continue
        b["denetim"] = {"imza": imza(b), "tarih": datetime.date.today().isoformat(), "duzeltmeler": duz}
        b["durum"] = "taslak"
        b["yazildi"] = datetime.datetime.now().isoformat(timespec="minutes")
        b["id"] = f"{datetime.date.today():%Y-%m-%d}-{_slug(b.get('baslik') or konu)}"
        kaydet(b)
        ilerle(100, "Bölüm hazır")
        return b
    raise MotorHatasi(f"Bölüm yazılamadı ({son_hata}). Birkaç dakika sonra tekrar dene.")
