import customtkinter
from PyQt5.QtWidgets import QApplication, QFileDialog
import os
from PIL import Image
from pathlib import Path

from src.RaBit import get_configuration, read_torrent, Torrent


class FileDialogs(customtkinter.CTkFrame):
    def __init__(self, master, start_path: str, **kwargs):
        super().__init__(master, **kwargs)
        self.valid_file = False
        self.valid_dir = False

        # torrent file
        self.torrent_path_input = customtkinter.CTkTextbox(self, activate_scrollbars=False, wrap="none", font=("", 12), width=375, height=15)
        self.torrent_path_input.grid(row=0, column=0, padx=(10, 0), pady=(20, 0), rowspan=1, columnspan=1, sticky="ew")

        # check mark image
        check_mark = customtkinter.CTkImage(Image.open(App.NEGATIVE_PATH), size=(25, 25))
        self.torrent_path_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.torrent_path_image_label.grid(row=0, column=1, padx=(10, 0), pady=(20, 2))

        self.torrent_path_input.bind("<KeyRelease>", lambda event: self.on_key_release(event, False))

        # select file button
        self.torrent_path_dialog = customtkinter.CTkButton(self, text="Select file", width=125,
                                                           command=lambda: self.file_dialog(False, start_path))
        self.torrent_path_dialog.grid(row=0, column=2, padx=10, pady=(20, 0), rowspan=1, sticky="w")

        # download dir
        self.download_dir_input = customtkinter.CTkTextbox(self, activate_scrollbars=False, wrap="none", font=("", 12), width=375, height=15)
        self.download_dir_input.insert("0.0", start_path)
        self.download_dir_input.grid(row=1, column=0, padx=(10, 0), pady=(20, 2), rowspan=1, columnspan=1, sticky="ew")

        # check mark image
        self.download_dir_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.download_dir_image_label.grid(row=1, column=1, padx=(10, 0), pady=(20, 2))

        self.download_dir_input.bind("<KeyRelease>", lambda event: self.on_key_release(event, True))

        # select file button
        self.download_dir_dialog = customtkinter.CTkButton(self, text="Select folder", width=125,
                                                           command=lambda: self.file_dialog(True, start_path))
        self.download_dir_dialog.grid(row=1, column=2, padx=10, pady=(20, 0), rowspan=1, sticky="w")

        # skip hash checkbox
        self.skip_hash_checkbox = customtkinter.CTkCheckBox(self, text="Skip hash check")
        self.skip_hash_checkbox.grid(row=2, columnspan=3, pady=(25, 5))

        # confirm button
        self.confirm_button = customtkinter.CTkButton(self, text="Confirm", state="disabled", command=lambda: print('yes! ', self.skip_hash_checkbox.get()))
        self.confirm_button.grid(row=3, column=0, padx=50, pady=30, columnspan=3, sticky="ew")

        # start params could be valid
        self.on_key_release(None, True)

    def on_key_release(self, event, is_dir: bool):
        path_input = self.download_dir_input if is_dir else self.torrent_path_input
        image_label = self.download_dir_image_label if is_dir else self.torrent_path_image_label
        path = path_input.get("0.0", "end")
        image = customtkinter.CTkImage(self.get_validation_mark(path, is_dir), size=(25, 25))
        image_label.configure(image=image)

    def get_validation_mark(self, path: str, is_dir: bool) -> Image:
        path = Path(path.strip("\n"))
        if is_dir:
            if os.path.isdir(path):
                self.valid_dir = True
                image = Image.open(App.POSITIVE_PATH)
            else:
                self.valid_dir = False
                image = Image.open(App.NEGATIVE_PATH)
        else:
            if path.is_file() and path.suffix == ".torrent":
                self.valid_file = True
                image = Image.open(App.POSITIVE_PATH)
            else:
                self.valid_file = False
                image = Image.open(App.NEGATIVE_PATH)

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

    def file_dialog(self, is_folder: bool, start_directory: str):
        instance = self.download_dir_input if is_folder else self.torrent_path_input
        image_label = self.download_dir_image_label if is_folder else self.torrent_path_image_label
        path = FileDialogs.open_file_dialog(is_folder, start_directory)
        if path:
            instance.delete("0.0", "end")
            instance.insert("0.0", path)
            self.on_key_release(None, is_folder)


class TorrentInfo(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)


class App(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"
    POSITIVE_PATH = r"assets\positive_mark.png"
    NEGATIVE_PATH = r"assets\negative_mark.png"

    WIDTH = 600
    HEIGHT = 375

    def __init__(self, start_path: str):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        self.geometry(f"{App.WIDTH}x{App.HEIGHT}")
        self.background = ("gray92", "gray14")

        self.columnconfigure(0, weight=1)

        self.title("RaBit v0.1")
        self.iconbitmap(App.ICON_PATH)
        self.minsize(App.WIDTH, App.HEIGHT)

        self.title = customtkinter.CTkLabel(self, text="Add a Torrent", font=("", 35))
        self.title.grid(row=0, column=0, rowspan=1, columnspan=3, padx=15, pady=20, sticky="ew")

        self.file_frame = FileDialogs(self, start_path)
        self.file_frame.grid(row=1, column=0, rowspan=3, columnspan=2, padx=15, pady=20)


app = App(get_configuration("download_dir"))
app.mainloop()
