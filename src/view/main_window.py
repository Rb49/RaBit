import tkinter
from pathlib import Path
from typing import List, Dict
import customtkinter
from PIL import Image

from .add_torrent import get_TopWindow
from .zoomable_canvas import get_ZoomableMapCanvas
from .utils import *


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
    torrent_labels: List[List] = []

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        columns_titles = [('Select', 0), ('Name', 5), ('Size', 2), ('Progress', 6), ('Status', 2), ('Peers', 1), ('ETA', 2)]
        for i, data in enumerate(columns_titles):
            title, weight = data
            label = customtkinter.CTkLabel(self, text=title, font=("", 13))
            self.columnconfigure(i, weight=weight)
            label.grid(row=0, rowspan=1, column=i, pady=(0, 2), sticky="ew")

    def add_torrent(self, first_add: bool, name: str, size: int, progress: float, status: str, peers: int, ETA: float):
        if first_add:
            labels = [0] * 7
            row = len(TorrentsInfo.torrent_labels) + 1
            for i, param in enumerate([None, name, size, progress, status, peers, ETA]):
                if i == 0:  # radio button select
                    labels[i] = customtkinter.CTkRadioButton(self, text=f"No. {row}",
                                                             variable=self.master.selected_row, value=row,
                                                             command=self.master.open_torrent_info_tab)
                elif i == 1:  # name
                    labels[i] = customtkinter.CTkTextbox(self, fg_color="transparent", activate_scrollbars=True, wrap="none", font=("", 13), height=15)
                    labels[i].insert("0.0", name)
                    labels[i].configure(state="disabled")
                elif i == 2:  # size
                    labels[i] = customtkinter.CTkLabel(self, text=convert_size(param), font=("", 13), justify="left")
                elif i == 3:  # progress
                    labels[i] = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="determinate",
                                                             width=50, height=15, corner_radius=0, progress_color="green")
                    labels[i].set(progress / 100)
                elif i == 6:  # ETA
                    labels[i] = customtkinter.CTkLabel(self, text=convert_seconds(param), font=("", 13), justify="left")
                else:  # status, peers
                    labels[i] = customtkinter.CTkLabel(self, text=str(param), font=("", 13), justify="left")

                labels[i].grid(row=row, rowspan=1, column=i, pady=(0, 2), padx=4, sticky="ew")

            TorrentsInfo.torrent_labels.append(labels)
            labels[0].invoke()  # display current torrent stats
        else:  # update
            for row in range(1, len(TorrentsInfo.torrent_labels) + 1):
                if self.grid_slaves(row=row, column=1)[0].get("0.0", "end").strip('\n') == name:
                    # progress
                    self.grid_slaves(row=row, column=3)[0].set(progress / 100)
                    # else
                    self.grid_slaves(row=row, column=4)[0].configure(text=str(status))
                    self.grid_slaves(row=row, column=5)[0].configure(text=str(peers))
                    self.grid_slaves(row=row, column=6)[0].configure(text=convert_seconds(ETA))
                    return



