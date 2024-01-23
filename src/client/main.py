from src.read_file.read_torrent import read_torrent
from src.tracker.initial_announce import get_peers_addresses
import asyncio
from src.peer.handshake import *


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

    return


if __name__ == '__main__':

    asyncio.run(main())
