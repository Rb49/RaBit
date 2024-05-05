import time

from src.RaBit import Client


def main():
    client = Client()
    client.start()

    client.add_torrent(
        r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\data\debian-edu-12.4.0-amd64-netinst.iso.torrent",
        r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\results",
        False)

    while True:
        print(client.torrents)
        time.sleep(1)

    exit(0)


if __name__ == '__main__':
    import tracemalloc
    tracemalloc.start()

    import sys
    if sys.version_info[0:2] != (3, 10):
        raise Exception("Wrong Python version! Use version 3.10 only.")

    main()
