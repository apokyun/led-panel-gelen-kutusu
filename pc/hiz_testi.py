"""LED panel Bluetooth hız testi (Windows 11).

Panele bağlanır, 15 saniye normal bağlantıyla, 15 saniye de Windows 11'in
"yüksek hız" (ThroughputOptimized) bağlantı ayarıyla kayan bir gökkuşağı
gönderir ve iki durumda saniyede kaç kare gittiğini yazar.

Kurulum (bir kez):
    py -m pip install bleak

Çalıştırma:
    py hiz_testi.py

Önce tarayıcıdaki LED Panel Atölyesi'ni ve telefondaki panel uygulamasını kapat:
panel aynı anda tek bağlantı kabul eder.
"""
import asyncio
import colorsys
import sys
import time
from collections import deque

from bleak import BleakClient, BleakScanner

SERVICE = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE = "0000fa02-0000-1000-8000-00805f9b34fb"
NOTIFY = "0000fa03-0000-1000-8000-00805f9b34fb"
PANELS = {0x00: (64, 64), 0x80: (64, 64), 0x81: (32, 32), 0x82: (32, 16), 0x83: (64, 16), 0x84: (96, 16),
          0x85: (64, 20), 0x86: (128, 32), 0x87: (144, 16), 0x88: (192, 16), 0x89: (48, 24), 0x8a: (64, 32),
          0x8b: (96, 32), 0x8c: (128, 32), 0x8d: (96, 32), 0x8e: (160, 32), 0x8f: (192, 32), 0x94: (16, 16)}
TEST_SECONDS = 15


# ---------- protokol: index.html'deki Core ile birebir aynı ----------
def u16(n):
    return [n & 255, (n >> 8) & 255]


def u32(n):
    return [n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >> 24) & 255]


def cmd(c, payload):
    return bytes(u16(4 + len(payload)) + u16(c) + list(payload))


def handshake(t):
    return cmd(0x8001, [t.tm_hour, t.tm_min, t.tm_sec, 0])


def diy(mode):
    return cmd(0x0104, [mode])


def frame_size_for(code):
    return 12288 if code in (0x00, 0x80, 0x81) else 4096


def live_frames(rgb, frame_size):
    total, out = len(rgb), []
    for i, off in enumerate(range(0, total, frame_size)):
        chunk = rgb[off:off + frame_size]
        head = u16(9 + len(chunk)) + [0, 0, 0 if i == 0 else 2] + u32(total)
        out.append(bytes(head) + bytes(chunk))
    return out


def split_writes(p, size):
    return [p[o:o + size] for o in range(0, len(p), size)]


def rainbow(w, h, t):
    out = bytearray(w * h * 3)
    for y in range(h):
        for x in range(w):
            r, g, b = colorsys.hsv_to_rgb(((x + y) * 0.03 + t * 0.6) % 1.0, 1.0, 0.6)
            i = (y * w + x) * 3
            out[i], out[i + 1], out[i + 2] = int(r * 255), int(g * 255), int(b * 255)
    return bytes(out)


# ---------- Windows 11 bağlantı ayarları ----------
def winrt_device(client):
    return getattr(client._backend, "_requester", None)


def conn_info(client):
    dev = winrt_device(client)
    try:
        p = dev.get_connection_parameters()
        return f"aralık {p.connection_interval * 1.25:.1f} ms, gecikme {p.connection_latency}"
    except Exception as e:
        return f"okunamadı ({type(e).__name__})"


def request_fast(client):
    dev = winrt_device(client)
    if dev is None:
        return None, "Windows Bluetooth nesnesine ulaşılamadı"
    P = None
    for mod in ("winrt.windows.devices.bluetooth", "bleak_winrt.windows.devices.bluetooth"):
        try:
            P = __import__(mod, fromlist=["BluetoothLEPreferredConnectionParameters"]).BluetoothLEPreferredConnectionParameters
            break
        except Exception:
            pass
    if P is None:
        return None, "winrt Bluetooth modülü bulunamadı"
    try:
        req = dev.request_preferred_connection_parameters(P.throughput_optimized)
        return req, f"istek durumu: {req.status}"
    except AttributeError:
        return None, "bu Windows sürümü bağlantı ayarı isteğini desteklemiyor (Windows 11 22H2+ gerekir)"
    except Exception as e:
        return None, f"istek başarısız: {e}"


