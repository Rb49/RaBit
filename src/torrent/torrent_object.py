from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, List, Union


@dataclass
class Torrent(object):
    """
    object to store attributes from the torrent file
    """

    info: OrderedDict  # metadate dict
    info_hash: Union[bytes, None]  # sha-1 hash of the entire bencoded info dict
    piece_hashes: Union[List[bytes], None]  # list of sha-1 hashes of all the pieces
    multi_file: bool  # are there multiple files in this torrent?

    peer_id: Union[bytes, None]  # a randomly chosen 20-bytes peer id for this download
    length: int = 0

    announce: Optional[bytes] = None  # tracker
    comment: Optional[Union[bytes, None]] = None  # comment added by uploader, optional
    created_by: Optional[Union[bytes, None]] = None  # added by uploader, optional
    date_created: Optional[Union[bytes, None]] = None  # added by uploader, optional

    # other extensions to the protocol
    announce_list: Optional[list] = None  # support of multiple trackers
    nodes: Optional[list] = None  # support distributed hash tables

    # download/upload stats
    downloaded: int = 0
    uploaded: int = 0
    wasted: int = 0
    corrupted: int = 0
