import socket
from numpy import int32, int64
import random
from typing import Tuple
import struct


def conn_req() -> Tuple[bytes, int]:
    connection_id = int64(0x41727101980)  # connection_id for connect
    action = int32(0)  # action = connect (0)
    transaction_id = int32(struct.unpack('<i', struct.pack('<I', random.getrandbits(32)))[0])

    data = connection_id.tobytes() + action.tobytes() + transaction_id.tobytes()

    return data, transaction_id


def udp_request(tracker_url: bytes):
    # remove the 'udp://' and '/announce' from address
    tracker_url = tracker_url.decode('utf-8').replace('udp://', '')
    tracker_url = tracker_url.split('/')[0]

    server_address = tracker_url.split(':')[0], int(tracker_url.split(':')[1])

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)

    request, transaction_id = conn_req()
    print(server_address, len(request))

    udp_socket.sendto(request, server_address)

    while True:
        data, server = udp_socket.recvfrom(1024)
        print(data)

