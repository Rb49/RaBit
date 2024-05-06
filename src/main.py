from src.RaBit import Client
from src.view.loading_window import get_LoadingWindow
from src.view.main_window import get_MainWindow

import threading
import time


def wait_for_loading(client: Client, window: get_LoadingWindow()):
    start_client_thread = threading.Thread(target=lambda: (client.start(), window.quit()), daemon=True)
    start_client_thread.start()
    window.mainloop()
    window.destroy()


def gui_updates(client: Client, main_window: get_MainWindow()):
    first = dict()
    while True:
        for torrent in client.torrents:
            if torrent not in first:
                first[torrent] = True
            main_window.torrents_info_frame.add_torrent(first[torrent], torrent.name, torrent.length, torrent.progress, torrent.state, len(torrent.peers), torrent.ETA)
            first[torrent] = False
        time.sleep(0.5)


# start the client and display the loading window
myClient = Client()
loading_window = get_LoadingWindow()()
wait_for_loading(myClient, loading_window)

# start the main window
main_window = get_MainWindow()()
threading.Thread(target=lambda: gui_updates(myClient, main_window), daemon=True).start()
main_window.mainloop()
