import customtkinter

from src.RaBit import DownloadSession


class TorrentsInfo(customtkinter.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.torrents = []  # TODO add as param



class PeersInfo(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)



class App(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"

    WIDTH = 640
    HEIGHT = 360

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        self.columnconfigure(0, weight=1)

        self.title("RaBit Client")
        self.iconbitmap(App.ICON_PATH)
        self.minsize(App.WIDTH, App.HEIGHT)

        self.torrents_info_frame = TorrentsInfo(self)
        self.torrents_info_frame.grid(row=0, rowspan=3, padx=15, pady=(20, 3), sticky="news")

        self.peers_info_frame = PeersInfo(self)
        self.peers_info_frame.grid(row=3, rowspan=6, padx=15, pady=(3, 20), sticky="news")




app = App()
app.mainloop()
