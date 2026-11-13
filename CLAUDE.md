# LED Panel gelen kutusu

Bu depo iki şey tutar:

- `index.html`: LED Panel Atölyesi (Web Bluetooth ile iPixel uyumlu panele görüntü gönderen tek sayfa). "Gelen kutusu" sekmesi bu depoyu GitHub'dan okur.
- `inbox/`: kullanıcının sesli ya da yazılı tarif ettiği piksel çizimler. Sayfa bunları birkaç saniye içinde görür ve panelde gösterir.

## Kullanıcı bir çizim istediğinde

1. Tarifi piksel çizime çevir. Varsayılan boyut **32×16** (kullanıcının paneli yatay 32×16). Kullanıcı başka boyut ya da dikey panel söylerse ona uy. Küçük bir simge için 16×16 da olur; sayfa ortalar.
2. `inbox/cizimler/YYYYMMDD-HHMM-kisa-ad.json` dosyasını yaz (Türkiye saati, küçük harf, Türkçe karakter yok). Biçim `tools/cizim.py` başındaki açıklamada. Her satır tam `w` karakter, her kare tam `h` satır. `.` sönük piksel. Animasyon istenirse birden çok kare ve `delay`/`delays` (ms) ekle; en çok 64 kare.
3. LED'de koyu renkler zor görünür: doygun, parlak renkler seç; arka planı çoğunlukla `.` bırak.
4. `python3 tools/cizim.py` çalıştır (doğrular, `inbox/index.json`'u yeniden yazar). Sonra `python3 tools/cizim.py png inbox/cizimler/<dosya>.json` ile PNG önizlemeyi üret ve Read ile bakıp çizimi kontrol et; kötüyse düzelt.
5. Çizim commit'lerini doğrudan `main`'e it (sayfa yalnızca `main`'i okur, kullanıcı hızlı görmek istiyor). Commit mesajı: `Gelen kutusu: <başlık>`.
6. Kullanıcıya bir cümleyle neyi çizdiğini söyle ve PNG önizlemeyi gönder.

`index.html` değişiklikleri ise normal kod değişikliğidir: dal aç, PR öner.

## Sayfa nasıl okuyor

- Kesin yol: `api.github.com/repos/<depo>/git/ref/heads/main` ETag ile sorulur. Anahtarsız GitHub saatte 60 soru verir (304'ler de sayılıyor), sayfa kalan hakkı `X-RateLimit-*` başlıklarına bakarak saate yayar. SHA değişince liste ve çizimler `raw.githubusercontent.com/<depo>/<sha>/...` adresinden, önbelleksiz okunur.
- Yedek yol: aradaki 10 sn'lik yoklamalarda ve sınır dolunca `raw.githubusercontent.com/<depo>/main/inbox/index.json` okunur. Sınırsızdır ama GitHub önbelleği yüzünden birkaç dakika gecikebilir; yalnızca yeni çizim ekler.
- Kullanıcı isteğe bağlı bir GitHub anahtarı (fine-grained, public read-only) girerse API 10 sn'de bir sorulur.
