from typing import Dict

from src.RaBit import get_configuration, get_ongoing_torrents, set_configuration, start_seeding_server, DownloadSession


def get_download_dir() -> str:
    return get_configuration("download_dir")


def get_download_sessions() -> Dict[bytes, DownloadSession]:
    return DownloadSession.Sessions







