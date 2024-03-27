import src.app_data.db_utils as db_utils
from src.torrent.torrent import read_torrent
from src.tracker.announce import announce
from src.tracker.utils import format_peers_list
from src.geoip.utils import get_my_public_ip
from src.download.piece_picker import PiecePicker
from src.peer.peer_communication import tcp_wire_communication
from src.file.file_object import File
from src.download.upload_in_download import TitForTat
from src.seeding.server import start_seeding_server

import threading
import os
import asyncio


async def work_wrapper(disk_loop, tit_for_tat_loop, *work):
    tit_for_tat_loop = asyncio.create_task(tit_for_tat_loop())
    disk_loop = await asyncio.to_thread(disk_loop)

    await asyncio.gather(tit_for_tat_loop, disk_loop, *work)


# TODO organize all files, add error messages with exceptions, documentation, type hints, ...
async def main() -> None:
    # path for test torrent file
    # torrent_name = "Coding with AI For Dummies by Chris Minnick PDF.torrent"
    torrent_name = "The Best American Short Stories, 2011–2023 (13 books).torrent"
    torrent_name = "debian-edu-12.4.0-amd64-netinst.iso.torrent"
    # torrent_name = "Young.Sheldon.S07E01.HDTV.x264-TORRENTGALAXY.torrent"
    # torrent_name = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "././data/" + torrent_name

    # read torrent file
    TorrentData = read_torrent(test_path)

    # do not re-download existing torrent!
    if file_object := db_utils.CompletedTorrentsDB().get_torrent(TorrentData.info_hash):
        for path in file_object.file_names:
            if not os.path.exists(path):
                # TODO check hash of every piece, re-download corrupted ones
                db_utils.CompletedTorrentsDB().delete_torrent(TorrentData.info_hash)
                break
        else:
            print('all files already exist!')
            return

    # initial announce
    size = TorrentData.info[b'piece length'] * len(TorrentData.piece_hashes)  # safe size calculation
    peers_list = await announce(TorrentData, 0, 0, size, db_utils.get_configuration('v4_forward')['external_port'], 2)

    my_ip = await get_my_public_ip()
    peers_list = format_peers_list(peers_list, my_ip)

    # --------

    # peer wire protocol
    piece_picker = PiecePicker(TorrentData)
    tit_for_tat_manager = TitForTat(piece_picker)

    # start disk IO thread
    file = File(TorrentData, piece_picker, piece_picker.results_queue, '././results/', False)

    # TODO better peer management
    # TODO run a peer reputation db and reconnect to good peers if needed
    work = [tcp_wire_communication(peer, TorrentData, file, piece_picker, tit_for_tat_manager) for peer in peers_list]
    try:
        thread = threading.Thread(target=lambda: asyncio.run(work_wrapper(file.save_pieces_loop, tit_for_tat_manager.loop, *work)), daemon=True)
        thread.start()
        thread.join()
    except:
        pass

    if db_utils.CompletedTorrentsDB().find_info_hash(TorrentData.info_hash):
        # announce completion
        total_download, total_upload = TorrentData.downloaded + TorrentData.corrupted + TorrentData.wasted, TorrentData.uploaded
        await announce(TorrentData, total_download, total_upload, 0, db_utils.get_configuration('v4_forward')['external_port'], 1)
    else:
        print('Failed Download!!!')

    return


if __name__ == '__main__':
    import tracemalloc

    tracemalloc.start()

    import sys

    if sys.version_info[0:2] != (3, 10):
        raise Exception("Wrong Python version! Use version 3.10 only.")

    seeding_thread = threading.Thread(target=lambda: asyncio.run(start_seeding_server()), daemon=True)
    seeding_thread.start()
    # TODO wait for the seeding server before starting download
    download_thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
    download_thread.start()

    download_thread.join()
    print('download complete!')
    seeding_thread.join()

    exit(0)
