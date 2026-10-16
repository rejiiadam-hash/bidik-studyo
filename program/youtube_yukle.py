"""
YouTube baglantisi ve yukleme (YouTube Data API v3).

Kurulum uygulamanin "YouTube" sekmesinden adim adim yapilir:
  1. Google Cloud'da proje + "YouTube Data API v3"
  2. OAuth izin ekrani (Harici, kendi Gmail'in test kullanicisi)
  3. OAuth istemci kimligi (Masaustu uygulamasi) -> JSON indir
  4. JSON'u uygulamada sec -> "Hesabimi bagla"

Not: Google'in denetiminden (audit) gecmemis projelerden yuklenen videolari
YouTube "ozel" olarak kisitlar. Denetim onaylanana kadar zamanlanan videolar
herkese acilmayabilir.
"""
import datetime, json, os
from ortak import KOK, ayar_kaydet

SILME_KAPSAMI = "https://www.googleapis.com/auth/youtube.force-ssl"   # video silebilmek icin
KAPSAM = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly",
          SILME_KAPSAMI]
ISTEMCI = os.path.join(KOK, "client_secret.json")
JETON = os.path.join(KOK, "youtube_token.json")


class YuklemeHatasi(Exception):
    pass


def hazir_mi():
    return os.path.exists(ISTEMCI)


def bagli_mi():
    return os.path.exists(JETON)


def istemci_kaydet(icerik):
    """Kullanicinin sectigi client_secret JSON'unu dogrulayip kaydeder."""
    try:
        veri = json.loads(icerik)
    except ValueError:
        raise YuklemeHatasi("Secilen dosya gecerli bir JSON degil. Google Cloud'dan indirdigin dosyayi sec.")
    if "web" in veri and "installed" not in veri:
        raise YuklemeHatasi("Bu istemci 'Web uygulamasi' turunde. Yeni istemci olustururken "
                            "Uygulama turu olarak 'Masaustu uygulamasi' secmelisin.")
    ic = veri.get("installed") or {}
    if not ic.get("client_id") or not ic.get("client_secret"):
        raise YuklemeHatasi("Dosyada client_id / client_secret bulunamadi. Dogru dosyayi sectiginden emin ol.")
    with open(ISTEMCI, "w", encoding="utf-8") as f:
        json.dump(veri, f)
    if os.path.exists(JETON):   # yeni istemci = yeni baglanti gerekir
        os.remove(JETON)
    ayar_kaydet({"youtube_kanal": ""})


def _kutuphaneler():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        return Credentials, InstalledAppFlow, Request, build
    except ImportError:
        raise YuklemeHatasi("YouTube bilesenleri kurulu degil. BIDIK klasorundeki BASLAT.bat'i bir kez calistir.")


def _servis(izin_iste=False):
    Credentials, InstalledAppFlow, Request, build = _kutuphaneler()
    if not hazir_mi():
        raise YuklemeHatasi("Once YouTube sekmesinden kurulumu tamamla (client_secret.json).")
    kimlik = None
    if os.path.exists(JETON) and not izin_iste:
        try:
            # dosyadaki (verilmis olan) izinlerle yukle: eski baglantilar yeni izin eklendi diye bozulmasin
            kimlik = Credentials.from_authorized_user_file(JETON)
        except ValueError:
            kimlik = None
    if kimlik and not kimlik.valid and kimlik.expired and kimlik.refresh_token:
        try:
            kimlik.refresh(Request())
        except Exception:
            kimlik = None
    if not kimlik or not kimlik.valid:
        if not izin_iste:
            raise YuklemeHatasi("YouTube baglantisi yok ya da suresi dolmus. YouTube sekmesinden 'Hesabimi bagla'ya bas.")
        akis = InstalledAppFlow.from_client_secrets_file(ISTEMCI, KAPSAM)
        try:
            kimlik = akis.run_local_server(
                port=0, prompt="consent", timeout_seconds=300, open_browser=True,
                authorization_prompt_message="",
                success_message="Bıdık Stüdyo YouTube hesabına bağlandı. Bu sekmeyi kapatıp uygulamaya dönebilirsin.")
        except Exception as e:
            raise YuklemeHatasi(f"Google izni tamamlanmadi ({e}). Tekrar 'Hesabimi bagla'ya bas.")
        if not kimlik:
            raise YuklemeHatasi("Google izni 5 dakika icinde verilmedi. Tekrar dene.")
        with open(JETON, "w", encoding="utf-8") as f:
            f.write(kimlik.to_json())
    return build("youtube", "v3", credentials=kimlik, cache_discovery=False)


