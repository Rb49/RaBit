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
from collections import defaultdict
from random import shuffle


class BetterQueue(asyncio.Queue):
    """
    an async queue with extra functionality
    """
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
    """
    a small dataclass to represent a piece index and its availability for picking calculations
    """
    piece_index: int  # piece index
    peer_count: int = 0  # availability, position in priority bucket


class PriorityBucket(object):
    """
    a priority bucket containing a list of PiecePos sharing the same availability.
    the lower the priority (key) the rarer the piece is
    """
    keys: List[int] = []
    buckets: List = []

    def __init__(self, pieces_list: List[PiecePos] = None) -> None:
        """
        :param pieces_list: a number of PiecePos with the same availability
        :return: None
        """
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
    """
    monitors the state of the download.
    picks blocks for peers based on their pieces, availability, completion and urgency.
    builds completed pieces together and reports them to the disk IO manager.
    adds control messages (choke, unchoke, have) to the peers' control queues.
    and more.
    """
    FILE_STATUS: Dict[bytes, bitstring.BitArray] = dict()

    def __init__(self, TorrentData: Torrent, session, bitarray: bitstring.bitarray, index_range: List[int] = None) -> None:
        """
        :param TorrentData: torrent data instance
        :param session: DownloadingSession instance with some stats
        :param bitarray: the initial position of the downloaded files
        :param index_range: the range of missing pieces for a faster partial download
        :return: None
        """
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
        """
        sorts the self.downloading dict by priority
        """
        # prioritize pieces that are closest to completion
        self.downloading = dict(sorted(self.downloading.items(), key=lambda x: x[1].priority))

    async def get_block(self, have_mask: bitstring.bitarray) -> Block:
        """
        request a block from the remaining blocks
        a block is chosen using rarest-first strategy with priority to failed pieces
        :param have_mask: which pieces the peer can share
        :return: a Block instance | None if all blocks have been requested
        """
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

    async def report_block(self, block: Block, add_data_args: Tuple[bytes, Tuple[str, int]]) -> None:
        """
        report about receiving a block of data
        if the piece is complete send it to disk IO manager
        :param block: Block instance whose data has arrived
        :param add_data_args: data received + ip of sender (tuple)
        :return: None
        """
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

    async def add_failed_piece(self, piece: DownloadingPiece) -> None:
        """
        adds a piece that failed hash check to the downloading dict with an urgency flag
        :param piece: instance of a piece to be retested
        :return None
        """
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

    def change_availability(self, piece_index: int, difference: int) -> None:
        """
        changes the availability of a piece
        note: this function should be called from within an asyncio.Lock()
        :param piece_index: piece index in the torrent
        :param difference: with what value to increase the availability (can be negative)
        :return: None
        """
        if self.is_in_endgame:
            return

        if piece_index in self.downloading or PiecePicker.FILE_STATUS[self.TorrentData.info_hash][piece_index]:
            return

        # get the bucket the piece is in
        piece: PiecePos = self.pieces_map[piece_index]
        bucket: PriorityBucket = self.buckets_dict[piece.peer_count]
        if piece in bucket.pieces_list:
            bucket.remove(piece)
            piece.peer_count += difference
            self.buckets_dict[piece.peer_count].add_piece(piece)

    def deselect_block(self, block: Block) -> None:
        """
        deselects a block and pass it to be requested again
        """
        if not self.is_in_endgame:
            self.pending_blocks.pop(block)
        else:
            self.add_endgame_block(block)
        self.downloading[block.index].deselect_block(block)

    def endgame(self) -> None:
        """
        toggles endgame mode.
        calculates the remaining blocks and toggles endgame mode in all peers
        """
        unfiltered_blocks = list(self.pending_blocks.keys())
        for piece in self.downloading.values():
            while isinstance((block := piece.get_next_request()), Block):
                unfiltered_blocks.append(block)

        # print('ENDGAME !!!')
        self.is_in_endgame = True

        for peer in Peer.peer_instances[self.TorrentData.info_hash]:
            peer.is_in_endgame = True
            peer.endgame_blocks = set(filter(lambda x: peer.have_pieces[x.index], unfiltered_blocks))

    def add_endgame_block(self, block: Block):
        """
        adds a deselected block to the endgame blocks set
        """
        for peer in Peer.peer_instances[self.TorrentData.info_hash]:
            if peer.have_pieces[block.index]:
                peer.endgame_blocks.add(block)

    async def send_have(self, piece_index: int):
        """
        adds 'have' message to the queues of all peers that don't already have this piece
        """
        async with asyncio.Lock():
            for peer in Peer.peer_instances[self.TorrentData.info_hash]:
                if not peer.have_pieces[piece_index]:
                    have_msg: bytes = Have.encode(piece_index)
                    peer.control_msg_queue.append(have_msg)

    @staticmethod
    async def send_chock(peer: Peer):
        """
        adds 'chock' message to the queue of a peer
        """
        async with asyncio.Lock():
            peer.am_chocked = True
            chock_msg: bytes = Chock.encode()
            peer.control_msg_queue = list(filter(lambda x: x[4] == 4, peer.control_msg_queue))
            peer.control_msg_queue.append(chock_msg)
            print('chocked ', repr(peer))

    @staticmethod
    async def send_unchock(peer: Peer):
        """
        adds 'unchock' message to the queue of a peer
        """
        async with asyncio.Lock():
            peer.am_chocked = False
            unchock_msg: bytes = Unchock.encode()
            peer.control_msg_queue = list(filter(lambda x: x[4] == 4, peer.control_msg_queue))
            peer.control_msg_queue.append(unchock_msg)
            print('unchocked ', repr(peer))

    @property
    def get_health(self):
        """
        health of a torrent: what percentage of all pieces is available to download for me
        """
        return round((1 - self.buckets_dict[0].length / len(self.TorrentData.piece_hashes)) * 100, 2)
