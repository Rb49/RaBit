from src.RaBit import Client

import asyncio
from PIL import Image
import customtkinter
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


class DataFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=0)

        # check mark image
        check_mark = customtkinter.CTkImage(Image.open(SettingsWindow.POSITIVE_PATH), size=(25, 25))
        self.validation_flags = [True] * 4

        # max leechers value
        self.max_leechers_title = customtkinter.CTkLabel(self, text="Max leecher peers")
        self.max_leechers_title.grid(row=0, column=0, columnspan=3, padx=(20, 0), pady=(5, 0), sticky="w")
        self.max_leechers_entry = customtkinter.CTkEntry(self, placeholder_text="Type here...")
        self.max_leechers_entry.insert(0, master.client.get_configuration("max_leecher_peers"))
        self.max_leechers_entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=(20, 0), pady=5)

        self.max_leechers_entry.bind("<KeyRelease>", lambda event: self.validate("max_leecher_peers"))

        self.max_leechers_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.max_leechers_image_label.grid(row=1, column=3, columnspan=1, padx=7, pady=0)

        # max optimistic unchock value
        self.max_optimistic_unchock_title = customtkinter.CTkLabel(self, text="Max optimistically unchocked peers")
        self.max_optimistic_unchock_title.grid(row=2, column=0, columnspan=3, padx=(20, 0), pady=(5, 0), sticky="w")
        self.max_optimistic_unchock_entry = customtkinter.CTkEntry(self, placeholder_text="Type here...")
        self.max_optimistic_unchock_entry.insert(0, master.client.get_configuration("max_optimistic_unchock"))
        self.max_optimistic_unchock_entry.grid(row=3, column=0, columnspan=3, sticky="ew", padx=(20, 0), pady=5)

        self.max_optimistic_unchock_entry.bind("<KeyRelease>", lambda event: self.validate("max_optimistic_unchock"))

        self.max_optimistic_unchock_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.max_optimistic_unchock_image_label.grid(row=3, column=3, columnspan=1, padx=7, pady=0)

        # max unchocked peers value
        self.max_unchock_title = customtkinter.CTkLabel(self, text="Max regularly unchocked peers")
        self.max_unchock_title.grid(row=4, column=0, columnspan=3, padx=(20, 0), pady=(5, 0), sticky="w")
        self.max_unchock_entry = customtkinter.CTkEntry(self, placeholder_text="Type here...")
        self.max_unchock_entry.insert(0, master.client.get_configuration("max_unchocked_peers"))
        self.max_unchock_entry.grid(row=5, column=0, columnspan=3, sticky="ew", padx=(20, 0), pady=5)

        self.max_unchock_entry.bind("<KeyRelease>", lambda event: self.validate("max_unchocked_peers"))

        self.max_unchock_image_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.max_unchock_image_image_label.grid(row=5, column=3, columnspan=1, padx=7, pady=0)

        # banned countries value
        self.banned_countries_title = customtkinter.CTkLabel(self, text="Banned countries (ISO alpha-2 codes)")
        self.banned_countries_title.grid(row=6, column=0, columnspan=3, padx=(20, 0), pady=(5, 0), sticky="w")
        self.banned_countries_entry = customtkinter.CTkEntry(self, placeholder_text="Type here...")
        banned_countries = ', '.join(master.client.get_banned_countries())
        self.banned_countries_entry.insert(0, banned_countries)
        self.banned_countries_entry.grid(row=7, column=0, columnspan=3, sticky="ew", padx=(20, 0), pady=5)

        self.banned_countries_entry.bind("<KeyRelease>", lambda event: self.validate("banned_countries"))

        self.banned_countries_image_label = customtkinter.CTkLabel(self, image=check_mark, text="")
        self.banned_countries_image_label.grid(row=7, column=3, columnspan=1, padx=7, pady=0)

        with open(SettingsWindow.COUNTRY_LIST_PATH, 'r') as file:
            lines = file.readlines()
            self.countries = [line.strip() for line in lines]

        # confirm button
        self.confirm_button = customtkinter.CTkButton(self, text="Save", state="normal",
                                                      command=lambda: asyncio.run(self.confirm_save()))
        self.confirm_button.grid(row=8, column=1, columnspan=1, padx=50, pady=30, sticky="ew")

    def validate(self, setting):
        self.validate_data(setting)
        if all(self.validation_flags):
            self.confirm_button.configure(state="normal")
        else:
            self.confirm_button.configure(state="disabled")

    def validate_data(self, setting: str):
        if setting == "max_leecher_peers":
            entry_data = self.max_leechers_entry.get().strip('\n')
            if entry_data.isdigit():
                entry_data = int(entry_data)
                if entry_data > 0:
                    image = customtkinter.CTkImage(Image.open(SettingsWindow.POSITIVE_PATH), size=(25, 25))
                    self.max_leechers_image_label.configure(image=image)
                    self.validation_flags[0] = True
                    return
            image = customtkinter.CTkImage(Image.open(SettingsWindow.NEGATIVE_PATH), size=(25, 25))
            self.max_leechers_image_label.configure(image=image)
            self.validation_flags[0] = False

        elif setting == "max_optimistic_unchock":
            entry_data = self.max_optimistic_unchock_entry.get().strip('\n')
            if entry_data.isdigit():
                entry_data = int(entry_data)
                if entry_data > 0:
                    image = customtkinter.CTkImage(Image.open(SettingsWindow.POSITIVE_PATH), size=(25, 25))
                    self.max_optimistic_unchock_image_label.configure(image=image)
                    self.validation_flags[1] = True
                    return
            image = customtkinter.CTkImage(Image.open(SettingsWindow.NEGATIVE_PATH), size=(25, 25))
            self.max_optimistic_unchock_image_label.configure(image=image)
            self.validation_flags[1] = False

        elif setting == "max_unchocked_peers":
            entry_data = self.max_unchock_entry.get().strip('\n')
            if entry_data.isdigit():
                entry_data = int(entry_data)
                if entry_data > 0:
                    image = customtkinter.CTkImage(Image.open(SettingsWindow.POSITIVE_PATH), size=(25, 25))
                    self.max_unchock_image_image_label.configure(image=image)
                    self.validation_flags[2] = True
                    return
            image = customtkinter.CTkImage(Image.open(SettingsWindow.NEGATIVE_PATH), size=(25, 25))
            self.max_unchock_image_image_label.configure(image=image)
            self.validation_flags[2] = False

        elif setting == "banned_countries":
            entry_data = self.banned_countries_entry.get().strip('\n')
            if entry_data:
                bad_entries = list(filter(lambda x: x.strip() not in self.countries, entry_data.split(',')))
            else:
                bad_entries = False

            if not bad_entries:
                image = customtkinter.CTkImage(Image.open(SettingsWindow.POSITIVE_PATH), size=(25, 25))
                self.banned_countries_image_label.configure(image=image)
                self.validation_flags[3] = True
            else:
                image = customtkinter.CTkImage(Image.open(SettingsWindow.NEGATIVE_PATH), size=(25, 25))
                self.banned_countries_image_label.configure(image=image)
                self.validation_flags[3] = False

    async def confirm_save(self):
        new_data = int(self.max_leechers_entry.get().strip('\n'))
        await self.master.client.set_configuration("max_leecher_peers", new_data)

        new_data = int(self.max_optimistic_unchock_entry.get().strip('\n'))
        await self.master.client.set_configuration("max_optimistic_unchock", new_data)

        new_data = int(self.max_unchock_entry.get().strip('\n'))
        await self.master.client.set_configuration("max_unchocked_peers", new_data)

        new_data = self.banned_countries_entry.get().strip('\n')
        if new_data:
            new_data = list(map(lambda x: x.strip(), new_data.split(',')))
        else:
            new_data = []
        await self.master.client.set_banned_countries(new_data)

        self.master.destroy()


class SettingsWindow(customtkinter.CTkToplevel):
    COUNTRY_LIST_PATH = abs_db_path("assets/countries.txt")
    POSITIVE_PATH = abs_db_path("assets/positive_mark.png")
    NEGATIVE_PATH = abs_db_path("assets/negative_mark.png")

    WIDTH = 600
    HEIGHT = 450

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.geometry(f"{SettingsWindow.WIDTH}x{SettingsWindow.HEIGHT}")
        self.background = ("gray92", "gray14")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)

        self.client = Client()

        self.title("")
        self.minsize(SettingsWindow.WIDTH, SettingsWindow.HEIGHT)

        self.title = customtkinter.CTkLabel(self, text="Settings", font=("", 35))
        self.title.pack(padx=20, pady=20)

        self.attributes("-topmost", True)

        self.data_frame = DataFrame(self)
        self.data_frame.pack(fill=customtkinter.BOTH, expand=True, padx=20, pady=(0, 10), anchor="center")


def get_TopWindow():
    return SettingsWindow
