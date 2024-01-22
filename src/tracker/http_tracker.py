from urllib.parse import urlencode
import bencodepy
from collections import OrderedDict
from typing import Union, List, Tuple
import asyncio
import aiohttp


async def http_tracker_announce(tracker_url: str, info_hash: bytes, peer_id: bytes, port: int, event: int = 0) -> Union[Tuple[List[Tuple[str, int]], OrderedDict], str]:
    """
    connect to a http tracker through GET
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :param port: tells the tracker where the client is listening
    :param tracker_url: url of the tracker
    :param info_hash: info_hash of the torrent file
    :param peer_id: peer_id
    :return: str: error message | list: decoded response of the tracker in form of (ip, port), OrderedDict: entire response
    """

    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'uploaded': 0,
        'downloaded': 0,
        'left': 0,
        'event': event,
        'port': port
    }
    params = urlencode(params)

    async with aiohttp.ClientSession() as session:
        async with session.get(tracker_url, params=params, timeout=2) as response:
            # check if the request was successful (HTTP status code 200)
            if response.status == 200:
                peer_data = await response.text()
                peer_data = bencodepy.decode(str.encode(peer_data))

                return [(peer[b'ip'].decode('utf=8'), peer[b'port']) for peer in peer_data[b'peers']], peer_data
            else:
                return f"Failed to connect to the tracker. HTTP Status Code: {response.status}"
