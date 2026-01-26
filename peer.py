import socket
import threading
from adaptive import AdaptiveController
from video import Video
from audio import Audio


class Peer:
    def __init__(self, port, target_id, target_port):
        self.addr = (target_id, target_port)

        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(('', port))

        self.adaptive = AdaptiveController()
        self.video = Video(self.adaptive)
        self.audio = Audio()

    def start(self):
        threading.Thread(target=self.video_send, daemon=True).start()
        threading.Thread(target=self.video_recv, daemon=True).start()
        threading.Thread(target=self.audio_send, daemon=True).start()
        threading.Thread(target=self.audio_recv, daemon=True).start()

        while True:
            pass

    def video_send(self):
        while True:
            self.video.send(self.udp, self.addr)

    def video_recv(self):
        while True:
            self.video.receive(self.udp)

    def audio_send(self):
        while True:
            self.audio.send(self.udp, self.addr)

    def audio_recv(self):
        while True:
            self.audio.receive(self.udp)
