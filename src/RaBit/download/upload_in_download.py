from ..app_data import db_utils
from ..download.piece_picker import PiecePicker
from ..peer.peer_object import Peer

from typing import List
import asyncio
from random import sample
import time


class TitForTat:
    """
    a choking mechanism based on a tit-for-tat algorithm: reward sharing peers, punish egoistic peers.
    """
    def __init__(self, piece_picker: PiecePicker) -> None:
        """
        :param piece_picker: PiecePicker instance for some stats
        :return: None
        """
        self.MAX_UNCHOKED_PEERS = db_utils.get_configuration('max_unchoked_peers')
        self.MAX_OPTIMISTIC_PEERS = db_utils.get_configuration('max_optimistic_unchoke')

        self.piece_picker: PiecePicker = piece_picker
        Peer.peer_instances[piece_picker.TorrentData.info_hash] = []  # this init happens before any peer is connected
        self.piece_picker.session.peers = Peer.peer_instances[piece_picker.TorrentData.info_hash]
        self.peers: List[Peer] = Peer.peer_instances[piece_picker.TorrentData.info_hash]  # all connected peers
        self.downloaders: List[Peer] = []  # downloaders interested in what I offer
        self.good_uninterested_peers: List[Peer] = []  # not interested peers and upload better than downloaders
        self.optimistic_unchoke_peers: List[Peer] = []  # not interested peers randomly chosen

    async def loop(self) -> None:
        """
        performs a tit-for-tat choking algorithm every 10 seconds
        and optimistic unchoking every 30 seconds
        :return: None
        """
        three_iteration_counter = 0
        while True:
            # am I being snubbed?
            if time.time() - self.piece_picker.last_data_received >= 60:
                for peer in self.peers:
                    if not peer.am_choked:
                        await self.piece_picker.send_choke(peer)
                await asyncio.sleep(1)
                continue

            sorted_peers = sorted(list(filter(lambda x: x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=True)
            self.downloaders = sorted_peers[:self.MAX_UNCHOKED_PEERS]
            if self.downloaders:
                self.good_uninterested_peers = list(filter(lambda x: not x.am_interested and x.upload_rate > self.downloaders[-1].upload_rate, self.peers))
            else:
                self.good_uninterested_peers = sorted(list(filter(lambda x: not x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=True)[:self.MAX_UNCHOKED_PEERS]

            three_iteration_counter += 1
            # optimistic unchoking
            if three_iteration_counter == 3:
                candidates = list(filter(lambda x: not x.am_interested and x not in self.good_uninterested_peers and x not in self.optimistic_unchoke_peers, self.peers))
                new_peers = sample(candidates, min(self.MAX_OPTIMISTIC_PEERS, len(candidates)))
                if new_peers:
                    self.optimistic_unchoke_peers = new_peers
                else:
                    pass  # there have to be some optimistically unchoked peers. leave it as it is.

                three_iteration_counter = 0

            # execute changes
            for peer in self.peers:
                if peer in self.downloaders:
                    if peer.am_choked:
                        # send unchoke
                        await self.piece_picker.send_unchoke(peer)

                elif peer in self.good_uninterested_peers:
                    if peer.am_choked:
                        # send unchoke
                        await self.piece_picker.send_unchoke(peer)

                elif peer in self.optimistic_unchoke_peers:
                    if peer.am_choked:
                        # send unchoke
                        await self.piece_picker.send_unchoke(peer)

                else:  # rest of peers, previous optimistically unchoked peers
                    if not peer.am_choked:
                        # send choke
                        await self.piece_picker.send_choke(peer)

            await asyncio.sleep(10)

    async def report_interested(self, peer: Peer) -> None:
        """
        what to do when a peer sends an interesting message?
        decides whatever to unchoke it or not
        :param peer: Peer instance of the requesting peer
        :return: None
        """
        peer.am_interested = True
        if len(self.downloaders) < self.MAX_UNCHOKED_PEERS:
            self.downloaders.append(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

            if peer in self.good_uninterested_peers:
                self.good_uninterested_peers.remove(peer)

            await self.piece_picker.send_unchoke(peer)

        elif peer in self.good_uninterested_peers:
            kicked_peer = self.downloaders.pop()  # worst downloader
            await self.piece_picker.send_choke(kicked_peer)

            self.downloaders.append(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

            await self.piece_picker.send_unchoke(peer)

        else:  # don't let worse peers to be unchoked instead of better ones
            await self.piece_picker.send_choke(peer)

    async def report_uninterested(self, peer: Peer) -> None:
        """
        what to do when a peer sends an uninteresting message?
        :param peer: Peer instance of the requesting peer
        :return: None
        """
        peer.am_interested = False
        if peer in self.downloaders:
            self.downloaders.remove(peer)
            await self.piece_picker.send_choke(peer)

            sorted_peers = sorted(list(filter(lambda x: x.am_interested, self.peers)), key=lambda x: x.upload_rate, reverse=False)
            while sorted_peers and len(self.downloaders) < self.MAX_UNCHOKED_PEERS:
                new_peer = sorted_peers.pop()
                self.downloaders.append(new_peer)
                await self.piece_picker.send_unchoke(peer)
            self.downloaders.sort(key=lambda x: x.upload_rate, reverse=True)

        elif peer in self.good_uninterested_peers:
            self.good_uninterested_peers.remove(peer)

        else:
            pass  # do nothing
