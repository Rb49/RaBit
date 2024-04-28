import RaBit.app_data.db_utils
import RaBit.app_data.db_utils as db_utils
from RaBit.seeding.server import start_seeding_server
from RaBit.download.download_session_object import DownloadSession

import threading
import asyncio
import time


def main(*torrents, **kwargs):
    """
    temp main function.
    gets a list of torrents to download and pauses the download of unfinished other torrents.
    starts seeding server qas well.
    """
    seeding_thread = threading.Thread(target=lambda: asyncio.run(start_seeding_server()), daemon=True)
    seeding_thread.start()

    # TODO wait for the seeding server before starting download
    while True:
        from RaBit.seeding.server import SEEDING_SERVER_IS_UP
        if SEEDING_SERVER_IS_UP:
            break
        time.sleep(0.5)

    download_dir = kwargs.get('download_dir')
    if not download_dir:
        download_dir = db_utils.get_configuration('download_dir')

    threads = []

    ongoing_torrents = db_utils.get_ongoing_torrents()
    for data in ongoing_torrents:
        torrent, path = data
        session = DownloadSession(torrent, path)
        download_thread = threading.Thread(target=lambda: asyncio.run(session.download()), daemon=True)
        threads.append(download_thread)
        download_thread.start()

    torrents = set(torrents) - set(map(lambda x: x[0], ongoing_torrents))
    for torrent_path in torrents:
        session = DownloadSession(torrent_path, download_dir)
        download_thread = threading.Thread(target=lambda: asyncio.run(session.download()), daemon=True)
        threads.append(download_thread)
        download_thread.start()

    for thread in threads:
        thread.join()
        print('download complete!')

    seeding_thread.join()


# TODO organize all files, add error messages with exceptions, documentation, type hints, ...
if __name__ == '__main__':
    import tracemalloc
    tracemalloc.start()

    import sys
    if sys.version_info[0:2] != (3, 10):
        raise Exception("Wrong Python version! Use version 3.10 only.")

    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\ubuntu-23.10-live-server-amd64.iso.torrent"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\debian-edu-12.4.0-amd64-netinst.iso.torrent"
    # torrent_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The.Rock.1996.1080p.BluRay.x265-RARBG.torrent"

    main(
        r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The Best American Short Stories, 2011–2023 (13 books).torrent",
        r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\The Complete Art of War_ Sun Tzu-Sun Pin [blackatk].torrent",
        download_dir=r"/results"
    )

    exit(0)
