from src.torrent.torrent_object import Torrent
from .data_structures import *
from src.peer.message_types import *
from src.peer.peer_object import Peer

from typing import List, Dict, Set
import bitstring
from dataclasses import dataclass
import time
import threading
import asyncio
import queue
from collections import defaultdict
from random import shuffle, choice


class BetterQueue(asyncio.Queue):
    def __init__(self, maxsize: int = 0):
        super().__init__(maxsize)
        self.size = 0

    async def put(self, item):
        await super().put(item)
        self.size += 1

    async def get(self):
        item = await super().get()
        self.size -= 1
        return item


@dataclass
class PiecePos(object):
    piece_index: int  # piece index
    peer_count: int = 0  # availability, position in priority bucket


class PriorityBucket(object):
    keys: List[int] = []
    buckets: List = []

    def __init__(self, pieces_list: List[PiecePos] = None):
        PriorityBucket.buckets.append(self)
        if pieces_list:
            self.pieces_list: List[PiecePos] = pieces_list  # pieces "stack"
            self.length = len(pieces_list)
            self.priority = pieces_list[0].peer_count
            PriorityBucket.keys.append(self.priority)
            PriorityBucket.keys.sort()
        else:
            self.pieces_list: List[PiecePos] = []
            self.length = 0
            self.priority = None

    @property
    def is_empty(self):
        return not self.length

    def add_piece(self, piece: PiecePos):
        self.length += 1
        if self.priority is None:
            self.priority = piece.peer_count
            PriorityBucket.keys.append(piece.peer_count)
            PriorityBucket.keys.sort()

        self.pieces_list.append(piece)

    def remove(self, piece: PiecePos):
        self.pieces_list.remove(piece)
        self.length -= 1

    def add_pieces(self, pieces: List[PiecePos]):
        for piece in pieces:
            self.add_piece(piece)


