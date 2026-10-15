# Bıdık Stüdyo

"Deniz" YouTube kanalı için Bıdık karakterli Shorts üretim uygulamasının program dosyaları.

Bu depo **güncelleme kanalıdır**: bilgisayardaki uygulama 30 dakikada bir `surum.json`'a bakar,
sürüm yükselmişse yalnızca parmak izi (sha256) değişen dosyaları indirir ve panelde
"Yeni güncelleme var" bandını gösterir.

## Yeni sürüm yayınlama
1. `program/` altındaki dosyaları değiştir.
2. `python araclar/manifest_yap.py 1.5.2 "Ne değişti"` → `surum.json` yenilenir.
3. Commit + push (main). `program/surum.txt` depoya konmaz; güncelleyici yazar.

Şifreler, API anahtarları ve YouTube yetkileri (`ayarlar.json`, `client_secret*.json`,
`youtube_token.json`) bu depoya **asla** konmaz.
