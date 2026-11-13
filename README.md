# led-panel-gelen-kutusu

LED Panel Atölyesi (`index.html`) ve onun **Gelen kutusu**.

Claude'a sesli ya da yazılı olarak bir piksel çizim tarif edersin; Claude çizimi `inbox/cizimler/` altına JSON olarak yazıp bu depoya iter. Atölye sayfasındaki **Saat ve görsel → Gelen kutusu** sekmesi depoyu birkaç saniyede bir yoklar, yeni çizim gelince listeye ekler, istersen hemen panelde gösterir.

## Kullanım

1. `index.html`'i Android'de Chrome ile aç (Web Bluetooth gerekir). GitHub Pages açıksa `https://apokyun.github.io/led-panel-gelen-kutusu/` adresinden de açılır.
2. Panele bağlan, **Gelen kutusu** sekmesine geç.
3. Yeni çizim geldiğinde "Yeni gelince göster" açıksa panelde kendiliğinden belirir.
4. Bir çizimi **Çizimde düzenle** ile Çizim sekmesine aktarabilir, **Panel hafızasına kaydet** ile panelin 9 yerinden birine kalıcı yükleyebilirsin.

## Çizim biçimi

```json
{
 "title": "Atan kalp",
 "created": "2026-11-14T02:00:00+03:00",
 "w": 16, "h": 16,
 "palette": { "R": "#ff2a3c", "W": "#ffffff" },
 "frames": [ ["................", "..RRRR....RRRR..", "..."] ],
 "delays": [500, 250]
}
```

- `.` sönük piksel; diğer her karakter `palette`'teki bir renk.
- `frames` birden çok kare içerirse animasyon olur. Süre `delay` (tüm kareler) ya da `delays` (kare başına), milisaniye.
- En çok 64×64 piksel ve 64 kare.

Değişiklikten sonra `python3 tools/cizim.py` çalıştır: dosyaları doğrular ve `inbox/index.json`'u yeniden yazar. `python3 tools/cizim.py png --hepsi` PNG önizlemeleri `/tmp/onizleme/` altına çıkarır.
