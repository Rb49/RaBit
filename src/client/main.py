from src.seeding.server import start_seeding_server
from src.download.download_session_object import DownloadSession

import threading
import asyncio
import time


# TODO organize all files, add error messages with exceptions, documentation, type hints, ...
if __name__ == '__main__':
    import tracemalloc
    tracemalloc.start()

    import sys
    if sys.version_info[0:2] != (3, 10):
        raise Exception("Wrong Python version! Use version 3.10 only.")

    seeding_thread = threading.Thread(target=lambda: asyncio.run(start_seeding_server()), daemon=True)
    seeding_thread.start()

    # TODO wait for the seeding server before starting download
    while True:
        from src.seeding.server import SEEDING_SERVER_IS_UP
        if SEEDING_SERVER_IS_UP:
            break
        time.sleep(0.5)

    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\ubuntu-23.10-live-server-amd64.iso.TorrentData"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\debian-edu-12.4.0-amd64-netinst.iso.TorrentData"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The Best American Short Stories, 2011–2023 (13 books).TorrentData"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\Young.Sheldon.S07E01.HDTV.x264-TORRENTGALAXY.TorrentData"
    torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The Complete Art of War_ Sun Tzu-Sun Pin [blackatk].torrent"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The.Rock.1996.1080p.BluRay.x265-RARBG.TorrentData"

    result_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\results"

    session = DownloadSession(torrent_path, result_path)
    download_thread = threading.Thread(target=lambda: asyncio.run(session.download()), daemon=True)
    download_thread.start()

    download_thread.join()
    print('download complete!')
    seeding_thread.join()

    exit(0)
