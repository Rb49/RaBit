from .tracker_object import Tracker, ANNOUNCING, WORKING, UNREACHABLE
from .udp_tracker import udp_tracker_announce
from .http_tracker import http_tracker_announce
from src.torrent.torrent_object import Torrent

import asyncio
from typing import List, Tuple
import time
import math


async def initial_announce(TorrentData: Torrent, downloaded: int, uploaded: int, left: int, port: int, event: int) -> Tuple[List[Tuple[str, int]], List[Tracker]]:
    """
    performs announce request to trackers
    :param TorrentData: a TorrentData object from TorrentData file
    :param downloaded: bytes downloaded
    :param uploaded: bytes uploaded
    :param left: bytes left to download
    :param port: port the client is listening on
    :param event: 0: none; 1: completed; 2: started; 3: stopped
    :return: a list of peer addresses (ip, port)
    """
    # TODO add tracker object support, scrape and updating udp trackers by protocol timeouts
    # initial announce
    if not TorrentData.announce_list:
        TorrentData.announce_list = [[TorrentData.announce]]

    peers_list: List[Tuple[str, int]] = []
    tracker_list: List[Tracker] = []

    async def _announce(tracker_url) -> None:
        nonlocal peers_list
        nonlocal tracker_list

        response = ''
        tracker_url = tracker_url[0].decode('utf-8')
        tracker_object = Tracker(tracker_url, TorrentData.info_hash, TorrentData.peer_id)
        tracker_list.append(tracker_object)
        tracker_object.state = ANNOUNCING

        try:
            if 'udp' in tracker_url:
                response = await udp_tracker_announce(tracker_url, TorrentData.info_hash, TorrentData.peer_id, downloaded, uploaded, left, event, port, timeout_list=[1, 1])  # set manual timeout_list to prevent blocking for now

            elif 'http' in tracker_url:
                response = await http_tracker_announce(tracker_url, TorrentData.info_hash, TorrentData.peer_id, downloaded, uploaded, left, event, port)

            if not isinstance(response, str):  # extend peer_list if an error message is not returned
                peers_list.extend(response[0])
                tracker_object.interval = response[1]
                tracker_object.state = WORKING
                tracker_object.last_announce = time.time()
            else:
                raise

        except Exception as e:
            tracker_object.interval = math.inf
            tracker_object.state = UNREACHABLE
            tracker_object.last_announce = time.time()

        return

    tasks = [_announce(url) for url in TorrentData.announce_list]

    await asyncio.gather(*tasks)

    # remove duplicates from peers[]
    peers_list = list(dict.fromkeys(peers_list))

    return peers_list, tracker_list
