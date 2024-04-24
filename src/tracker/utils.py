import src.app_data.db_utils as db_utils
from src.geoip.utils import calc_distance, get_info
import struct
import socket
from typing import Tuple, List, Any, Union
from math import inf as INF


def format_peers_list(peers: List[Tuple[str, int]], my_ip: str) -> List[Tuple[Tuple[str, int], None, None]]:
    """
    formats the peers' list received from the trackers
    Note: blocking function!
    :param peers: peers list from a trackers
    :param my_ip: my public ip for geolocation calculations
    :return: formatted peer list: [0]: address [1]: geolocation info [2]: distance from me
    """

    # some formatting
    for i in range(len(peers)):
        peers[i] = peers[i], (get_info(peers[i][0])), calc_distance(peers[i][0], my_ip)

    # remove banned peers
    database = db_utils.BannedPeersDB()
    peers = list(filter(lambda x: not database.find_ip(x[0][0]), peers))

    # remove peers from banned countries
    banned_list = db_utils.get_banned_countries()
    peers = list(filter(lambda x: x[1][1] if x[1] is not None else '' not in banned_list, peers))

    # remove peers with distance 0 (could be me)
    filtered_peers = list(filter(lambda x: x[2] > 0 if x[2] is not None else True, peers))

    # sort by distance
    sorted_peers = sorted(filtered_peers, key=lambda x: x[2] if x[2] is not None else INF)

    # new peer structure: [0]: address. [1]: city, country, latitude, longitude. [2]: distance from me
    return sorted_peers


def format_announce_response(data: bytes, ip_version: str, format_string: str = '>IIIII', header_length: int = 20) -> Tuple[List[Tuple[str, int]], int]:
    """
    formats the announce response
    :param header_length: length of announce header, default is 20 bytes
    :param format_string: format the first 20 bytes, default is format for udp trackers
    :param data: binary data received from tracker
    :param ip_version: ip_version of tracker
    :return: [0]: list of peers addresses (ip, port) [1]: interval
    """
    INDEX_FROM_HEADER = header_length // 4  # min index from where the header ends

    # unpack data
    if ip_version == 'v4':
        dynamic_format = '4sH'  # format of ipv4 and port
        n = (len(data) - header_length) // 6
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        interval = unpacked_data[2]
        # format ipv4 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + INDEX_FROM_HEADER] = socket.inet_ntop(socket.AF_INET, unpacked_data[i + INDEX_FROM_HEADER])

    else:  # ip_version == 'v6'
        dynamic_format = '16sH'
        n = (len(data) - header_length) // 18
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        interval = unpacked_data[2]
        # format ipv6 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + INDEX_FROM_HEADER] = socket.inet_ntop(socket.AF_INET6, unpacked_data[i + INDEX_FROM_HEADER])

    # convert peers addresses to a separate list
    peers = []
    for i in range(0, n, 2):
        peers.append((unpacked_data[i + INDEX_FROM_HEADER], unpacked_data[i + INDEX_FROM_HEADER + 1]))

    return peers, interval
