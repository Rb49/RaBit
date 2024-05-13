import customtkinter
from PIL import Image
import os
import sys


def abs_db_path(file_name: str) -> str:
    """
    computes the absolute path of the file (based on this root dir)
    :return: absolute path
    """
    if hasattr(sys, '_MEIPASS'):  # TODO add `data` dir in exe for all data, paste manually
        base_path = os.path.join(sys._MEIPASS, 'data')
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, file_name)


class Frame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        icon = customtkinter.CTkImage(Image.open(LoadingWindow.ICON_PATH),
                                      size=(master.winfo_screenwidth() // 12, master.winfo_screenwidth() // 12))

        image_label = customtkinter.CTkLabel(self, image=icon, text="", fg_color=master.background)
        image_label.grid(row=0, padx=20, pady=(10, 20))

        if "nt" == os.name:  # linux tkinter doesn't support this font
            font = "impact"
        else:
            font = "aptos black"

        name = customtkinter.CTkLabel(self, text="RaBit ™", font=(font, 35))
        name.grid(row=1, padx=20, pady=0)

        description = customtkinter.CTkLabel(self, text="A BitTorrent Client", font=("aptos black", 20))
        description.grid(row=2, padx=20, pady=0)

        self.description2 = customtkinter.CTkLabel(self, text="Loading...")
        self.description2.grid(row=3, padx=20, pady=(20, 5))

        self.progressbar = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")
        self.progressbar.start()
        self.progressbar.grid(row=4, padx=20, pady=0)


class LoadingWindow(customtkinter.CTk):
    ICON_PATH = abs_db_path("assets/RaBit_icon.ico")
    WIDTH = 640
    HEIGHT = 360

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        self.background = ("gray92", "gray14")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        self.title("RaBit v1.0.0")
        if "nt" == os.name:  # linux tkinter doesn't support .ico
            self.iconbitmap(LoadingWindow.ICON_PATH)
        self.minsize(LoadingWindow.WIDTH, LoadingWindow.HEIGHT)

        self.frame = Frame(self, fg_color=self.background)
        self.frame.grid(row=0, padx=10, pady=(10, 0))


def get_LoadingWindow():
    return LoadingWindow
