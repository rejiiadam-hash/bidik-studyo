"""
Bidik senaryo motoru: her gun yeni, birbirinden farkli, eglenceli ve
bilgilendirici 15 saniyelik skecler yazar ve ONAYA birakir.

Akis:
  1. ayarlar.json'daki konu alanlarindan, hafiza.json'da olmayan konular secilir
  2. Yapay zeka (Gemini, ucretsiz katman) ADAY_SAYISI senaryo yazar
  3. Ikinci bir cagri "sert bir editor" gibi her adayi puanlar
  4. Gecerli ve en yuksek puanli GUNLUK_VIDEO kadari senaryolar/bekleyen/<tarih>/ klasorune yazilir
  5. Onay, onizleme ve paylasim: kontrol paneli (BASLAT.bat)

Gereken: Gemini API anahtari (aistudio.google.com'dan ucretsiz; panelin Ayarlar bolumune girilir).
Sadece Python standart kutuphanesi kullanir.
"""
import json, os, random, re, sys, datetime, urllib.request, urllib.error
from video_uret import dogrula, IKONLAR, RENKLER
from karakter import IFADELER, KOL_POZLARI
from ortak import ayarlar, HAFIZA, SENARYO
from kostumler import KOSTUMLER, kostum_sec

API = "https://generativelanguage.googleapis.com/v1beta"


class MotorHatasi(Exception):
    pass


class GeciciHata(MotorHatasi):
    """Model mesgul / dakikalik limit: biraz bekleyip veya baska modelle tekrar denenir."""
    pass


def hafiza():
    if os.path.exists(HAFIZA):
        with open(HAFIZA, encoding="utf-8") as f:
            return json.load(f)
    return {"konular": []}


def hafizaya_ekle(konu, alan, baslik, durum):
    h = hafiza()
    h["konular"].append({"konu": konu, "alan": alan, "baslik": baslik, "durum": durum,
                         "tarih": datetime.date.today().isoformat()})
    with open(HAFIZA, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)


# --- Gemini ------------------------------------------------------------------
def _istek(url, veri=None):
    anahtar = ayarlar().get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    if not anahtar:
        raise MotorHatasi("Gemini API anahtari girilmemis. Paneldeki Ayarlar bolumune yapistir.")
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "key=" + anahtar,
                                 data=json.dumps(veri).encode() if veri else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        govde = e.read().decode(errors="ignore")[:400]
        if e.code == 402:
            raise MotorHatasi(
                "Bu API anahtari, bakiyesi bitmis ucretli (Prepay) bir faturalandirma hesabina bagli. "
                "Ucretsiz kullanmak icin faturalandirmasi OLMAYAN bir projeden yeni anahtar al: "
                "aistudio.google.com/apikey > Create API key > yeni proje. "
                "Hata surerse anahtari baska bir Google hesabiyla olustur.")
        if e.code in (429, 500, 503, 504):
            raise GeciciHata(f"Gemini {e.code}: {govde}")
        if e.code == 404:
            raise GeciciHata(f"Model bulunamadi: {govde}")
        raise MotorHatasi(f"Gemini hatasi {e.code}: {govde}")
    except TimeoutError:
        raise GeciciHata("Gemini cevap vermedi (zaman asimi)")
    except urllib.error.URLError as e:
        raise MotorHatasi(f"Internete baglanilamadi: {e.reason}")


def model_sec(tercih):
    """Denenecek modellerin sirali listesi (ilki tercih edilen)."""
    if tercih:
        return [tercih]
    modeller = _istek(f"{API}/models?pageSize=200").get("models", [])
    uygun = [m["name"].split("/")[-1] for m in modeller
             if "generateContent" in m.get("supportedGenerationMethods", [])
             and "flash" in m["name"] and not any(x in m["name"] for x in ("tts", "image", "live", "audio"))]
    if not uygun:
        raise MotorHatasi("Uygun Gemini modeli bulunamadi; ayarlar.json'a 'model' yaz.")
    # kararli surumleri (preview/exp olmayan) ve yeni olanlari one al;
    # tam ve "lite" modelleri sirayla karistir: yogunlukta lite modeller genelde daha cabuk cevap verir
    anahtar = lambda n: (("preview" in n) or ("exp" in n), [-int(x) for x in re.findall(r"\d+", n)])
    tam = sorted([n for n in uygun if "lite" not in n], key=anahtar)
    lite = sorted([n for n in uygun if "lite" in n], key=anahtar)
    sirali = []
    for i in range(max(len(tam), len(lite))):
        sirali += tam[i:i + 1] + lite[i:i + 1]
    return sirali[:8]


