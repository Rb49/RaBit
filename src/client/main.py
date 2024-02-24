from typing import Dict

from src.file.data_structures import Piece
from src.torrent.torrent import read_torrent
from src.tracker.announce import announce
from src.tracker.utils import format_peers_list
from src.peer.handshake import tcp_wire_communication
from src.geolocation.utils import get_my_public_ip
from src.peer.endgame import EndgameManager

import asyncio
import queue
from random import shuffle


class BetterQueue(queue.Queue):
    def __init__(self, maxsize: int = 0):
        super().__init__(maxsize)
        self.size = 0

    def put(self, item, block=True, timeout=None):
        super().put(item, block, timeout)
        self.size += 1

    def get(self, block=True, timeout=None):
        item = super().get(block, timeout)
        self.size -= 1
        return item


async def main() -> None:
    # path for test torrent file
    # test_path = "Young.Sheldon.S07E01.HDTV.x264-TORRENTGALAXY.torrent"
    test_path = "debian-edu-12.4.0-amd64-netinst.iso.torrent"
    # test_path = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "././data/" + test_path

    # read torrent file
    TorrentData = read_torrent(test_path)

    # initial announce
    size = TorrentData.info[b'piece length'] * len(TorrentData.piece_hashes)  # safe size calculation
    peers_list = await announce(TorrentData, 0, 0, size, 56969, 2)  # fake port for now

    # my_ip = get_my_public_ip()
    # TODO save ip in config file and update only when expired
    my_ip = '176.230.227.216'
    peers_list = format_peers_list(peers_list, my_ip)

    # --------

    # peer wire protocol

    # TODO changing BLOCK_SIZE changes downloading speed!
    pieces_list = [Piece(TorrentData, index) for index in range(len(TorrentData.piece_hashes))]
    shuffle(pieces_list)
    pieces_dict = {piece.piece_index: piece for piece in pieces_list}

    failed_queue = asyncio.Queue()  # queue where the peers will take jobs
    results_queue = BetterQueue()  # where the results will be collected

    Endgame = EndgameManager()

    await asyncio.gather(*[tcp_wire_communication(peer, TorrentData, pieces_dict, failed_queue, results_queue, Endgame) for peer in peers_list])

    print('final: ', len(pieces_dict))
    return


if __name__ == '__main__':
    import tracemalloc

    tracemalloc.start()

    # t = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
    # t.start()
    # t.join()
    asyncio.run(main())
