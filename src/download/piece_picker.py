from src.torrent.torrent_object import Torrent
from .data_structures import *
from src.peer.message_types import *
from src.peer.peer_object import Peer

from typing import List, Dict
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


class PriorityBucket:
    keys = []

    def __init__(self, pieces_list: List[PiecePos] = None):
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
        if not self.priority:
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

    '''
    def get_piece(self):
        if self.is_empty:
            return None
        self.length -= 1
        return self.pieces_list.pop()
    '''


class PiecePicker(object):
    def __init__(self, TorrentData: Torrent, sequential: bool = False) -> None:
        self.TorrentData = TorrentData
        self.results_queue = BetterQueue()

        self.sequential = sequential
        self.is_in_endgame = False

        # will be iterated like this: for key in sorted(self.buckets_dict.keys()): ...
        # should not be extremely expensive because the availability range is usually 10-20
        self.buckets_dict: Dict[int, PriorityBucket] = defaultdict(PriorityBucket)  # dict of priority (availability) -> priority buckets

        self.pieces_map: List[PiecePos] = [PiecePos(i) for i in range(len(TorrentData.piece_hashes))]  # list of PiecePos
        temp_list = self.pieces_map[:]
        shuffle(temp_list)
        self.buckets_dict[0] = PriorityBucket(temp_list)  # all pieces start with availability 0

        self.downloading: Dict[int, DownloadingPiece] = dict()  # piece index -> DownloadingPiece
        self.pending_blocks: Dict[int, Tuple[Block, float]] = dict()

        self.num_of_pieces_left = len(TorrentData.piece_hashes)

    def sort_downloading(self):
        # prioritize pieces that are closest to completion
        self.downloading = dict(sorted(self.downloading.items(), key=lambda x: x[1].priority))

    async def get_block(self, have_mask: bitstring.bitarray) -> Block:
        async with asyncio.Lock():
            # search the downloading pieces first
            for index, piece in self.downloading.items():
                if have_mask[index]:
                    if isinstance((block := piece.get_next_request()), Block):
                        self.pending_blocks[id(block)] = (block, time.time())
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
                        # transfer the piece to downloading dict
                        self.downloading[piece.piece_index] = newPiece

                        # sort the downloading dict
                        # the most requested piece (in theory) will be the first one
                        # self.sort_downloading()  # no need to sort, the first pieces should be the most requested

                        block = newPiece.get_next_request()
                        self.pending_blocks[id(block)] = (block, time.time())
                        return block

            # TODO add endgame mode
            if endgame_time:
                print('ENDGAME !!!', len(self.pending_blocks))
                self.is_in_endgame = True

            # get endgame block
            '''
            sorted_pending_blocks = sorted(self.pending_blocks.values(), key=lambda x: x[1], reverse=True)
            for block, _ in sorted_pending_blocks:
                if have_mask[block.index]:
                    # self.pending_blocks.pop(id(block))
                    return block
            '''

            if self.num_of_pieces_left == 0:  # confirmed by disk IO thread
                print('finished!!')
                quit()

    async def report_block(self, block: Block):
        async with asyncio.Lock():
            # the stream already verified the block and made sure we requested it
            self.pending_blocks.pop(id(block))

            # print(len(self.downloading), len(self.pending_blocks))

            piece = self.downloading[block.index]
            piece.current_block += 1
            # check if the piece is complete
            # print(piece.current_block, piece.blocks_length)
            if piece.is_completed:

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
            self.sort_downloading()

    def change_availability(self, piece_index: int, difference: int):
        # this function is called from within an asyncio.Lock()

        # get the bucket the piece is in
        piece: PiecePos = self.pieces_map[piece_index]
        bucket: PriorityBucket = self.buckets_dict[piece.peer_count]

        bucket.remove(piece)
        piece.peer_count += difference
        self.buckets_dict[piece.peer_count].add_piece(piece)

    def deselect_block(self, block: Block):
        self.pending_blocks.pop(id(block))
        self.downloading[block.index].deselect_block(block)

    @staticmethod
    async def send_have(piece_index: int):
        for peer in Peer.peer_instances:
            if not peer.have_pieces[piece_index]:
                have_msg: bytes = Have.encode(piece_index)
                await peer.have_msg_queue.put(have_msg)