class GeneralTorrentInfo(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        torrent_info = [
            "Downloaded: ", "Uploaded: ", "Corrupted: ", "Wasted: ",
            "Progress: ", "Ratio: ", "Pieces: ", "Piece length: ",
            "Multi file: ", "Comment: ", "Created By: ", "Creation Date: "
        ]
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        for i, info in enumerate(torrent_info):
            row = i % 4
            column = i // 4
            label = customtkinter.CTkLabel(self, text=info, font=("", 13), anchor="w")
            label.grid(row=row, column=column, sticky="ew")


class MapFrame(customtkinter.CTkFrame):
    def __init__(self, master, addresses, **kwargs):
        super().__init__(master, **kwargs)
        self.map = get_ZoomableMapCanvas()(self, addresses, width=1000, height=500)
        self.map.pack(expand=True, anchor="ne")


class PeersInfoFrame(customtkinter.CTkScrollableFrame):
    peers = []

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.current_row = 0
        columns_titles = [('IP', 10), ('Port', 1), ('City', 10), ('Client', 10)]
        for i, data in enumerate(columns_titles):
            title, weight = data
            label = customtkinter.CTkLabel(self, text=title, font=("", 13))
            self.columnconfigure(i, weight=weight)
            label.grid(row=self.current_row, rowspan=1, column=i, pady=(0, 2), sticky="ew")

    def new_peers_info(self, info_hash: bytes, peers):
        self.current_row += 1
        labels = [0] * 6
        for i, param in enumerate([name, size, progress, status, peers, availability]):
            if i not in (0, 1, 2):  # not progress and name
                labels[i] = customtkinter.CTkLabel(self, text=str(param), font=("", 13), justify="left")
            elif i == 1:  # size
                labels[i] = customtkinter.CTkLabel(self, text=convert_size(param), font=("", 13), justify="left")
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

    def remove_torrent(self, info_hash: bytes):
        ...


class MainWindow(customtkinter.CTk):
    ICON_PATH = Path().resolve() / "view" / "assets" / "RaBit_icon.ico"
    SETTINGS_PATH = Path().resolve() / "view" / "assets" / "settings.png"
    ADD_PATH = Path().resolve() / "view" / "assets" / "add.png"
    REMOVE_PATH = Path().resolve() / "view" / "assets" / "remove.png"

    WIDTH = 720
    HEIGHT = 360

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.title("RaBit Client")
        self.iconbitmap(MainWindow.ICON_PATH)
        self.minsize(MainWindow.WIDTH, MainWindow.HEIGHT)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=2)
        self.rowconfigure(2, weight=1)
        # toolbar
        self.toolbar_frame = ToolbarFrame(self)
        self.toolbar_frame.grid(row=0, column=0, padx=10, pady=(3, 0), columnspan=1, rowspan=1, sticky="w")
        self.toplevel_window = None

        self.selected_row = customtkinter.IntVar(value=0)

        # torrent info holder
        self.torrents_info_frame = TorrentsInfo(self, orientation="vertical")
        self.torrents_info_frame.grid(row=1, column=0, rowspan=3, columnspan=2, padx=10, pady=(5, 0), sticky="news")

        self.addresses = []

        self.info_tabs = dict()
        self.current_tab = None



    def open_toplevel(self):
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = get_TopWindow()(self, "")
        else:
            self.toplevel_window.focus()

    def open_torrent_info_tab(self):
        row = self.selected_row.get()
        # get name
        name = self.torrents_info_frame.grid_slaves(row=row, column=1)[0].get("0.0", "end").strip('\n')
        if name not in self.info_tabs:
            self.info_tabs[name] = customtkinter.CTkTabview(master=self)

            self.info_tabs[name].add("General")
            self.info_tabs[name].add("Peers")
            self.info_tabs[name].set("General")
            self.info_tabs[name].tab("Peers").columnconfigure(0, weight=10)
            self.info_tabs[name].tab("Peers").columnconfigure(1, weight=1)

            # peer info and map holder
            map_frame = MapFrame(self.info_tabs[name].tab("Peers"), self.addresses, fg_color="transparent")
            map_frame.grid(row=0, column=1, columnspan=1, padx=(5, 0), pady=0, sticky="e")
            peers_info_frame = PeersInfoFrame(self.info_tabs[name].tab("Peers"))
            peers_info_frame.grid(row=0, column=0, columnspan=1, padx=(0, 5), pady=0, sticky="we")

            # general info
            general_info_tab = GeneralTorrentInfo(self.info_tabs[name].tab("General"), fg_color="transparent")
            general_info_tab.grid(row=0, column=0, padx=5, pady=5, sticky="new")

        if self.current_tab:
            self.current_tab.grid_forget()

        self.info_tabs[name].grid(row=4, column=0, rowspan=10, columnspan=2, padx=10, pady=(0, 5), sticky="news")
        self.current_tab = self.info_tabs[name]


def get_MainWindow():
    return MainWindow
