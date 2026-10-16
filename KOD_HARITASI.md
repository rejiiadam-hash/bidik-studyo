# Bıdık Stüdyo – KOD HARİTASI (Claude için)
Amaç: dosyaları baştan sona OKUMADAN doğru yere gitmek. Önce burayı oku, sonra
`grep -n "isim" program/dosya` ile ilgili yeri bul, `Read` ile SADECE o satır aralığını aç (offset/limit).
Satır numaraları yaklaşık (v1.12.0); kaydıysa grep ile yeniden bul.

## Çalışma kuralları (kredi tasarrufu)
- Büyük dosyaları (panel.html 967, panel.py 964, arka_planlar.py 731, video_uret.py 601) ASLA bütün okuma.
- Yeni özellik = yeni oturum + bu harita + PROJE_OZETI.md. Test için ekran görüntüsünü azalt.
- Günlük iş Sonnet 5.5; büyük/karmaşık iş Opus 5.5 (Deniz'e hatırlat).
- Yayın: `araclar/manifest_yap.py <sürüm> "not"` → commit → onay dalı → ONAY gelince main'e ff-only.

## Akış (kim kimi çağırır)
senaryo_motoru (Gemini yazar→editör→denetim) → senaryolar/bekleyen/*.json → panel (onay/düzenle/ertele)
→ video_uret.uret() (ses: edge-tts Ahmet; çizim: karakter+kostumler+arka_planlar+girisler; ffmpeg)
→ videolar/<gün>/*.mp4+json → panel.paylas → youtube_yukle.yukle. analiz.py kanal istatistiği çeker,
senaryo_motoru.alan_sec ağırlık olarak kullanır. github_kanal.py güncellemeyi GitHub'dan indirir.

## program/ dosyaları
- **ortak.py** (114): ayarlar()/ayar_kaydet (varsayılanlar burada), hashtagler/etiket_listesi, ffmpeg(), komut().
- **senaryo_motoru.py** (511): model_sec, gemini_json (istek+yeniden deneme), alan_sec(194, analiz ağırlıklı),
  yazar_istemi(216, KONU/ÜSLUP KURALLARI BURADA), editor_istemi(271), denetle/denetim_isle (yazım+bilgi kapısı, 295-394),
  calistir(394, ana akış), bekleyen_dosyalar/ertelenen_dosyalar(495-500), hafiza.
- **video_uret.py** (601): dogrula(45), _ses_uret(123, edge-tts tekrar turları), seslendir(172), altyazi(220),
  bilgi_karti(258), son_cagri(332), **uret(377)** = sahne döngüsü; arka plan/giriş/kostüm burada bağlanır.
- **karakter.py** (295): ciz_bidik(72, ifade/ağız/kostum parametreleri), kare(286).
- **kostumler.py** (352): 11 kostüm fonksiyonu (asci…doktor), KOSTUMLER, ust_boy(321), **kostum_sec(343)** alan→kostüm.
- **arka_planlar.py** (731): 12 tema fonksiyonu (uzay, burclar, hayvanlar, yemek, bilim, insan, tarih, psikoloji,
  teknoloji, cografya, cocuk, genel), tema_bul(693), ciz(699), secim(715, tekrar önleme: arka_gecmis.json).
- **girisler.py** (239): 15 açılış; durum(66, hareket), arka(111)/on(121, çizim), secim(224), TEMA_GIRIS/ADLAR üstte.
- **analiz.py** (220): cek(51, YouTube Data API), rapor(144), alan_agirliklari(199), en_iyi_basliklar(217), baslat/_dongu.
- **youtube_yukle.py** (203): OAuth(_servis 67, bagla 133), yukle(153), sil(113).
- **github_kanal.py** (144): kontrol_et(71, surum.json+sha256), baslat(137), 30 dk döngü.
- **telefon.py** (142): Tailscale (tailscale_ac 69), otomatik_baslat, uyku_engelle.
- **uygulama.py** (196): pencere/başlatıcı (pywebview/Edge), --arka modu.
- **panel.py** (~1030; kare_sayfasi = ana sayfa Bidik sprite sayfasi, /bidik-kareler/<kostum>.png): HTTP sunucu. Yardımcılar 30-90; durum 91; oturum/şifre 142-237; güncelleme 238-335;
  senaryo işlemleri kaydet 348, _video_yap 371, yeniden_uret 384, _yazim_kapisi 416, onayla 455,
  ertelenenler/ertele/geri_getir 481-512, reddet 513, paylas 525, video_sil 561, destek 595,
  telefon_islem 627, kostum_resmi 648, analiz_* 666, ayar 692, **ISLEMLER dict 735** (yeni endpoint buraya),
  Isleyici 743 (GET/POST, kapı), hazirla 914, main 951.
- **panel.html** (~1090): Ana sayfa sahnesi: #s-anasayfa + bidikDongu/BIDIK (JS), .sahne CSS. CSS üstte; JS ~460'tan: sekme 473, yenile 488, senaryoKarti 514, videoKarti 557,
  gunlereBol 608, admin 623, kalpler 640, ytCiz 647, ciz 700, formdanSenaryo 725, kaydet/onayla/ertele 735-745,
  ertelenenCiz 747, yenidenUret 767, paylasAc 825, analizYukle 864, telCiz 913, ayarKaydet 947.

## PC tarafı (C:\Users\PC1\Desktop\BIDIK)
ayarlar.json, senaryolar/{bekleyen,ertelenen,...}, videolar/<gün>/, analiz.json, guncelleme/ (GitHub'dan gelir), PROJE_OZETI.md.

## Sık işler → nereye bak
- Yeni konu alanı: ortak.py (alanlar) + panel.py hazirla (alanlar_v2) + kostumler.kostum_sec + arka_planlar.tema_bul + analiz.ALAN_ADI + senaryo_motoru.yazar_istemi.
- Yeni kostüm: kostumler.py (fonksiyon + KOSTUMLER) + kostum_sec.
- Yeni arka plan/giriş: arka_planlar.TEMALAR / girisler.GENEL,TEMA_GIRIS,ADLAR.
- Yeni buton/endpoint: panel.html JS + panel.py fonksiyon + ISLEMLER.
- Sesle ilgili sorun: video_uret._ses_uret.
