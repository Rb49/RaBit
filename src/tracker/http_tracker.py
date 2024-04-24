from .utils import format_announce_response
from urllib.parse import urlencode
import bencodepy
from collections import OrderedDict
from typing import Union, List, Tuple, Any, Iterable
import asyncio
import aiohttp
from yarl import URL


async def http_tracker_announce(tracker_url: str, info_hash: bytes, peer_id: bytes, downloaded: int, uploaded: int, left: int, event: int, port: int) \
        -> Union[Tuple[List[Tuple[str, int]], int], str]:
    """
    connect to a http tracker through GET
    :param tracker_url: url of the tracker
    :param info_hash: info_hash of the torrent file
    :param peer_id: peer_id
    :param uploaded: uploaded
    :param downloaded: downloaded
    :param left: left
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :return: str: error message | list: decoded response of the tracker in form of (ip, port), interval
    """
    events = ['none', 'completed', 'started', 'stopped']

    headers = {
        'User-Agent': 'RaBit v0.1.0'
    }

    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'uploaded': uploaded,
        'downloaded': downloaded,
        'left': left,
        'event': events[event],
        'port': port,
        'no_peer_id': 1
    }
    params = urlencode(params)
    tracker_url = f"{tracker_url}?{params}"

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(URL(tracker_url, encoded=True)) as response:
            # check if the request was successful (HTTP status code 200)
            if response.status == 200:
                peer_data = await response.read()
                peer_data = bencodepy.decode(peer_data)

                try:
                    return [(peer[b'ip'].decode('utf-8'), peer[b'port']) for peer in peer_data[b'peers']], peer_data[b'interval']

                except TypeError:  # this means the tracker returned a compact response
                    ipv4peers, ipv6peers = [], []
                    data = peer_data.get(b'peers')
                    if data:
                        ipv4peers = format_announce_response(data, 'v4', '>', 0)[0]
                    data = peer_data.get(b'peers6')
                    if data:
                        ipv6peers = format_announce_response(data, 'v6', '>', 0)[0]

                    ipv4peers.extend(ipv6peers)
                    return ipv4peers, peer_data[b'interval']

            else:
                return f"Failed to connect to the tracker. HTTP Status Code: {response.status}"
