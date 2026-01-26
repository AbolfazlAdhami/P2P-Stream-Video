import struct


def pack(data: bytes) -> bytes:
    return struct.pack('!I', len(data))+data


def unpack(sock):
    raw_len = sock.recv(4)
    if not raw_len:
        return None
    size = struct.unpack('!I', raw_len)[0]
    data = b""
    while len(data) < size:
        data += sock.recv(size-len(data))
    return data
