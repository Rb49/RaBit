import copy

from src.file.data_structures import Block

import asyncio
from typing import List, Dict, Union
import bitstring


class EndgameManager(object):
    def __init__(self) -> None:
        self.Lock = asyncio.Lock()

        self.blocks_list = []

        self.endgame = False
        self.endgame_status = None
        self.finished = False

    async def enable_endgame(self, pieces_dict: Dict) -> bool:
        if self.endgame:
            return True

        async with self.Lock:
            for piece in pieces_dict.values():
                for index, block in enumerate(piece.data):
                    if not piece.blocks_available[index]:
                        self.blocks_list.append(block)

            if len(self.blocks_list) > 20:
                self.blocks_list = []
                return False

            self.endgame = True
            self.endgame_status = bitstring.BitArray(bin='0' * len(self.blocks_list))
            return True

    @property
    async def get_endgame_blocks(self) -> List[Block]:
        async with self.Lock:
            return copy.deepcopy(self.blocks_list)

    async def have_block(self, block: Block) -> Union[bool, None]:
        if not self.endgame:
            return False

        async with self.Lock:
            if block not in self.blocks_list:
                return False

            index = self.blocks_list.index(block)
            if self.endgame_status[index]:
                return None

            self.endgame_status[index] = True
            print('got endgame index ', index)
            if all(self.endgame_status):
                ...
                # TODO must not activate kill switch until disk IO thread verifies a full download. if a piece is corrupted, re-request it in endgame mode
                self.finished = True

        return True
