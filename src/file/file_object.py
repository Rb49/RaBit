from src.file.data_structures import Piece
from src.torrent.torrent_object import Torrent

import asyncio
from hashlib import sha1
from typing import Dict, List
import aiofiles


class File(object):
    def __init__(self, TorrentData: Torrent, pieces: List[Piece], path: str, skip_hash_check: bool = False):
        self.TorrentData = TorrentData
        self.pieces = pieces
        self.path = path
        self.skip_hash_check = skip_hash_check

    async def alloc(self):
        async with aiofiles.open(self.path, 'wb') as file:
            await file.seek(self.TorrentData.info[b'piece length'] * len(self.TorrentData.piece_hashes))
            await file.write(b'\0')

    async def save_piece(self, piece: Piece, piece_dict: Dict) -> int:
        # hash check
        piece_hash = piece.get_hash
        torrent_piece_hash = sha1(self.TorrentData.piece_hashes[piece.piece_index])
        torrent_piece_hash = torrent_piece_hash.digest()

        if not self.skip_hash_check:
            if piece_hash != torrent_piece_hash:
                print('received corrupted piece ', piece.piece_index)

                async with asyncio.Lock():
                    piece_dict[piece.piece_index] = Piece(self.TorrentData, piece.piece_index)

                piece.free()
                return -1

        # save to file
        async with aiofiles.open(self.path, 'wb') as file:
            writing_begin_index = self.TorrentData.info[b'piece length'] * piece.piece_index
            await file.seek(writing_begin_index)
            await file.write(piece.get_data)

        # TODO send 'Have' messages to all peers uploading to (using queue.Queue() with threading lock)

        piece.free()
        return 0
