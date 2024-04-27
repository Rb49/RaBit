from .torrent_object import Torrent

import bencodepy
from hashlib import sha1
import random
import string


def read_torrent(path: str) -> Torrent:
    """
    function to read a .torrent file into a TorrentData file object
    :param path: path of TorrentData file
    :return: Torrent instance with the file's data
    """

    # open and decode the data
    with open(path, 'rb') as file:
        content = file.read()
        content = bencodepy.decode(content)

    # create a Torrent instance
    # need to add support for distributed torrents and magnet links, non multi-file torrents and no announcers
    torrent_data = Torrent(info=content[b'info'],
                                 info_hash=None,
                                 piece_hashes=None,
                                 multi_file=bool(content[b'info'].get(b'files')),
                                 peer_id=None,
                                 announce=content.get(b'announce'),
                                 comment=content.get(b'comment'),
                                 created_by=content.get(b'created by'),
                                 date_created=content.get(b'date created'),
                                 announce_list=content.get(b'announce-list'))

    if torrent_data.multi_file:
        for file in torrent_data.info[b'files']:
            torrent_data.length += file[b'length']
    else:
        torrent_data.length = content[b'info'].get(b'length')

    # set info_hash, piece_hashes and peer_id:
    # hashes are in sha1, 20 bytes long
    pieces = torrent_data.info[b'pieces']
    torrent_data.piece_hashes = [pieces[i: i + 20] for i in range(0, len(pieces), 20)]

    data = bencodepy.encode(torrent_data.info)
    sha1_hash = sha1(data).digest()
    torrent_data.info_hash = sha1_hash

    # Azureus - style peer id encoding : 8 bytes. rest is random 8 alphanumeric bytes
    torrent_data.peer_id = b'-RB0100-EPIC' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8)).encode()

    return torrent_data
