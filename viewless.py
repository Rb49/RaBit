#!/usr/bin/python

"""
main file of RaBit module only, without ui
"""

from src.RaBit.rabit import Client

import asyncio
import sys
import tracemalloc


async def main(client: Client, seed: bool = True):
    if not seed:
        client._force_start()
    else:
        client.start()

    if client.started:
        print('Client initialized successfully!')
        if len(sys.argv) == 5:
            _, _, torrent_path, result_path, skip_hash_check = sys.argv
            thread = client.add_torrent(torrent_path, result_path, bool(skip_hash_check))
        else:
            thread = None
    else:
        print('Client could not initialize!')
        return

    while seed or thread.is_alive() if hasattr(thread, "is_alive") else False:
        await client.torrents_state_update_loop()
        await asyncio.sleep(1)


if __name__ == '__main__':
    tracemalloc.start()

    if sys.version_info[0] != 3 or sys.version_info[1] < 10:
        raise Exception("Wrong Python version! Use version 3.10 and above.")

    client = Client()
    asyncio.run(main(client, bool(sys.argv[1])))
    sys.exit()
