#!/usr/bin/python

"""
a reset script to attempt recovery from file-related issues
"""

import json
import sys
import os
import hashlib
from pathlib import Path


def calculate_md5(file_path: str) -> str:
    """
    calculate md5 hash for a file
    """
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def calculate_md5_for_directory(directory: str = Path().resolve()):
    """
    calculates the md5 hash for a directory and all it's subdirectories
    """
    excluded_extensions = ['.json', '.db', '.mmdb']
    excluded_directories = ['__pycache__', '.idea', '.git', 'data', 'results']
    excluded_files = ['checksum.txt', 'reset.py']

    counter = 0
    with open('checksum.txt', 'w') as file:
        file.write(f"\n\n")
        for dirpath, _, filenames in os.walk(directory):
            if any(excluded_dir in dirpath for excluded_dir in excluded_directories):
                continue

            for filename in filenames:
                if filename in excluded_files:
                    continue

                file_path = os.path.join(dirpath, filename)

                if any(file_path.endswith(ext) for ext in excluded_extensions):
                    continue

                md5_hash = calculate_md5(file_path)
                file.write(f"{md5_hash}\n")
                counter += 1

        file.seek(0)
        file.write(str(counter))


def check_md5_for_directory(directory: str = Path().resolve()):
    """
    checks if the md5 hash of a file is intact, for a directory and all it's subdirectories
    """
    excluded_extensions = ['.json', '.db', '.mmdb']
    excluded_directories = ['__pycache__', '.idea', '.git', 'data', 'results']
    excluded_files = ['checksum.txt', 'reset.py']

    counter = 0
    for dirpath, _, filenames in os.walk(directory):
        if any(excluded_dir in dirpath for excluded_dir in excluded_directories):
            continue

        for filename in filenames:
            if filename in excluded_files:
                continue

            file_path = os.path.join(dirpath, filename)

            if any(file_path.endswith(ext) for ext in excluded_extensions):
                continue

            counter += 1

    with open('checksum.txt', 'r') as file:
        if int(file.readline().strip('\n')) != counter:
            print("A file has been added or removed. Can't check for corrupted files")
            return

        for dirpath, _, filenames in os.walk(directory):
            if any(excluded_dir in dirpath for excluded_dir in excluded_directories):
                continue

            for filename in filenames:
                if filename in excluded_files:
                    continue

                file_path = os.path.join(dirpath, filename)

                if any(file_path.endswith(ext) for ext in excluded_extensions):
                    continue

                md5_hash = calculate_md5(file_path)
                if file.readline().strip('\n') != md5_hash:
                    print(f"{file_path} is corrupted!")


if __name__ == '__main__':
    try:
        parent_path = 'src/RaBit/app_data'

        # delete completed torrents db
        if os.path.exists(path := os.path.join(parent_path, 'completed_torrents.db')):
            os.remove(path)

        # delete banned peers db
        # os.remove(os.path.join(parent_path, 'banned_peers.db'))

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

        # find corrupted files
        check_md5_for_directory()

        print('Reset was successful!')
    except Exception as e:
        print('Reset was unsuccessful due to ', e)
    finally:
        sys.exit()
