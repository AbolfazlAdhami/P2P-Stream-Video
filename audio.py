import pyaudio
from packet_loss import should_drop
from config import AUDIO_CHUNK, AUDIO_RATE, LOSS_THRESHOLD


class Audio:
    def __init__(self):
        self.audio = pyaudio.PyAudio()

        self.stream_in = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK
        )

        self.stream_out = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=AUDIO_RATE,
            output=True,
            frames_per_buffer=AUDIO_CHUNK
        )

    def send(self, sock, addr):
        data = self.stream_in.read(AUDIO_CHUNK, exception_on_overflow=False)
        if not should_drop(LOSS_THRESHOLD):
            sock.sendto(data, addr)

    def receive(self, sock):
        data, _ = sock.recvfrom(AUDIO_CHUNK*2)
        self.stream_out.write(data)