def silme_izni_var():
    """Mevcut baglanti video silme iznini iceriyor mu?"""
    try:
        with open(JETON, encoding="utf-8") as f:
            izinler = json.load(f).get("scopes") or []
        if isinstance(izinler, str):
            izinler = izinler.split()
        return SILME_KAPSAMI in izinler or "https://www.googleapis.com/auth/youtube" in izinler
    except (OSError, ValueError):
        return False


def sil(video_id):
    """Videoyu YouTube'dan kalici olarak siler. Zaten silinmisse sorun saymaz."""
    from googleapiclient.errors import HttpError
    if not silme_izni_var():
        raise YuklemeHatasi("Uygulamanin video silme izni yok. YouTube sekmesindeki 'Silme iznini ver' "
                            "dugmesiyle baglantiyi bir kez yenile.")
    yt = _servis()
    try:
        yt.videos().delete(id=video_id).execute()
    except HttpError as e:
        kod = getattr(e, "status_code", None) or getattr(getattr(e, "resp", None), "status", None)
        if int(kod or 0) == 404:
            return "zaten yok"
        if int(kod or 0) == 403:
            raise YuklemeHatasi("YouTube silmeye izin vermedi. Video bu kanala ait olmayabilir ya da "
                                "baglantinin yenilenmesi gerekiyor.")
        raise YuklemeHatasi(f"YouTube'dan silinemedi: {str(e)[:200]}")
    return "silindi"


def gizlilik_ayarla(video_id, gizlilik):
    """Videonun gorunurlugunu degistirir ('private' / 'public'). Donus: eski gizlilik ya da 'yok' / 'zaten'."""
    from googleapiclient.errors import HttpError
    if gizlilik not in ("private", "public", "unlisted"):
        raise ValueError("gecersiz gizlilik")
    if not silme_izni_var():
        raise YuklemeHatasi("Videolarin gizliligini degistirmek icin YouTube sekmesindeki 'Izni ver' dugmesiyle "
                            "baglantiyi bir kez yenile.")
    yt = _servis()
    try:
        r = yt.videos().list(part="status", id=video_id).execute()
        if not r.get("items"):
            return "yok"
        st = r["items"][0]["status"]
        eski = st.get("privacyStatus", "")
        if eski == gizlilik:
            return "zaten"
        yeni = {"privacyStatus": gizlilik}
        for k in ("embeddable", "license", "publicStatsViewable", "selfDeclaredMadeForKids"):
            if k in st:
                yeni[k] = st[k]
        yt.videos().update(part="status", body={"id": video_id, "status": yeni}).execute()
        return eski
    except HttpError as e:
        kod = int(getattr(e, "status_code", None) or getattr(getattr(e, "resp", None), "status", 0) or 0)
        if kod == 403 and "quota" in str(e).lower():
            raise YuklemeHatasi("YouTube'un gunluk islem kotasi doldu; yarin kaldigi yerden devam edebilirsin.")
        raise YuklemeHatasi(f"Gizlilik degistirilemedi: {str(e)[:200]}")


