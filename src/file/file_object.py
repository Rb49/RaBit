from src.download.data_structures import DownloadingPiece
from src.download.piece_picker import BetterQueue, PiecePicker
from src.torrent.torrent_object import Torrent

import asyncio
from hashlib import sha1
from typing import Dict, List
import threading
import os


class File(object):
    def __init__(self, TorrentData: Torrent, piece_picker: PiecePicker, results_queue: BetterQueue, path: str, skip_hash_check: bool = False):
        self.TorrentData = TorrentData
        self.results_queue = results_queue
        self.file_name = path + TorrentData.info[b'name'].decode('utf-8')
        self.fd = os.open(self.file_name, os.O_RDWR | os.O_CREAT)
        self.skip_hash_check = skip_hash_check
        self.piece_picker = piece_picker

    async def save_pieces_loop(self):
        while True:
            if self.piece_picker.num_of_pieces_left == 0:
                # TODO a more elegant exit, let all interested disconnect and then switch to seeding in server sock
                exit(0)

            with threading.Lock():
                piece: DownloadingPiece = await self.results_queue.get()

            # hash check
            data = piece.get_data
            print(type(data), len(data))
            piece_hash = sha1(data).digest()
            torrent_piece_hash = self.TorrentData.piece_hashes[piece.index]

            if not self.skip_hash_check:
                if piece_hash != torrent_piece_hash:
                    # TODO create corrupt pieces and blocks instances and remember the addresses of senders
                    print('received corrupted piece ', piece.index)

                    # TODO what happens if the last piece is found corrupted while in endgame mode?
                    self.TorrentData.corrupted += len(data)
                    piece.reset()
                    await self.piece_picker.add_failed_piece(piece)

                    continue

            print("\033[90m{}\033[00m".format(f'got piece. {round((1 - (self.piece_picker.num_of_pieces_left - 1) / len(self.TorrentData.piece_hashes)) * 100, 2)}%. index: {piece.index}'))

            writing_begin_index = self.TorrentData.info[b'piece length'] * piece.index
            if piece.index == len(self.TorrentData.piece_hashes) - 1:
                end_position = self.TorrentData.length - writing_begin_index
                data = data[:end_position]

            os.lseek(self.fd, writing_begin_index, os.SEEK_SET)
            os.write(self.fd, data)

            self.piece_picker.num_of_pieces_left -= 1
            self.piece_picker.FILE_STATUS[piece.index] = True  # update primary bitfield
            await self.piece_picker.send_have(piece.index)
            piece.reset()

    def __del__(self):
        os.close(self.fd)
