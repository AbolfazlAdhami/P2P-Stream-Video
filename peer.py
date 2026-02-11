import socket
import cv2
import numpy as np
import pyaudio
import threading
import time
import struct
import argparse
from collections import deque

# تنظیمات
TCP_PORT = 5000      # برای کنترل و چک اتصال
UDP_VIDEO_PORT = 5001
UDP_AUDIO_PORT = 5002

RESOLUTIONS = [(640, 480, 25), (424, 240, 20), (320, 180, 15)]
CURRENT_RES_IDX = 0

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 22050
CHUNK = 1024

JPEG_QUALITY = 75  # 0-100, کمتر = حجم کمتر اما کیفیت پایین‌تر


class Peer:
    def __init__(self, peer_ip=None, mode="both"):
        self.peer_ip = peer_ip
        self.mode = mode
        self.running = True

        # آمار
        self.sent_bytes = 0
        self.recv_bytes = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0
        self.latency_samples = deque(maxlen=20)

        print("\n" + "="*60)
        print("   پروژه P2P استریم ویدیو و صدا - نسخه دیباگ")
        print("   حالت:", mode.upper())
        if peer_ip:
            print("   Peer مقابل:", peer_ip)
        print("   پورت‌ها → TCP: {} | UDP Video: {} | UDP Audio: {}".format(
            TCP_PORT, UDP_VIDEO_PORT, UDP_AUDIO_PORT))
        print("="*60 + "\n")

    def print_stats(self):
        while self.running:
            time.sleep(5)
            avg_latency = sum(self.latency_samples) / \
                len(self.latency_samples) if self.latency_samples else 0
            packet_loss_rate = (
                self.packets_lost / self.packets_sent * 100) if self.packets_sent > 0 else 0

            print("\n" + "-"*50)
            print(f"📊 آمار لحظه‌ای:")
            print(
                f"  ارسال شده: {self.sent_bytes / 1024 / 1024:.2f} MB | پکت‌ها: {self.packets_sent}")
            print(
                f"  دریافت شده: {self.recv_bytes / 1024 / 1024:.2f} MB | پکت‌ها: {self.packets_received}")
            print(
                f"  پکت لاست تقریبی: {self.packets_lost} ({packet_loss_rate:.1f}%)")
            print(f"  تأخیر میانگین: {avg_latency:.1f} ms")
            print(f"  رزولوشن فعلی: {RESOLUTIONS[CURRENT_RES_IDX][:2]}")
            print("-"*50)

    def check_connection(self, tcp_sock):
        seq = 0
        while self.running:
            try:
                start = time.time()
                tcp_sock.send(struct.pack("!I", seq))
                data = tcp_sock.recv(8)
                if len(data) == 8:
                    recv_seq, timestamp = struct.unpack("!II", data)
                    latency = (time.time() - timestamp) * 1000
                    self.latency_samples.append(latency)

                    # تنظیم رزولوشن
                    if len(self.latency_samples) > 5:
                        avg = sum(self.latency_samples) / \
                            len(self.latency_samples)
                        if avg > 180 and CURRENT_RES_IDX < len(RESOLUTIONS)-1:
                            global CURRENT_RES_IDX
                            CURRENT_RES_IDX += 1
                            print(
                                f"[RES ↓] تأخیر بالا → رزولوشن جدید: {RESOLUTIONS[CURRENT_RES_IDX][:2]}")
                        elif avg < 90 and CURRENT_RES_IDX > 0:
                            CURRENT_RES_IDX -= 1
                            print(
                                f"[RES ↑] اتصال خوب → رزولوشن جدید: {RESOLUTIONS[CURRENT_RES_IDX][:2]}")

                seq += 1
                time.sleep(1.5)
            except Exception as e:
                print(f"[TCP چک] خطا: {e}")
                time.sleep(2)

    def send_video(self):
        cap = cv2.VideoCapture(0)
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        print("[VIDEO SEND] شروع ارسال ویدیو...")

        while self.running:
            try:
                ret, frame = cap.read()
                if not ret:
                    print("[VIDEO] نمی‌تونم از وب‌کم بخونم!")
                    time.sleep(1)
                    continue

                w, h, _ = RESOLUTIONS[CURRENT_RES_IDX]
                frame = cv2.resize(frame, (w, h))

                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                data = buffer.tobytes()

                # اضافه کردن هدر ساده: sequence + اندازه
                header = struct.pack("!II", self.packets_sent, len(data))
                packet = header + data

                udp_sock.sendto(packet, (self.peer_ip, UDP_VIDEO_PORT))

                self.sent_bytes += len(packet)
                self.packets_sent += 1

                time.sleep(1 / RESOLUTIONS[CURRENT_RES_IDX][2])  # کنترل fps
            except Exception as e:
                print(f"[VIDEO SEND] خطا: {e}")
                time.sleep(1)

        cap.release()
        udp_sock.close()

    def receive_video(self):
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(('', UDP_VIDEO_PORT))
        udp_sock.settimeout(0.5)

        print("[VIDEO RECV] منتظر دریافت ویدیو...")

        while self.running:
            try:
                data, _ = udp_sock.recvfrom(65507)
                if len(data) < 8:
                    continue

                seq, size = struct.unpack("!II", data[:8])
                jpeg_data = data[8:8+size]

                self.recv_bytes += len(data)
                self.packets_received += 1

                nparr = np.frombuffer(jpeg_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    cv2.imshow('دریافت ویدیو', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.running = False
                else:
                    print("[VIDEO] فریم نامعتبر دریافت شد")

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[VIDEO RECV] خطا: {e}")

        cv2.destroyAllWindows()
        udp_sock.close()

    def send_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        print("[AUDIO SEND] شروع ارسال صدا...")

        while self.running:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                udp_sock.sendto(data, (self.peer_ip, UDP_AUDIO_PORT))
                self.sent_bytes += len(data)
            except Exception as e:
                print(f"[AUDIO SEND] خطا: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()
        udp_sock.close()

    def receive_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        output=True)
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(('', UDP_AUDIO_PORT))

        print("[AUDIO RECV] منتظر دریافت صدا...")

        while self.running:
            try:
                data, _ = udp_sock.recvfrom(8192)
                stream.write(data)
                self.recv_bytes += len(data)
            except:
                continue

        stream.stop_stream()
        stream.close()
        p.terminate()
        udp_sock.close()

    def run(self):
        if self.mode in ["send", "both"] and not self.peer_ip:
            print("خطا: برای ارسال یا both باید --peer_ip مشخص کنید!")
            return

        threads = []
        tcp_sock = None

        # شروع threadهای اصلی
        if self.mode in ["send", "both"]:
            threads.append(threading.Thread(
                target=self.send_video, daemon=True))
            threads.append(threading.Thread(
                target=self.send_audio, daemon=True))

        if self.mode in ["receive", "both"]:
            threads.append(threading.Thread(
                target=self.receive_video, daemon=True))
            threads.append(threading.Thread(
                target=self.receive_audio, daemon=True))

        # TCP برای چک اتصال
        if self.mode in ["send", "both"]:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                tcp_sock.connect((self.peer_ip, TCP_PORT))
                print("[TCP] اتصال کنترل برقرار شد")
            except Exception as e:
                print(f"[TCP] نمی‌توان به peer وصل شد: {e}")

        elif self.mode == "receive":
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('', TCP_PORT))
            server.listen(1)
            print("[TCP] منتظر اتصال peer برای کنترل...")
            tcp_sock, addr = server.accept()
            print(f"[TCP] peer وصل شد: {addr}")

        if tcp_sock:
            threads.append(threading.Thread(
                target=self.check_connection, args=(tcp_sock,), daemon=True))

        # آمار
        threads.append(threading.Thread(target=self.print_stats, daemon=True))

        for t in threads:
            t.start()

        try:
            while self.running:
                time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n[خروج] در حال بستن...")
            self.running = False

        for t in threads:
            t.join(timeout=1.5)

        if tcp_sock:
            tcp_sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P Streaming Debug Version")
    parser.add_argument(
        "--mode", choices=["send", "receive", "both"], default="both")
    parser.add_argument(
        "--peer_ip", help="IP peer مقابل (برای send/both لازم است)")
    args = parser.parse_args()

    peer = Peer(peer_ip=args.peer_ip, mode=args.mode)
    peer.run()
