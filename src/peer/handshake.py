from typing import Tuple
from .peer_object import PeerObject
import asyncio
import struct


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


async def tcp_wire_communication(address: Tuple[str, int], info_hash: bytes, peer_id: bytes):
    try:
        reader, writer = await __open_tcp_connection(address)

        request_data = __build_tcp_download_handshake_packet(info_hash, peer_id)
        # print(address, request_data)
        if reader:
            data = None
            try:
                writer.write(request_data)
                # Ensure the data is flushed to the transport
                await writer.drain()

                data = await reader.read(4096)

            except asyncio.CancelledError:
                # print('task cancelled')
                pass

            finally:
                # print("Closing the connection.")
                writer.close()
                await writer.wait_closed()
                return data

    except Exception as e:
        # print(e)
        pass





