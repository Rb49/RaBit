from src.file.file_object import PickableFile

import asyncio
from pathlib import Path
import sqlite3
import pickle
from typing import Union, Any, Dict, List
import json


def get_configuration(config_to_get: str) -> Any:
    with open(abs_db_path('config.json'), 'r') as json_file:
        configs: Dict[str, Any] = json.load(json_file)
        try:
            return configs[config_to_get]
        except KeyError:
            return None


async def set_configuration(config_to_set: str, new_value: Any) -> bool:
    async with asyncio.Lock():
        with open(abs_db_path('config.json'), 'r+') as json_file:
            configs: Dict[str, Any] = json.load(json_file)
            if config_to_set in configs:
                configs[config_to_set] = new_value
                json_file.seek(0)
                json_file.truncate()
                json.dump(configs, json_file)
                return True
            return False


def get_banned_countries() -> List[str]:
    with open(abs_db_path('banned_countries.json'), 'r') as json_file:
        banned_list: List[str] = json.load(json_file)
        return banned_list


class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class BannedPeersDB(Singleton):
    def __init__(self):
        conn = sqlite3.connect(abs_db_path('banned_peers.db'))
        conn.cursor().execute('CREATE TABLE IF NOT EXISTS ip_addresses (ip_address TEXT PRIMARY KEY)')
        conn.commit()
        self.conn = conn

    def insert_ip(self, ip_address: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO ip_addresses (ip_address) VALUES (?)", (ip_address,))
        self.conn.commit()

    def find_ip(self, ip_address: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ip_addresses WHERE ip_address=?", (ip_address,))
        count = cursor.fetchone()[0]
        return count > 0

    def delete_ip(self, ip_address: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ip_addresses WHERE ip_address=?", (ip_address,))
        self.conn.commit()

    def __del__(self):
        self.conn.close()


class CompletedTorrentsDB(Singleton):
    # TODO close and reopen file descriptors when needed, raising exception if the files don't exist
    def __init__(self):
        conn = sqlite3.connect(abs_db_path('completed_torrents.db'))
        # info hash, pickled file object
        conn.cursor().execute('CREATE TABLE IF NOT EXISTS completed_torrents (info_hash BLOB PRIMARY KEY, file_object BLOB)')
        conn.commit()
        self.conn = conn

    def insert_torrent(self, file_object: PickableFile):
        params = (file_object.info_hash, pickle.dumps(file_object))
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO completed_torrents (info_hash, file_object) VALUES (?, ?)", params)
        self.conn.commit()

    def get_torrent(self, info_hash: bytes) -> Union[PickableFile, None]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_object FROM completed_torrents WHERE info_hash=?", (info_hash,))
        file_object = cursor.fetchone()
        if file_object:
            return pickle.loads(file_object[0])
        else:
            return None

    def find_info_hash(self, info_hash: bytes) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM completed_torrents WHERE info_hash=?", (info_hash,))
        count = cursor.fetchone()[0]
        return count > 0

    def delete_torrent(self, info_hash: bytes):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM completed_torrents WHERE info_hash=?", (info_hash,))
        self.conn.commit()

    def __del__(self):
        self.conn.close()


def abs_db_path(file_name: str) -> Path:
    """
    computes the absolute path of the file (based on this root dir)
    :return: absolute path
    """
    hpath_parent = Path(__file__).parent
    return hpath_parent.joinpath(file_name)

    # thanks to sapoj for help with this function

