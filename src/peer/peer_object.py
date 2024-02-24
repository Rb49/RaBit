from src.torrent.torrent_object import Torrent

import time
from typing import Tuple
import bitstring


class Peer(object):
    """
    object to store attributes of a peer and some stats
    """

    def __init__(self, TorrentData: Torrent, address: Tuple[str, int], geodata: Tuple[str, str, float, float]):
        self.torrent = TorrentData

        self.MAX_PIPELINE_SIZE = 5  # 5 is default
        self.address = address

        self.is_chocked = True
        self.am_interested = False

        self.have_pieces = bitstring.BitArray(bin='0' * len(self.torrent.piece_hashes))
        self.pipelined_requests = []

        self.is_in_endgame = False
        self.endgame_sent = None
        self.endgame_received = None
        self.endgame_queue = []

        self.last_data_sent = time.time()

        self.peer_id = None
        self.download_rate = 0  # in KiB/s
        self.upload_rate = 0  # in KiB/s

        self.geodata = geodata
        self.client = None

    def update_download_rate(self, len_bytes_sent: int):
        if self.is_in_endgame:
            self.MAX_PIPELINE_SIZE = 1
            return

        rn = time.time()
        if (dt := rn - self.last_data_sent) < 1:
            return

        rate = (len_bytes_sent / 1024) / dt
        # update pipeline size using rtorrent algorithm
        if rate < 20:
            self.MAX_PIPELINE_SIZE = rate + 2
        else:
            self.MAX_PIPELINE_SIZE = rate / 5 + 18
        self.last_data_sent = rn
        self.download_rate = rate
        # print(rate)







