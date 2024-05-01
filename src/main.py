import customtkinter
import threading

from src.RaBit import Client
from src.view.main_window import get_MainWindow
from src.view.add_torrent import get_TopWindow
from src.view.loading_window import get_LoadingWindow


def start_client(client: Client, window: customtkinter.CTk):
    client.start()
    window.destroy()


def wait_for_loading(client: Client, window: customtkinter.CTk):
    start_client_thread = threading.Thread(target=lambda: start_client(client, window), daemon=True)
    start_client_thread.start()
    window.mainloop()
    print('hi')


# start the client and meantime display the loading window
client = Client()
loading_window = get_LoadingWindow()()
wait_for_loading(client, loading_window)
