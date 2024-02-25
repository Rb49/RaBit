import copy
import math

from src.torrent.torrent_object import Torrent
from .endgame import EndgameManager
from .peer_object import Peer
from src.file.data_structures import Block
from .utils import *

from typing import Dict, List
import asyncio
import struct
import bitstring
import time
import queue
import threading
from random import shuffle

__BUFFER_SIZE = 4096
__MAX_TIMEOUT = 1000000000000000


async def tcp_wire_communication(peerData: Tuple, TorrentData: Torrent, pieces_dict: Dict, failed_queue: asyncio.Queue, results_queue, Endgame: EndgameManager):
    address, city, distance = peerData
    endgame_blocks: List[Block] = []
    try:
        thisPeer = Peer(TorrentData, address, city)

        request_data = build__handshake_packet(TorrentData.info_hash, TorrentData.peer_id)

        reader, writer = await asyncio.wait_for(open_tcp_connection(address), timeout=3)

        if reader:
            try:
                # start with a handshake
                writer.write(request_data)
                await writer.drain()
                data = await reader.read(68)  # len of handshake

                # validate the protocol
                peer_id = validate_handshake(data, TorrentData.info_hash)
                assert peer_id

                thisPeer.peer_id = peer_id

                # send interested
                writer.write(struct.pack('>IB', 1, 2))
                await writer.drain()
                thisPeer.am_interested = True
                print('connected', address, city)

                buffer = b''
                finished = False
                last_time = time.time()
                LEN = len(TorrentData.piece_hashes)

                while not finished:
                    data = await reader.read(__BUFFER_SIZE)
                    buffer += data
                    if not data and not buffer:
                        ...
                        # print('breaking', address, city)
                        # break

                    length = struct.unpack('>I', buffer[0:4])[0] + 4
                    if length == 4:  # keepalive, ignore
                        buffer = buffer[4:]

                    if len(buffer) < length:
                        continue

                    msg = buffer[0: length]
                    buffer = buffer[length:]

                    if msg[4] == 0:  # chock
                        thisPeer.is_chocked = True
                        # send interested
                        writer.write(struct.pack('>IB', 1, 2))
                        await writer.drain()
                        thisPeer.am_interested = True

                    elif msg[4] == 1:  # unchoke
                        thisPeer.is_chocked = False

                    elif msg[4] == 4:  # have
                        _, _, index = struct.unpack('>IBI', msg)
                        thisPeer.have_pieces[index] = True

                        async with asyncio.Lock():
                            if not thisPeer.have_pieces[index] and index in pieces_dict:
                                pieces_dict[index].rarity += 1

                    elif msg[4] == 5:  # bitfield
                        _, _, bitfield = struct.unpack(f'>IB{length - 5}s', msg)
                        bitfield = bitstring.BitArray(bytes=bitfield)
                        bitfield = bitfield[0: len(TorrentData.piece_hashes)]  # remove padding

                        if all(bitfield):
                            thisPeer.is_seed = True

                        if not thisPeer.is_seed:
                            async with asyncio.Lock():
                                for index in range(len(bitfield)):
                                    if bitfield[index] and not thisPeer.have_pieces[index] and index in pieces_dict:
                                        pieces_dict[index].rarity += 1

                        thisPeer.have_pieces |= bitfield

                    elif msg[4] == 7:  # piece
                        _, _, index, begin, data = struct.unpack(f'>IBII{length - 13}s', msg)
                        # update stats of torrent
                        TorrentData.downloaded += len(data)

                        # update pipeline size
                        thisPeer.update_download_rate(len(data))

                        # check if I want this block?
                        for block in thisPeer.pipelined_requests:
                            # print(block, index, begin, len(data))
                            if block.is_equal(index, begin, len(data)):
                                break
                        else:
                            print('received wrong block!', address, city)
                            # TODO add address to blacklist
                            raise ConnectionAbortedError

                        # remove from the list
                        thisPeer.pipelined_requests.remove(block)

                        # add to the piece queue
                        async with asyncio.Lock():
                            piece = pieces_dict[index]

                            await Endgame.have_block(block)

                            if not piece.add_block(begin, data):
                                print('got duplicate block!')

                            elif piece.completed:
                                print(f'got piece. {round((results_queue.size / LEN) * 100, 2)}%')

                                with threading.Lock():
                                    # note this is a reference to piece
                                    results_queue.put(piece)

                                # remove the completed piece reference from pieces dict
                                pieces_dict.pop(index)

                        for block in endgame_blocks:
                            if block.is_equal(index, begin, len(data)):
                                await Endgame.have_block(block)
                                thisPeer.endgame_received[endgame_blocks.index(block)] = True
                                if Endgame.finished:
                                    print('Finished!')
                                    finished = True
                                break

                        # TODO pass un-answered requests to someone else
                        for block in thisPeer.pipelined_requests:
                            if time.time() - block.time_requested > __MAX_TIMEOUT:
                                if not thisPeer.is_in_endgame:
                                    # send cancel
                                    cancel_packet = struct.pack('>IBIII', 13, 8, block.piece_index, block.begin,
                                                                block.length)
                                    writer.write(cancel_packet)
                                    await writer.drain()

                                    print('passed hot potato')
                                    block.time_requested = 0
                                    await failed_queue.put(block)

                                    thisPeer.pipelined_requests.remove(block)
                                elif block in endgame_blocks:  # do not pass endgame timeout messages to others
                                    thisPeer.pipelined_requests.remove(block)

                    # sort every 1 seconds
                    if time.time() - last_time > 1:
                        last_time = time.time()
                        async with asyncio.Lock():
                            pieces_dict = dict(sorted(pieces_dict.items(), key=lambda x: x[1].priority))

                    # --------------

                    # NOT IN ENDGAME MODE
                    if not thisPeer.is_in_endgame:
                        while not thisPeer.is_chocked and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE:
                            request: None = None
                            if not failed_queue.empty():
                                request: Block = await failed_queue.get()

                            else:
                                all_blocks_requested = True
                                async with asyncio.Lock():
                                    for piece in pieces_dict.values():
                                        if thisPeer.have_pieces[piece.piece_index]:
                                            request: Block = piece.get_block()
                                            if request is None:
                                                continue
                                            else:
                                                break
                                        elif all_blocks_requested:
                                            if any(piece.data) is not Block:
                                                all_blocks_requested = False

                            if request is None:
                                if all_blocks_requested:
                                    # this peer should now be standing by waiting for all peers to stand by too
                                    # thisPeer.toggle_endgame_ready()
                                    print('ready!')
                                    # print(Peer.endgame_ready)
                                    # if not all(Peer.endgame_ready):
                                    #    break

                                    # endgame mode should be activated now when all pieces have been requested
                                    if not await Endgame.enable_endgame(pieces_dict):
                                        break

                                    print('endgame on!')

                                    thisPeer.is_in_endgame = True
                                    endgame_blocks = await Endgame.get_endgame_blocks
                                    shuffle(endgame_blocks)  # to make sure all peers will not request the same blocks
                                    thisPeer.endgame_queue = endgame_blocks.copy()
                                    thisPeer.endgame_sent = bitstring.BitArray(bin='0' * len(endgame_blocks))
                                    thisPeer.endgame_received = bitstring.BitArray(bin='0' * len(endgame_blocks))
                                    break
                                else:
                                    break

                            request_packet = struct.pack('>IBIII', 13, 6, request.piece_index, request.begin,
                                                         request.length)
                            writer.write(request_packet)
                            await writer.drain()

                            request.time_requested = time.time()
                            thisPeer.pipelined_requests.insert(0, request)

                    # IN ENDGAME MODE
                    if thisPeer.is_in_endgame:
                        endgame_blocks = await Endgame.get_endgame_blocks
                        print(len(endgame_blocks))

                        print(Endgame.endgame_status, thisPeer.peer_id, len(thisPeer.endgame_queue))

                        # send requests from endgame queue
                        if thisPeer.is_chocked is False and len(thisPeer.pipelined_requests) < thisPeer.MAX_PIPELINE_SIZE and thisPeer.endgame_queue:
                            if not failed_queue.empty():
                                request: Block = await failed_queue.get()
                            else:
                                request: Block = thisPeer.endgame_queue.pop()
                                # check if someone else already received this block
                                if Endgame.endgame_status[endgame_blocks.index(request)] or not thisPeer.have_pieces[request.piece_index] or request in thisPeer.pipelined_requests:
                                    continue

                            request_packet = struct.pack('>IBIII', 13, 6, request.piece_index, request.begin, request.length)
                            writer.write(request_packet)
                            await writer.drain()

                            request.time_requested = time.time()
                            thisPeer.pipelined_requests.insert(0, request)
                            # update this peer tracking
                            thisPeer.endgame_sent[endgame_blocks.index(request)] = True
                        # print('hii')
                        # send cancels, without checking the pipeline limit
                        """
                        EXAMPLE:
                        status:    1 0 1 1 0
                        sent:      1 1 1 1 0
                        received:  1 0 0 1 0
                        sum:       0 0 1 0 0
                        need to send cancel for blocks that were received not by me but have been requested by me
                        """
                        bitarray = Endgame.endgame_status & thisPeer.endgame_sent & (~thisPeer.endgame_received)
                        # print(Endgame.endgame_status, thisPeer.endgame_sent, (~thisPeer.endgame_received))
                        for bit in bitarray:
                            if bit:
                                cancel: Block = endgame_blocks[bit]
                                cancel_packet = struct.pack('>IBIII', 13, 8, cancel.piece_index, cancel.begin,
                                                            cancel.length)
                                writer.write(cancel_packet)
                                await writer.drain()
                                # update peer tracking
                                thisPeer.endgame_received[bit] = True
                                print('canceled')
                                thisPeer.pipelined_requests.remove(cancel)

                        # await asyncio.sleep(1)

            except Exception as e:  # exception with peer
                # print('error ', e)
                # raise e
                pass

            finally:
                # print("Closing the connection.")
                writer.close()
                await writer.wait_closed()

                # return requests back to queue
                await put_back_requests(thisPeer, failed_queue, endgame_blocks)

                if not thisPeer.is_seed:
                    async with asyncio.Lock():
                        for bit in thisPeer.have_pieces:
                            if bit and bit in pieces_dict:
                                pieces_dict[bit].rarity -= 1

                del thisPeer
                return

    except Exception as e:  # exception with tcp connection
        print('failed', address, city)
        # raise e
        print('error ', e)
        pass
