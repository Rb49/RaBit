from ..torrent.torrent_object import Torrent

from typing import Tuple, Union
import asyncio
import struct


async def open_tcp_connection(address: Tuple[str, int]) -> Tuple:
    """
    opens a tcp connection to an address
    :param address: (ip, port) of peer
    :return: asyncio instances of (reader, writer) | (None, None)
    """
    try:
        reader, writer = await asyncio.open_connection(*address)
        return reader, writer
    except OSError:
        # print('connection refused')
        return None, None


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


def __validate_handshake(data: bytes, info_hash1: bytes) -> Union[bytes, None]:
    """
    validates the other peer actually "speaks" the protocol and has the file
    :param data: raw handshake bytes
    :param info_hash1: expected info hash to be returned
    :return: peer id | None if operation failed
    """
    string_format = '>20sQ20s20s'
    len_n_protocol, extensions, info_hash2, peer_id = struct.unpack(string_format, data)
    if len_n_protocol == b'\x13BitTorrent protocol' and info_hash1 == info_hash2:
        return peer_id
    else:
        return None


async def handshake(TorrentData: Torrent, reader, writer) -> Union[bytes, None]:
    """
    performs the exchange of handshakes
    :param TorrentData: torrent data instance
    :param reader: asyncio reader instance
    :param writer: asyncio writer instance
    :return: peer id | None if operation failed
    """
    request_data = __build__handshake_packet(TorrentData.info_hash, TorrentData.peer_id)

    writer.write(request_data)
    await writer.drain()
    data = await reader.read(68)  # len of handshake

    # validate the protocol
    peer_id = __validate_handshake(data, TorrentData.info_hash)
    return peer_id
