import src.app_data.db_utils as db_utils
from src.download.data_structures import DownloadingPiece, FailedPiece
from src.download.piece_picker import BetterQueue, PiecePicker
from src.peer.peer_object import Peer
from src.torrent.torrent_object import Torrent

import asyncio
from hashlib import sha1
from typing import Tuple
import threading
import os


class File(object):
    def __init__(self, TorrentData: Torrent, piece_picker: PiecePicker, results_queue: BetterQueue, path: str, skip_hash_check: bool = False):
        self.TorrentData = TorrentData
        self.results_queue = results_queue
        self.skip_hash_check = skip_hash_check
        self.piece_picker = piece_picker

        if not TorrentData.multi_file:
            self.file_names = [path + TorrentData.info[b'name'].decode('utf-8')]
            self.file_indices = [TorrentData.length]
            self.multi_file = False
        else:
            os.makedirs((path := path + TorrentData.info[b'name'].decode('utf-8')), exist_ok=True)
            self.file_names = [path + '/' + name[b'path'][0].decode('utf-8') for name in TorrentData.info[b'files']]
            self.multi_file = True

            total = 0
            self.file_indices = []
            for name in TorrentData.info[b'files']:
                total += name[b'length']
                self.file_indices.append(total)

        self.fds = [os.open(file_name, os.O_RDWR | os.O_CREAT | os.O_BINARY) for file_name in self.file_names]

    def reopen_files(self):
        """
        reopens completed files in read-only mode
        :return: None
        """
        self.fds = [os.open(file_name, os.O_RDONLY | os.O_BINARY) for file_name in self.file_names]

    def close_files(self):
        for fd in self.fds:
            os.close(fd)
        self.fds = []

    def get_piece(self, piece_index: int, begin: int, length: int) -> Tuple[int, int, bytes]:
        reading_begin_index = self.TorrentData.info[b'piece length'] * piece_index + begin
        if not self.multi_file:
            fd = self.fds[0]
            os.lseek(fd, reading_begin_index, os.SEEK_SET)
            data = os.read(fd, length)
            if len(data) < length:  # add padding to the last piece
                data += b'\x00' * (length - len(data))
            return piece_index, begin, data
        else:
            ...

    async def save_pieces_loop(self):
        while True:
            if self.piece_picker.num_of_pieces_left == 0:
                # TODO a more elegant exit, let all interested disconnect and then switch to seeding in seeding server
                self.close_files()
                # add to completed torrents db
                db_utils.CompletedTorrentsDB().insert_torrent(PickableFile(self))
                loop = asyncio.get_event_loop()
                loop.close()

            with threading.Lock():
                piece: DownloadingPiece = await self.results_queue.get()

            # hash check
            data = piece.get_data
            piece_hash = sha1(data).digest()
            torrent_piece_hash = self.TorrentData.piece_hashes[piece.index]

            if not self.skip_hash_check:
                if piece_hash != torrent_piece_hash:
                    # TODO create corrupt pieces and blocks instances and remember the addresses of senders
                    print('received corrupted piece ', piece.index)

                    self.TorrentData.corrupted += len(data)

                    piece.previous_tries.append(FailedPiece(piece))
                    piece.reset()
                    await self.piece_picker.add_failed_piece(piece)

                    continue

            print("\033[90m{}\033[00m".format(f'got piece. {round((1 - (self.piece_picker.num_of_pieces_left - 1) / len(self.TorrentData.piece_hashes)) * 100, 2)}%. have index: {piece.index}'))

            # ban bad peers if any
            bad_peers = piece.get_bad_peers()
            async with asyncio.Lock():
                database = db_utils.BannedPeersDB()
                for peer_ip in bad_peers:
                    database.insert_ip(peer_ip)
                    peer = list(filter(lambda x: x.address[0] == peer_ip, Peer.peer_instances))[0]
                    peer.found_dirty = True
                    print('banned ', peer_ip)

            writing_begin_index = self.TorrentData.info[b'piece length'] * piece.index
            if piece.index == len(self.TorrentData.piece_hashes) - 1:
                end_position = min(self.TorrentData.length, writing_begin_index + len(data))
                data = data[:end_position - writing_begin_index]

            # get file fd
            relative_start = 0
            for index, fd in enumerate(self.fds):
                indice = self.file_indices[index]
                if indice - (writing_begin_index + relative_start) < 0:
                    continue
                relative_start = min(relative_start, indice - writing_begin_index)
                relative_end = min(indice - writing_begin_index, len(data))
                data_block = data[relative_start:relative_end]
                if not data_block:
                    break
                print(relative_start, relative_end)
                os.lseek(fd, writing_begin_index + relative_start, os.SEEK_SET)
                os.write(fd, data_block)
                relative_start = relative_end

            self.piece_picker.num_of_pieces_left -= 1
            self.piece_picker.FILE_STATUS[piece.index] = True  # update primary bitfield
            await self.piece_picker.send_have(piece.index)
            piece.reset()

    def __del__(self):
        try:
            self.close_files()
        except OSError:
            pass


class PickableFile(object):
    def __init__(self, file_object: File):
        self.info_hash = file_object.TorrentData.info_hash
        self.peer_id = file_object.TorrentData.peer_id
        self.length = file_object.TorrentData.length
        self.piece_length = file_object.TorrentData.info[b'piece length']
        self.num_pieces = len(file_object.TorrentData.piece_hashes)
        # statistics
        self.downloaded = file_object.TorrentData.downloaded
        self.uploaded = file_object.TorrentData.uploaded

        self.file_names = file_object.file_names
        self.fds = []
        self.indices = file_object.file_indices
        self.multi_file = file_object.multi_file

    def reopen_files(self):
        """
        reopens completed files in read-only mode
        :return: None
        """
        self.fds = [os.open(file_name, os.O_RDONLY | os.O_BINARY) for file_name in self.file_names]

    def close_files(self):
        for fd in self.fds:
            os.close(fd)
        self.fds = []

    def get_piece(self, piece_index: int, begin: int, length: int) -> Tuple[int, int, bytes]:
        reading_begin_index = self.piece_length * piece_index + begin
        if not self.multi_file:
            fd = self.fds[0]
            os.lseek(fd, reading_begin_index, os.SEEK_SET)
            data = os.read(fd, length)
            if len(data) < length:  # add padding to the last piece
                data += b'\x00' * (length - len(data))
            return piece_index, begin, data
        else:
            ...

    def __del__(self):
        try:
            self.close_files()
        except OSError:
            pass
