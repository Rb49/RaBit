import customtkinter
from PIL import Image, ImageTk


class ZoomableMapFrame(customtkinter.CTkCanvas):
    MAP_PATH = r"assets\full_size_map.gif"
    initial_zoom = 0.35

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.pack()

        self.image = Image.open(ZoomableMapFrame.MAP_PATH)
        self.image_on_canvas = None
        self.zoom_level = ZoomableMapFrame.initial_zoom

        self.x = 0
        self.y = 0
        self.prev_x = 0
        self.prev_y = 0
        self.prev_width = self.image.width
        self.prev_height = self.image.height

        self.show_image()

        self.bind("<MouseWheel>", self.zoom)
        self.bind('<Motion>', self.motion)

    def reset(self, event):
        self.zoom_level = ZoomableMapFrame.initial_zoom
        self.x = 0
        self.y = 0
        self.prev_x = 0
        self.prev_y = 0
        self.prev_width = self.image.width
        self.prev_height = self.image.height
        self.show_image()

    def motion(self, event):
        self.x, self.y = event.x, event.y

    def show_image(self):
        prev_width_range = (self.prev_x, self.prev_x + self.prev_width)
        prev_height_range = (self.prev_y, self.prev_y + self.prev_height)

        if not (prev_width_range[0] <= self.x <= prev_width_range[1] and prev_height_range[0] <= self.y <=
                prev_height_range[1]):
            return

        normalized_x = ZoomableMapFrame.normalize(self.x, *prev_width_range)
        normalized_y = ZoomableMapFrame.normalize(self.y, *prev_height_range)

        image = self.image.resize((int(self.image.width * self.zoom_level), int(self.image.height * self.zoom_level)))
        self.image_on_canvas = ImageTk.PhotoImage(image)

        new_x = self.x - ZoomableMapFrame.inverse_normalization(normalized_x, 0, image.width)
        new_y = self.y - ZoomableMapFrame.inverse_normalization(normalized_y, 0, image.height)

        self.prev_width = image.width
        self.prev_height = image.height

        self.prev_x = new_x
        self.prev_y = new_y

        self.create_image(self.prev_x, self.prev_y, anchor="nw", image=self.image_on_canvas, tags="image")

    def zoom(self, event):
        if event.delta > 0 and self.zoom_level < 2.25:
            self.zoom_level *= 1.25
            self.show_image()
        if event.delta < 0:
            if self.zoom_level > self.initial_zoom:
                self.zoom_level /= 1.25
                self.show_image()
            else:
                self.reset(None)

    @staticmethod
    def normalize(value: int, min_value: int, max_value: int):
        return (value - min_value) / (max_value - min_value)

    @staticmethod
    def inverse_normalization(norm_value: float, min_value: int, max_value: int):
        return int((norm_value * (max_value - min_value)) + min_value)


def get_ZoomableMapFrame():
    return ZoomableMapFrame
