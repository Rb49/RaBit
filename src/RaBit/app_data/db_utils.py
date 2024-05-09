from collections import namedtuple

from ..file.file_object import PickleableFile

import asyncio
import re
from pathlib import Path
import sqlite3
import pickle
from typing import Union, Any, Dict, List, Tuple
import json
import threading
import copy


Peers = namedtuple('Peers', 'address geodata client')


def get_configuration(config_to_get: str) -> Any:
    """
    gets a configuration from config.json file
    :param config_to_get: what setting to get
    :return: Any
    """
    with open(abs_db_path('config.json'), 'r') as json_file:
        configs: Dict[str, Any] = json.load(json_file)
        if config_to_get in configs:
            return configs[config_to_get]
        return None


async def set_configuration(config_to_set: str, new_value: Any) -> bool:
    """
    sets a configuration to config.json file
    :param config_to_set: what setting to get
    :param new_value: value to set
    :return: whatever the operation was successful
    """
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


async def set_banned_countries(countries: List[str]):
    with threading.Lock():
        async with asyncio.Lock():
            with open(abs_db_path('banned_countries.json'), 'w') as json_file:
                json_file.seek(0)
                json_file.truncate()
                json.dump(countries, json_file)


def get_client(peer_id: bytes) -> str:
    """
    partial fingerprinting of the client software used by the peer
    only identifies azureus style encodings (they are the most popular ones)
    :param peer_id: peer id
    :return: software and its version
    """
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


def get_ongoing_torrents() -> List[Tuple[str]]:
    """
    get a list of torrents that were not finished gracefully
    """
    with open(abs_db_path('ongoing_torrents.json'), 'r') as json_file:
        torrents: List[Tuple[str]] = json.load(json_file)
        return torrents


async def add_ongoing_torrent(torrent_file_path: str, download_dir_path: str):
    with threading.Lock():
        async with asyncio.Lock():
            with open(abs_db_path('ongoing_torrents.json'), 'r+') as json_file:
                torrents: List[List[str]] = json.load(json_file)
                if torrent_file_path not in map(lambda x: x[0], torrents):
                    torrents.append([torrent_file_path, download_dir_path])
                    json_file.seek(0)
                    json_file.truncate()
                    json.dump(torrents, json_file)


def remove_ongoing_torrent(torrent_file_path: str):
    with threading.Lock():
        with open(abs_db_path('ongoing_torrents.json'), 'r+') as json_file:
            torrents: List[str] = json.load(json_file)
            torrents = list(filter(lambda x: x[0] != torrent_file_path, torrents))
            json_file.seek(0)
            json_file.truncate()
            json.dump(torrents, json_file)


class Singleton:
    """
    singleton pattern instance for sqlite databases instances
    """
    _instances: Dict[int, Dict[Any, Any]] = dict()

    def __new__(cls, *args, **kwargs):
        thread_id = threading.get_ident()
        if thread_id not in cls._instances:
            cls._instances[thread_id]: Dict[cls, cls] = dict()
        if cls not in cls._instances[thread_id]:
            cls._instances[thread_id][cls] = super().__new__(cls, *args, **kwargs)
        return cls._instances[thread_id][cls]


class BannedPeersDB(Singleton):
    """
    sqlite database api for accessing or inserting into the database of banned ip addresses that must be avoided.
    """
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
    """
    sqlite database api for accessing or inserting into the database of completed torrents (PickleableFile) for seeding.
    """
    def __init__(self):
        conn = sqlite3.connect(abs_db_path('completed_torrents.db'))
        # info hash, pickled file object
        conn.cursor().execute('CREATE TABLE IF NOT EXISTS completed_torrents (info_hash BLOB PRIMARY KEY, file_object BLOB)')
        conn.commit()
        self.conn = conn

    def insert_torrent(self, file_object: PickleableFile):
        params = (file_object.info_hash, pickle.dumps(file_object))
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO completed_torrents (info_hash, file_object) VALUES (?, ?)", params)
        self.conn.commit()

    def update_torrent(self, file_object: PickleableFile):
        new_file_object = copy.copy(file_object)
        new_file_object.peers = [Peers(peer.address, peer.geodata, peer.client) for peer in new_file_object.peers]
        params = (pickle.dumps(new_file_object), new_file_object.info_hash)
        cursor = self.conn.cursor()
        cursor.execute("UPDATE completed_torrents SET file_object=? WHERE info_hash=?", params)
        self.conn.commit()

    def get_torrent(self, info_hash: bytes) -> Union[PickleableFile, None]:
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

    def get_all_torrents(self) -> List[PickleableFile]:
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

