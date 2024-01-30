from src.torrent.torrent_object import Torrent
from typing import Optional, List, Union, Tuple
import bitstring


class Peer(object):
    """
    object to store attributes of a peer and some stats
    """

    def __init__(self, TorrentData: Torrent, address: Tuple[str, int], peer_id: bytes = None):
        self.torrent = TorrentData

        self.address = address

        self.is_chocked = True
        self.am_interested = False

        self.have_pieces = bitstring.BitArray(bin='0' * len(self.torrent.piece_hashes))
        self.peer_id = peer_id
        self.downloaded = 0
        self.uploaded = 0



"""
    address: Tuple[str, int]  # the address of this peer (ip, port)
    # status of this peer
    isChocked: bool  # is the peer chocked rn?
    isInterested: bool  # is the peer interested rn?
    id: Optional[bytes]  # peer id

    # some stats
    client: Optional[Union[str, None]] = None  # which client is this peer using?
    downloaded: Optional[int] = 0  # how much data has been downloaded from this peer
    uploaded: Optional[int] = 0  # how much data has been uploaded to this peer
    flags: Optional[List[str]] = None  # flags - other information over the status of this peer
"""