# ---------- gönderim (sayfadaki uyarlanır pencereyle aynı mantık) ----------
class Sender:
    def __init__(self, client, w, h, code):
        self.client, self.w, self.h, self.code = client, w, h, code
        self.inflight, self.window, self.ok, self.miss, self.no_ack = deque(), 2, 0, 0, False
        self.write_size = max(20, min(509, (client.mtu_size or 23) - 3))

    def on_ack(self):
        if self.inflight:
            self.inflight.popleft()
        self.miss = 0
        self.ok += 1
        if self.ok >= 40 and self.window < 5:
            self.window += 1
            self.ok = 0

    async def send(self, packet):
        for part in split_writes(packet, self.write_size):
            await self.client.write_gatt_char(WRITE, part, response=False)

    async def run(self, seconds):
        frames, t0, max_window = 0, time.perf_counter(), self.window
        while time.perf_counter() - t0 < seconds:
            rgb = rainbow(self.w, self.h, time.perf_counter())
            for f in live_frames(rgb, frame_size_for(self.code)):
                while not self.no_ack and len(self.inflight) >= self.window:
                    if time.perf_counter() - self.inflight[0] > 0.4:
                        self.inflight.popleft()
                        self.ok = 0
                        self.window = max(1, self.window - 1)
                        self.miss += 1
                        if self.miss >= 4:
                            self.no_ack = True
                            self.inflight.clear()
                    else:
                        await asyncio.sleep(0.003)
                await self.send(f)
                if not self.no_ack:
                    self.inflight.append(time.perf_counter())
            if self.no_ack:
                await asyncio.sleep(0.045)
            frames += 1
            max_window = max(max_window, self.window)
        return frames / (time.perf_counter() - t0), max_window


async def main():
    print("Panel aranıyor (adı LED_BLE ile başlayan cihaz)...")
    dev = await BleakScanner.find_device_by_filter(lambda d, ad: (d.name or "").startswith("LED_BLE"), timeout=12)
    if not dev:
        print("Panel bulunamadı. Panel açık mı, tarayıcı sayfası ve telefon uygulaması kapalı mı?")
        return
    print(f"Bulundu: {dev.name} ({dev.address}). Bağlanılıyor...")
    async with BleakClient(dev, timeout=20) as client:
        hs = asyncio.get_running_loop().create_future()
        sender = None

        def notify(_, data: bytearray):
            if len(data) < 5:
                return
            c = data[2] | (data[3] << 8)
            if c == 0x8001 and not hs.done():
                hs.set_result(data[4])
            elif c == 0x0000 and sender:
                sender.on_ack()

        await client.start_notify(NOTIFY, notify)
        await client.write_gatt_char(WRITE, handshake(time.localtime()), response=False)
        try:
            code = await asyncio.wait_for(hs, 3)
        except asyncio.TimeoutError:
            code = 0x82
            print("El sıkışma yanıtı gelmedi, 32x16 varsayıldı.")
        w, h = PANELS.get(code, (32, 16))
        print(f"Panel: {w}x{h} (kod 0x{code:02x}), MTU {client.mtu_size}")
        await client.write_gatt_char(WRITE, diy(1), response=False)
        await asyncio.sleep(0.3)

        sender = Sender(client, w, h, code)
        print(f"\n1) Normal bağlantı · {conn_info(client)}")
        print(f"   {TEST_SECONDS} sn gönderiliyor...")
        fps1, win1 = await sender.run(TEST_SECONDS)
        print(f"   SONUÇ: {fps1:.1f} kare/sn (en çok {win1} kare yolda{', onaysız' if sender.no_ack else ''})")

        req, msg = request_fast(client)
        print(f"\n2) Yüksek hız modu isteniyor · {msg}")
        await asyncio.sleep(2)
        print(f"   {conn_info(client)}")
        sender = Sender(client, w, h, code)
        print(f"   {TEST_SECONDS} sn gönderiliyor...")
        fps2, win2 = await sender.run(TEST_SECONDS)
        print(f"   SONUÇ: {fps2:.1f} kare/sn (en çok {win2} kare yolda{', onaysız' if sender.no_ack else ''})")

        await client.write_gatt_char(WRITE, diy(0), response=False)
        await asyncio.sleep(0.3)
        if req is not None:
            try:
                req.close()
            except Exception:
                pass

    print(f"\nÖZET: normal {fps1:.1f} kare/sn  ->  yüksek hız {fps2:.1f} kare/sn")
    print("Bu çıktının tamamını kopyalayıp Claude'a gönder.")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Bu test Windows 11 için yazıldı; diğer sistemlerde yüksek hız adımı çalışmaz.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    input("\nKapatmak için Enter'a bas...")
