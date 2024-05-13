from ..app_data import db_utils
from ..download.data_structures import DownloadingPiece, FailedPiece
from ..download.piece_picker import BetterQueue, PiecePicker
from ..peer.peer_object import Peer
from ..torrent.torrent_object import Torrent

import asyncio
from hashlib import sha1
from typing import Tuple
import threading
import os
import re
import random


def format_file_name(file_name: str) -> str:
    """
    formats a file name from illegal chars and names
    :param file_name: name of the file (not path!)
    :return: formatted file name
    """
    # remove illegal name chars
    file_name = re.sub(r'[<>:"/\\|?*]', '', file_name)
    file_name = ''.join([char for char in file_name if ord(char) > 31])
    file_name = re.sub(r'[ .]$', '', file_name)

    reserved_names = {'COM4', 'COM6', 'LPT4', 'AUX', 'LPT1', 'LPT6', 'COM1', 'NUL', 'PRN', 'COM7', 'COM5', 'COM8', 'LPT9', 'LPT3', 'LPT7', 'COM3', 'COM9', 'LPT8', 'CON', 'LPT5', 'COM2', 'LPT2'}
    if file_name.upper() in reserved_names:
        file_name += '_'

    return file_name


class File:
    """
    disk IO manager to read/write pieces and validate them.
    an instance is created for each download
    """
    def __init__(self, TorrentData: Torrent, session, piece_picker: PiecePicker, results_queue: BetterQueue, torrent_path: str, path: str, skip_hash_check: bool = False) -> None:
        """
        :param TorrentData: torrent data instance
        :param session: DownloadingSession instance with session stats
        :param piece_picker: PiecePicker instance for requesting and reporting blocks
        :param results_queue: asyncio queue where completed pieces are stored
        :param torrent_path: path to .torrent file
        :param path: path to where downloaded files will be saved
        :param skip_hash_check: whatever to skip the hash check
        (not recommended to turn off)
        :return: None
        """
        self.TorrentData = TorrentData
        self.results_queue = results_queue
        self.skip_hash_check = skip_hash_check
        self.piece_picker = piece_picker
        self.torrent_path = torrent_path
        self.session = session

        if not TorrentData.multi_file:
            self.file_names = [os.path.join(path, format_file_name(TorrentData.info[b'name'].decode('utf-8')))]
            self.file_indices = [TorrentData.length]
        else:
            path = os.path.join(path, format_file_name(TorrentData.info[b'name'].decode('utf-8')))
            os.makedirs(path, exist_ok=True)

            total = 0
            self.file_indices = []
            self.file_names = []
            for name in TorrentData.info[b'files']:
                total += name[b'length']
                self.file_indices.append(total)
                tree = list(reversed(name[b'path']))
                file_name = path
                while True:
                    level = tree.pop()
                    file_name = os.path.join(file_name, format_file_name(level.decode('utf-8')))
                    if not tree:
                        break
                    os.makedirs(file_name, exist_ok=True)
                self.file_names.append(file_name)

        if "nt" == os.name:
            self.fds = [os.open(file_name, os.O_RDWR | os.O_CREAT | os.O_BINARY) for file_name in self.file_names]
        else:
            self.fds = [os.open(file_name, os.O_RDWR | os.O_CREAT) for file_name in self.file_names]

    def close_files(self) -> None:
        """
        closes the file descriptors
        :return: None
        """
        for fd in self.fds:
            os.close(fd)
        self.fds = []

    def get_piece(self, piece_index: int, begin: int, length: int) -> Tuple[int, int, bytes]:
        """
        reads a block of data from the right file or files
        :param piece_index: torrent piece index
        :param begin: starting index inside a piece
        :param length: length of the requested block
        :return: piece, begin, data (comfortable to paste in the Piece.encode() function)
        """
        reading_begin_index = self.TorrentData.info[b'piece length'] * piece_index + begin
        remaining_length = length
        current_piece_abs_index = reading_begin_index
        first = True
        data = b''
        for index, indice in enumerate(self.file_indices):
            if reading_begin_index >= indice:
                continue

            len_for_indice = min(remaining_length, indice - current_piece_abs_index)

            relative_file_begin = 0 if not first else current_piece_abs_index - self.file_indices[index - 1] if index > 0 else current_piece_abs_index

            os.lseek(self.fds[index], relative_file_begin, os.SEEK_SET)
            data += os.read(self.fds[index], len_for_indice)

            remaining_length -= len_for_indice
            current_piece_abs_index += len_for_indice
            first = False
            if remaining_length == 0:
                break

        if len(data) < length:  # add padding to the last piece
            data += b'\x00' * (length - len(data))

        return piece_index, begin, data

    async def save_pieces_loop(self) -> None:
        """
        a loop to read completed pieces from the result_queue and save them to disk
        """
        while True:
            if self.piece_picker.num_of_pieces_left == 0:
                # TODO a more elegant exit, let all interested disconnect and then switch to seeding in seeding server
                self.close_files()
                # add to completed torrents db
                self.session.state = 'Seeding'
                self.session.peers = []
                db_utils.CompletedTorrentsDB().insert_torrent(PickleableFile(self))
                db_utils.remove_ongoing_torrent(self.torrent_path)
                loop = asyncio.get_event_loop()
                loop.stop()

            with threading.Lock():
                piece: DownloadingPiece = await self.results_queue.get()

            data = piece.get_data

            if not self.skip_hash_check:
                # hash check
                piece_hash = sha1(data).digest()
                torrent_piece_hash = self.TorrentData.piece_hashes[piece.index]
                if piece_hash != torrent_piece_hash:
                    print('received corrupted piece ', piece.index)

                    self.session.corrupted += len(data)

                    piece.previous_tries.append(FailedPiece(piece))
                    piece.reset()
                    await self.piece_picker.add_failed_piece(piece)

                    continue

            self.session.progress = round((1 - (self.piece_picker.num_of_pieces_left - 1) / len(self.piece_picker.pieces_map)) * 100, 2)
            print("\033[90m{}\033[00m".format(f'got piece. {self.session.progress}%. have index: {piece.index}. from {len(Peer.peer_instances[self.piece_picker.TorrentData.info_hash])} peers.'))

            # ban bad peers if any
            bad_peers = piece.get_bad_peers()
            if bad_peers:
                async with asyncio.Lock():
                    database = db_utils.BannedPeersDB()
                    for peer_ip in bad_peers:
                        database.insert_ip(peer_ip)
                        if peer in Peer.peer_instances[self.piece_picker.TorrentData.info_hash]:
                            peer = list(filter(lambda x: x.address[0] == peer_ip, Peer.peer_instances[self.piece_picker.TorrentData.info_hash]))[0]
                            peer.found_dirty = True
                            print('banned ', peer_ip)

            piece_abs_index = self.TorrentData.info[b'piece length'] * piece.index

            # save to files
            remaining_length = len(data)
            current_piece_abs_index = piece_abs_index
            piece_relative_begin = 0
            first = True
            for index, indice in enumerate(self.file_indices):
                if piece_abs_index >= indice:
                    continue

                len_for_indice = min(remaining_length, indice - current_piece_abs_index)
                piece_relative_end = piece_relative_begin + len_for_indice

                relative_file_begin = 0 if not first else current_piece_abs_index - self.file_indices[index - 1] if index > 0 else current_piece_abs_index

                os.lseek(self.fds[index], relative_file_begin, os.SEEK_SET)
                os.write(self.fds[index], data[piece_relative_begin:piece_relative_end])

                piece_relative_begin += len_for_indice
                remaining_length -= len_for_indice
                current_piece_abs_index += len_for_indice
                first = False
                if remaining_length == 0:
                    break

            self.piece_picker.num_of_pieces_left -= 1
            self.session.left -= len(data)
            self.piece_picker.FILE_STATUS[self.TorrentData.info_hash][piece.index] = True  # update primary bitfield
            await self.piece_picker.send_have(piece.index)
            piece.reset()

    def __del__(self):
        try:
            self.close_files()
        except (OSError, AttributeError):
            pass


