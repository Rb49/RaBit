from src.torrent.torrent_object import Torrent

import time
from typing import Tuple
import bitstring

# TODO add dynamic pipelining based on performance
MAX_PIPELINE_SIZE = 5  # 5 is default


class Peer(object):
    """
    object to store attributes of a peer and some stats
    """

    def __init__(self, TorrentData: Torrent, address: Tuple[str, int], geodata: Tuple[str, str, float, float]):
        self.torrent = TorrentData

        self.address = address

        self.is_chocked = True
        self.am_interested = False

        self.have_pieces = bitstring.BitArray(bin='0' * len(self.torrent.piece_hashes))
        self.pipelined_requests = []

        self.is_in_endgame = False
        self.endgame_sent = None
        self.endgame_received = None
        self.endgame_queue = []

        self.last_seen = time.time()

        self.peer_id = None
        self.downloaded = 0
        self.uploaded = 0

        self.geodata = geodata
        self.client = None
