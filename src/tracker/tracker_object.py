import math
import time

from .http_tracker import http_tracker_announce
from .udp_tracker import udp_tracker_announce
import src.app_data.db_utils as db_utils


UNREACHABLE = 0
ANNOUNCING = 1
WORKING = 2
NONE = None


class Tracker(object):
    def __init__(self, url: str, info_hash: bytes, peer_id: bytes, interval: int = 0):
        self.url = url
        self.type = 'http' if 'http' in url else 'udp'
        self.info_hash = info_hash
        self.last_announce = None
        self.interval = interval
        self.client_peer_id = peer_id
        self.state = NONE

    async def re_announce(self, download: int, uploaded: int, left: int, event: int = 0):
        self.state = ANNOUNCING
        port = db_utils.get_configuration('v4_forward')['external_port']
        try:
            response = ''
            if self.type == 'udp':
                response = await udp_tracker_announce(self.url, self.info_hash, self.client_peer_id, download, uploaded, left, event, port)

            elif self.type == 'http':
                response = await http_tracker_announce(self.url, self.info_hash, self.client_peer_id, download, uploaded, left, event, port)

            if not isinstance(response, str):
                self.state = WORKING
                self.interval = response[1]
            else:
                raise

        except:
            self.state = UNREACHABLE
            self.interval = math.inf
        finally:
            self.last_announce = time.time()

    def __repr__(self):
        return f"state: {self.state}, interval: {self.interval}, url: {self.url}"

    def __hash__(self):
        return hash(repr(self))
