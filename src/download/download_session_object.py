import src.app_data.db_utils as db_utils
from src.torrent.torrent import read_torrent
from src.tracker.initial_announce import initial_announce
from src.tracker.utils import format_peers_list
from src.geoip.utils import get_my_public_ip
from src.download.piece_picker import PiecePicker
from src.peer.peer_communication import tcp_wire_communication
from src.file.file_object import File
from src.download.upload_in_download import TitForTat
from src.tracker.tracker_object import Tracker, ANNOUNCING, WORKING
from src.seeding.announce_loop import announce_loop

import threading
import asyncio
from hashlib import sha1
import bitstring
from typing import List, Tuple, Dict, Any


class DownloadSession(object):
    Sessions: Dict[bytes, Any] = dict()

    def __init__(self, torrent_path: str, result_dir: str):
        self.torrent_path = torrent_path
        self.TorrentData = None
        self.result_dir = result_dir
        self.downloaded = 0
        self.uploaded = 0
        self.left = 0
        self.corrupted = 0
        self.wasted = 0
        self.state = None

    @staticmethod
    async def work_wrapper(disk_loop, tit_for_tat_loop, *work):
        tit_for_tat_loop = asyncio.create_task(tit_for_tat_loop())
        disk_loop = await asyncio.to_thread(disk_loop)

        await asyncio.gather(tit_for_tat_loop, disk_loop, *work)

    async def download(self) -> bool:
        # should be called from protected code

        # read TorrentData file
        self.state = 'Reading TorrentData'
        self.TorrentData = read_torrent(self.torrent_path)

        # is it already being downloaded?
        if self.TorrentData.info_hash in DownloadSession.Sessions:
            print('already downloading!')
            return False

        self.state = 'Verifying files'
        bitarray, missing = self.verify_torrent()

        if all(bitarray):
            print('got all!')
            return True

        if missing is None:
            self.left = self.TorrentData.length
        else:
            extra = len(self.TorrentData.piece_hashes) * self.TorrentData.info[b'piece length'] - self.TorrentData.length
            self.left = len(missing) * self.TorrentData.info[b'piece length'] - extra
            self.downloaded = self.TorrentData.length - self.left

        db_utils.CompletedTorrentsDB().delete_torrent(self.TorrentData.info_hash)

        # add the TorrentData file path for fail safety
        db_utils.add_ongoing_torrent(self.torrent_path)

        # add self to dict
        DownloadSession.Sessions[self.TorrentData.info_hash] = self

        # initial announce
        self.state = 'Announcing'
        peers_list, tracker_list = await initial_announce(self.TorrentData, self.downloaded, self.uploaded, self.left, db_utils.get_configuration('v4_forward')['external_port'], 2)
        # format peer list: sort and remove unwanted peers
        my_ip = await get_my_public_ip()
        peers_list = format_peers_list(peers_list, my_ip)

        if not peers_list:
            self.state = 'Failed'
            print("couldn't find any peers!")
            DownloadSession.Sessions.pop(self.TorrentData.info_hash)
            return False

        # --------
        # peer wire protocol
        self.state = 'Downloading...'
        announce_loop_task = asyncio.create_task(announce_loop(self, tracker_list))

        piece_picker = PiecePicker(self.TorrentData, self, bitarray, missing)
        tit_for_tat_manager = TitForTat(piece_picker)

        # start disk IO thread
        await db_utils.set_configuration('download_dir', self.result_dir)
        file = File(self.TorrentData, self, piece_picker, piece_picker.results_queue, self.torrent_path, self.result_dir, False)

        work = [tcp_wire_communication(peer, self.TorrentData, self, file, piece_picker, tit_for_tat_manager) for peer in peers_list]
        try:
            thread = threading.Thread(target=lambda: asyncio.run(DownloadSession.work_wrapper(file.save_pieces_loop, tit_for_tat_manager.loop, *work)), daemon=True)
            thread.start()
            thread.join()
        except RuntimeError:
            pass

        if db_utils.CompletedTorrentsDB().find_info_hash(self.TorrentData.info_hash):
            # announce completion
            total_download, total_upload = self.downloaded + self.corrupted + self.wasted, self.uploaded
            # TODO use the tracker update thread to announce complete

            async def final_announce(tracker: Tracker):
                if tracker.state in (ANNOUNCING, WORKING):
                    try:
                        await asyncio.wait_for(tracker.re_announce(total_download, total_upload, 0, 1), 2)
                    except asyncio.TimeoutError:
                        pass

            work = [final_announce(tracker) for tracker in tracker_list]
            await asyncio.gather(*work)

        else:
            self.state = 'Failed'
            print('Failed!')
            DownloadSession.Sessions.pop(self.TorrentData.info_hash)
            announce_loop_task.cancel()
            return False

        self.state = 'Completed'
        print(tracker_list)
        DownloadSession.Sessions.pop(self.TorrentData.info_hash)
        announce_loop_task.cancel()
        return True

    def verify_torrent(self) -> Tuple[bitstring.BitArray, List[int]]:
        # do not re-download existing torrent pieces!
        missing = None
        bitarray = bitstring.BitArray(bin='0' * len(self.TorrentData.piece_hashes))
        if self.torrent_path in db_utils.get_ongoing_torrents() or db_utils.CompletedTorrentsDB().find_info_hash(self.TorrentData.info_hash):
            temp_file = None
            try:
                bitarray = bitstring.BitArray(bin='1' * len(self.TorrentData.piece_hashes))
                missing = []
                temp_file = File(self.TorrentData, None, None, None, None, self.result_dir)
                for index, torrent_piece_hash in enumerate(self.TorrentData.piece_hashes):
                    # hash check
                    if index != len(self.TorrentData.piece_hashes) - 1:
                        data = temp_file.get_piece(index, 0, self.TorrentData.info[b'piece length'])
                    else:
                        extra = len(self.TorrentData.piece_hashes) * self.TorrentData.info[b'piece length'] - self.TorrentData.length
                        data = temp_file.get_piece(index, 0, self.TorrentData.info[b'piece length'] - extra)

                    piece_hash = sha1(data[2]).digest()
                    if torrent_piece_hash != piece_hash:
                        bitarray[index] = False
                        missing.append(index)
            except OSError:
                bitarray = bitstring.BitArray(bin='0' * len(self.TorrentData.piece_hashes))
            finally:
                del temp_file

        return bitarray, missing




