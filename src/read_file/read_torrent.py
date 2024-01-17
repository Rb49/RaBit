import bencodepy
from .torrent_object import TorrentObject
from hashlib import sha1
import random


def read_torrent(path: str) -> TorrentObject:
    """
    function to read a torrent file into a torrent file object
    :param path: path of torrent file
    :return: TorrentObject
    """

    # open and decode the data
    with open(path, 'rb') as file:
        content = file.read()
        content = bencodepy.decode(content)

    # create a Torrent instance
    # need to add support for distributed torrents and magnet links, non multi-file torrents and no announcers
    torrent_data = TorrentObject(info=content.get(b'info'),
                                 info_hash=None,
                                 piece_hashes=None,
                                 peer_id=None,
                                 announce=content.get(b'announce'),
                                 comment=content.get(b'comment'),
                                 announce_list=content.get(b'announce-list'))

    # set info_hash, piece_hashes and peer_id:
    # hashes are in sha1, 20 bytes long
    pieces = torrent_data.info[b'pieces']
    torrent_data.piece_hashes = [pieces[i: i + 20] for i in range(0, len(pieces), 20)]

    data = bencodepy.encode(torrent_data.info)
    sha1_hash = sha1(data).digest()
    torrent_data.info_hash = sha1_hash

    torrent_data.peer_id = random.getrandbits(160).to_bytes(20, byteorder='big')

    return torrent_data
