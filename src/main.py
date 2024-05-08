from src.RaBit import Client
from src.view.loading_window import get_LoadingWindow
from src.view.main_window import get_MainWindow
from src.view.utils import *

import threading
import asyncio


def wait_for_loading(client: Client, window: get_LoadingWindow()):
    start_client_thread = threading.Thread(target=lambda: (client.start(), window.quit()), daemon=True)
    start_client_thread.start()
    window.mainloop()
    window.destroy()


async def gui_updates(client: Client, main_window: get_MainWindow()):
    first = dict()
    while True:
        for torrent in client.torrents.copy():
            if torrent not in first:
                first[torrent] = True
            # update progress info
            main_window.add_torrent(first[torrent],
                                    hash(torrent),
                                    torrent.name,
                                    torrent.length,
                                    torrent.progress,
                                    torrent.state,
                                    len(torrent.peers),
                                    torrent.ETA)
            first[torrent] = False

            if torrent.TorrentData if hasattr(torrent, "TorrentData") else True:
                # update initialized objects only
                if main_window.current_obj_hash == hash(torrent):
                    # update displayed window only
                    if main_window.current_tab.get() == "General":
                        # update general info
                        main_window.update_general_info_tab(hash(torrent),
                                                            convert_size(torrent.downloaded),
                                                            convert_size(torrent.uploaded),
                                                            convert_size(torrent.corrupted),
                                                            convert_size(torrent.wasted),
                                                            f"{torrent.progress}%",
                                                            round(torrent.uploaded / (torrent.downloaded + torrent.wasted + torrent.corrupted + 1), 2),
                                                            f"{(num := torrent.num_pieces if hasattr(torrent, 'num_pieces') else len(torrent.TorrentData.piece_hashes))} (have {round(num * torrent.progress / 100)})",
                                                            convert_size(torrent.piece_length if hasattr(torrent, "piece_length") else torrent.TorrentData.info[b'piece length']),
                                                            len(list(filter(lambda x: x.state, torrent.trackers))),
                                                            torrent.TorrentData.comment if hasattr(torrent, "TorrentData") else torrent.comment,
                                                            torrent.TorrentData.created_by if hasattr(torrent, "TorrentData") else torrent.created_by,
                                                            torrent.TorrentData.date_created if hasattr(torrent, "TorrentData") else torrent.date_created)
                    elif main_window.current_tab.get() == "Peers":
                        # update peers info
                        main_window.update_peers_info_tab(hash(torrent),
                                                          list(map(lambda x: (hash(x), *x.address, x.geodata, x.client), torrent.peers)))

        prev_torrents = client.torrents.copy()
        await client.torrents_state_update_loop()

        # handle removed torrents
        removed = prev_torrents - client.torrents
        if removed:
            main_window.remove_torrents([hash(torrent) for torrent in removed])
        else:
            await asyncio.sleep(1)


# start the client and display the loading window
myClient = Client()
loading_window = get_LoadingWindow()()
wait_for_loading(myClient, loading_window)

# start the main window
main_window = get_MainWindow()()
threading.Thread(target=lambda: asyncio.run(gui_updates(myClient, main_window)), daemon=True).start()
main_window.mainloop()