class PickleableFile:
    """
    stores all data needed to seed a torrent in a pickleable format
    """
    def __init__(self, file_object: File) -> None:
        """
        :param file_object: File instance to make pickleable
        :return: None
        """
        self.name = file_object.session.name
        self.state = file_object.session.state
        self.info_hash = file_object.TorrentData.info_hash
        self.peer_id = file_object.TorrentData.peer_id
        self.length = file_object.TorrentData.length
        self.trackers = file_object.session.trackers
        self.peers = []
        self.piece_length = file_object.TorrentData.info[b'piece length']
        self.num_pieces = len(file_object.TorrentData.piece_hashes)
        # additional torrent data
        self.comment = file_object.TorrentData.comment
        self.created_by = file_object.TorrentData.created_by
        self.date_created = file_object.TorrentData.date_created
        # statistics
        self.progress = file_object.session.progress
        self.downloaded = file_object.session.downloaded
        self.corrupted = file_object.session.corrupted
        self.wasted = file_object.session.wasted
        self.uploaded = file_object.session.uploaded
        # file details
        self.file_names = file_object.file_names
        self.fds = []
        self.file_indices = file_object.file_indices

        self.announce_task = None

        self.__seed = random.getrandbits(64)

        del file_object

    def reopen_files(self) -> None:
        """
        reopens completed files in read-only mode
        :return: None
        """
        if "nt" == os.name:
            self.fds = [os.open(file_name, os.O_RDONLY | os.O_BINARY) for file_name in self.file_names]
        else:
            self.fds = [os.open(file_name, os.O_RDONLY) for file_name in self.file_names]

    def close_files(self) -> None:
        """
        closes the file descriptors
        :return: None
        """
        for fd in self.fds:
            os.close(fd)
        self.fds = []

    def get_piece(self, piece_index: int, begin: int, length: int) -> Tuple[int, int, bytes]:
        """
        reads a block of data from the right file or files
        :param piece_index: torrent piece index
        :param begin: starting index inside a piece
        :param length: length of the requested block
        :return: piece, begin, data (comfortable to paste in the Piece.encode() function)
        """
        reading_begin_index = self.piece_length * piece_index + begin

        remaining_length = length
        current_piece_abs_index = reading_begin_index
        first = True
        data = b''
        for index, indice in enumerate(self.file_indices):
            if reading_begin_index >= indice:
                continue

            len_for_indice = min(remaining_length, indice - current_piece_abs_index)

            relative_file_begin = 0 if not first else current_piece_abs_index - self.file_indices[index - 1] if index > 0 else current_piece_abs_index

            os.lseek(self.fds[index], relative_file_begin, os.SEEK_SET)
            data += os.read(self.fds[index], len_for_indice)

            remaining_length -= len_for_indice
            current_piece_abs_index += len_for_indice
            first = False
            if remaining_length == 0:
                break

        if len(data) < length:  # add padding to the last piece
            data += b'\x00' * (length - len(data))

        return piece_index, begin, data

    @property
    def ETA(self) -> float:
        """
        :return: estimated time of arrival, in seconds
        """
        return 3184622406  # a very long time (100.9y) because download is already complete

    def __repr__(self):
        return f"uploaded: {self.uploaded}, name: {self.name}, info hash: {self.info_hash}"

    def __hash__(self):
        return hash(self.__seed)

    def __del__(self):
        try:
            self.close_files()
        except OSError:
            pass
