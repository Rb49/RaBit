from typing import Dict

from src.torrent.torrent import read_torrent
from src.tracker.announce import announce
from src.tracker.utils import format_peers_list
from src.geoip.utils import get_my_public_ip
from src.download.piece_picker import PiecePicker
from src.peer.peer_communication import tcp_wire_communication
from src.file.file_object import File
import threading

import asyncio
import queue
from random import shuffle


async def main() -> None:
    # path for test torrent file
    # torrent_name = "Coding with AI For Dummies by Chris Minnick PDF.torrent"
    torrent_name = "debian-edu-12.4.0-amd64-netinst.iso.torrent"
    # torrent_name = "Young.Sheldon.S07E01.HDTV.x264-TORRENTGALAXY.torrent"
    # torrent_name = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "././data/" + torrent_name

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
    piece_picker = PiecePicker(TorrentData)

    # start disk IO thread
    file = File(TorrentData, piece_picker, piece_picker.results_queue, '././results/', False)
    disk_loop = await asyncio.to_thread(file.save_pieces_loop)

    # TODO better peer management
    # TODO run a peer reputation db and reconnect to good peers if needed
    work = [tcp_wire_communication(peer, TorrentData, piece_picker) for peer in peers_list]
    await asyncio.gather(disk_loop, *work)

    print('final: ', piece_picker.num_of_pieces_left)
    return


if __name__ == '__main__':
    import tracemalloc

    tracemalloc.start()

    # t = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
    # t.start()
    # t.join()

    asyncio.run(main())
