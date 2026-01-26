import cv2
import pickle
from packet_loss import should_drop
from config import LOSS_THRESHOLD
import numpy as np


class Video:
    def __init__(self, adaptive):
        self.cap = cv2.VideoCapture(0)
        self.adaptive = adaptive

    def send(self, sock, addr):
        ret, frame = self.cap.read()
        if not ret:
            return
        q = self.adaptive.current()
        frame = cv2.resize(frame, (q["width"], q["height"]))
        encoded = cv2.imencode('.jpg', frame)[1]  # encode video packet

        if should_drop(LOSS_THRESHOLD):
            sock.sendto(pickle.dumps(encoded), addr)

    def receive(self, sock):
        data, _ = sock.recvfrom(65536)
        frame = pickle.loads(data)
        img = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        if img is None:
                return
        cv2.imshow("Peer Video (UDP)", img)
        cv2.waitKey(1)