def gemini_json(modeller, istem, sicaklik=1.0, ilerle=None):
    """
    Hizli deneme sirasi: once en son basarili olan model; mesgulse BEKLEMEDEN siradaki modele gecer.
    Hepsi mesgulse kisa bir bekleme sonrasi tum modelleri bir tur daha dener.
    """
    import time
    from ortak import ayar_kaydet
    ilerle = ilerle or (lambda y, m: None)
    if isinstance(modeller, str):
        modeller = [modeller]
    son = ayarlar().get("son_model")
    if son in modeller:
        modeller = [son] + [m for m in modeller if m != son]
    olu, son_hata = set(), None
    for tur, bekle in enumerate((0, 6, 15)):
        if bekle:
            ilerle(None, f"Tum modeller mesgul, {bekle} sn sonra tekrar deneniyor ({tur + 1}/3)")
            time.sleep(bekle)
        for model in modeller:
            if model in olu:
                continue
            try:
                sonuc = _cevap_coz(_istek(f"{API}/models/{model}:generateContent", {
                    "contents": [{"role": "user", "parts": [{"text": istem}]}],
                    "generationConfig": {"temperature": sicaklik, "responseMimeType": "application/json",
                                         "maxOutputTokens": 32768},
                }))
                if model != son:
                    ayar_kaydet({"son_model": model})
                return sonuc
            except GeciciHata as e:
                son_hata = e
                if "bulunamadi" in str(e):
                    olu.add(model)
                ilerle(None, f"{model} {'cevabi okunamadi' if 'okunamadi' in str(e) or 'bos cevap' in str(e) else 'mesgul'}, baska modele geciliyor")
    raise MotorHatasi("Google'in modellerinden su an kullanilabilir cevap alinamadi. Birkac dakika sonra tekrar dene. ("
                      + str(son_hata)[:200] + ")")


def _liste(sonuc, anahtar):
    """Model {"senaryolar": [...]} yerine dogrudan [...] ya da farkli anahtar dondurebilir; hepsini kabul et."""
    if isinstance(sonuc, dict):
        if isinstance(sonuc.get(anahtar), list):
            sonuc = sonuc[anahtar]
        else:
            sonuc = next((v for v in sonuc.values() if isinstance(v, list)), [sonuc] if sonuc else [])
    if not isinstance(sonuc, list):
        return []
    return [x for x in sonuc if isinstance(x, dict)]


def _kurtar(metin):
    """
    Yarida kesilmis / bozuk JSON'dan eksiksiz gelen ogeleri kurtarir.
    Ornek: {"senaryolar": [ {..tam..}, {..tam..}, {..yarim  ->  {"senaryolar": [tam, tam]}
    """
    desenler = [(a, r'"%s"\s*:\s*\[' % a) for a in ("senaryolar", "puanlar", "sonuclar")] + [("senaryolar", r'^\s*\[')]
    for anahtar, desen in desenler:
        m = re.search(desen, metin)
        if not m:
            continue
        coz, i, ogeler = json.JSONDecoder(), m.end(), []
        while True:
            while i < len(metin) and metin[i] in " \t\r\n,":
                i += 1
            if i >= len(metin) or metin[i] != "{":
                break
            try:
                oge, i = coz.raw_decode(metin, i)
            except json.JSONDecodeError:
                break
            ogeler.append(oge)
        if ogeler:
            return {anahtar: ogeler}
    return None


