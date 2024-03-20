from src.peer.message_types import BLOCK_SIZE

from typing import List, Tuple, Any
from dataclasses import dataclass
from random import random

# block states
OPEN = 0
REQUESTED = 1
FINISHED = 2


# TODO add failed_block class for smart banning

@dataclass
class Block(object):
    """
    NOTE:
    one Block object is passed many times between functions and a lot of references of it are created,
    but they all point to the same instance
    """

    # block attributes
    index: int
    begin: int
    length: int
    piece: Any  # corresponding DownloadingPiece instance

    data: bytes = None
    state: int = OPEN
    
    downloaded_from: str = None  # address is stored for smart banning

    def reset(self):
        self.data = None
        self.state = OPEN
        self.downloaded_from = None

    def add_data(self, data: bytes, address: Tuple[str, int]):
        if self.data is None:
            self.data = data
            self.state = FINISHED
            self.downloaded_from = address[0]
            self.piece.current_block += 1
            return True
        return False

    def is_equal(self, index: int, begin: int, length: int) -> bool:
        return self.index == index and self.begin == begin and self.length == length

    def __repr__(self):
        return f"index: {self.index}, begin: {self.begin}, length: {self.length}"

    def __hash__(self):
        return hash(repr(self))


class FailedBlock(Block):
    pass


class DownloadingPiece(object):
    def __init__(self, index, piece_length: int, block_size: int = BLOCK_SIZE):
        self.index = index
        self.piece_length = piece_length
        self.block_size = block_size

        self.all_requested = False

        self.blocks: List[Block] = []
        for i in range(self.piece_length // self.block_size + 1):
            begin = i * self.block_size
            end = min((i + 1) * self.block_size, self.piece_length)
            length = end - begin
            if length != 0:
                block = Block(self.index, begin, length, self)
                self.blocks.append(block)

        self.current_block = 0
        self.blocks_length = len(self.blocks)

        self.urgent = False  # true if the piece needs to be completed as fast as possible due to a failed request

    def reset(self):
        self.all_requested = False
        self.current_block = 0
        for block in self.blocks:
            block.reset()

    def get_next_request(self):
        if self.all_requested:
            return None

        for block in self.blocks:
            if block.state == OPEN:
                block.state = REQUESTED
                return block

        self.all_requested = True
        return None

    def deselect_block(self, block: Block):
        self.all_requested = False
        for blk in self.blocks:
            if blk is block:
                if blk.state == FINISHED:
                    self.current_block -= 1 if self.current_block > 0 else 0
                blk.reset()
                return

    @property
    def get_data(self) -> bytes:
        data = b''.join([block.data for block in self.blocks])
        return data

    @property
    def is_completed(self) -> bool:
        return self.current_block == self.blocks_length

    @property
    def priority(self):
        return (not self.urgent), self.all_requested, (1 - self.current_block / self.blocks_length), random()


class FailedPiece(DownloadingPiece):
    pass
