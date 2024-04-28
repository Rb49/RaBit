from ..app_data import db_utils
from ..file.file_object import PickableFile
from ..seeding.utils import FileObjects
from ..geoip.utils import get_info

from typing import Tuple, Union
import struct
import os


def validate_peer_ip(peer_ip: str) -> Union[Tuple[str, str, float, float], None]:
    """
    validates the ip address of the peer is not banned or from a banned country
    :param peer_ip: id address of the peer
    :return: geodata of the peer: country iso code, city, geo coordination
    """
    if db_utils.BannedPeersDB().find_ip(peer_ip):  # refuse dirty peers
        return None
    geodata = get_info(peer_ip)
    if geodata is not None:
        if geodata[1] in db_utils.get_banned_countries():  # refuse peers from banned countries
            return None
    else:
        return (None, None)

    return geodata


def __build__handshake_packet(info_hash: bytes, peer_id: bytes) -> bytes:
    """
    builds the handshake packet
    :param info_hash: info hash of the requested torrent
    :param peer_id: peer id of the client for this torrent
    :return: packet data in raw bytes
    """
    string_format = '>B19sQ20s20s'

    data = struct.pack(string_format,
                       19,  # len of protocol name
                       b'BitTorrent protocol',  # protocol name
                       0,  # reserve 8 bytes for extensions, none will be used
                       info_hash,  # info hash of info dictionary
                       peer_id)  # my id for this download

    return data


def __get_handshake_data(data: bytes) -> Union[Tuple[bytes, bytes], Tuple[None, None]]:
    """
    gets info hash and peer id from the incoming handshake packet
    :param data: raw packet bytes
    :return: info hash, peer id | None, None if packet is invalid
    """
    string_format = '>20sQ20s20s'
    len_n_protocol, extensions, info_hash, peer_id = struct.unpack(string_format, data)
    if len_n_protocol == b'\x13BitTorrent protocol':
        return info_hash, peer_id
    else:
        return None, None


async def handshake(reader, writer) -> Union[Tuple[bytes, bytes], Tuple[None, None]]:
    """
    performs the exchange of handshakes
    if the requested info hash is in the completed torrents' db, accept the connection and send handshake
    :param reader: asyncio reader instance
    :param writer: asyncio writer instance
    :return: info hash, peer id | None, None
    """
    data = await reader.read(68)  # len of handshake
    info_hash, peer_id = __get_handshake_data(data)
    # validate the protocol
    if not info_hash:
        return None, None

    # check if I have this torrent
    file_object: PickableFile = db_utils.CompletedTorrentsDB().get_torrent(info_hash)
    if not file_object:
        return None, None

    # check if all files exist
    for path in file_object.file_names:
        if not os.path.exists(path):
            db_utils.CompletedTorrentsDB().delete_torrent(info_hash)
            FileObjects.pop(info_hash)
            print('files not found!')
            return None, None

    # send handshake
    handshake_packet = __build__handshake_packet(info_hash, file_object.peer_id)
    del file_object
    writer.write(handshake_packet)
    await writer.drain()

    return info_hash, peer_id

