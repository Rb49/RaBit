from src.torrent.torrent_object import Torrent

import time
from typing import Tuple, List, Set
import bitstring


class Peer(object):
    """
    object to store attributes of a peer and some stats
    """
    MAX_ENDGAME_PIPELINE = 2
    peer_instances: List = []

    def __init__(self, TorrentData: Torrent, address: Tuple[str, int], geodata: Tuple[str, str, float, float]):
        Peer.peer_instances.append(self)

        self.torrent = TorrentData

        self.MAX_PIPELINE_SIZE = 10  # 10 is default
        self.address = address

        self.is_chocked = True  # am I chocked?
        # self.is_interested = True  # am I interested in what the peer offers? always true on download
        self.am_chocked = True  # have I chocked the peer?
        self.am_interested = False  # is the peer interested in what I offer?

        self.have_pieces = bitstring.BitArray(bin='0' * len(self.torrent.piece_hashes))
        self.is_seed = False
        self.pipelined_requests = []

        self.have_msg_sent: Set = set()
        self.endgame_cancel_msg_sent: Set = set()

        self.last_data_sent = time.time()

        self.download_rate = 0  # in KiB/s
        self.upload_rate = 0  # in KiB/s

        self.geodata = geodata
        self.peer_id = None
        self.client = None

    def update_download_rate(self, len_bytes_sent: int):
        # idk how but this function generates ridiculously incredible downloading on account of cpu usage
        rn = time.time()
        if (dt := rn - self.last_data_sent) < 0.05:
            return

        rate = (len_bytes_sent / 1024) / dt
        # update pipeline size using rtorrent algorithm
        if rate < 20:
            self.MAX_PIPELINE_SIZE = rate + 2
        else:
            self.MAX_PIPELINE_SIZE = rate / 5 + 18

        self.last_data_sent = rn
        self.download_rate = rate

    def __del__(self):
        Peer.peer_instances.remove(self)
