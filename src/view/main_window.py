import customtkinter


class App(customtkinter.CTk):
    ICON_PATH = r"assets\RaBit_icon.ico"

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.title("RaBit Client")
        self.iconbitmap(App.ICON_PATH)
        self.minsize(640, 360)



app = App()
app.mainloop()
