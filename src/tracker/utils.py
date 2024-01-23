import struct
import socket
from typing import Tuple, List, Any, Union


def format_announce_response(data: bytes, ip_version: str, format_string: str = '>4s4sIII', header_length: int = 20) -> Tuple[List[Any], Union[None, str]]:
    """
    formats the announce response
    :param header_length: length of announce header, default is 20 bytes
    :param format_string: format the first 20 bytes, default is format for udp trackers
    :param data: binary data received from tracker
    :param ip_version: ip_version of tracker
    :return: [0]: list of peers addresses (ip, port) [1]: unpacked entire data
    """
    INDEX_FROM_HEADER = header_length // 4  # min index from where the header ends

    # unpack data
    if ip_version == 'v4':
        dynamic_format = '4sH'  # format of ipv4 and port
        n = (len(data) - header_length) // 6
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        # format ipv4 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + INDEX_FROM_HEADER] = socket.inet_ntop(socket.AF_INET, unpacked_data[i + INDEX_FROM_HEADER])

    else:  # ip_version == 'v6'
        dynamic_format = '16sH'
        n = (len(data) - header_length) // 18
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        # format ipv6 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + INDEX_FROM_HEADER] = socket.inet_ntop(socket.AF_INET6, unpacked_data[i + INDEX_FROM_HEADER])

    # convert peers addresses to a separate list
    peers = []
    for i in range(0, n, 2):
        peers.append((unpacked_data[i + INDEX_FROM_HEADER], unpacked_data[i + INDEX_FROM_HEADER + 1]))

    return peers, unpacked_data
