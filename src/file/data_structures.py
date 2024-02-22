import math
from random import random

from src.torrent.torrent_object import Torrent

from typing import Union, Dict
from dataclasses import dataclass
from typing import List, Any
from hashlib import sha1
import bitstring


# TODO changing BLOCK_SIZE changes downloading speed! however some peers will not respond if request is greater than 32768
DEFAULT_BLOCK_SIZE = 16384


@dataclass
class Block:
    piece_index: int
    begin: int
    length: int
    data: bytes = None

    time_requested: float = 0

    def is_equal(self, piece_index, begin, length) -> bool:
        return self.piece_index == piece_index and self.begin == begin and self.length == length

    @property
    def get_all(self) -> List[Any]:
        return [self.piece_index, self.begin, self.length, self.data]

    def __repr__(self):
        return f"index: {self.piece_index}, begin: {self.begin}, length: {self.length}"

    def free(self):
        self.data = None


class Piece(object):
    @staticmethod
    def __generate_block(TorrentData: Torrent, piece_index: int, BLOCK_SIZE: DEFAULT_BLOCK_SIZE) -> Union[int, Block]:
        """
        function to generate Block instances for a piece.
        the first iteration will return the total number of blocks, not a Block instance.
        :param TorrentData: the Torrent instance.
        :param piece_index: index of the piece.
        :param BLOCK_SIZE: size of one block in bytes. default is the block size constant
        :return: number of blocks | Block instance.
        """
        piece_length = TorrentData.info[b'piece length']

        # calc the total number of blocks
        counter = 0
        for i in range(piece_length // BLOCK_SIZE + 1):
            begin = i * BLOCK_SIZE
            end = min((i + 1) * BLOCK_SIZE, piece_length)
            length = end - begin
            if length != 0:
                counter += 1
        yield counter

        # generate blocks
        for i in range(piece_length // BLOCK_SIZE + 1):
            begin = i * BLOCK_SIZE
            end = min((i + 1) * BLOCK_SIZE, piece_length)
            length = end - begin
            if length != 0:
                block = Block(piece_index, begin, length)
                yield block

    def __init__(self, TorrentData: Torrent, piece_index: int, BLOCK_SIZE: int = 16384) -> None:
        self.rarity = 0
        self.is_not_partially_downloaded = True
        self.completed = False

        self.piece_index = piece_index
        self.__generator = Piece.__generate_block(TorrentData, piece_index, BLOCK_SIZE)
        self.num_of_blocks = next(self.__generator)

        self.blocks_available = bitstring.BitArray(bin='0' * self.num_of_blocks)
        self.current_block = 0
        self.is_being_downloaded = False

        self.data = [None for _ in range(self.num_of_blocks)]

    def get_block(self) -> Block:
        if self.current_block < self.num_of_blocks:
            block = next(self.__generator)
            self.data[self.current_block] = block
            self.current_block += 1
            return block

        self.is_not_partially_downloaded = True

    @property
    def get_data(self) -> bytes:
        if self.is_completed():
            return b''.join([block.data for block in self.data])
        return b''

    @property
    def get_hash(self) -> bytes:
        sha1_object = sha1(self.get_data)
        return sha1_object.digest()

    def add_block(self, begin: int, data: bytes) -> bool:
        for index, block in enumerate(self.data):
            if isinstance(block, Block):
                if block.begin == begin:
                    if block.data is not None:
                        return False

                    block.data = data
                    self.blocks_available[index] = True
                    self.is_not_partially_downloaded = False

                    if not self.completed:
                        if all(self.blocks_available):
                            self.completed = True
                            self.is_not_partially_downloaded = True

                    return True

    def free(self):
        for block in self.data:
            if isinstance(block, Block):
                block.free()

    @property
    def priority(self):
        if not self.is_not_partially_downloaded:
            return 0, 1 - self.current_block / self.num_of_blocks, self.rarity, random()
        elif self.completed:
            return 2, self.rarity
        else:
            return 1, self.rarity if self.rarity > 0 else math.inf, random()