def _cevap_coz(cevap):
    try:
        aday = cevap["candidates"][0]
        metin = aday["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise GeciciHata("Yapay zeka bos cevap verdi")
    metin = re.sub(r"^```(json)?|```$", "", metin.strip()).strip()
    try:
        return json.loads(metin)
    except json.JSONDecodeError as e:
        kurtarilan = _kurtar(metin)
        if kurtarilan:
            print(f"Bozuk/yarim cevap: {len(next(iter(kurtarilan.values())))} oge kurtarildi ({e})")
            return kurtarilan
        raise GeciciHata(f"Yapay zeka cevabi okunamadi ({e})")


# --- istemler -----------------------------------------------------------------
def yazar_istemi(ayar, kullanilan, alanlar):
    return f"""Sen Turkce YouTube Shorts yazarisin. Kanalin tek ve sabit karakteri BIDIK:
sari, yumurta seklinde, kafasinda kivrik percem olan, kirmizi ayakkabili, merakli ve biraz sakar sevimli bir yaratik.
Her video ~15 saniye: Bidik ilginc ve DOGRU bir bilgiyi komik bir durum uzerinden anlatir.

{len(alanlar)} farkli senaryo yaz, her biri su alanlardan birinden (sirayla): {", ".join(alanlar)}.
Uslup: {ayar["uslup"]}

KURALLAR
- Ilk sahne (ilk 2 saniye) izleyiciyi durduracak bir soru ya da sasirtici iddia olsun.
- Bilgi kesin olarak dogru ve dogrulanabilir olmali; supheli/efsane bilgileri KULLANMA.
- Son sahne ilk sahneye baglanip dongu hissi versin veya komik bir son vurusla bitsin.
- 4-6 sahne, toplam sure 13-16 saniye, her replik en fazla 60 karakter, gunluk konusma dili.
- Bu konular daha once islendi, TEKRARLAMA: {", ".join(kullanilan) or "yok"}
- Tum senaryolar birbirinden farkli konu ve farkli espri yapisinda olsun.
- "burclar ve gokyuzu" alani: astrolojinin TARIHI, KULTURU ve GOKBILIMI hakkinda dogru bilgiler
  (or. burclarin kokeni, takimyildizlarin kaymasi, 13. takimyildiz Yilanci). Burclarin kisilik/gelecek
  belirledigini ASLA iddia etme; bu bilimsel olarak dogru degildir.
- "cocuklarin neden sorulari" alani: cocuklarin sordugu "Neden?" sorulari (gokyuzu neden mavi, neden esneriz...).
  Cok basit, sicak, aile dostu dil; her yastan izleyici icin (sadece kucuk cocuklara hitap etme).

Sahne alanlari:
- "sure": saniye (1.5-4)
- "ifade": {IFADELER}
- "kol": {KOL_POZLARI}
- "ziplama": 0-80 (heyecan aninda)
- "replik": Bidik'in soyledigi / ekrandaki yazi
- "konusuyor": true/false
- "kart" (istege bagli, bilginin en carpici sayisi icin, en fazla 2 sahnede):
   {{"buyuk": "3", "alt": "KALP", "ikon": {IKONLAR} veya null, "adet": 0-6, "renk": {list(RENKLER)}}}

YAYIN METINLERI (kesfette bulunmak icin cok onemli):
- "baslik": merak uyandiran, konunun ana kelimesini iceren, max 60 karakter, en fazla 1 emoji.
- "aciklama": 2-3 kisa cumle. 1) videodaki bilgiyi ozetleyen merak cumlesi, 2) bilgiye kucuk bir ek detay,
  3) izleyiciye yorum yaptiracak bir SORU (or. "Sen bunu biliyor muydun?"). Hashtag YAZMA, onlari ayri alana koy.
- "hashtagler": TAM 3 hashtag, #isaretiyle, Turkce karakterli olabilir, bosluksuz:
  1. konunun kendisi (#ahtapot), 2. kategorisi (#hayvanlar / #bilim), 3. genel bilgi etiketi (#bilgi veya #ilgincbilgiler).
- "etiketler": 10-12 etiket; insanlarin YouTube'da gercekten arayacagi ifadeler. Karisim:
  konu adi ve esanlamlilari, "... nedir / neden ..." gibi arama kaliplari, kategori, "ilginc bilgiler",
  "bunu biliyor muydun", "komik animasyon", "bidik". Hepsi kucuk harf, # isaretsiz, her biri max 30 karakter.

CIKTI: yalnizca su JSON:
{{"senaryolar": [{{"baslik": "...",
  "alan": "...", "konu": "kisa konu adi", "aciklama": "...", "hashtagler": ["#...", "#...", "#..."],
  "etiketler": ["..."], "dogrulama_notu": "bilginin dayanagi, tek cumle",
  "sahneler": [ ... ]}}]}}"""


def editor_istemi(senaryolar):
    ozet = [{"no": i, "baslik": s["baslik"], "replikler": [x.get("replik") for x in s["sahneler"]],
             "dogrulama_notu": s.get("dogrulama_notu")} for i, s in enumerate(senaryolar)]
    return f"""Sen acimasiz bir YouTube Shorts editorusun. Asagidaki Turkce skecleri puanla (1-10):
- kanca: ilk saniyede kaydirmayi durdurur mu
- komiklik: gercekten guldurur mu, yavan mi
- bilgi: bilgi dogru ve ilginc mi (yanlis/supheli bilgi varsa bilgi=1)
- son: sonu tatmin edici veya donguye giren bir vurus mu
Skecler: {json.dumps(ozet, ensure_ascii=False)}
CIKTI yalnizca JSON: {{"puanlar": [{{"no": 0, "kanca": 7, "komiklik": 6, "bilgi": 9, "son": 6, "not": "kisa elestiri"}}]}}"""


# --- yazim ve bilgi denetimi ---------------------------------------------------
def _metinler(s):
    """Izleyicinin goruecegi tum metinler: (anahtar, deger) listesi."""
    m = [("baslik", s.get("baslik", "")), ("aciklama", s.get("aciklama", ""))]
    for i, sh in enumerate(s.get("sahneler", [])):
        m.append((f"replik{i}", sh.get("replik", "")))
        k = sh.get("kart") or {}
        m.append((f"kart_buyuk{i}", str(k.get("buyuk", ""))))
        m.append((f"kart_alt{i}", str(k.get("alt", ""))))
    return m


def imza(s):
    import hashlib
    return hashlib.sha1(json.dumps(_metinler(s), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def denetim_gecerli(s):
    """Metin, temiz cikmis bir denetimden beri hic degismediyse True."""
    return (s.get("denetim") or {}).get("imza") == imza(s)


def denetim_istemi(senaryolar):
    ozet = []
    for i, s in enumerate(senaryolar):
        ozet.append({"no": i, "baslik": s.get("baslik", ""), "aciklama": s.get("aciklama", ""),
                     "replikler": [x.get("replik", "") for x in s["sahneler"]],
                     "kartlar": [{"sahne": j, "buyuk": (x.get("kart") or {}).get("buyuk", ""),
                                  "alt": (x.get("kart") or {}).get("alt", "")}
                                 for j, x in enumerate(s["sahneler"]) if x.get("kart")],
                     "dogrulama_notu": s.get("dogrulama_notu", "")})
    return f"""Sen titiz bir Turkce dil editoru ve bilgi dogrulayicisisin. Asagidaki YouTube Shorts metinleri yayina girmeden son kez denetleniyor.

1) YAZIM/DILBILGISI: Gercek yazim hatalarini, noktalama hatalarini, eksik/yanlis Turkce karakterleri (ı/i, ş, ğ, ü, ö, ç), \"de/da\", \"ki\", \"mi\" ayrimlarini, kelime hatalarini duzelt.
   - Anlami, ustubu, espriyi ve kelime sayisini DEGISTIRME; sadece hata varsa dokun. Hata yoksa metni AYNEN geri ver.
   - Replik sayisi ve sirasi ayni kalsin. Hicbir replik 70 karakteri gecmesin.
   - Marka/ozel adlari (Bidik/Bıdık, Wi-Fi gibi) dogru yazimlariyla koru.
2) BILGI DOGRULUGU: Metinlerdeki tum olgusal iddialari kontrol et. Yanlis, supheli, efsane olan ya da yaniltici derecede basitlestirilmis bir iddia varsa bilgi_dogru=false yap ve bilgi_sorunu alanina tek cumleyle neyin sorunlu oldugunu yaz. Emin degilsen false yap.

Metinler: {json.dumps(ozet, ensure_ascii=False)}

CIKTI yalnizca JSON:
{{"sonuclar": [{{"no": 0, "baslik": "...", "aciklama": "...", "replikler": ["...", "..."],
  "kartlar": [{{"sahne": 2, "buyuk": "...", "alt": "..."}}], "bilgi_dogru": true, "bilgi_sorunu": ""}}]}}"""


def denetle(modeller, senaryolar, ilerle=None):
    """
    Her senaryoyu yazim + bilgi acisindan denetler; yazim duzeltmelerini senaryoya UYGULAR.
    Donus (senaryo sirasiyla): {"tamam": bool, "bilgi_dogru": bool, "bilgi_sorunu": str, "duzeltmeler": [str]}
    tamam=False: bu senaryo denetlenemedi (cevap eksik/bozuk) -> yayina girmemeli.
    """
    sonuc_listesi = _liste(gemini_json(modeller, denetim_istemi(senaryolar), 0.1, ilerle), "sonuclar")
    harita = {}
    for r in sonuc_listesi:
        try:
            harita[int(r.get("no"))] = r
        except (TypeError, ValueError):
            pass
    cikti = []
    for i, s in enumerate(senaryolar):
        r = harita.get(i)
        sahneler = s["sahneler"]
        if (not r or not isinstance(r.get("replikler"), list) or len(r["replikler"]) != len(sahneler)
                or not isinstance(r.get("bilgi_dogru"), bool)):
            cikti.append({"tamam": False, "bilgi_dogru": False, "bilgi_sorunu": "", "duzeltmeler": []})
            continue
        duz = []

        def uygula(etiket, eski, yeni, ayarla, maks=None):
            if not isinstance(yeni, str):
                return
            yeni = yeni.strip()
            if not yeni or yeni == (eski or "").strip() or (maks and len(yeni) > maks):
                return
            duz.append(f"{etiket}: '{eski}' -> '{yeni}'")
            ayarla(yeni)

        if "baslik" in s:
            uygula("Baslik", s.get("baslik"), r.get("baslik"), lambda v: s.__setitem__("baslik", v), 100)
        if s.get("aciklama"):
            uygula("Aciklama", s.get("aciklama"), r.get("aciklama"), lambda v: s.__setitem__("aciklama", v), 4000)
        for j, sh in enumerate(sahneler):
            if sh.get("replik"):
                uygula(f"Sahne {j + 1} replik", sh.get("replik"), r["replikler"][j],
                       lambda v, sh=sh: sh.__setitem__("replik", v), 70)
        for k in (r.get("kartlar") or []):
            try:
                j = int(k.get("sahne"))
                kart = sahneler[j].get("kart")
            except (TypeError, ValueError, IndexError, AttributeError):
                continue
            if not kart:
                continue
            for alan in ("buyuk", "alt"):
                uygula(f"Sahne {j + 1} kart", str(kart.get(alan, "")), k.get(alan),
                       lambda v, kart=kart, alan=alan: kart.__setitem__(alan, v), 40)
        cikti.append({"tamam": True, "bilgi_dogru": r["bilgi_dogru"],
                      "bilgi_sorunu": str(r.get("bilgi_sorunu") or "").strip(), "duzeltmeler": duz})
    return cikti


def denetim_isle(s, sonuc):
    """Temiz cikmissa (duzeltme yok, bilgi dogru) senaryoya imza koyar."""
    if sonuc["tamam"] and sonuc["bilgi_dogru"] and not sonuc["duzeltmeler"]:
        s["denetim"] = {"imza": imza(s), "tarih": datetime.date.today().isoformat()}
    else:
        s.pop("denetim", None)


# --- ana akis -----------------------------------------------------------------
def calistir(ilerleme=None):
    _ilerle = ilerleme or (lambda y, m: print(m))
    son = {"y": 0}

    def ilerle(y, m):
        if y is not None:
            son["y"] = y
        _ilerle(son["y"], m)
    ayar = ayarlar()
    ilerle(5, "Model seciliyor")
    modeller = model_sec(ayar["model"])
    kullanilan = [k["konu"] for k in hafiza()["konular"]][-200:]
    bekleyen = [json.load(open(p, encoding="utf-8")).get("konu", "") for p in bekleyen_dosyalar()]
    kullanilan += bekleyen
    aday_sayisi = min(int(ayar["aday_sayisi"]), max(5, int(ayar["gunluk_video"]) * 2))   # kisa cevap = hizli ve kesilmez
    alanlar = [random.choice(ayar["alanlar"]) for _ in range(aday_sayisi)]
    ilerle(15, f"{len(alanlar)} aday senaryo yaziliyor ({modeller[0]})")
    adaylar = _liste(gemini_json(modeller, yazar_istemi(ayar, kullanilan, alanlar), 1.1, ilerle), "senaryolar")

    gecerli = []
    kucuk = [k.lower() for k in kullanilan]
    for s in adaylar:
        # daha kucuk modeller bazi alanlari atlayabiliyor: varsayilanla doldur
        s.setdefault("baslik", s.get("konu") or "Bıdık")
        s.setdefault("konu", s["baslik"])
        s.setdefault("alan", "genel")
        if s.get("kostum") not in KOSTUMLER:
            s["kostum"] = kostum_sec(s.get("alan"), s.get("konu"))   # konuya uygun kiyafet
        h = dogrula(s)
        if h:
            print("  elendi (format):", s.get("baslik"), "-", "; ".join(h))
        elif s.get("konu", "").lower() in kucuk:
            print("  elendi (tekrar):", s.get("baslik"))
        else:
            gecerli.append(s)
    if not gecerli:
        raise MotorHatasi("Gecerli senaryo cikmadi, tekrar dene.")

    ilerle(60, f"{len(gecerli)} senaryo editor tarafindan puanlaniyor")
    puanlar = _liste(gemini_json(modeller, editor_istemi(gecerli), 0.2, ilerle), "puanlar")
    for p in puanlar:
        try:
            p["no"] = int(p.get("no"))
        except (TypeError, ValueError):
            continue
        if 0 <= p["no"] < len(gecerli):
            s = gecerli[p["no"]]
            s["puan"] = {k: p.get(k) for k in ("kanca", "komiklik", "bilgi", "son")}
            s["editor_notu"] = p.get("not", "")

    def skor(s):
        p = s.get("puan") or {}
        if (p.get("bilgi") or 0) < 6:   # bilgisi supheli olanlar asla secilmez
            return -1
        return 1.5 * (p.get("kanca") or 0) + 1.5 * (p.get("komiklik") or 0) + (p.get("bilgi") or 0) + (p.get("son") or 0)

    hedef = int(ayar["gunluk_video"])
    gecerli.sort(key=skor, reverse=True)
    secilen, alanlar_secilen = [], set()
    for tur in (1, 2):   # once her alandan en fazla bir tane, yetmezse kalanlar
        for s in gecerli:
            if len(secilen) == hedef:
                break
            if s in secilen or skor(s) < 0 or (tur == 1 and s["alan"] in alanlar_secilen):
                continue
            secilen.append(s)
            alanlar_secilen.add(s["alan"])
    if not secilen:
        raise MotorHatasi("Hicbir senaryo bilgi dogrulugu esigini gecemedi; tekrar dene.")

    # yayina yakin son denetim: yazim duzeltmeleri uygulanir, bilgisi supheli olanlar elenir
    if ayar.get("yazim_denetimi", True):
        ilerle(85, "Yazim ve bilgi denetimi yapiliyor")
        try:
            sonuclar = denetle(modeller, secilen, ilerle)
            kalan = []
            for s, r in zip(secilen, sonuclar):
                if r["tamam"] and not r["bilgi_dogru"]:
                    print("  elendi (bilgi supheli):", s.get("baslik"), "-", r["bilgi_sorunu"])
                    continue
                if r["duzeltmeler"]:
                    print("  yazim duzeltildi:", s.get("baslik"), "-", " | ".join(r["duzeltmeler"]))
                denetim_isle(s, r)   # denetlenemeyenler imzasiz kalir: onay asamasi tekrar kontrol eder
                kalan.append(s)
            secilen = kalan
        except MotorHatasi as e:
            print("Denetim yapilamadi, onay asamasinda yapilacak:", e)
        if not secilen:
            raise MotorHatasi("Senaryolarin bilgisi denetimde supheli bulundu; tekrar dene.")

    gun = datetime.datetime.now().strftime("%Y-%m-%d")
    klasor = os.path.join(SENARYO, "bekleyen", gun)
    os.makedirs(klasor, exist_ok=True)
    mevcut = len(os.listdir(klasor))
    for i, s in enumerate(secilen, mevcut + 1):
        with open(os.path.join(klasor, f"{i}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    ilerle(100, f"{len(secilen)} senaryo onaya hazir")
    return secilen


def bekleyen_dosyalar():
    import glob
    return sorted(glob.glob(os.path.join(SENARYO, "bekleyen", "*", "*.json")))


if __name__ == "__main__":
    try:
        calistir()
    except MotorHatasi as e:
        print("HATA:", e)
        sys.exit(1)
