import random
from typing import Tuple, List, Union, Any
import struct
import asyncio
import aioudp
import socket


__timeouts = (15, 30, 60, 120, 240, 480, 960, 1920, 3840)  # protocol timeouts for udp sockets


def __format_url(tracker_url: str) -> Tuple[Tuple[str, int], str]:
    """
    formats an url to proper address and finds out the ip version of the tracker
    :param tracker_url: raw tracker url
    :return: (url, port), ip version (v4 | v6): (str, int), str
    """
    # remove the 'udp://' and '/announce' from address
    tracker_url = tracker_url.replace('udp://', '')
    tracker_url = tracker_url.split('/')[0]

    address = tracker_url.split(':')[0], int(tracker_url.split(':')[1])
    try:
        ip = socket.gethostbyname(address[0])
    except socket.error as e:
        return address, 'failed resolve'

    ip_address_version = 'v6' if ':' in ip else 'v4'
    return address, ip_address_version


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


def __build_announce_packet(connection_id: bytes, info_hash: bytes, peer_id: bytes, event: int, port: int) -> bytes:
    """
    generates a udp announce packet
    :param connection_id:
    :param info_hash: info_hash of the torrent file
    :param peer_id: peer_id
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :return: bytes of announce packet
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


def __format_announce_response(data: bytes, ip_version: str) -> Tuple[List[Tuple[str, int]], List[Any]]:
    """
    formats the announce response
    :param data: binary data received from tracker
    :param ip_version: ip_version of tracker
    :return: [0]: list of peers addresses (ip, port) [1]: unpacked entire data
    """
    # unpack data
    format_string = '>4s4sIII'  # format of first 20 bytes

    if ip_version == 'v4':
        dynamic_format = '4sH'  # format of ipv4 and port
        n = (len(data) - 20) // 6
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        # format ipv4 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + 5] = '.'.join([str(i) for i in unpacked_data[i + 5]])

    else:  # ip_version == 'v6'
        dynamic_format = '16sH'
        n = (len(data) - 20) // 18
        format_string += dynamic_format * n
        unpacked_data = list(struct.unpack(format_string, data))
        # format ipv6 addresses from bytes
        for i in range(0, n, 2):
            unpacked_data[i + 5] = socket.inet_ntop(socket.AF_INET6, unpacked_data[i + 5])

    # convert peers addresses to a separate list
    peers = []
    for i in range(0, n, 2):
        peers.append((unpacked_data[i + 5], unpacked_data[i + 6]))

    return peers, unpacked_data


async def __udp_connection(request_data: bytes, address: Tuple[str, int], timeout: int) -> bytes:
    try:
        async with aioudp.connect(*address) as connection:
            await connection.send(request_data)
            data = await asyncio.wait_for(connection.recv(), timeout)
            await asyncio.sleep(0.01)
            return data

    except asyncio.TimeoutError:
        return b''
    except Exception as e:
        raise e


async def __get_connection_id(tracker_address: Tuple[str, int], timeout_list: List[int] = __timeouts) -> Union[bytes, None]:
    """
    gets a connection_id from tracker for announce / scrape
    :param tracker_address: formatted tracker address
    :param timeout_list: list that specifies how much time to wait before retransmission
    :return: bytes: successfully received a connection_id. None: did not receive a connection_id
     | raised exception: something went wrong
    """
    request_data = __build_connect_packet()

    for timeout in timeout_list:

        data = await __udp_connection(request_data, tracker_address, timeout)

        if len(data) >= 16:
            if data[4:8] == request_data[12:] and data[0:4] == request_data[8:12]:  # same transaction_id and action
                # if received data passes checks, it's the right packet
                connection_id = data[8:]
                return connection_id

    return None


async def udp_tracker_announce(tracker_url: str, info_hash: bytes, peer_id: bytes, port: int, event: int = 0, timeout_list: List[int] = __timeouts) \
        -> Union[Tuple[List[Tuple[str, int]], List[Any]], str]:
    """
    creates an announce request to the tracker and awaits response
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :param timeout_list: list that specifies how much time to wait before retransmission
    :param tracker_url: tracker udp url
    :param info_hash: info_hash
    :param peer_id: peer_id
    :return:
    """
    tracker_address, ip_version = __format_url(tracker_url)

    if ip_version == 'failed resolve':
        return f"failed to resolve tracker url"

    # build the announce packet
    connection_id = await __get_connection_id(tracker_address, timeout_list)
    if connection_id is None:
        return f"tracker is not reachable"

    request_data = __build_announce_packet(connection_id, info_hash, peer_id, event, port)

    for timeout in timeout_list:

        data = await __udp_connection(request_data, tracker_address, timeout)

        if len(data) >= 20:
            if request_data[12:16] == data[4:8] and request_data[8:12] == data[0:4]:  # same transaction_id and action
                return __format_announce_response(data, ip_version)

    return f"tracker is not reachable"
