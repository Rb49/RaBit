from typing import List, Any, Dict
import time
import asyncio

from src.file.file_object import PickableFile
from src.tracker.tracker_object import Tracker, WORKING, ANNOUNCING


async def announce_loop(trackers: List[Tracker], session):
    while True:
        new_trackers = list(filter(lambda x: x.state == WORKING, trackers))
        new_trackers.sort(key=lambda x: x.last_announce + x.interval, reverse=False)
        for tracker in new_trackers:
            if tracker.last_announce + tracker.interval <= time.time():
                download = session.corrupted + session.wasted + session.downloaded
                upload = session.uploaded
                left = session.left
                asyncio.create_task(tracker.re_announce(download, upload, left))
                print('announced! ', tracker)
            else:
                break
        await asyncio.sleep(5)
