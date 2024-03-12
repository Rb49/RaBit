from typing import Dict, Tuple
from src.torrent.torrent_object import Torrent
from .peer_object import Peer
from .handshake import handshake, open_tcp_connection
from .message_types import *
from src.download.piece_picker import PiecePicker, Block
import asyncio
import struct

_BUFFER_SIZE = 4096


class Stream(object):
    def __init__(self, reader, TorrentData: Torrent):
        self.reader = reader
        self.buffer = b''
        self.TorrentData = TorrentData

    def __consume(self, msg_length):
        self.buffer = self.buffer[msg_length:]

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            while True:
                data = await self.reader.read(_BUFFER_SIZE)
                self.buffer += data
                if not data and not self.buffer:
                    ...
                    # raise StopAsyncIteration

                length = struct.unpack('>I', self.buffer[0:4])[0] + 4
                if length == 4:  # keepalive, ignore
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

        except struct.error:
            raise AssertionError


async def tcp_wire_communication(peerData: Tuple, TorrentData: Torrent, piece_picker: PiecePicker):

    # TODO remove pieces_dict !! use increase / decrease availability method instead

    address, city, distance = peerData
    try:
        reader, writer = await asyncio.wait_for(open_tcp_connection(address), timeout=3)
        if (reader, writer) == (None, None):
            return

        thisPeer = Peer(TorrentData, address, city)
        try:
            # start with a handshake
            peer_id = await handshake(TorrentData, reader, writer)
            # validate the protocol
            assert peer_id

            thisPeer.peer_id = peer_id

            # TODO now send bitfield / have all/none and fast allowed after fast extension support

            # send interested
            # I am always interested in the peer
            writer.write(struct.pack('>IB', 1, 2))
            await writer.drain()
            print("\033[92m{}\033[00m".format(f'connected {address}, {city}'))

            async for msg in Stream(reader, TorrentData):
                if isinstance(msg, Chock):
                    thisPeer.is_chocked = True
                    # send interested
                    writer.write(struct.pack('>IB', 1, 2))
                    await writer.drain()
                elif isinstance(msg, Unchock):
                    thisPeer.is_chocked = False

                # the peer is interested in what I have
                elif isinstance(msg, Interested):
                    thisPeer.am_interested = True
                elif type(msg) is NotInterested:
                    thisPeer.am_interested = False

                elif isinstance(msg, Have):
                    msg: Have
                    assert not thisPeer.is_seed  # a seed will not send have msg. if a peer completes its bitfield don't consider him a seed.

                    thisPeer.have_pieces[msg.piece_index] = True
                    async with asyncio.Lock():
                        await piece_picker.change_availability(msg.piece_index, 1)

                elif isinstance(msg, Bitfield):
                    msg: Bitfield
                    if all(msg.bitfield):
                        thisPeer.is_seed = True
                        print('seed')
                        # continue

                    else:
                        print('not seed')
                        async with asyncio.Lock():
                            for index in range(len(msg.bitfield)):
                                if msg.bitfield[index] and not thisPeer.have_pieces[index]:
                                    await piece_picker.change_availability(index, 1)

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

                    # check if I requested this block?
                    for block in thisPeer.pipelined_requests:
                        if block.is_equal(msg.piece_index, msg.begin, msg.length):
                            break
                    else:
                        print('received wrong block!')
                        raise AssertionError

                    # update pipeline size
                    thisPeer.update_download_rate(len(msg.data))

                    thisPeer.pipelined_requests.remove(block)
                    block.add_data(msg.data, thisPeer.address)
                    await piece_picker.report_block(block)

                while not thisPeer.is_chocked and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE:
                    if isinstance((request := await piece_picker.get_block(thisPeer.have_pieces)), Block):
                        # print(repr(request))
                        request_packet = struct.pack('>IBIII', 13, 6, request.index, request.begin, request.length)
                        writer.write(request_packet)
                        await writer.drain()
                        thisPeer.pipelined_requests.append(request)

                        await asyncio.sleep(0.01)  # giving time for other connections to get pieces

                    else:  # endgame logic here
                        ...


        except AssertionError as e:  # protocol error, blacklist this peer
            # print(e)
            pass
        except ConnectionError as e:  # connection error
            # print(e)
            pass
        except asyncio.CancelledError as e:  # the task was canceled (probably because the download was finished)
            # print(e)
            pass
        except Exception as e:  # general error
            print(e)
            raise e

        finally:
            print("\033[91m{}\033[00m".format(f'failed {address}, {city}'))
            # print("Closing the connection.")
            writer.close()
            await writer.wait_closed()

            # change availability
            if not thisPeer.is_seed:
                async with asyncio.Lock():
                    for bit in thisPeer.have_pieces:
                        if bit:
                            await piece_picker.change_availability(bit, -1)

            # return requested blocks
            for block in thisPeer.pipelined_requests:
                piece_picker.deselect_block(block)

    except Exception as e:  # general error related to the connection
        print(e)
        # raise e
        return

    finally:
        return
