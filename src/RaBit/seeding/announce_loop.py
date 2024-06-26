from ..app_data import db_utils
from ..file.file_object import PickleableFile
from ..tracker.tracker_object import Tracker, WORKING
from .utils import FileObjects

from typing import List
import time
import asyncio


async def announce_loop(trackers: List[Tracker], session) -> None:
    """
    a loop for an info hash: re-announces for each tracker interval with relevant stats
    :param trackers: a list of Tracker instances
    :param session: DownloadingSession or PickleableFile instance with stats
    :return: None
    """
    while True:
        if session.info_hash not in FileObjects:
            return
        new_trackers = list(filter(lambda x: x.state == WORKING, trackers))
        new_trackers.sort(key=lambda x: x.last_announce + x.interval, reverse=False)
        for tracker in new_trackers:
            if tracker.last_announce + tracker.interval <= time.time():
                download = session.corrupted + session.wasted + session.downloaded
                upload = session.uploaded
                if isinstance(session, PickleableFile):
                    left = 0
                else:
                    left = session.left
                asyncio.create_task(tracker.re_announce(download, upload, left, 0))
                print('announced! ', tracker)
            else:
                break
        if isinstance(session, PickleableFile):
            db_utils.CompletedTorrentsDB().update_torrent(session)
        await asyncio.sleep(1)
