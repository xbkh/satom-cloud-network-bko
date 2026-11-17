"""GRE IPv4 minimal pour les liens point à point isolés du lab."""
import errno
import fcntl
import os
import selectors
import socket
import struct
import sys
import time

name, outer_local, outer_peer = sys.argv[1:]
tun = os.open("/dev/net/tun", os.O_RDWR)
fcntl.ioctl(tun, 0x400454CA, struct.pack("16sH", name.encode(), 0x1001))
raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_GRE)
raw.bind((outer_local, 0))
selector = selectors.DefaultSelector()
selector.register(tun, selectors.EVENT_READ)
selector.register(raw, selectors.EVENT_READ)
header = b"\x00\x00\x08\x00"
while True:
    for ready, _ in selector.select():
        try:
            if ready.fd == tun:
                packet = os.read(tun, 65535)
                if packet:
                    raw.sendto(header + packet, (outer_peer, 0))
            else:
                packet, peer = raw.recvfrom(65535)
                ihl = (packet[0] & 15) * 4
                if peer[0] == outer_peer and packet[ihl:ihl + 4] == header:
                    os.write(tun, packet[ihl + 4:])
        except OSError as error:
            if error.errno not in (errno.EIO, errno.ENETDOWN, errno.ENETUNREACH, errno.EINVAL):
                raise
            time.sleep(0.05)
