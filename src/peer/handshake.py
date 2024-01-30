from src.torrent.torrent_object import Torrent
from typing import Tuple
import asyncio
import struct
from .peer import Message


__BUFFER_SIZE = 16384
__MAX_BLOCK_SIZE = 16384
__MAX_PIPELINE_SIZE = 5


async def __open_tcp_connection(address: Tuple[str, int]):
    try:
        reader, writer = await asyncio.open_connection(*address)
        return reader, writer
    except OSError:
        # print('connection refused')
        return None, None


def __build_tcp_download_handshake_packet(info_hash: bytes, peer_id: bytes) -> bytes:
    string_format = '>B19sQ20s20s'

    data = struct.pack(string_format,
                       19,  # len of protocol name
                       b'BitTorrent protocol',  # protocol name
                       0,  # reserve 8 bytes for extensions, none will be used
                       info_hash,  # info hash of info dictionary
                       peer_id)  # my id for this download

    return data


async def tcp_wire_communication(peer: Tuple, TorrentData: Torrent):
    address, city, distance = peer
    try:
        reader, writer = await asyncio.wait_for(__open_tcp_connection(address), timeout=3)

        # start with a handshake
        request_data = __build_tcp_download_handshake_packet(TorrentData.info_hash, TorrentData.peer_id)
        if reader:
            data = None
            try:
                writer.write(request_data)
                # ensure the data is flushed to the transport
                await writer.drain()

                while True:

                    data = await reader.read(__BUFFER_SIZE)
                    if not data:
                        break

                    print(address, city, distance, data)

                    if data[0:20] == b'\x13BitTorrent protocol':
                        # create peer instance
                        data = data[68:]  # len of handshake

                    # get messages
                    while data != b'':
                        format_string = f'>IB{len(data) - 5}s'
                        length, ID, payload = struct.unpack(format_string, data)
                        data = data[4 + length:]
                        # print(length, ID, payload)





            except asyncio.CancelledError:
                # print('task cancelled')
                pass

            finally:
                # print("Closing the connection.")
                writer.close()
                await writer.wait_closed()
                return data

    except Exception as e:
        # raise e
        pass





