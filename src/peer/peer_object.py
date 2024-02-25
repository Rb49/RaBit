from src.torrent.torrent_object import Torrent

import time
from typing import Tuple
import bitstring


class Peer(object):
    """
    object to store attributes of a peer and some stats
    """
    endgame_ready = []

    def __init__(self, TorrentData: Torrent, address: Tuple[str, int], geodata: Tuple[str, str, float, float]):
        self.torrent = TorrentData

        self.MAX_PIPELINE_SIZE = 5  # 5 is default
        self.address = address

        self.is_chocked = True
        self.am_interested = False

        self.have_pieces = bitstring.BitArray(bin='0' * len(self.torrent.piece_hashes))
        self.is_seed = False
        self.pipelined_requests = []

        self.standing_by = False
        Peer.endgame_ready.append(self.standing_by)

        self.is_in_endgame = False
        self.endgame_sent = None
        self.endgame_received = None
        self.endgame_queue = []

        self.last_data_sent = time.time()

        self.peer_id = None
        self.downloaded = 0  # in bytes
        self.uploaded = 0  # in bytes
        self.download_rate = 0  # in KiB/s
        self.upload_rate = 0  # in KiB/s

        self.geodata = geodata
        self.client = None

    def update_download_rate(self, len_bytes_sent: int):
        if self.is_in_endgame:
            self.MAX_PIPELINE_SIZE = 1
            return

        self.downloaded += len_bytes_sent
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
        self.downloaded = 0
        self.download_rate = rate
        # print(rate)

    def toggle_endgame_ready(self):
        if self.standing_by:
            Peer.endgame_ready.remove(True)
            self.standing_by = False
            Peer.endgame_ready.append(False)
            return False
        else:
            Peer.endgame_ready.remove(False)
            self.standing_by = True
            Peer.endgame_ready.append(True)
            return True

    def __del__(self):
        Peer.endgame_ready.remove(self.standing_by)