class PiecePicker(object):
    FILE_STATUS: Dict[bytes, bitstring.BitArray] = dict()

    def __init__(self, TorrentData: Torrent, session, bitarray: bitstring.bitarray, index_range: List[int] = None) -> None:
        self.TorrentData = TorrentData
        self.results_queue = BetterQueue()

        self.session = session
        PiecePicker.FILE_STATUS[TorrentData.info_hash] = bitarray

        self.is_in_endgame = False
        self.endgame_received_blocks: Set = set()  # blocks received while in endgame mode

        # will be iterated like this: for key in sorted(self.buckets_dict.keys()): ...
        # should not be extremely expensive because the availability range is usually 10-20
        self.buckets_dict: Dict[int, PriorityBucket] = defaultdict(PriorityBucket)  # dict of priority (availability) -> priority buckets

        index_range = range(len(TorrentData.piece_hashes)) if index_range is None else index_range
        self.pieces_map: Dict[int, PiecePos] = {i: PiecePos(i) for i in index_range}  # list of PiecePos
        items = list(self.pieces_map.items())
        shuffle(items)
        self.pieces_map = {item[0]: item[1] for item in items}

        self.buckets_dict[0] = PriorityBucket(list(self.pieces_map.values()))  # all pieces start with availability 0
        self.buckets_dict[0].priority = 0

        self.downloading: Dict[int, DownloadingPiece] = dict()  # piece index -> DownloadingPiece
        self.pending_blocks: Dict[Block, Tuple[Block, float]] = dict()

        self.num_of_pieces_left = len(self.pieces_map)
        self.last_data_received = time.time()

    def sort_downloading(self):
        # prioritize pieces that are closest to completion
        self.downloading = dict(sorted(self.downloading.items(), key=lambda x: x[1].priority))

    async def get_block(self, have_mask: bitstring.bitarray) -> Block:
        if self.is_in_endgame:
            return None
        async with asyncio.Lock():
            # search the downloading pieces first
            for index, piece in self.downloading.items():
                if have_mask[index]:
                    if isinstance((block := piece.get_next_request()), Block):
                        self.pending_blocks[block] = (block, time.time())
                        return block

            # add another piece to the downloading dict
            endgame_time = True  # will stay true if there are no pieces
            for key in PriorityBucket.keys:
                bucket: PriorityBucket = self.buckets_dict[key]
                for piece in bucket.pieces_list:
                    endgame_time = False
                    if have_mask[piece.piece_index]:
                        bucket.remove(piece)

                        newPiece = DownloadingPiece(piece.piece_index, self.TorrentData.info[b'piece length'])
                        # remove excessive blocks from the last piece
                        if piece.piece_index == len(self.TorrentData.piece_hashes) - 1:
                            extra = len(self.TorrentData.piece_hashes) * self.TorrentData.info[b'piece length'] - self.TorrentData.length
                            while extra > BLOCK_SIZE:
                                extra -= BLOCK_SIZE
                                newPiece.blocks.pop()
                                newPiece.blocks_length -= 1
                            newPiece.blocks[-1].length -= extra

                        # transfer the piece to downloading dict
                        self.downloading[piece.piece_index] = newPiece

                        # sort the downloading dict
                        # the most requested piece (in theory) will be the first one
                        # self.sort_downloading()  # no need to sort, the first pieces should be the most requested

                        block = newPiece.get_next_request()
                        self.pending_blocks[block] = (block, time.time())
                        return block

            # TODO add endgame mode
            if endgame_time and not self.is_in_endgame:
                self.endgame()
            return None

    async def report_block(self, block: Block, add_data_args: Tuple[bytes, Tuple[str, int]]):
        async with asyncio.Lock():
            # the stream already verified the block and made sure we requested it
            self.last_data_received = time.time()
            if not block.add_data(*add_data_args) or PiecePicker.FILE_STATUS[self.TorrentData.info_hash][block.index]:
                self.session.wasted += len(add_data_args[0])
                print('got duplicate')
                return

            if self.is_in_endgame:
                self.endgame_received_blocks.add(block)
            else:
                self.pending_blocks.pop(block)

            piece = self.downloading[block.index]  # all endgame pieces must be in this dict
            # check if the piece is complete
            # print(piece.current_block, piece.blocks_length)
            if piece.is_completed:
                # print('have ', piece.index, len(piece.get_data))
                if not self.is_in_endgame:
                    self.downloading.pop(piece.index)

                with threading.Lock():
                    # pass to disk IO thread
                    await self.results_queue.put(piece)

    async def add_failed_piece(self, piece: DownloadingPiece):
        # TODO record failed piece block hashes and store them
        # re-add failed pieces directly to the download dict with a toggled urgent flag
        # to download it successfully and ban the responsible peers as soon as possible
        piece.urgent = True
        async with asyncio.Lock():
            self.downloading[piece.index] = piece
            if not self.is_in_endgame:
                self.sort_downloading()
            else:
                set_blocks = set(piece.blocks)
                self.endgame_received_blocks -= set_blocks
                for peer in Peer.peer_instances[self.TorrentData.info_hash]:
                    peer.endgame_request_msg_sent -= set_blocks

                for block in piece.blocks:
                    self.add_endgame_block(block)

    def change_availability(self, piece_index: int, difference: int):
        # this function is called from within an asyncio.Lock()
        if self.is_in_endgame:
            return

        if piece_index in self.downloading or PiecePicker.FILE_STATUS[self.TorrentData.info_hash][piece_index]:
            return

        # get the bucket the piece is in
        piece: PiecePos = self.pieces_map[piece_index]
        bucket: PriorityBucket = self.buckets_dict[piece.peer_count]

        bucket.remove(piece)
        piece.peer_count += difference
        self.buckets_dict[piece.peer_count].add_piece(piece)

    def deselect_block(self, block: Block):
        if not self.is_in_endgame:
            self.pending_blocks.pop(block)
        else:
            self.add_endgame_block(block)
        self.downloading[block.index].deselect_block(block)

    def endgame(self):
        unfiltered_blocks = list(self.pending_blocks.keys())
        for piece in self.downloading.values():
            while isinstance((block := piece.get_next_request()), Block):
                unfiltered_blocks.append(block)

        print('ENDGAME !!!')
        self.is_in_endgame = True

        for peer in Peer.peer_instances[self.TorrentData.info_hash]:
            peer.is_in_endgame = True
            peer.endgame_blocks = set(filter(lambda x: peer.have_pieces[x.index], unfiltered_blocks))

    def add_endgame_block(self, block: Block):
        for peer in Peer.peer_instances[self.TorrentData.info_hash]:
            if peer.have_pieces[block.index]:
                peer.endgame_blocks.add(block)

    async def send_have(self, piece_index: int):
        async with asyncio.Lock():
            for peer in Peer.peer_instances[self.TorrentData.info_hash]:
                if not peer.have_pieces[piece_index]:
                    have_msg: bytes = Have.encode(piece_index)
                    peer.control_msg_queue.append(have_msg)

    @staticmethod
    async def send_chock(peer: Peer):
        async with asyncio.Lock():
            peer.am_chocked = True
            chock_msg: bytes = Chock.encode()
            peer.control_msg_queue = list(filter(lambda x: x[4] == 4, peer.control_msg_queue))
            peer.control_msg_queue.append(chock_msg)
            print('chocked ', repr(peer))

    @staticmethod
    async def send_unchock(peer: Peer):
        async with asyncio.Lock():
            peer.am_chocked = False
            unchock_msg: bytes = Unchock.encode()
            peer.control_msg_queue = list(filter(lambda x: x[4] == 4, peer.control_msg_queue))
            peer.control_msg_queue.append(unchock_msg)
            print('unchocked ', repr(peer))

    @property
    def get_health(self):
        return round((1 - self.buckets_dict[0].length / len(self.TorrentData.piece_hashes)) * 100, 2)
