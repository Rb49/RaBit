from .app_data.db_utils import (get_configuration, set_configuration, get_ongoing_torrents,
                                CompletedTorrentsDB, remove_ongoing_torrent)
from .seeding.server import start_seeding_server, add_completed_torrent
from .seeding.utils import FileObjects
from .download.download_session_object import DownloadSession
from .file.file_object import PickleableFile

import asyncio
import threading
import time
from typing import Set, Union


class _Singleton:
    """
    singleton pattern instance for Client instance
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance


class Client(_Singleton):
    """
    RaBit module main class
    """

    def __init__(self):
        if hasattr(self, 'started'):
            return
        asyncio.run(set_configuration('seeding_server_is_up', False))
        self.torrents: Set[Union[DownloadSession, PickleableFile]] = set()
        self.started = False

    def start(self) -> bool:
        if self.started:
            return False

        seeding_thread = threading.Thread(target=lambda: asyncio.run(start_seeding_server()), daemon=True)
        seeding_thread.start()

        # wait for the seeding server before starting download
        while True:
            if get_configuration('seeding_server_is_up'):
                break
            time.sleep(0.25)

        # add torrents for seeding
        completed_torrents = CompletedTorrentsDB().get_all_torrents()
        for torrent in completed_torrents:
            self.torrents.add(torrent)
            add_completed_torrent(torrent)

        # start unfinished torrents
        ongoing_torrents = get_ongoing_torrents()
        self.torrents: Set[Union[DownloadSession, PickleableFile]] = set()
        for torrent, path in ongoing_torrents:
            session = DownloadSession(torrent, path, False)
            self.torrents.add(session)
            download_thread = threading.Thread(target=lambda: asyncio.run(session.download()), daemon=True)
            time.sleep(0.05)
            download_thread.start()

        # add completed torrents
        seeding_torrents = set(CompletedTorrentsDB().get_all_torrents())
        self.torrents.update(seeding_torrents)

        self.started = True
        return True

    def add_torrent(self, torrent_path: str, download_dir: str, skip_hash_check: bool) -> bool:
        if not self.started:
            return False
        session = DownloadSession(torrent_path, download_dir, skip_hash_check)
        self.torrents.add(session)
        download_thread = threading.Thread(target=lambda: asyncio.run(session.download()), daemon=True)
        time.sleep(0.05)
        download_thread.start()
        return True

    def remove_torrent(self, info_hash: bytes) -> bool:
        if not self.started:
            return False
        success = False
        for torrent in self.torrents.copy():
            if torrent.info_hash == info_hash:
                if isinstance(torrent, DownloadSession):
                    DownloadSession.Sessions.pop(torrent.info_hash)
                    remove_ongoing_torrent(torrent.torrent_path)
                else:
                    CompletedTorrentsDB().delete_torrent(torrent.info_hash)
                    FileObjects.pop(torrent.info_hash)
                self.torrents.remove(torrent)
                success = True
        return success

    async def torrents_state_update_loop(self):
        for torrent in self.torrents.copy():
            if isinstance(torrent, DownloadSession):
                if torrent.state in ('Completed', 'Failed', 'Seeding'):
                    self.torrents.remove(torrent)
                    torrent_from_db = CompletedTorrentsDB().get_torrent(torrent.info_hash)
                    if torrent_from_db:
                        if torrent_from_db.info_hash not in map(lambda x: x.info_hash, self.torrents):
                            self.torrents.add(torrent_from_db)
                            await add_completed_torrent(torrent_from_db)
            else:  # isinstance(torrent, PickleableFile)
                if not CompletedTorrentsDB().find_info_hash(torrent.info_hash):
                    self.torrents.remove(torrent)


    @staticmethod
    def get_download_dir() -> str:
        return get_configuration("download_dir")
