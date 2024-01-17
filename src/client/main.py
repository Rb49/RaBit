from src.read_file.read_torrent import read_torrent
from src.tracker.udp_tracker import udp_tracker_announce
from src.tracker.http_tracker import http_tracker_announce
from collections import OrderedDict

if __name__ == '__main__':
    # path for test torrent file
    test_path = "The.Hunger.Games.The.Ballad.of.Songbirds.and.Snakes.2023.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX[TGx].torrent"
    test_path = "../../data/" + test_path

    # read torrent file
    TorrentFile = read_torrent(test_path)

    # connect to trackers

    if not TorrentFile.announce_list:
        TorrentFile.announce_list = [[TorrentFile.announce]]

    peers = []
    for url in TorrentFile.announce_list:
        response = ''
        url = url[0].decode('utf-8')
        try:
            if 'udp' in url:
                response = udp_tracker_announce(url, TorrentFile.info_hash, TorrentFile.peer_id, timeout_list=[1])

            elif 'http' in url:
                response = http_tracker_announce(url, TorrentFile.info_hash, TorrentFile.peer_id)

            if not isinstance(response, str):
                peers.extend(response[0])

        except Exception as e:
            print(e)

    # remove duplicates from peers[]
    peers = list(dict.fromkeys(peers))

    # create peer instances for each peer and connect


    quit(0)