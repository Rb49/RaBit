from typing import Tuple

import customtkinter
from PIL import Image, ImageTk
import os


class ZoomableMapCanvas(customtkinter.CTkCanvas):
    MAP_PATH = r"assets\full_size_map.png"
    PINS_PATH = r"assets\country_pins"
    initial_zoom = 0.35

    def __init__(self, master, addresses, **kwargs):
        super().__init__(master, **kwargs)

        self.pack()

        self.image = Image.open(ZoomableMapCanvas.MAP_PATH).convert('RGBA')
        self.image_on_canvas = None
        self.zoom_level = ZoomableMapCanvas.initial_zoom

        self.x = 0
        self.y = 0
        self.prev_x = 0
        self.prev_y = 0
        self.prev_width = self.image.width
        self.prev_height = self.image.height

        self.addresses = addresses

        self.show_image()

        self.bind("<MouseWheel>", self.zoom)
        self.bind('<Motion>', self.motion)

    def reset(self, event):
        self.zoom_level = ZoomableMapCanvas.initial_zoom
        self.show_image(True)

    def motion(self, event):
        self.x, self.y = event.x, event.y

    def show_image(self, reset: bool = False):
        if not reset:
            prev_width_range = (self.prev_x, self.prev_x + self.prev_width)
            prev_height_range = (self.prev_y, self.prev_y + self.prev_height)

            if not (prev_width_range[0] <= self.x <= prev_width_range[1] and prev_height_range[0] <= self.y <= prev_height_range[1]):
                return

            normalized_x = ZoomableMapCanvas.normalize(self.x, *prev_width_range)
            normalized_y = ZoomableMapCanvas.normalize(self.y, *prev_height_range)

            image = self.image.resize((int(self.image.width * self.zoom_level), int(self.image.height * self.zoom_level)))

            new_x = self.x - ZoomableMapCanvas.inverse_normalization(normalized_x, 0, image.width)
            new_y = self.y - ZoomableMapCanvas.inverse_normalization(normalized_y, 0, image.height)

            self.prev_width = image.width
            self.prev_height = image.height

            self.prev_x = new_x
            self.prev_y = new_y
        else:
            image = self.image.resize((int(self.image.width * ZoomableMapCanvas.initial_zoom), int(self.image.height * ZoomableMapCanvas.initial_zoom)))
            self.prev_x = 0
            self.prev_y = 0
            self.prev_width = image.width
            self.prev_height = image.height

        # add pins
        size = (int(max(25, 1.25 * 25 * self.zoom_level)), int(max(33, 1.25 * 33 * self.zoom_level)))
        for pin in self.addresses:
            pin: Tuple[str, str, float, float]  # city, country code, latitude, longitude
            if None in pin[2:4]:
                continue
            if pin[1] is not None:
                pin_image = Image.open(os.path.join(ZoomableMapCanvas.PINS_PATH, f"{pin[1]}.png")).convert('RGBA')
            else:
                pin_image = Image.open(os.path.join(ZoomableMapCanvas.PINS_PATH, "NONE.png")).convert('RGBA')
            pin_image = pin_image.resize(size)
            position = ZoomableMapCanvas.format_coords(pin[2], pin[3], *size, self.prev_width, self.prev_height)

            Image.Image.alpha_composite(image, pin_image, position)
        self.delete("image")
        self.image_on_canvas = ImageTk.PhotoImage(image)
        self.create_image(self.prev_x, self.prev_y, anchor="nw", image=self.image_on_canvas, tags="image")

    @staticmethod
    def format_coords(latitude, longitude, pin_width, pin_height, map_width, map_height) -> Tuple[int, int]:
        latitude = 90 - latitude
        longitude += 180

        new_width = int((map_width / 360) * (longitude - 1))
        new_height = int((map_height / 180) * (latitude - 1))
        x_position = new_width
        y_position = new_height - pin_height
        return x_position, y_position

    def zoom(self, event):
        if event.delta > 0 and self.zoom_level < 1.5:
            self.zoom_level *= 1.35
            self.show_image()
        if event.delta < 0:
            if self.zoom_level > self.initial_zoom:
                self.zoom_level /= 1.35
                self.show_image()
            else:
                self.reset(None)

    @staticmethod
    def normalize(value: int, min_value: int, max_value: int):
        return (value - min_value) / (max_value - min_value)

    @staticmethod
    def inverse_normalization(norm_value: float, min_value: int, max_value: int):
        return int((norm_value * (max_value - min_value)) + min_value)


def get_ZoomableMapCanvas():
    return ZoomableMapCanvas
