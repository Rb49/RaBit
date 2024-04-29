from .loading_window import App as Loading
from .add_torrent import App as Add
from .main_window import App as Main


class View(object):
    def __init__(self):
        self.loading_window = Loading
        self.add_torrent_window = Add
        self.main_window = Main

        self.current_window = Loading





