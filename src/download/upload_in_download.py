from src.download.piece_picker import PiecePicker
from src.peer.peer_object import Peer
import src.app_data.db_utils as db_utils

from typing import List
import asyncio
from random import sample
import time


class TitForTat(object):
    """
    a chocking mechanism based on a tit-for-tat algorithm: reward sharing peers, punish egoistic peers.
    """
    _MAX_UNCHOCKED_PEERS = db_utils.get_configuration('max_unchocked_peers')
    _MAX_OPTIMISTIC_PEERS = db_utils.get_configuration('max_optimistic_unchock')

    def __init__(self, piece_picker: PiecePicker) -> None:
        """
        :param piece_picker: PiecePicker instance for some stats
        :return: None
        """
        self.piece_picker: PiecePicker = piece_picker
        Peer.peer_instances[piece_picker.TorrentData.info_hash] = []  # this init happens before any peer is connected
        self.peers: List[Peer] = Peer.peer_instances[piece_picker.TorrentData.info_hash]  # all connected peers
        self.downloaders: List[Peer] = []  # downloaders interested in what I offer
        self.good_uninterested_peers: List[Peer] = []  # not interested peers and upload better than downloaders
        self.optimistic_unchock_peers: List[Peer] = []  # not interested peers randomly chosen

    async def loop(self) -> None:
        """
        performs a tit-for-tat chocking algorithm every 10 seconds
        and optimistic unchocking every 30 seconds
        :return: None
        """
        three_iteration_counter = 0
        while True:
            # am I being snubbed?
            if time.time() - self.piece_picker.last_data_received >= 60:
                for peer in self.peers:
                    if not peer.am_chocked:
                        await self.piece_picker.send_chock(peer)
                await asyncio.sleep(10)
                continue

            sorted_peers = sorted(list(filter(lambda x: x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=True)
            self.downloaders = sorted_peers[:TitForTat._MAX_UNCHOCKED_PEERS]
            if self.downloaders:
                self.good_uninterested_peers = list(filter(lambda x: not x.am_interested and x.upload_rate > self.downloaders[-1].upload_rate, self.peers))
            else:
                self.good_uninterested_peers = sorted(list(filter(lambda x: not x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=True)[:TitForTat._MAX_UNCHOCKED_PEERS]

            three_iteration_counter += 1
            # optimistic unchocking
            if three_iteration_counter == 3:
                candidates = list(filter(lambda x: not x.am_interested and x not in self.good_uninterested_peers and x not in self.optimistic_unchock_peers, self.peers))
                new_peers = sample(candidates, min(TitForTat._MAX_OPTIMISTIC_PEERS, len(candidates)))
                if new_peers:
                    self.optimistic_unchock_peers = new_peers
                else:
                    pass  # there have to be some optimistically unchocked peers. leave it as it is.

                three_iteration_counter = 0

            # execute changes
            for peer in self.peers:
                if peer in self.downloaders:
                    if peer.am_chocked:
                        # send unchock
                        await self.piece_picker.send_unchock(peer)

                elif peer in self.good_uninterested_peers:
                    if peer.am_chocked:
                        # send unchock
                        await self.piece_picker.send_unchock(peer)

                elif peer in self.optimistic_unchock_peers:
                    if peer.am_chocked:
                        # send unchock
                        await self.piece_picker.send_unchock(peer)

                else:  # rest of peers, previous optimistically unchocked peers
                    if not peer.am_chocked:
                        # send chock
                        await self.piece_picker.send_chock(peer)

            await asyncio.sleep(10)

    async def report_interested(self, peer: Peer) -> None:
        """
        what to do when a peer sends an interesting message?
        decides whatever to unchock it or not
        :param peer: Peer instance of the requesting peer
        :return: None
        """
        peer.am_interested = True
        if len(self.downloaders) < TitForTat._MAX_UNCHOCKED_PEERS:
            self.downloaders.append(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

            if peer in self.good_uninterested_peers:
                self.good_uninterested_peers.remove(peer)

            await self.piece_picker.send_unchock(peer)

        elif peer in self.good_uninterested_peers:
            kicked_peer = self.downloaders.pop()  # worst downloader
            await self.piece_picker.send_chock(kicked_peer)

            self.downloaders.append(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

            await self.piece_picker.send_unchock(peer)

        else:  # don't let worse peers to be unchocked instead of better ones
            await self.piece_picker.send_chock(peer)

    async def report_uninterested(self, peer: Peer) -> None:
        """
        what to do when a peer sends an uninteresting message?
        :param peer: Peer instance of the requesting peer
        :return: None
        """
        peer.am_interested = False
        if peer in self.downloaders:
            self.downloaders.remove(peer)
            await self.piece_picker.send_chock(peer)

            sorted_peers = sorted(list(filter(lambda x: x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=False)
            while sorted_peers and len(self.downloaders) < TitForTat._MAX_UNCHOCKED_PEERS:
                new_peer = sorted_peers.pop()
                self.downloaders.append(new_peer)
                await self.piece_picker.send_unchock(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

        elif peer in self.good_uninterested_peers:
            self.good_uninterested_peers.remove(peer)

        else:
            pass  # do nothing
