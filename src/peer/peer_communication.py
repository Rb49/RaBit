from typing import Dict, Tuple
from src.torrent.torrent_object import Torrent
from .peer_object import Peer
from .handshake import handshake, open_tcp_connection
from .message_types import *
from src.download.piece_picker import PiecePicker, Block
from src.download.upload_in_download import TitForTat
import asyncio
import struct
from random import sample, shuffle, random, seed

_BUFFER_SIZE = 4096


class Stream(object):
    def __init__(self, reader, writer, thisPeer, TorrentData: Torrent):
        self.reader = reader
        self.writer = writer
        self.thisPeer = thisPeer
        self.buffer = b''
        self.TorrentData = TorrentData

    def __consume(self, msg_length):
        self.buffer = self.buffer[msg_length:]

    async def __send_control_messages(self):
        while not self.thisPeer.control_msg_queue.empty():
            msg: bytes = await self.thisPeer.control_msg_queue.get()
            self.writer.write(msg)
            await self.writer.drain()

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            data = b''

            async def __get_data():
                nonlocal data
                data = await self.reader.read(_BUFFER_SIZE)

            await asyncio.gather(self.__send_control_messages(), __get_data())
            self.buffer += data
            if not self.buffer:
                #  raise StopAsyncIteration
                ...
                continue

            length = struct.unpack('>I', self.buffer[0:4])[0] + 4
            if length == 4:  # keepalive
                self.__consume(4)
                continue

            if len(self.buffer) < length:
                continue

            msg = self.buffer[:length]
            msg_id = msg[4]

            self.__consume(length)

            if msg_id == CHOKE:
                return Chock()
            elif msg_id == UNCHOKE:
                return Unchock()
            elif msg_id == INTERESTED:
                return Interested()
            elif msg_id == NOT_INTERESTED:
                return NotInterested()
            elif msg_id == HAVE:
                return Have.decode(msg)
            elif msg_id == BITFIELD:
                return Bitfield.decode(msg, len(self.TorrentData.piece_hashes))
            elif msg_id == REQUEST:
                return Request.decode(msg)
            elif msg_id == PIECE:
                return Piece.decode(msg)
            elif msg_id == CANCEL:
                return Cancel.decode(msg)

            # elif msg_id == PORT:
            #     return Port(msg)

            else:
                # unsupported message
                raise AssertionError


