from .peer_object import Peer
from typing import Tuple, List
import asyncio
import struct

from ..file.data_structures import Block


async def open_tcp_connection(address: Tuple[str, int]):
    try:
        reader, writer = await asyncio.open_connection(*address)
        return reader, writer
    except OSError:
        # print('connection refused')
        return None, None


def build__handshake_packet(info_hash: bytes, peer_id: bytes) -> bytes:
    string_format = '>B19sQ20s20s'

    data = struct.pack(string_format,
                       19,  # len of protocol name
                       b'BitTorrent protocol',  # protocol name
                       0,  # reserve 8 bytes for extensions, none will be used
                       info_hash,  # info hash of info dictionary
                       peer_id)  # my id for this download

    return data


def validate_handshake(data: bytes, info_hash1: bytes):
    string_format = '>20sQ20s20s'
    len_n_protocol, _, info_hash2, peer_id = struct.unpack(string_format, data)
    if len_n_protocol == b'\x13BitTorrent protocol' and info_hash1 == info_hash2:
        return peer_id
    else:
        return None


async def put_back_requests(peer: Peer, failed_queue: asyncio.Queue, endgame_blocks: List[Block]):
    while peer.pipelined_requests:
        if (block := peer.pipelined_requests.pop()) not in endgame_blocks:
            block.time_requested = 0
            await failed_queue.put(block)

