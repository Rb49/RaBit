from typing import Optional, List, Union, Tuple


class PeerObject(object):
    """
    object to store attributes of a peer and some stats
    """

    def __init__(self, address: Tuple[str, int]):
        self.address = address

        self.is_chocked = True
        self.am_interested = False


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
