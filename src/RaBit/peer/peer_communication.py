from ..app_data import db_utils
from ..torrent.torrent_object import Torrent
from ..download.piece_picker import PiecePicker, Block
from ..download.upload_in_download import TitForTat
from ..file.file_object import File
from .peer_object import Peer
from .handshake import handshake, open_tcp_connection
from .message_types import *

import asyncio
import struct
from random import random, seed
from typing import Tuple, List, Any

_BUFFER_SIZE = 4096
_MAX_REQUESTS = 500


class Stream:
    def __init__(self, reader, thisPeer, TorrentData: Torrent):
        self.reader = reader
        self.thisPeer = thisPeer
        self.buffer = b''
        self.bitfield_len = len(TorrentData.piece_hashes)

    def __consume(self, msg_length):
        self.buffer = self.buffer[msg_length:]

    def __aiter__(self):
        return self

    async def __anext__(self) -> Any:
        """
        reads and formats messages from an outgoing peer
        :return: msg instance corresponding to the type
        """
        while True:
            assert not self.thisPeer.found_dirty  # get rid of a connection with a dirty peer

            data = b''

            async def send_control_msg():
                async with asyncio.Lock():
                    while self.thisPeer.control_msg_queue:
                        self.thisPeer.writer.write(self.thisPeer.control_msg_queue.pop())
                        await self.thisPeer.writer.drain()

            async def get_data():
                nonlocal data
                data = await self.reader.read(_BUFFER_SIZE)

            if self.thisPeer.control_msg_queue:
                await send_control_msg()

            insufficient = False
            if len(self.buffer) >= 4:
                length = struct.unpack('>I', self.buffer[0:4])[0] + 4
                if length == 4:  # keepalive
                    self.__consume(4)
                    continue

                # defend overflow
                if length > MAX_ALLOWED_MSG_SIZE:
                    raise AssertionError

                if len(self.buffer) < length:
                    insufficient = True

                else:
                    msg = self.buffer[:length]
                    msg_id = msg[4]

            if insufficient or len(self.buffer) < 4:
                await get_data()
                self.buffer += data
                if not self.buffer:
                    raise StopAsyncIteration
                continue

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
                return Bitfield.decode(msg, self.bitfield_len)
            elif msg_id == REQUEST:
                return Request.decode(msg)
            elif msg_id == PIECE:
                return Piece.decode(msg)
            elif msg_id == CANCEL:
                return Cancel.decode(msg)

            else:
                # unsupported message
                raise AssertionError


async def tcp_wire_communication(peerData: Tuple, TorrentData: Torrent, session, file_manager: File, piece_picker: PiecePicker, chocking_manager: TitForTat) -> None:
    """
    main function for communicating with a peer
    :param peerData: geodata of the peer
    :param TorrentData: torrent data instance
    :param session: DownloadingSession instance with session stats
    :param file_manager: File instance managing disk IO operations
    :param piece_picker: PiecePicker instance for requesting and reporting blocks
    :param chocking_manager: tit-for-tat algorithm for chocking management
    :return: None
    """
    address, city, distance = peerData
    try:
        reader, writer = await asyncio.wait_for(open_tcp_connection(address), timeout=3)
        if (reader, writer) == (None, None):
            return

        thisPeer = Peer(writer, TorrentData, address, city)
        request_queue: List[Tuple[int, int, int]] = []
        balance_counter = 0
        try:
            # start with a handshake
            peer_id = await asyncio.wait_for(handshake(TorrentData, reader, writer), timeout=10)
            # validate the protocol
            assert peer_id

            thisPeer.add_peer_id(peer_id)

            # TODO now send bitfield / have all/none and fast allowed after fast extension support
            writer.write(Bitfield.encode(piece_picker.FILE_STATUS[session.TorrentData.info_hash]))
            await writer.drain()

            # send interested
            # I am always interested in the peer
            writer.write(Interested.encode())
            await writer.drain()
            print("\033[92m{}\033[00m".format(f'connected {repr(thisPeer)}'))

            async for msg in Stream(reader, thisPeer, TorrentData):
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

                elif isinstance(msg, Request):
                    if not thisPeer.am_chocked:
                        if piece_picker.FILE_STATUS[msg.piece_index]:
                            request_queue.append((msg.piece_index, msg.begin, msg.length))
                            if len(request_queue) > _MAX_REQUESTS:
                                # attempted dos detected
                                print('banned ', thisPeer.address[0])
                                db_utils.BannedPeersDB().insert_ip(thisPeer.address[0])
                                raise AssertionError
                        else:
                            pass

                elif isinstance(msg, Cancel):
                    if (details := (msg.piece_index, msg.begin, msg.length)) in request_queue:
                        request_queue.remove(details)
                    else:
                        pass

                # TODO add port type

                elif isinstance(msg, Piece):
                    msg: Piece
                    # update statistics
                    session.downloaded += len(msg.data)
                    thisPeer.uploaded += len(msg.data)
                    balance_counter += 1

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

                else:
                    while not thisPeer.is_chocked and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE:
                        seed(hash(thisPeer))
                        # available_blocks = all blocks - blocks I already requested - blocks somebody else got - pipelined requests (from before endgame)
                        available_blocks = thisPeer.endgame_blocks - thisPeer.endgame_request_msg_sent - piece_picker.endgame_received_blocks - thisPeer.pipelined_requests
                        available_blocks = list(available_blocks)
                        available_blocks.sort(key=lambda x: piece_picker.pieces_map[x.index].peer_count + random(), reverse=True)
                        if not available_blocks:
                            break

                        request = available_blocks.pop()
                        thisPeer.endgame_request_msg_sent.add(request)

                        thisPeer.pipelined_requests.add(request)
                        writer.write(Request.encode(request.index, request.begin, request.length))
                        await writer.drain()

                        await asyncio.sleep(0.1)  # giving *more* time for other connections to get pieces

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

                # fulfill requests
                while request_queue and balance_counter:
                    # don't contribute more than the peer's contribution
                    params = file_manager.get_piece(*request_queue.pop())
                    writer.write(Piece.encode(*params))
                    await writer.drain()
                    balance_counter -= 1
                    # update statistics
                    session.uploaded += len(params[2])
                    thisPeer.downloaded += len(params[2])
                    print('fulfilled request!')

                '''
                writer.write(b'\x00\x00\x00\x00')
                await writer.drain()
                '''

        except (AssertionError, struct.error) as e:  # protocol error, TODO reduce reputation this peer
            print('bad peer! ', e)
            ...

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            pass

        except Exception as e:  # general error
            import traceback
            print('general error! ', traceback.format_exc())
            # raise e

        finally:
            print("\033[91m{}\033[00m".format(f'failed {repr(thisPeer)}'))
            # print("Closing the connection.")
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

            if thisPeer in Peer.peer_instances[session.TorrentData.info_hash]:
                Peer.peer_instances[session.TorrentData.info_hash].remove(thisPeer)
            else:
                return

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

            del thisPeer

    except Exception as e:  # general error related to the connection
        # print('ERROR: ', e)
        # raise e
        return

