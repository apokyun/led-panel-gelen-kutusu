#!/usr/bin/env python3
"""Gelen kutusu çizim aracı.

Kullanım:
  python3 tools/cizim.py                 # tüm çizimleri doğrula, inbox/index.json'u yeniden yaz
  python3 tools/cizim.py png DOSYA.json  # çizimin PNG önizlemesini /tmp/onizleme/ altına yaz
  python3 tools/cizim.py png --hepsi     # hepsinin önizlemesi

Çizim dosyası (inbox/cizimler/<kimlik>.json):
{
  "title": "Kalp",
  "created": "2026-11-14T02:10:00+03:00",
  "w": 16, "h": 16,
  "palette": { "R": "#ff3040", "W": "#ffffff" },
  "frames": [ ["................", "..RR....RR......", ...] ],
  "delay": 200,              # kare süresi (ms), isteğe bağlı
  "delays": [600, 120],      # kare başına süre (ms), isteğe bağlı, delay'i ezer
  "note": "isteğe bağlı açıklama"
}
'.' ve ' ' her zaman boş (sönük) pikseldir.
"""
import hashlib
import json
import os
import re
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "inbox", "cizimler")
INDEX = os.path.join(ROOT, "inbox", "index.json")
MAX_SIDE, MAX_FRAMES = 64, 256
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def hata(yol, msg):
    raise SystemExit(f"HATA {os.path.relpath(yol, ROOT)}: {msg}")


def yukle(yol):
    with open(yol, "rb") as f:
        raw = f.read()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        hata(yol, f"JSON bozuk: {e}")
    kimlik = os.path.splitext(os.path.basename(yol))[0]
    if not ID.match(kimlik):
        hata(yol, "dosya adı küçük harf, rakam ve '-' olmalı")
    for k in ("title", "w", "h", "palette", "frames"):
        if k not in d:
            hata(yol, f"'{k}' alanı yok")
    w, h = d["w"], d["h"]
    if not (isinstance(w, int) and isinstance(h, int) and 1 <= w <= MAX_SIDE and 1 <= h <= MAX_SIDE):
        hata(yol, f"w ve h 1..{MAX_SIDE} arası tam sayı olmalı")
    pal = d["palette"]
    if not isinstance(pal, dict):
        hata(yol, "palette bir nesne olmalı")
    for ch, col in pal.items():
        if len(ch) != 1 or ch in ". ":
            hata(yol, f"renk anahtarı tek karakter olmalı ve '.' olamaz: {ch!r}")
        if not (isinstance(col, str) and HEX.match(col)):
            hata(yol, f"renk #rrggbb olmalı: {ch} = {col!r}")
    fr = d["frames"]
    if not (isinstance(fr, list) and 1 <= len(fr) <= MAX_FRAMES):
        hata(yol, f"frames 1..{MAX_FRAMES} kare içermeli")
    for i, f in enumerate(fr):
        if not (isinstance(f, list) and len(f) == h):
            hata(yol, f"kare {i + 1}: {h} satır olmalı, {len(f) if isinstance(f, list) else '?'} var")
        for j, row in enumerate(f):
            if not isinstance(row, str) or len(row) != w:
                hata(yol, f"kare {i + 1} satır {j + 1}: {w} karakter olmalı, {len(row) if isinstance(row, str) else '?'} var")
            for ch in row:
                if ch not in ". " and ch not in pal:
                    hata(yol, f"kare {i + 1} satır {j + 1}: palette'te olmayan karakter {ch!r}")
    if "delay" in d and not (isinstance(d["delay"], int) and 20 <= d["delay"] <= 10000):
        hata(yol, "delay 20..10000 ms olmalı")
    if "delays" in d:
        ds = d["delays"]
        if not (isinstance(ds, list) and len(ds) == len(fr) and all(isinstance(x, int) and 20 <= x <= 10000 for x in ds)):
            hata(yol, "delays, kare sayısı kadar 20..10000 ms değer içermeli")
    return kimlik, d, raw


def index_yaz():
    os.makedirs(DIR, exist_ok=True)
    items = []
    for ad in sorted(os.listdir(DIR)):
        if not ad.endswith(".json"):
            continue
        yol = os.path.join(DIR, ad)
        kimlik, d, raw = yukle(yol)
        items.append({
            "id": kimlik,
            "title": d["title"],
            "file": "inbox/cizimler/" + ad,
            "rev": hashlib.sha1(raw).hexdigest()[:10],
            "w": d["w"], "h": d["h"],
            "frames": len(d["frames"]),
            "created": d.get("created", ""),
        })
    items.sort(key=lambda it: (it["created"], it["id"]), reverse=True)
    out = {"version": 1, "items": items}
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{len(items)} çizim doğrulandı, inbox/index.json yazıldı.")
    for it in items:
        print(f"  {it['created'][:16]:16}  {it['id']:32}  {it['w']}x{it['h']}  {it['frames']} kare  {it['title']}")


def png(d, yol, cell=14):
    w, h, pal = d["w"], d["h"], d["palette"]
    rgb = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in pal.items()}
    frames = d["frames"]
    gap = 6
    W = len(frames) * (w * cell) + (len(frames) - 1) * gap
    H = h * cell
    img = [[(40, 40, 46)] * W for _ in range(H)]
    for fi, f in enumerate(frames):
        ox = fi * (w * cell + gap)
        for y in range(h):
            for x in range(w):
                c = rgb.get(f[y][x])
                for yy in range(cell):
                    for xx in range(cell):
                        edge = xx == 0 or yy == 0
                        img[y * cell + yy][ox + x * cell + xx] = (8, 10, 14) if edge else (c or (22, 24, 30))
    rows = b"".join(b"\x00" + bytes(v for px in r for v in px) for r in img)
    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
    with open(yol, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    return yol


def main(argv):
    if not argv:
        index_yaz()
        return
    if argv[0] == "png":
        os.makedirs("/tmp/onizleme", exist_ok=True)
        hedefler = [os.path.join(DIR, a) for a in sorted(os.listdir(DIR)) if a.endswith(".json")] if argv[1:] == ["--hepsi"] else argv[1:]
        for yol in hedefler:
            kimlik, d, _ = yukle(os.path.abspath(yol))
            print(png(d, f"/tmp/onizleme/{kimlik}.png"))
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
