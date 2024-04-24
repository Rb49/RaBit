from src.file.file_object import PickableFile

import asyncio
import re
from pathlib import Path
import sqlite3
import pickle
from typing import Union, Any, Dict, List
import json
import threading


def get_configuration(config_to_get: str) -> Any:
    with open(abs_db_path('config.json'), 'r') as json_file:
        configs: Dict[str, Any] = json.load(json_file)
        if config_to_get in configs:
            return configs[config_to_get]
        return None


async def set_configuration(config_to_set: str, new_value: Any) -> bool:
    with threading.Lock():
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


def get_client(peer_id: bytes) -> str:
    pattern = re.compile(b"^-[a-zA-Z~]{2}[0-9a-zA-Z]{4}-")
    match = re.match(pattern, peer_id)
    if match:
        match = match.group(0).decode('utf-8')
        with open(abs_db_path('azureus_style_clients.json'), 'r') as json_file:
            clients: Dict[str, str] = json.load(json_file)
            if match[1:3] in clients:
                client_name = clients[match[1:3]]
            elif peer_id[1:3] == b'RB' and peer_id[8:12] == b'EPIC':  # could be my own client ;)
                client_name = 'RaBit'
            else:
                client_name = 'Unknown client'
            version = [str(9 + ord(x) - 96) if 'a' <= x <= 'z' else str(9 + ord(x) - 64) if 'A' <= x <= 'Z' else x for x in match[3:7]]
            version = '.'.join(version[0:4] if version[3] != '0' else version[0:3])
            return client_name + ' v' + version
    else:
        return 'Unrecognized client'


def get_ongoing_torrents() -> List[str]:
    with open(abs_db_path('ongoing_torrents.json'), 'r') as json_file:
        torrents: List[str] = json.load(json_file)
        return torrents


def add_ongoing_torrent(path: str):
    with threading.Lock():
        with open(abs_db_path('ongoing_torrents.json'), 'r+') as json_file:
            torrents: List[str] = json.load(json_file)
            if path not in torrents:
                torrents.append(path)
                json_file.seek(0)
                json_file.truncate()
                json.dump(torrents, json_file)


def remove_ongoing_torrent(path: str):
    with threading.Lock():
        with open(abs_db_path('ongoing_torrents.json'), 'r+') as json_file:
            torrents: List[str] = json.load(json_file)
            if path in torrents:
                torrents.remove(path)
                json_file.seek(0)
                json_file.truncate()
                json.dump(torrents, json_file)


class Singleton(object):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls, *args, **kwargs)
        return cls._instances[cls]


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

    def get_all_torrents(self) -> List[PickableFile]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM completed_torrents")
        torrents = []
        for torrent in cursor.fetchall():
            torrents.append(pickle.loads(torrent[1]))
        return torrents

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

