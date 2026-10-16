"""
Kanal analizi (YouTube Data API v3, mevcut 'youtube.readonly' izniyle - yeni izin gerekmez).

- cek(): kanaldaki TUM videolarin izlenme / begeni / yorum sayisini ceker, gunun anlik goruntusunu
         BIDIK\\analiz.json'a yazar (gunde bir kez otomatik; panelden elle de).
- rapor(donem): "gunluk" | "haftalik" | "aylik" -> ozet kartlar, konu alanina gore ortalama izlenme,
         yayin saatine gore ortalama, en cok izlenenler, son 24 saatte en hizli artanlar.
- alan_agirliklari(): senaryo motoru icin konu alanlarinin basari agirligi (cok izlenen alan daha sik).
Yerel kayitlardan (videolar/*.json) alan, konu, kostum, giris, arka plan eslestirilir.
"""
import datetime, glob, json, os, re, threading, time

from ortak import KOK, VIDEO

DOSYA = os.path.join(KOK, "analiz.json")
_KILIT = threading.Lock()
DURUM = {"son": "", "hata": ""}


def _oku():
    try:
        with open(DOSYA, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"videolar": {}, "son_cekim": ""}


def _yaz(v):
    gecici = DOSYA + ".yaziliyor"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False)
    os.replace(gecici, DOSYA)


def _yerel_kayitlar():
    """youtube_id -> yerel meta (alan, konu, kostum, giris, arka plan, baslik)."""
    sonuc = {}
    for yol in glob.glob(os.path.join(VIDEO, "*", "*.json")):
        try:
            with open(yol, encoding="utf-8") as f:
                m = json.load(f)
        except (OSError, ValueError):
            continue
        url = m.get("youtube_url") or ""
        vid = m.get("youtube_id") or (url.rstrip("/").rsplit("/", 1)[-1] if url else "")
        if vid:
            sonuc[vid] = {k: m.get(k, "") for k in ("alan", "konu", "kostum", "_giris", "_arka_plan", "baslik", "yayin_zamani")}
    return sonuc


def cek(ilerle=None):
    """Kanalin tum videolarinin istatistiklerini ceker ve bugunku goruntuyu kaydeder."""
    import youtube_yukle as yt
    ilerle = ilerle or (lambda y, m: None)
    servis = yt._servis()
    ilerle(10, "Kanal bilgisi aliniyor")
    kanal = servis.channels().list(part="contentDetails,statistics", mine=True).execute()["items"][0]
    yuklemeler = kanal["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, sayfa = [], None
    while True:
        c = servis.playlistItems().list(part="contentDetails", playlistId=yuklemeler, maxResults=50, pageToken=sayfa).execute()
        ids += [o["contentDetails"]["videoId"] for o in c.get("items", [])]
        sayfa = c.get("nextPageToken")
        if not sayfa or len(ids) >= 1000:
            break
    ilerle(40, f"{len(ids)} videonun istatistikleri aliniyor")
    yerel = _yerel_kayitlar()
    bugun = datetime.date.today().isoformat()
    with _KILIT:
        veri = _oku()
        for i in range(0, len(ids), 50):
            c = servis.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i + 50])).execute()
            for o in c.get("items", []):
                st, sn = o.get("statistics", {}), o.get("snippet", {})
                kayit = veri["videolar"].setdefault(o["id"], {"gunluk": {}})
                baslik = sn.get("title", "").replace("#shorts", "").replace("#Shorts", "").strip()
                kayit.update(baslik=baslik, yayin=o.get("status", {}).get("publishAt") or sn.get("publishedAt", ""),
                             gizlilik=o.get("status", {}).get("privacyStatus", ""))
                if o["id"] in yerel:
                    y = yerel[o["id"]]
                    kayit.update(alan=y["alan"], konu=y["konu"], kostum=y["kostum"], giris=y["_giris"], arka=y["_arka_plan"], bidik=True)
                    if y.get("yayin_zamani"):
                        kayit["yayin"] = y["yayin_zamani"]
                kayit["gunluk"][bugun] = {"izlenme": int(st.get("viewCount", 0)), "begeni": int(st.get("likeCount", 0)),
                                          "yorum": int(st.get("commentCount", 0))}
            ilerle(40 + int(50 * (i + 50) / max(1, len(ids))), "Istatistikler kaydediliyor")
        veri["son_cekim"] = datetime.datetime.now().isoformat(timespec="minutes")
        veri["abone"] = int(kanal.get("statistics", {}).get("subscriberCount", 0) or 0)
        veri.setdefault("abone_gunluk", {})[bugun] = veri["abone"]
        _yaz(veri)
    DURUM.update(son=veri["son_cekim"], hata="")
    return f"Analiz guncellendi: {len(ids)} video"


