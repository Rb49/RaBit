from typing import List, Dict
import tkinter as tk

import customtkinter
from PIL import Image
from src.view.add_torrent import get_TopWindow
from src.view.zoomable_map import get_ZoomableMapFrame


class ToolbarFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # settings button
        image = customtkinter.CTkImage(Image.open(MainWindow.SETTINGS_PATH), size=(20, 20))
        self.settings_button = customtkinter.CTkButton(self, image=image, fg_color="transparent", text="",
                                                       width=20, height=20,
                                                       command=lambda: ...)
        self.settings_button.grid(row=0, column=0, rowspan=1, columnspan=1, padx=(5, 2), pady=5, sticky="w")

        # add button
        image = customtkinter.CTkImage(Image.open(MainWindow.ADD_PATH), size=(20, 20))
        self.settings_button = customtkinter.CTkButton(self, image=image, fg_color="transparent", text="",
                                                       width=20, height=20,
                                                       command=master.open_toplevel)
        self.settings_button.grid(row=0, column=1, rowspan=1, columnspan=1, padx=2, pady=5, sticky="w")

        # remove button
        image = customtkinter.CTkImage(Image.open(MainWindow.REMOVE_PATH), size=(20, 20))
        self.settings_button = customtkinter.CTkButton(self, image=image, fg_color="transparent", text="",
                                                       width=20, height=20,
                                                       command=lambda: print(get_TopWindow().added_torrents))
        self.settings_button.grid(row=0, column=2, rowspan=1, columnspan=1, padx=(2, 5), pady=5, sticky="w")


class TorrentsInfo(customtkinter.CTkScrollableFrame):
    torrent_labels: Dict[bytes, List] = dict()

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.current_row = 0
        columns_titles = [('Name', 5), ('Size', 2), ('Progress', 4), ('Status', 2), ('Peers', 1), ('Availability', 1)]
        for i, data in enumerate(columns_titles):
            title, weight = data
            label = customtkinter.CTkLabel(self, text=title, font=("", 13))
            self.columnconfigure(i, weight=weight)
            label.grid(row=self.current_row, rowspan=1, column=i, pady=(0, 2), sticky="ew")

    def add_torrent(self, name: str, size: int, progress: float, status: str, peers: int, availability: float, info_hash: bytes):
        self.current_row += 1
        labels = [0] * 6
        for i, param in enumerate([name, size, progress, status, peers, availability]):
            if i not in (0, 1, 2):  # not progress and name
                labels[i] = customtkinter.CTkLabel(self, text=str(param), font=("", 13), justify="left")
            elif i == 1:  # size
                labels[i] = customtkinter.CTkLabel(self, text=TorrentsInfo.convert_size(param), font=("", 13), justify="left")
            elif i == 2:  # progress
                labels[i] = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="determinate",
                                                         width=50, corner_radius=0, progress_color="green")
                labels[i].set(progress / 100)
            else:  # name
                labels[i] = customtkinter.CTkTextbox(self, fg_color="transparent", activate_scrollbars=True, wrap="none", font=("", 13), height=15)
                labels[i].insert("0.0", name)
                labels[i].configure(state="disabled")

            labels[i].grid(row=self.current_row, rowspan=1, column=i, pady=(0, 2), sticky="ew")

        TorrentsInfo.torrent_labels[info_hash] = labels

    @staticmethod
    def convert_size(size: int) -> str:
        bytes_in_gib = 0.000000000931322574615478515625
        bytes_in_mib = 0.00000095367431640625
        bytes_in_kib = 0.0009765625
        if size * bytes_in_gib < 1:
            if size * bytes_in_mib < 1:
                return f"{round(size * bytes_in_kib, 2)} KiB"
            return f"{round(size * bytes_in_mib, 2)} MiB"
        return f"{round(size * bytes_in_gib, 2)} GiB"


class SingleTorrent(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)


class PeersInfo(customtkinter.CTkFrame):
    def __init__(self, master, addresses, **kwargs):
        super().__init__(master, **kwargs)

        self.map = get_ZoomableMapFrame()(self, addresses, width=1000, height=500)
        self.map.pack(expand=True, anchor="ne")


class MainWindow(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"
    SETTINGS_PATH = r"assets\settings.png"
    ADD_PATH = r"assets\add.png"
    REMOVE_PATH = r"assets\remove.png"

    WIDTH = 720
    HEIGHT = 360

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.title("RaBit Client")
        self.iconbitmap(MainWindow.ICON_PATH)
        self.minsize(MainWindow.WIDTH, MainWindow.HEIGHT)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        self.toolbar_frame = ToolbarFrame(self)
        self.toolbar_frame.grid(row=0, column=0, padx=10, pady=(3, 0), columnspan=1, rowspan=1)
        self.toplevel_window = None

        self.torrents_info_frame = TorrentsInfo(self, orientation="vertical")
        self.torrents_info_frame.grid(row=1, column=0, rowspan=3, columnspan=2, padx=10, pady=(5, 3), sticky="news")

        addresses = [('Dhaka', 'BD', 23.746, 90.382),
                     ('Adelaide', 'AU', -34.9517, 138.607),
                     ('Athens', 'GR', 37.9842, 23.7353),
                     ('Auckland', 'NZ', -36.8506, 174.7679),
                     ('Cuenca', 'EC', -2.8976, -79.0045),
                     ('Montes Claros', 'BR', -16.5879, -43.9),
                     ('Dieppe', 'CA', 46.097, -64.7049),
                     ('Cape Town', 'ZA', -33.91, 18.4304),
                     ('Dublin', 'IE', 53.3798, -6.4136),
                     ('Zurich', 'CH', 47.3614, 8.4899),
                     ('Barcelona', 'ES', 41.4357, 2.1339),
                     (None, None, 52.3759, 4.8975)]

        self.peers_info_frame = PeersInfo(self, addresses)
        self.peers_info_frame.grid(row=4, column=0, rowspan=10, columnspan=2, padx=10, pady=(3, 20), sticky="news")

    def open_toplevel(self):
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = get_TopWindow()(self, "")
        else:
            self.toplevel_window.focus()


def get_MainWindow():
    return MainWindow


app = MainWindow()
app.mainloop()
