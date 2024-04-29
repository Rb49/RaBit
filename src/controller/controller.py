from src.RaBit import Client
from src.view import View


class Controller(object):
    def __init__(self):
        self.module = Client()
        self.view = View()

