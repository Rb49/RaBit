import customtkinter
from PIL import Image


class Frame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        icon = customtkinter.CTkImage(Image.open(App.ICON_PATH),
                                      size=(master.winfo_screenwidth() // 12, master.winfo_screenwidth() // 12))

        image_label = customtkinter.CTkLabel(self, image=icon, text="", fg_color=master.background)
        image_label.grid(row=0, padx=20, pady=(10, 20))

        name = customtkinter.CTkLabel(self, text="RaBit ™", font=("impact", 35))
        name.grid(row=1, padx=20, pady=0)

        description = customtkinter.CTkLabel(self, text="A BitTorrent Client", font=("aptos black", 20))
        description.grid(row=2, padx=20, pady=0)

        description2 = customtkinter.CTkLabel(self, text="Loading...")
        description2.grid(row=3, padx=20, pady=(20, 0))

        progressbar = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")
        progressbar.start()
        progressbar.grid(row=4, padx=20, pady=0)


class App(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"
    WIDTH = 640
    HEIGHT = 360

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        self.background = ("gray92", "gray14")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        self.title("RaBit v0.1")
        self.iconbitmap(App.ICON_PATH)
        self.minsize(App.WIDTH, App.HEIGHT)

        self.frame = Frame(self, fg_color=self.background)
        self.frame.grid(row=0, padx=10, pady=(10, 0))


app = App()
app.mainloop()
