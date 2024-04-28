import struct
import bitstring

# messages id
CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7
CANCEL = 8
PORT = 9

# default request block size
BLOCK_SIZE = 2 ** 14
MAX_ALLOWED_MSG_SIZE = 2 ** 15 + 9


class Chock:
    """
    I cannot send requests to this peer anymore
    choke: <len=0001><id=0>
    """

    @staticmethod
    def encode() -> bytes:
        return struct.pack('>IB', 1, CHOKE)


class Unchock:
    """
    I can now send requests to this peer
    unchoke: <len=0001><id=1>
    """

    @staticmethod
    def encode() -> bytes:
        return struct.pack('>IB', 1, UNCHOKE)


class Interested:
    """
    let the peer know I want to download from it
    interested: <len=0001><id=2>
    """

    @staticmethod
    def encode() -> bytes:
        return struct.pack('>IB', 1, INTERESTED)


class NotInterested:
    """
    let the peer know I do want to download from it
    not interested: <len=0001><id=3>
    """

    @staticmethod
    def encode() -> bytes:
        return struct.pack('>IB', 1, NOT_INTERESTED)


class Have:
    """
    to let the downloader know it can request this piece
    have: <len=0005><id=4><piece index>
    """

    def __init__(self, piece_index):
        self.piece_index = piece_index

    @staticmethod
    def encode(piece_index: int) -> bytes:
        return struct.pack('>IBI',
                           5,
                           HAVE,
                           piece_index)

    @classmethod
    def decode(cls, msg: bytes) -> object:
        _, _, index = struct.unpack('>IBI', msg)
        return cls(index)


class Bitfield:
    """
    to let the downloader know which pieces it can request
    bitfield: <len=0001+X><id=5><bitfield>
    """

    def __init__(self, bitfield: bitstring.bitarray):
        self.bitfield = bitfield

    @staticmethod
    def encode(org_bitfield: bitstring.BitArray) -> bytes:
        bitfield = org_bitfield[:]
        if len(bitfield) % 8 != 0:  # add padding
            bitfield += bitstring.BitArray(uint=0, length=(8 - (len(bitfield) % 8)))

        return struct.pack(f'>IB{len(bitfield.bytes)}s',
                           len(bitfield.bytes) + 1,
                           BITFIELD,
                           bitfield.bytes)

    @classmethod
    def decode(cls, msg: bytes, pieces_num: int) -> object:
        _, _, bitfield = struct.unpack(f'>IB{len(msg) - 5}s', msg)
        bitfield = bitstring.BitArray(bytes=bitfield)
        bitfield = bitfield[:pieces_num]
        return cls(bitfield)


class Request:
    """
    request the data of a block
    request: <len=0013><id=6><index><begin><length>
    """

    def __init__(self, piece_index: int, begin: int, length: int):
        self.piece_index = piece_index
        self.begin = begin
        self.length = length

    @staticmethod
    def encode(piece_index: int, begin: int, length: int = BLOCK_SIZE) -> bytes:
        return struct.pack('>IBIII',
                           13,
                           REQUEST,
                           piece_index,
                           begin,
                           length)

    @classmethod
    def decode(cls, msg: bytes) -> object:
        _, _, piece_index, begin, length = struct.unpack('>IBIII', msg)
        return cls(piece_index, begin, length)


class Piece:
    """
    contains the data of a requested block
    piece: <len=0009+X><id=7><index><begin><block>
    """

    def __init__(self, piece_index: int, begin: int, data: bytes):
        self.piece_index = piece_index
        self.begin = begin
        self.length = len(data)
        self.data = data

    @staticmethod
    def encode(piece_index, begin, data) -> bytes:
        return struct.pack(f'>IBII{len(data)}s',
                           len(data) + 9,
                           PIECE,
                           piece_index,
                           begin,
                           data)

    @classmethod
    def decode(cls, msg: bytes) -> object:
        _, _, piece_index, begin, data = struct.unpack(f'>IBII{len(msg) - 13}s', msg)
        return cls(piece_index, begin, data)


class Cancel:
    """
    cancel the pending block request
    cancel: <len=0013><id=8><index><begin><length>
    """

    def __init__(self, piece_index: int, begin: int, length: int):
        self.piece_index = piece_index
        self.begin = begin
        self.length = length

    @staticmethod
    def encode(piece_index: int, begin: int, length: int) -> bytes:
        return struct.pack('>IBIII',
                           13,
                           CANCEL,
                           piece_index,
                           begin,
                           length)

    @classmethod
    def decode(cls, msg: bytes) -> object:
        _, _, piece_index, begin, length = struct.unpack('>IBIII', msg)
        return cls(piece_index, begin, length)


class Port:
    """
    the port this peer's DHT node is listening on
    port: <len=0003><id=9><listen-port>
    """

    def __init__(self, port: int):
        self.port = port

    @staticmethod
    def encode(port: int):
        return struct.pack('>IBH',
                           3,
                           PORT,
                           port)

    @classmethod
    def decode(cls, msg: bytes) -> object:
        _, _, port = struct.unpack('>IBH', msg)
        return cls(port)