# --- otomatik gunluk cekim ---------------------------------------------------------------
def _dongu():
    import youtube_yukle as yt
    time.sleep(90)
    while True:
        try:
            if yt.bagli_mi() and not _oku().get("son_cekim", "").startswith(datetime.date.today().isoformat()):
                cek()
        except Exception as e:
            DURUM["hata"] = str(e)[:200]
            print("Analiz cekilemedi:", DURUM["hata"])
        time.sleep(3600)


def baslat():
    threading.Thread(target=_dongu, daemon=True, name="analiz").start()


# --- rapor ------------------------------------------------------------------------------------
ALAN_ADI = {"hayvanlar": "Hayvanlar", "bilim": "Bilim", "uzay": "Uzay", "insan vucudu": "İnsan vücudu", "tarih": "Tarih",
            "psikoloji": "Psikoloji", "yemek ve mutfak bilimi": "Yemek", "teknoloji": "Teknoloji",
            "dunya cografyasi": "Coğrafya", "burclar ve gokyuzu": "Burçlar", "cocuklarin neden sorulari": "Çocuk soruları"}


def _tarih(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return t.astimezone() if t.tzinfo else t
    except ValueError:
        return None


def _son(kayit):
    g = kayit.get("gunluk") or {}
    return g[max(g)] if g else {"izlenme": 0, "begeni": 0, "yorum": 0}


def _artis(kayit, gun):
    """Son goruntu ile 'gun' gun onceki (ya da en yakin daha eski) goruntu arasindaki izlenme farki."""
    g = kayit.get("gunluk") or {}
    if len(g) < 2:
        return None
    son = max(g)
    sinir = (datetime.date.fromisoformat(son) - datetime.timedelta(days=gun)).isoformat()
    eskiler = [d for d in g if d <= sinir] or [min(g)]
    once = max(eskiler)
    return g[son]["izlenme"] - g[once]["izlenme"] if once != son else None


def _sayi_yaz(n):
    return f"{int(n):,}".replace(",", ".")


def _yorumlar(oz, alanlar, saatler, taban):
    """Panelde 'Bu donemin ozeti': kisa, okunur cikarimlar (veri azsa bunu da soyler)."""
    y = []
    if not taban:
        return ["Henüz özetlenecek video yok."]
    en = max(taban, key=lambda v: v["izlenme"])
    y.append(f"En çok izlenen: “{en['baslik'][:60]}” ({_sayi_yaz(en['izlenme'])} izlenme).")
    if alanlar:
        b = alanlar[0]
        y.append(f"En iyi konu alanı: {b['ad']} (video başına {_sayi_yaz(b['ort'])} izlenme"
                 + (", ancak yalnızca bir video var, kesin sayılmaz" if b["adet"] < 2 else "") + ").")
        if len(alanlar) > 1 and alanlar[-1]["adet"] >= 1:
            z = alanlar[-1]
            y.append(f"En zayıf konu alanı: {z['ad']} (video başına {_sayi_yaz(z['ort'])}). Bir süre daha az öne çıkarabiliriz.")
    if saatler and saatler[0]["adet"] >= 1:
        y.append(f"En iyi yayın saati: {saatler[0]['ad']} (video başına {_sayi_yaz(saatler[0]['ort'])} izlenme).")
    bidik = sorted(v["izlenme"] for v in taban if v["bidik"])
    if bidik:
        med = bidik[len(bidik) // 2]
        y.append(f"Bıdık videolarının ortanca izlenmesi {_sayi_yaz(med)}; ilk 30 gün hedefi 1.000"
                 + (" (hedefe ulaşıldı)." if med >= 1000 else "."))
    if oz["gecmis_gun"] >= 7 and oz["donem_izlenme"] and oz["abone_artis"] is not None and oz["donem_izlenme"] > 0:
        oran = 100 * oz["abone_artis"] / oz["donem_izlenme"]
        y.append(f"Aboneye dönüşüm bu dönemde: %{oran:.2f}".replace(".", ",") + " (ilk hedef %0,12).")
    elif oz["abone"] and oz["toplam_izlenme"]:
        oran = 100 * oz["abone"] / oz["toplam_izlenme"]
        y.append(f"Aboneye dönüşüm (tüm zamanlar): %{oran:.2f}".replace(".", ",")
                 + " (ilk hedef %0,12). Dönemlik oran, veri 7 güne ulaşınca gösterilecek.")
    return y


def rapor(donem="haftalik"):
    gun = {"gunluk": 1, "haftalik": 7, "aylik": 30}.get(donem, 7)
    veri = _oku()
    simdi = datetime.datetime.now().astimezone()
    bas = simdi - datetime.timedelta(days=gun)
    videolar = []
    for vid, k in veri.get("videolar", {}).items():
        t = _tarih(k.get("yayin"))
        if not t or t > simdi or k.get("gizlilik") == "private" and not k.get("bidik"):
            continue
        s = _son(k)
        videolar.append({"id": vid, "baslik": k.get("baslik", ""), "yayin": t.isoformat(), "alan": k.get("alan", ""),
                         "kostum": k.get("kostum", ""), "giris": k.get("giris", ""), "bidik": bool(k.get("bidik")),
                         "izlenme": s["izlenme"], "begeni": s["begeni"], "yorum": s["yorum"],
                         "artis": _artis(k, gun), "artis24": _artis(k, 1), "saat": t.strftime("%H:00"),
                         "donemde": t >= bas})
    donem_v = [v for v in videolar if v["donemde"]]
    # donemde yayinlanan yoksa (or. bugun hic paylasim yok) karsilastirma icin tum Bidik videolari
    taban = donem_v or [v for v in videolar if v["bidik"]] or videolar

    def grupla(anahtar, liste, ad=lambda x: x):
        g = {}
        for v in liste:
            k = v[anahtar] or "-"
            g.setdefault(k, []).append(v)
        satir = [{"ad": ad(k), "anahtar": k, "adet": len(vs), "ort": round(sum(x["izlenme"] for x in vs) / len(vs)),
                  "toplam": sum(x["izlenme"] for x in vs)} for k, vs in g.items() if k != "-"]
        return sorted(satir, key=lambda x: -x["ort"])

    artislar = [v["artis"] for v in videolar if v["artis"] is not None]
    toplam_izlenme = sum(v["izlenme"] for v in videolar)
    donem_izlenme = sum(artislar) if artislar else None
    begeni, izl = sum(v["begeni"] for v in taban), sum(v["izlenme"] for v in taban)
    hizli = sorted([v for v in videolar if v["artis24"]], key=lambda v: -v["artis24"])[:5]
    abone = veri.get("abone_gunluk") or {}
    abone_artis = None
    if len(abone) >= 2:
        son = max(abone)
        sinir = (datetime.date.fromisoformat(son) - datetime.timedelta(days=gun)).isoformat()
        once = max([d for d in abone if d <= sinir] or [min(abone)])
        abone_artis = abone[son] - abone[once] if once != son else None
    ozet_ = {"toplam_izlenme": toplam_izlenme, "donem_izlenme": donem_izlenme, "abone_artis": abone_artis,
             "ort_izlenme": round(izl / len(taban)) if taban else 0, "taban": taban, "hizli": hizli,
             "abone": veri.get("abone"),
             "gecmis_gun": len({d for k in veri.get("videolar", {}).values() for d in (k.get("gunluk") or {})})}
    return {
        "yorumlar": _yorumlar(ozet_, grupla("alan", taban, lambda k: ALAN_ADI.get(k, k)),
                              sorted(grupla("saat", taban), key=lambda x: -x["ort"]), taban),
        "donem": donem, "gun": gun, "son_cekim": veri.get("son_cekim", ""), "hata": DURUM["hata"],
        "gecmis_gun": len({d for k in veri.get("videolar", {}).values() for d in (k.get("gunluk") or {})}),
        "ozet": {"toplam_izlenme": toplam_izlenme, "donem_izlenme": donem_izlenme, "abone": veri.get("abone"),
                 "abone_artis": abone_artis, "donem_video": len(donem_v),
                 "ort_izlenme": round(izl / len(taban)) if taban else 0,
                 "etkilesim": round(100 * begeni / izl, 1) if izl else 0, "taban_donem": bool(donem_v)},
        "alanlar": grupla("alan", taban, lambda k: ALAN_ADI.get(k, k)),
        "saatler": sorted(grupla("saat", taban), key=lambda x: x["anahtar"]),
        "en_cok": sorted(taban, key=lambda v: -v["izlenme"])[:8],
        "hizli": hizli,
    }


# --- tekrar eden konular ve eski videolar ------------------------------------------------------
_DURAK = {"hakk", "şaşı", "şoke", "şok", "bilg", "gerç", "sırr", "sırl", "gizem", "sıra", "nedi", "nede", "nasıl", "ilgi",
          "inan", "unut", "bunu", "bilm", "mutl", "kesi", "ortaya", "çıkt", "çözü",
          "hang", "görü", "olur", "kalı", "kala", "dakik", "nere", "neyi", "yapı", "yapa", "bulu", "tüm", "başk", "sonu"}


def _kokler(metin):
    m = (metin or "").replace("İ", "i").replace("I", "ı").lower()
    kelime = re.findall(r"[a-zçğıöşü0-9]+", m)
    return {k[:4] for k in kelime if len(k) >= 4 and k[:4] not in _DURAK}


def benzer_mi(a, b):
    """Iki baslik/konu ayni konuyu mu anlatiyor? (ortak koklerin orani; en az 2 ortak kok)"""
    ka, kb = _kokler(a), _kokler(b)
    ortak = ka & kb
    return len(ortak) >= 2 and len(ortak) / max(1, min(len(ka), len(kb))) >= 0.6


def kanal_basliklari(adet=80):
    """Kanaldaki (gizli olanlar dahil degil) en yeni basliklar: senaryo yazarina 'tekrarlama' listesi."""
    v = [(k.get("yayin", ""), k.get("baslik", "")) for k in _oku().get("videolar", {}).values()
         if k.get("baslik") and k.get("gizlilik") != "private"]
    return [b for _, b in sorted(v, reverse=True)[:adet]]


def eski_adaylar():
    """Bidik donemi oncesinden kalan herkese acik videolar (gizlenmeye aday). Tekrar edenler / dusukler once."""
    veri = _oku()
    bidikler = [k.get("yayin", "")[:10] for k in veri.get("videolar", {}).values() if k.get("bidik") and k.get("yayin")]
    if not bidikler:
        return {"baslangic": "", "adaylar": []}
    baslangic = min(bidikler)
    hepsi = sorted(((k.get("yayin", ""), vid, k) for vid, k in veri.get("videolar", {}).items() if k.get("baslik")),
                   key=lambda x: x[0])
    gorulen, adaylar = [], []
    for yayin, vid, k in hepsi:
        tekrar = any(benzer_mi(k["baslik"], g) for g in gorulen)
        gorulen.append(k["baslik"])
        if yayin[:10] >= baslangic or k.get("bidik") or k.get("gizlilik") != "public":
            continue
        iz = _son(k)["izlenme"]
        adaylar.append({"id": vid, "baslik": k["baslik"], "yayin": yayin[:10], "izlenme": iz, "tekrar": tekrar})
    adaylar.sort(key=lambda x: (not x["tekrar"], x["izlenme"]))
    return {"baslangic": baslangic, "adaylar": adaylar}


def alan_agirliklari(alanlar):
    """Son 30 gunde yayinlanmis (48+ saatlik) Bidik videolarinin ortalama izlenmesine gore agirlik.
    Verisi olmayan alan ortalama agirlik alir (yeni konular da denensin). Agirlik 0.6 - 2.0 arasi."""
    veri = _oku()
    simdi = datetime.datetime.now().astimezone()
    toplam = {}
    for k in veri.get("videolar", {}).values():
        t = _tarih(k.get("yayin"))
        if not k.get("bidik") or not t or not (simdi - datetime.timedelta(days=30) <= t <= simdi - datetime.timedelta(hours=48)):
            continue
        toplam.setdefault(k.get("alan", ""), []).append(_son(k)["izlenme"])
    ort = {a: sum(v) / len(v) for a, v in toplam.items() if v}
    if not ort:
        return {a: 1.0 for a in alanlar}
    genel = sum(ort.values()) / len(ort) or 1
    return {a: max(0.6, min(2.0, ort.get(a, genel) / genel)) for a in alanlar}


def en_iyi_basliklar(adet=3):
    """Senaryo yazarina ilham: son 30 gunun en cok izlenen Bidik basliklari."""
    v = rapor("aylik")["en_cok"]
    return [x["baslik"] for x in v if x["bidik"]][:adet]
