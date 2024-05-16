from ..app_data import db_utils

import time
from typing import Tuple, List


class Leecher:
    """
    object to store attributes of a leecher peer and some stats
    """
    leecher_instances: List = []

    def __init__(self, writer, address: Tuple[str, int], geodata: Tuple[str, str, float, float], peer_id: bytes, priority: int) -> None:
        """
        :param writer: asyncio writer instance
        :param address: (ip, port) of the peer
        :param geodata: geodata of the peer (tuple)
        :param peer_id: peer id the peer has chosen for this download
        :param priority: the priority value of the peer ip
        :return: None
        """
        self.writer = writer

        Leecher.leecher_instances.append(self)

        self.address = address
        self.priority = priority

        self.am_choked = True  # have I choked the peer?
        self.am_interested = False  # is the peer interested in what I offer?

        self.pipelined_requests: List[Tuple[int, int, int]] = []

        self.last_data_sent = time.time()

        self.download_rate = 0  # in KiB/s
        self.downloaded = 0  # in bytes
        self.download_counter = 0

        self.geodata = geodata
        self.peer_id = peer_id
        self.client = db_utils.get_client(peer_id)

    def update_download_rate(self, len_bytes_sent: int) -> None:
        """
        updates the downloading rate of a peer
        :param len_bytes_sent: length of data received
        :return: None
        """
        self.download_counter += len_bytes_sent
        rn = time.time()
        if (dt := rn - self.last_data_sent) < 0.05:
            return
        rate = (self.download_counter / 1024) / dt

        self.last_data_sent = rn
        self.download_rate = rate
        self.download_counter = 0

    def __repr__(self):
        return f"peer id: {self.peer_id}, address: {self.address}, geodata: {self.geodata}"

    def __hash__(self):
        return hash(repr(self))







