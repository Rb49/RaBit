from typing import List, Tuple

from src.read_file.read_torrent import read_torrent
from src.tracker.initial_announce import get_peers_addresses
import asyncio
from src.geolocation.utils import calc_distance, get_my_public_ip, get_info, get_banned_countries


async def main() -> None:
    # path for test torrent file
    test_path = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "../../data/" + test_path

    # read torrent file
    TorrentData = read_torrent(test_path)

    # initial announce
    if not TorrentData.announce_list:
        TorrentData.announce_list = [[TorrentData.announce]]

    size = TorrentData.info[b'piece length'] * len(TorrentData.piece_hashes)
    peers_list = await get_peers_addresses(TorrentData.announce_list, TorrentData.info_hash, TorrentData.peer_id, size, 56969)  # dummy port for now

    # --------

    # peer wire protocol
    queue = asyncio.Queue()

    ip = get_my_public_ip()

    def format_peers_list(peers: List[Tuple[str, int]], my_ip: str) -> List[Tuple[Tuple[str, int], List[str]]]:
        """
        formats the peers' list received from the trackers
        :param my_ip: my ip address
        :type peers: formatted peer list: [0]: address [1]: geolocation info [2]: distance from me
        """
        for i in range(len(peers)):
            peers[i] = [peers[i], (get_info(peers[i][0]))]
            peers[i].append(calc_distance(peers[i][0][0], my_ip))

        # remove peers from banned countries
        banned_list = get_banned_countries()
        peers = list(filter(lambda x: x[1][1] not in banned_list, peers))

        # remove peers with distance 0 (could be me)
        filtered_peers = list(filter(lambda x: x[2] > 0, peers))

        # sort by distance
        sorted_peers = sorted(filtered_peers, key=lambda x: x[2])

        # new peer structure: [0]: address. [1]: city, country, latitude, longitude
        return sorted_peers

    peers_list = format_peers_list(peers_list, ip)

    return


if __name__ == '__main__':

    asyncio.run(main())
