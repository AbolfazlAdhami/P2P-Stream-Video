import time


class NetworkMonitor:
    def __init__(self):
        self.last_ping = None
        self.latency = 0

    def ping(self, sock):
        start = time.time()
        sock.send(b"PING")
        sock.recv(4)
        self.latency = time.time()-start
        return self.latency