def bagla(ilerleme=None):
    ilerle = ilerleme or (lambda y, m: None)
    ilerle(20, "Tarayicida Google izin sayfasi acildi; kanal hesabini secip izin ver")
    yt = _servis(izin_iste=True)
    ilerle(80, "Kanal bilgisi aliniyor")
    cevap = yt.channels().list(part="snippet", mine=True).execute()
    ogeler = cevap.get("items") or []
    if not ogeler:
        raise YuklemeHatasi("Bu Google hesabinda YouTube kanali bulunamadi. Kanalin bagli oldugu hesabi sec.")
    ad = ogeler[0]["snippet"]["title"]
    ayar_kaydet({"youtube_kanal": ad})
    return f"YouTube'a baglandi: {ad}"


def baglantiyi_kes():
    if os.path.exists(JETON):
        os.remove(JETON)
    ayar_kaydet({"youtube_kanal": ""})


def yukle(video_yolu, baslik, aciklama, etiketler, yayin_zamani=None, ilerleme=None, shorts=True, kapak=None):
    """
    yayin_zamani: saat dilimli datetime. 15 dakikadan ileriyse video o an otomatik
    yayina girecek sekilde zamanlanir; degilse hemen herkese acik yuklenir.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    ilerle = ilerleme or (lambda y, m: None)
    simdi = datetime.datetime.now(datetime.timezone.utc)
    zamanli = yayin_zamani is not None and yayin_zamani > simdi + datetime.timedelta(minutes=15)
    durum = {"selfDeclaredMadeForKids": False}
    if zamanli:
        durum["privacyStatus"] = "private"
        durum["publishAt"] = yayin_zamani.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        durum["privacyStatus"] = "public"
    if shorts:
        baslik = baslik if "#shorts" in baslik.lower() else f"{baslik} #shorts"
    govde = {
        "snippet": {"title": baslik[:100], "description": aciklama[:4900], "tags": etiketler[:15],
                    "categoryId": "27",   # Egitim
                    "defaultLanguage": "tr", "defaultAudioLanguage": "tr"},
        "status": durum,
    }
    ilerle(5, "YouTube'a baglaniliyor")
    yt = _servis()
    istek = yt.videos().insert(part="snippet,status", body=govde,
                               media_body=MediaFileUpload(video_yolu, chunksize=1024 * 1024, resumable=True))
    cevap = None
    try:
        while cevap is None:
            ilerleme_durumu, cevap = istek.next_chunk()
            if ilerleme_durumu:
                ilerle(10 + int(80 * ilerleme_durumu.progress()), "Video yukleniyor")
    except HttpError as e:
        metin = str(e)
        if "quotaExceeded" in metin:
            raise YuklemeHatasi("YouTube gunluk yukleme kotasi doldu. Yarin tekrar dene.")
        if "uploadLimitExceeded" in metin:
            raise YuklemeHatasi("Kanalin gunluk yukleme siniri doldu. Yarin tekrar dene.")
        raise YuklemeHatasi(f"YouTube hatasi: {metin[:300]}")
    vid = cevap["id"]
    kapak_sonuc = ""
    if kapak and os.path.exists(kapak):
        ilerle(92, "Kapak gorseli yukleniyor")
        try:   # ozel kapak icin kanalin telefonla dogrulanmis olmasi gerekir; olmazsa YouTube kendisi secer
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(kapak, mimetype="image/png")).execute()
            kapak_sonuc = "yuklendi"
        except Exception as e:
            kapak_sonuc = f"yuklenemedi: {str(e)[:120]}"
    ilerle(95, "Yayin durumu kontrol ediliyor")
    gercek = {}
    try:
        gercek = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    except Exception:
        pass
    kisitli = (not zamanli and gercek.get("privacyStatus") == "private")
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}" if shorts else f"https://youtu.be/{vid}",
            "kapak": kapak_sonuc, "zamanli": zamanli,
            "yayin_zamani": yayin_zamani.isoformat() if yayin_zamani else simdi.isoformat(),
            "kisitli": kisitli, "durum": gercek}
