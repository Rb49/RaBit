import socket
import random
from typing import Tuple, List, Union, Any
import struct

__timeouts = (15, 30, 60, 120, 240, 480, 960, 1920, 3840)  # protocol timeouts for udp sockets


def __format_url(tracker_url: str) -> Tuple[str, int]:
    """
    formats an url to proper address
    :param tracker_url: raw tracker url
    :return: (url, port): (str, int)
    """
    # remove the 'udp://' and '/announce' from address
    tracker_url = tracker_url.replace('udp://', '')
    tracker_url = tracker_url.split('/')[0]

    address = tracker_url.split(':')[0], int(tracker_url.split(':')[1])
    return address


def __build_connect_packet() -> bytes:
    """
    generates a udp connect packet
    :return: entire packet data
    """
    format_string = '>QII'
    data = struct.pack(format_string,
                       0x41727101980,  # connect magic number
                       0,  # action - connect
                       random.getrandbits(32))  # random transaction_id
    return data


def __get_connection_id(tracker_address: Tuple[str, int], timeout_list: List[int] = __timeouts) -> Union[bytes, None]:
    """
    gets a connection_id from tracker for announce / scrape
    :param tracker_address: formatted tracker address
    :param timeout_list: list that specifies how much time to wait before retransmission
    :return: bytes: successfully received a connection_id. None: did not receive a connection_id
     | raised exception: something went wrong
    """
    request_data = __build_connect_packet()

    for timeout in timeout_list:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.settimeout(timeout)
            udp_socket.sendto(request_data, tracker_address)

            while True:
                data, server = udp_socket.recvfrom(1024)
                if len(data) >= 16:
                    if data[4:8] == request_data[12:] and data[0:4] == request_data[8:12]:  # same transaction_id and action
                        # if received data passes checks, it's the right packet
                        connection_id = data[8:]
                        udp_socket.close()
                        return connection_id

        except socket.timeout:
            udp_socket.close()
            continue
        except Exception as e:
            udp_socket.close()
            raise e

    return None


def __build_announce_packet(connection_id: bytes, info_hash: bytes, peer_id: bytes, event: int = 0, port: int = 6881) -> bytes:
    """
    generates a udp announce packet
    :param connection_id:
    :param info_hash: info_hash of the torrent file
    :param peer_id: peer_id
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :return:
    """

    format_string = '>8sII20s20sQQQIIIiH'

    data = struct.pack(format_string,
                       connection_id,
                       1,  # action - announce
                       random.getrandbits(32),  # transaction_id
                       info_hash,
                       peer_id,
                       0,  # downloaded
                       0,  # left
                       0,  # uploaded
                       event,
                       0,  # ip address, default is 0
                       random.getrandbits(32),  # random key
                       -1,  # num_want, default is -1 (50)
                       port)

    return data


def __format_announce_response(data: bytes) -> Tuple[List[Tuple[str, int]], List[Any]]:
    """
    formats the announce response
    :param data: binary data received from tracker
    :return: [0]: list of peers addresses (ip, port) [1]: unpacked entire data
    """
    # unpack data
    format_string = ">4s4sIII"  # format of first 20 bytes
    dynamic_format = "4sH"  # format of ip and port
    n = (len(data) - 20) // 6
    format_string += dynamic_format * n
    unpacked_data = list(struct.unpack(format_string, data))

    # format ip addresses from bytes
    for i in range(0, n, 2):
        unpacked_data[i + 5] = '.'.join([str(i) for i in unpacked_data[i + 5]])

    # convert peers addresses to a separate list
    peers = []
    for i in range(0, n, 2):
        peers.append((unpacked_data[i + 5], unpacked_data[i + 6]))

    return peers, unpacked_data


def udp_tracker_announce(tracker_url: str, info_hash: bytes, peer_id: bytes, timeout_list: List[int] = __timeouts) -> Union[Tuple[List[Tuple[str, int]], List[Any]], str]:
    """
    creates an announce request to the tracker and awaits response
    :param timeout_list: list that specifies how much time to wait before retransmission
    :param tracker_url: tracker udp url
    :param info_hash: info_hash
    :param peer_id: peer_id
    :return:
    """
    tracker_address = __format_url(tracker_url)

    # build the announce packet
    connection_id = __get_connection_id(tracker_address, timeout_list)
    if connection_id is None:
        return f"tracker is not reachable"

    request_data = __build_announce_packet(connection_id, info_hash, peer_id)

    for timeout in __timeouts:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.settimeout(timeout)
            udp_socket.sendto(request_data, tracker_address)

            while True:
                data, server = udp_socket.recvfrom(4096)
                if len(data) >= 20:
                    if request_data[12:16] == data[4:8] and request_data[8:12] == data[0:4]:  # same transaction_id and action
                        return __format_announce_response(data)

        except socket.timeout:
            udp_socket.close()
            continue
        except Exception as e:
            udp_socket.close()
            raise e

    return f"tracker is not reachable"