async def tcp_wire_communication(peerData: Tuple, TorrentData: Torrent, piece_picker: PiecePicker,
                                 chocking_manager: TitForTat):
    address, city, distance = peerData
    try:
        reader, writer = await asyncio.wait_for(open_tcp_connection(address), timeout=3)
        if (reader, writer) == (None, None):
            return

        thisPeer = Peer(TorrentData, address, city)
        try:
            # start with a handshake
            peer_id = await asyncio.wait_for(handshake(TorrentData, reader, writer), timeout=10)
            # validate the protocol
            assert peer_id

            thisPeer.add_peer_id(peer_id)

            # TODO now send bitfield / have all/none and fast allowed after fast extension support
            writer.write(Bitfield.encode(piece_picker.FILE_STATUS[:]))
            await writer.drain()

            # send interested
            # I am always interested in the peer
            writer.write(Interested.encode())
            await writer.drain()
            print("\033[92m{}\033[00m".format(f'connected {repr(thisPeer)}'))

            async for msg in Stream(reader, writer, thisPeer, TorrentData):
                if isinstance(msg, Chock):
                    thisPeer.is_chocked = True
                    # send interested
                    writer.write(Interested.encode())
                    await writer.drain()
                elif isinstance(msg, Unchock):
                    thisPeer.is_chocked = False

                # the peer is interested in what I have
                elif isinstance(msg, Interested):
                    await chocking_manager.report_interested(thisPeer)
                elif isinstance(msg, NotInterested):
                    await chocking_manager.report_uninterested(thisPeer)

                elif isinstance(msg, Have):
                    msg: Have
                    assert not thisPeer.is_seed  # a seed will not send have msg. if a peer completes its bitfield don't consider him a seed.
                    thisPeer.have_pieces[msg.piece_index] = True
                    if all(thisPeer.have_pieces):
                        thisPeer.is_seed = True
                        print('seed')

                    async with asyncio.Lock():
                        piece_picker.change_availability(msg.piece_index, 1)

                elif isinstance(msg, Bitfield):
                    msg: Bitfield
                    if all(msg.bitfield):
                        thisPeer.is_seed = True
                        print('seed')
                    else:
                        print('not seed')

                    async with asyncio.Lock():
                        for index in range(len(msg.bitfield)):
                            if msg.bitfield[index] and not thisPeer.have_pieces[index]:
                                piece_picker.change_availability(index, 1)

                    thisPeer.have_pieces |= msg.bitfield

                # TODO implement uploading
                elif isinstance(msg, Request):
                    ...

                # TODO implement uploading
                elif isinstance(msg, Cancel):
                    ...

                # TODO add port type

                elif isinstance(msg, Piece):
                    msg: Piece
                    # update statistics
                    TorrentData.downloaded += len(msg.data)
                    thisPeer.uploaded += len(msg.data)

                    # check if I requested this block?
                    for block in thisPeer.pipelined_requests:
                        if block.is_equal(msg.piece_index, msg.begin, msg.length):
                            thisPeer.pipelined_requests.remove(block)
                            break
                    else:
                        for block in thisPeer.endgame_request_msg_sent:
                            if block.is_equal(msg.piece_index, msg.begin, msg.length):
                                break
                        else:
                            print('received wrong block!')
                            raise AssertionError

                    # update pipeline size
                    thisPeer.update_upload_rate(len(msg.data))

                    if thisPeer.is_in_endgame:
                        if block in thisPeer.endgame_cancel_msg_sent:
                            thisPeer.MAX_PIPELINE_SIZE -= 1
                            Peer.MAX_ENDGAME_REQUESTS -= 1
                        else:
                            thisPeer.endgame_cancel_msg_sent.add(block)

                    await piece_picker.report_block(block, (msg.data, thisPeer.address))

                # send requests
                if not thisPeer.is_in_endgame:
                    if len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE / 2:  # save some cpu usage
                        while not thisPeer.is_chocked and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE:
                            if isinstance((request := await piece_picker.get_block(thisPeer.have_pieces)), Block):
                                writer.write(Request.encode(request.index, request.begin, request.length))
                                await writer.drain()
                                thisPeer.pipelined_requests.add(request)

                                await asyncio.sleep(0.01)  # giving time for other connections to get pieces
                            else:
                                break

                if thisPeer.is_in_endgame:
                    while not thisPeer.is_chocked and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE:
                        seed(hash(thisPeer))
                        # available_blocks = all blocks - blocks I already requested - blocks somebody else got
                        available_blocks = thisPeer.endgame_blocks - thisPeer.endgame_request_msg_sent - piece_picker.endgame_received_blocks
                        available_blocks = list(available_blocks)
                        available_blocks.sort(key=lambda x: piece_picker.pieces_map[x.index].peer_count + random(), reverse=True)
                        print(len(Peer.peer_instances), thisPeer.peer_id, thisPeer.is_seed, len(available_blocks), piece_picker.num_of_pieces_left, Peer.peer_instances)
                        if not available_blocks:
                            break

                        request = available_blocks.pop()
                        thisPeer.endgame_request_msg_sent.add(request)

                        thisPeer.pipelined_requests.add(request)
                        writer.write(Request.encode(request.index, request.begin, request.length))
                        await writer.drain()

                        await asyncio.sleep(0.01)  # giving time for other connections to get pieces

                    # send cancels
                    requested_not_canceled = thisPeer.endgame_request_msg_sent - thisPeer.endgame_cancel_msg_sent
                    need_to_cancel = requested_not_canceled.intersection(piece_picker.endgame_received_blocks)
                    for block in need_to_cancel:
                        writer.write(Cancel.encode(block.index, block.begin, block.length))
                        await writer.drain()
                    thisPeer.endgame_cancel_msg_sent.update(need_to_cancel)

                    # request more blocks and don't get stuck on specific blocks
                    Peer.MAX_ENDGAME_REQUESTS += len(need_to_cancel)
                    thisPeer.MAX_PIPELINE_SIZE += len(need_to_cancel)

                '''
                writer.write(b'\x00\x00\x00\x00')
                await writer.drain()
                '''

        except (AssertionError, struct.error) as e:  # protocol error, TODO reduce reputation this peer
            print('bad peer! ', e)
            ...

        except (asyncio.exceptions.CancelledError, asyncio.exceptions.TimeoutError) as e:
            pass

        except Exception as e:  # general error
            import traceback
            print('general error! ', traceback.format_exc())
            # raise e

        finally:
            print("\033[91m{}\033[00m".format(f'failed {repr(thisPeer)}'))
            # print("Closing the connection.")
            writer.close()
            await writer.wait_closed()

            await chocking_manager.report_uninterested(thisPeer)

            # return requested blocks
            for block in thisPeer.pipelined_requests:
                piece_picker.deselect_block(block)

            # change availability
            if not thisPeer.is_in_endgame:
                async with asyncio.Lock():
                    for bit in thisPeer.have_pieces:
                        if bit:
                            piece_picker.change_availability(bit, -1)

            if thisPeer in Peer.peer_instances:
                Peer.peer_instances.remove(thisPeer)
            del thisPeer

    except Exception as e:  # general error related to the connection
        print('ERROR: ', e)
        # raise e
        return

