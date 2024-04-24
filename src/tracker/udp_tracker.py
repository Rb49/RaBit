from .utils import format_announce_response
import random
from typing import Tuple, List, Union, Any
import struct
import asyncio
import aioudp
import socket


__timeouts = (15, 30, 60, 120, 240, 480, 960, 1920, 3840)  # protocol timeouts for udp sockets


def __format_url(tracker_url: str) -> Union[str, List[Tuple[Tuple[str, str], str]]]:
    """
    formats an url to proper addresses and finds out the ip version of them
    :param tracker_url: raw tracker url
    :return: (url, port), ip version (v4 | v6): (str, int), OR str: error code
    """
    # remove the 'udp://' and '/announce' from address
    tracker_url = tracker_url.replace('udp://', '')
    tracker_url = tracker_url.split('/')[0]

    address = tracker_url.split(':')[0], int(tracker_url.split(':')[1])
    try:
        result = socket.getaddrinfo(*address)
        addresses = [((res[4][0], res[4][1]), 'v6' if ':' in res[4][0] else 'v4') for res in result]
    except socket.error as e:
        return 'failed resolve'

    return addresses


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


def __build_announce_packet(connection_id: bytes, info_hash: bytes, peer_id: bytes, downloaded: int, uploaded: int, left: int, event: int, port: int, key: int) -> bytes:
    """
    generates a udp announce packet
    :param connection_id:
    :param info_hash: info_hash of the torrent file
    :param peer_id: peer_id
    :param uploaded: uploaded
    :param downloaded: downloaded
    :param left: left
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :param key: random key
    :return: bytes of announce packet
    """

    format_string = '>8sII20s20sQQQIIIiH'

    data = struct.pack(format_string,
                       connection_id,
                       1,  # action - announce
                       random.getrandbits(32),  # transaction_id
                       info_hash,
                       peer_id,
                       downloaded,  # downloaded
                       left,  # left
                       uploaded,  # uploaded
                       event,  # event
                       0,  # ip address, default is 0
                       key,  # random key
                       -1,  # num_want, default is -1 (50)
                       port)

    return data


async def __udp_connection(request_data: bytes, address: Tuple[str, int], timeout: int) -> Union[bytes, str]:
    try:
        async with aioudp.connect(*address) as connection:
            await connection.send(request_data)
            data = await asyncio.wait_for(connection.recv(), timeout)
            await asyncio.sleep(0.01)
            return data

    except asyncio.TimeoutError:
        return 'connection timeout'
    except Exception as e:
        # raise e
        pass


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


async def udp_tracker_announce(tracker_url: str, info_hash: bytes, peer_id: bytes, downloaded: int, uploaded: int, left: int, event: int, port: int, timeout_list: List[int] = __timeouts) \
        -> Union[Tuple[List[Tuple[str, int]], int], str]:
    """
    creates an announce request to the tracker and awaits response
    :param tracker_url: tracker udp url
    :param info_hash: info_hash
    :param peer_id: peer_id
    :param uploaded: uploaded
    :param downloaded: downloaded
    :param left: left
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :param timeout_list: list that specifies how much time to wait before retransmission
    :return: [0]: peer list, [1]: interval | str: exception
    """
    tracker_addresses = __format_url(tracker_url)
    if isinstance(tracker_addresses, str):
        return f"failed to resolve tracker url"

    # generate only one random key to follow protocol
    key = random.getrandbits(32)

    async def _announce(address: Tuple[Tuple[str, int], str]):

        # build the announce packet
        connection_id = await __get_connection_id(address[0], timeout_list)
        if connection_id is None:
            return f"tracker is not reachable"

        request_data = __build_announce_packet(connection_id, info_hash, peer_id, downloaded, uploaded, left, event, port, key)

        for timeout in timeout_list:

            data = await __udp_connection(request_data, address[0], timeout)

            if len(data) >= 20:
                if request_data[12:16] == data[4:8] and request_data[8:12] == data[0:4]:  # same transaction_id and action
                    return format_announce_response(data, address[1])

        return f"tracker is not reachable"

    # iterate over every address this tracker has
    lst = []
    for address in tracker_addresses:
        peers, interval = await _announce(address)
        if isinstance(peers, str):
            return peers
        else:
            lst.extend(peers)
    return lst, interval
