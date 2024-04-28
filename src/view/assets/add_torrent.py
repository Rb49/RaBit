import customtkinter
from PyQt5.QtWidgets import QApplication, QFileDialog

from src.RaBit import get_configuration


def open_file_dialog(is_folder: bool = False, start_directory: str = ""):
    app = QApplication([])
    file_dialog = QFileDialog()
    if is_folder:
        file_dialog.setFileMode(QFileDialog.Directory)
    else:
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Torrent Files (*.torrent)")
    if start_directory:
        file_dialog.setDirectory(start_directory)
    if file_dialog.exec_():
        selected_file = file_dialog.selectedFiles()[0]
        return selected_file
    else:
        return None


class Frame(customtkinter.CTkFrame):
    def __init__(self, master, start_path: str, **kwargs):
        super().__init__(master, **kwargs)
        description = customtkinter.CTkLabel(self, text="Add a Torrent")
        description.grid(row=0, column=0, padx=20, pady=(0, 20), columnspan=2, sticky="ew")

        torrent_path_input = customtkinter.CTkTextbox(self)
        torrent_path_input.insert("0.0", start_path)
        torrent_path_input.grid(row=1, column=0, padx=20, pady=(0, 20), rowspan=1, columnspan=1, sticky="w")

        def file_dialog(*args):
            path = open_file_dialog(*args)
            if path:
                torrent_path_input.delete("0.0", "end")
                torrent_path_input.insert("0.0", path)

        torrent_path_dialog = customtkinter.CTkButton(self, text="Select File", command=lambda: file_dialog(False, start_path))
        torrent_path_dialog.grid(row=1, column=1, padx=20, pady=(0, 20), rowspan=1, sticky="w")


class App(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"
    WIDTH = 320
    HEIGHT = 180

    def __init__(self, start_path: str):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        self.background = ("gray92", "gray14")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        self.title("RaBit v0.1")
        # self.iconbitmap(App.ICON_PATH)
        self.minsize(App.WIDTH, App.HEIGHT)

        self.frame = Frame(self, start_path, fg_color=self.background)
        self.frame.grid(row=0, padx=10, pady=(10, 0))


app = App(get_configuration("download_dir"))
app.mainloop()
