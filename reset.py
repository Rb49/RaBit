#!/usr/bin/python

"""
a reset script to attempt recovery from file-related issues
"""

import json
import sys
import os


if __name__ == '__main__':
    try:
        parent_path = 'src/RaBit/app_data'

        # delete completed torrents db
        if os.path.exists(path := os.path.join(parent_path, 'completed_torrents.db')):
            os.remove(path)

        # delete banned peers db
        # if os.path.exists(path := os.path.join(parent_path, 'banned_peers.db')):
        #     os.remove(path)

        # remove ongoing torrents
        with open(os.path.join(parent_path, 'ongoing_torrents.json'), 'r+') as json_file:
            json_file.seek(0)
            json_file.truncate()
            json.dump([], json_file)

        # reset config
        with open(os.path.join(parent_path, 'default_config.json'), 'r') as json_file:
            default = json.load(json_file)
        with open(os.path.join(parent_path, 'config.json'), 'r+') as json_file:
            json_file.seek(0)
            json_file.truncate()
            json.dump(default, json_file)

        print('Reset was successful!')
    except Exception as e:
        print('Reset was unsuccessful due to ', e)
    finally:
        sys.exit()
