from src.torrent.torrent import read_torrent
from src.tracker.announce import announce
from src.tracker.utils import format_peers_list
import asyncio
from src.peer.handshake import tcp_wire_communication
from src.geolocation.utils import get_my_public_ip


async def main() -> None:
    # path for test torrent file
    test_path = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "../../data/" + test_path

    # read torrent file
    TorrentData = read_torrent(test_path)

    # initial announce
    size = TorrentData.info[b'piece length'] * len(TorrentData.piece_hashes)
    peers_list = await announce(TorrentData, 0, 0, size, 56969, 2)  # fake port for now

    # my_ip = get_my_public_ip()
    my_ip = '176.230.227.216'
    peers_list = format_peers_list(peers_list, my_ip)

    # --------

    # peer wire protocol
    queue = asyncio.Queue()

    await asyncio.gather(*[tcp_wire_communication(peer, TorrentData) for peer in peers_list])

    return


if __name__ == '__main__':

    asyncio.run(main())
