import copy
import threading

from .utils import *
from src.peer.message_types import *
from src.seeding.leecher_object import Leecher
from src.seeding.handshake import handshake, validate_peer_ip
from src.file.file_object import PickableFile

import asyncio
from math import ceil
import bitstring
from random import sample


_BUFFER_SIZE = 4096
_MAX_REQUESTS = 500
_LEASE_DURATION = 3600  # an hour
_MAX_LEECHER_PEERS = db_utils.get_configuration('max_leecher_peers')


class Stream(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.buffer = b''

    def __consume(self, msg_length):
        self.buffer = self.buffer[msg_length:]

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            data = await asyncio.wait_for(await self.reader.read(_BUFFER_SIZE), 60)
            self.buffer += data
            if not self.buffer:
                raise StopAsyncIteration

            length = struct.unpack('>I', self.buffer[0:4])[0] + 4
            if length == 4:  # keepalive
                self.__consume(4)
                continue

            if len(self.buffer) < length:
                continue

            msg = self.buffer[:length]
            msg_id = msg[4]

            self.__consume(length)

            if msg_id == INTERESTED:
                return Interested()
            elif msg_id == NOT_INTERESTED:
                return NotInterested()

            elif msg_id == REQUEST:
                return Request.decode(msg)
            elif msg_id == CANCEL:
                return Cancel.decode(msg)

            elif msg_id in [CHOKE, UNCHOKE, HAVE, BITFIELD]:
                continue

            else:
                # unsupported message
                raise AssertionError


async def handle_leecher(reader, writer):
    print('got connection')
    leecher = None
    try:
        # make sure peer is not dirty
        peer_address = writer.get_extra_info('peername')
        print('connected to ', peer_address)
        geodata = validate_peer_ip(peer_address[0])
        assert geodata

        # prioritize ip
        ip_priority = crc32c_sort_v4(peer_address)
        if len(Leecher.leecher_instances) == _MAX_LEECHER_PEERS:
            sorted_leechers = sorted(Leecher.leecher_instances, key=lambda x: x.priority)
            if ip_priority > sorted_leechers[0]:
                # kick that peer
                sorted_leechers[-1].writer.close()
                await sorted_leechers[0].writer.wait_closed()
            else:
                raise ConnectionRefusedError

        # handshake
        info_hash, peer_id = await handshake(reader, writer)
        assert info_hash

        file_object: PickableFile = copy.deepcopy(FileObjects[info_hash])
        file_object.reopen_files()

        # send bitfield
        bitfield = bitstring.BitArray(bin='1' * file_object.num_pieces)
        zero_indexes = sample(range(len(bitfield)), min(ceil(len(bitfield) / 100), 50))
        for index in zero_indexes:
            bitfield[index] = False
        writer.write(Bitfield.encode(bitfield))
        await writer.drain()
        for index in zero_indexes:
            writer.write(Have.encode(index))
            await writer.drain()

        leecher = Leecher(writer, peer_address, geodata, peer_id, ip_priority)
        async for msg in Stream(reader, writer):
            if isinstance(msg, Interested):
                leecher.am_interested = True
                leecher.am_chocked = False
                writer.write(Unchock.encode())
                await writer.drain()
            elif isinstance(msg, NotInterested):
                leecher.am_interested = False
                leecher.am_chocked = True
                writer.write(Chock.encode())
                await writer.drain()

            elif isinstance(msg, Request):
                if not leecher.am_chocked:
                    leecher.pipelined_requests.append((msg.piece_index, msg.begin, msg.length))
                    if len(leecher.pipelined_requests) > _MAX_REQUESTS:
                        # attempted dos detected
                        db_utils.BannedPeersDB().insert_ip(leecher.address[0])
                        raise AssertionError

            elif isinstance(msg, Cancel):
                if (details := (msg.piece_index, msg.begin, msg.length)) in leecher.pipelined_requests:
                    leecher.pipelined_requests.remove(details)

            # fulfill 50% of request
            for _ in range(0, len(leecher.pipelined_requests), 2):
                piece_params = file_object.get_piece(*leecher.pipelined_requests.pop(0))
                writer.write(Piece.encode(*piece_params))
                await writer.drain()
                # update statistics
                file_object.uploaded += len(piece_params[2])
                leecher.downloaded += len(piece_params[2])

                # introduce more delay as peer is more and more demanding
                normalize = lambda value, max_value, new_min, new_max: (value / max_value) * (new_max - new_min) + new_min
                await asyncio.sleep(normalize(len(leecher.pipelined_requests), _MAX_REQUESTS, 0.01, 0.20))

    except AssertionError as e:
        ...

    except Exception as e:
        print(f'An error occurred: {e}')
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()

        if leecher in Leecher.leecher_instances:
            FileObjects[info_hash].close_files()
            Leecher.leecher_instances.remove(leecher)
            file_object.close_files()
            del leecher

        return


async def start_seeding_server():
    internal_ipv4, internal_ipv6 = get_internal_ip()
    assert internal_ipv4

    async def forward_port(internal_ip: str, internal_port, external_port, last_forward, version: str):
        try:
            server = await asyncio.start_server(handle_leecher, internal_ip, internal_port)
        except:  # the port is occupied
            server = await asyncio.start_server(handle_leecher, internal_ip, 0)
            internal_port = server.sockets[0].getsockname()[1]

        # attempt to forward the port only when the lease ends
        if time.time() - last_forward > _LEASE_DURATION:
            port_range = list(range(6881, 6890))
            if external_port != 0:  # attempt to re-lease last used port
                port_range.remove(external_port)
                port_range.insert(0, external_port)
            print(internal_port)
            for external_port in port_range:
                try:
                    res = await forward_port_upnp(external_port, internal_port, 'TCP', internal_ip, _LEASE_DURATION)
                except:  # conflict found, continue to next port
                    continue

                if res:
                    await save_forward(internal_port, external_port, version)
                    break
                else:  # no compatible device was found
                    raise Exception("Router not found. Most likely UPNP is not enabled on the router")

            else:  # encountered conflicts on every port
                raise Exception("Could not forward a port in specified range")

        print(f'successfully forwarded an ip{version} port: ex {external_port} -> in {internal_port}')

        return server

    # load previous forwarding
    internal_port_v4, external_port_v4, last_forward_v4 = load_forwarding('v4')
    if internal_port_v4 == 0:
        internal_port_v4 = -1

    server_v4 = await forward_port(internal_ipv4, internal_port_v4, external_port_v4, last_forward_v4, 'v4')

    # run server and updates thread
    await asyncio.to_thread(await update_mapping(internal_port_v4, external_port_v4, internal_ipv4, last_forward_v4, 'v4'))
    async with server_v4:
        await server_v4.serve_forever()

    '''
    internal_port_v6, external_port_v6, last_forward_v6 = load_forwarding('v6')
    if internal_port_v6 == 0:
        internal_port_v6 = -1
    server_v6 = await forward_port(internal_ipv6, internal_port_v6, external_port_v6, last_forward_v6, 'v6')
    '''


async def update_mapping(internal_port: int, external_port: int, internal_ip: str, last_forward: int, version: str):
    while True:
        await asyncio.sleep(_LEASE_DURATION - (time.time() - last_forward) - 2)  # 2 is the default ssdp discovery delay
        # re-lease the rule

        port_range = list(range(6881, 6890))
        # attempt to re-lease last used port
        port_range.remove(external_port)
        port_range.insert(0, external_port)
        for external_port in port_range:
            try:
                res = await forward_port_upnp(external_port, internal_port, 'TCP', internal_ip, _LEASE_DURATION)
            except:  # conflict found, continue to next port
                continue

            if res:
                await save_forward(internal_port, external_port, version)
                break
            else:  # no compatible device was found
                raise Exception("Router not found. Most likely UPNP is not enabled on the router")

        else:  # encountered conflicts on every port
            raise Exception("Could not forward a port in specified range")

        last_forward = time.time()
        print(f'successfully re-forwarded an ip{version} port: ex {external_port} -> in {internal_port}')




