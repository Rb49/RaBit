from .udp_tracker import udp_tracker_announce
from .http_tracker import http_tracker_announce
import asyncio
from typing import List, Tuple


async def get_peers_addresses(tracker_url_list: List[List[bytes]], info_hash: bytes, peer_id: bytes, left: int, port: int) -> List[Tuple[str, int]]:
    """
    performs the initial announce at the start of a download
    :param left: ascii base 10
    :param tracker_url_list: list of the trackers urls
    :param info_hash: info_hash of info dictionary
    :param peer_id: peer_id for this download
    :param port: port the client is listening on
    :return: list of peer addresses (ip, port)
    """
    peers_list = []

    async def announce(tracker_url) -> None:
        nonlocal peers_list

        response = ''
        tracker_url = tracker_url[0].decode('utf-8')

        try:
            if 'udp' in tracker_url:
                response = await udp_tracker_announce(tracker_url, info_hash, peer_id, 0, 0, left, 2, port, timeout_list=[1, 1])  # set manual timeout_list to prevent blocking for now

            elif 'http' in tracker_url:
                response = await http_tracker_announce(tracker_url, info_hash, peer_id, 0, 0, left, 2, port)

            if not isinstance(response, str):  # extend peer_list if error message is not returned
                peers_list.extend(response[0])

        except Exception as e:
            print(e)
            pass

        return

    tasks = [announce(url) for url in tracker_url_list]

    await asyncio.gather(*tasks)

    # remove duplicates from peers[]
    peers_list = list(dict.fromkeys(peers_list))

    return peers_list
