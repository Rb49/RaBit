from src.read_file.read_torrent import read_torrent
from src.tracker.udp_tracker import udp_tracker_announce
from src.tracker.http_tracker import http_tracker_announce
import asyncio


async def main() -> None:
    # path for test torrent file
    test_path = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "../../data/" + test_path

    # read torrent file
    TorrentData = read_torrent(test_path)

    # announce
    if not TorrentData.announce_list:
        TorrentData.announce_list = [[TorrentData.announce]]

    peers_list = []

    async def announce(tracker_url):
        nonlocal peers_list

        response = ''
        tracker_url = tracker_url[0].decode('utf-8')

        try:
            if 'udp' in tracker_url:
                response = await udp_tracker_announce(tracker_url, TorrentData.info_hash, TorrentData.peer_id, 6881, event=2, timeout_list=[1])

            elif 'http' in tracker_url:
                response = await http_tracker_announce(tracker_url, TorrentData.info_hash, TorrentData.peer_id, 6881, event=2)

            if not isinstance(response, str):
                peers_list.extend(response[0])

        except Exception as e:
            print(e)

        return

    tasks = [announce(url) for url in TorrentData.announce_list]

    await asyncio.gather(*tasks)

    # remove duplicates from peers[]
    peers_list = list(dict.fromkeys(peers_list))

    return


if __name__ == '__main__':
    asyncio.run(main())
