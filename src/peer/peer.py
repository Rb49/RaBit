import struct
from typing import Union
from enum import Enum


class MessageID(Enum):
    Choke = 0
    Unchoke = 1
    Interested = 2
    NotInterested = 3
    Have = 4
    Bitfield = 5
    Request = 6
    Piece = 7
    Cancel = 8


class Message(object):
    def __init__(self, length: int, ID: int, payload: bytes = None):
        self.length: int = length
        self.MessageID: str = MessageID(ID).name
        self.payload: Union[bytes, None] = payload








