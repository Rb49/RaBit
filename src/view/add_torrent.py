import concurrent.futures
import customtkinter
from PyQt5.QtWidgets import QApplication, QFileDialog
import os
from PIL import Image
from pathlib import Path

from src.RaBit import Client


class FileDialogs(customtkinter.CTkFrame):
    def __init__(self, master, start_path: str, **kwargs):
        super().__init__(master, **kwargs)
        self.valid_file = False
        self.file_path = ""
        self.valid_dir = False
        self.download_dir = ""

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1)

        # path of file label
        self.torrent_path_label = customtkinter.CTkLabel(self, text="Torrent path:")
        self.torrent_path_label.grid(row=0, column=0, padx=(20, 0), pady=(20, 0), sticky="w")

        # torrent file
        self.torrent_path_input = customtkinter.CTkEntry(self, font=("", 13), width=375, placeholder_text="Type here...")
        self.torrent_path_input.grid(row=1, column=0, padx=(10, 0), pady=(20, 0), rowspan=1, columnspan=1, sticky="ew")

        # check mark image
        check_mark = customtkinter.CTkImage(Image.open(AddTorrentWindow.NEGATIVE_PATH), size=(25, 25))
        self.torrent_path_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.torrent_path_image_label.grid(row=1, column=1, padx=(10, 0), pady=(20, 2))

        self.torrent_path_input.bind("<KeyRelease>", lambda event: self.on_key_release(event, False))

        # select file button
        self.torrent_path_dialog = customtkinter.CTkButton(self, text="Select file", width=125,
                                                           command=lambda: self.file_dialog(master, False, start_path))
        self.torrent_path_dialog.grid(row=1, column=2, padx=10, pady=(20, 0), rowspan=1, sticky="w")

        # save at label
        self.download_dir_label = customtkinter.CTkLabel(self, text="Save at:")
        self.download_dir_label.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="w")

        # download dir
        self.download_dir_input = customtkinter.CTkEntry(self, font=("", 13), width=375, placeholder_text="Type here...")
        self.download_dir_input.insert(0, start_path)
        self.download_dir_input.grid(row=3, column=0, padx=(10, 0), pady=(20, 2), rowspan=1, columnspan=1, sticky="ew")

        # check mark image
        self.download_dir_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.download_dir_image_label.grid(row=3, column=1, padx=(10, 0), pady=(20, 2))

        self.download_dir_input.bind("<KeyRelease>", lambda event: self.on_key_release(event, True))

        # select file button
        self.download_dir_dialog = customtkinter.CTkButton(self, text="Select folder", width=125,
                                                           command=lambda: self.file_dialog(master, True, start_path))
        self.download_dir_dialog.grid(row=3, column=2, padx=10, pady=(20, 0), rowspan=1, sticky="w")

        # skip hash checkbox
        self.skip_hash_checkbox = customtkinter.CTkCheckBox(self, text="Skip hash check (not recommended)")
        self.skip_hash_checkbox.grid(row=4, columnspan=3, pady=(25, 5))

        # confirm button
        self.confirm_button = customtkinter.CTkButton(self, text="Confirm", state="disabled",
                                                      command=lambda: self.add_torrent(master))
        self.confirm_button.grid(row=5, column=0, padx=50, pady=30, columnspan=3, sticky="ew")

        # start params could be valid
        self.on_key_release(None, True)

    def add_torrent(self, master):
        Client().add_torrent(self.file_path, self.download_dir, bool(self.skip_hash_checkbox.get()))
        master.destroy()

    def on_key_release(self, event, is_dir: bool):
        path_input = self.download_dir_input if is_dir else self.torrent_path_input
        image_label = self.download_dir_image_label if is_dir else self.torrent_path_image_label
        path = path_input.get()
        image = customtkinter.CTkImage(self.get_validation_mark(path, is_dir), size=(25, 25))
        image_label.configure(image=image)

    def get_validation_mark(self, path: str, is_dir: bool) -> Image:
        path = Path(path.strip("\n"))
        if is_dir:
            if path.is_dir() and path.is_absolute():
                self.valid_dir = True
                self.download_dir = str(path)
                image = Image.open(AddTorrentWindow.POSITIVE_PATH)
            else:
                self.valid_dir = False
                image = Image.open(AddTorrentWindow.NEGATIVE_PATH)
        else:
            if path.is_file() and path.is_absolute() and path.suffix == ".torrent":
                self.file_path = str(path)
                self.valid_file = True
                image = Image.open(AddTorrentWindow.POSITIVE_PATH)
            else:
                self.valid_file = False
                image = Image.open(AddTorrentWindow.NEGATIVE_PATH)

        if self.valid_file and self.valid_dir:
            self.confirm_button.configure(state="normal")
        else:
            self.confirm_button.configure(state="disabled")
        return image

    @staticmethod
    def open_file_dialog(is_folder: bool, start_directory: str) -> str:
        app = QApplication([])
        file_dialog = QFileDialog()
        if is_folder:
            file_dialog.setFileMode(QFileDialog.Directory)
        else:
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setNameFilter("Torrent Files (*.torrent)")
        if start_directory:
            file_dialog.setDirectory(start_directory)
        else:
            file_dialog.setDirectory(os.path.abspath(os.sep))
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            return selected_file
        else:
            return ""

    def file_dialog(self, master, is_folder: bool, start_directory: str):
        master.attributes("-topmost", False)
        instance = self.download_dir_input if is_folder else self.torrent_path_input
        # prevent total collapse
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(FileDialogs.open_file_dialog, is_folder, start_directory)
            path = future.result()
        if path:
            instance.delete(0, "end")
            instance.insert(0, path)
            self.on_key_release(None, is_folder)
        master.attributes("-topmost", True)


class AddTorrentWindow(customtkinter.CTkToplevel):
    POSITIVE_PATH = Path().resolve() / "view" / "assets" / "positive_mark.png"
    NEGATIVE_PATH = Path().resolve() / "view" / "assets" / "negative_mark.png"

    WIDTH = 600
    HEIGHT = 450

    def __init__(self, master, start_path: str, **kwargs):
        super().__init__(master, **kwargs)

        self.geometry(f"{AddTorrentWindow.WIDTH}x{AddTorrentWindow.HEIGHT}")
        self.background = ("gray92", "gray14")

        self.columnconfigure(0, weight=1)

        self.title("")
        self.minsize(AddTorrentWindow.WIDTH, AddTorrentWindow.HEIGHT)

        self.title = customtkinter.CTkLabel(self, text="Add a Torrent", font=("", 35))
        self.title.grid(row=0, column=0, rowspan=1, columnspan=3, padx=15, pady=20, sticky="ew")

        self.file_frame = FileDialogs(self, start_path)
        self.file_frame.grid(row=1, column=0, rowspan=3, columnspan=2, padx=15, pady=20)

        self.attributes("-topmost", True)


def get_TopWindow():
    return AddTorrentWindow
