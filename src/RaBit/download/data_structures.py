from ..peer.message_types import BLOCK_SIZE

from typing import List, Tuple, Any, Set, Union
from dataclasses import dataclass
from random import random

# block states
OPEN = 0
REQUESTED = 1
FINISHED = 2


@dataclass(slots=True)
class Block:
    """
    a representation of a block - the smallest unit that is requested with a 'Request' message
    a several blocks make up a piece.
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
        """
        flushes the block
        """
        self.data = None
        self.state = OPEN
        self.downloaded_from = None

    def add_data(self, data: bytes, address: Tuple[str, int]):
        """
        adds data to the block when it arrives
        """
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

    @property
    def data_hash(self):
        """
        hash value of the block's data, NOT the block's instance hash.
        """
        return hash(self.data)


class DownloadingPiece:
    """
    a downloading piece instance.
    creates a list of Block instances and keeps track of them
    """
    def __init__(self, index, piece_length: int, block_size: int = BLOCK_SIZE) -> None:
        """
        :param index: index of the piece
        :param piece_length: length of the piece
        :param block_size: size of each 'full' block the piece should have
        :return: None
        """
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
        self.previous_tries: List[FailedPiece] = []

    def reset(self):
        """
        flushes the piece
        """
        self.all_requested = False
        self.current_block = 0
        for block in self.blocks:
            block.reset()

    def get_next_request(self) -> Union[Block, None]:
        """
        returns the nest unpicked block, if there are any
        :return: Block | None if all blocks have been already picked
        """
        if self.all_requested:
            return None

        for block in self.blocks:
            if block.state == OPEN:
                block.state = REQUESTED
                return block

        self.all_requested = True
        return None

    def deselect_block(self, block: Block):
        """
        makes a block available for picking again
        """
        for blk in self.blocks:
            if blk is block:
                if blk.state == REQUESTED:
                    self.all_requested = False
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

    def get_bad_peers(self) -> Set[str]:
        """
        if the piece has failed hash checks before, the malicious peers can be identified and banned.
        :return: set of ip addresses
        """
        # runs at successful hash check
        bad_peers = set()
        while self.previous_tries:
            failed_piece = self.previous_tries.pop()
            bad_peers.update(failed_piece.get_bad_peers(self))
        return bad_peers


class FailedPiece:
    """
    instance containing hashes of blocks that failed a hash check.
    an instance will be created for each piece failure.
    """
    def __init__(self, failed_piece: DownloadingPiece):
        self.piece_index = failed_piece.index
        self.failed_blocks: List[Tuple[int, str]] = [(block.data_hash, block.downloaded_from) for block in failed_piece.blocks]

    def get_bad_peers(self, verified_piece: DownloadingPiece) -> Set[str]:
        """
        compares the hashes of individual blocks to identify malicious peers
        """
        verified_blocks: List[Tuple[int, str]] = [(block.data_hash, block.downloaded_from) for block in verified_piece.blocks]

        bad_peers = set()
        for good_block, bad_block in zip(verified_blocks, self.failed_blocks):
            if good_block[0] == bad_block[0]:
                continue

            # bad peer detected!
            bad_peers.add(bad_block[1])

        return bad_peers










