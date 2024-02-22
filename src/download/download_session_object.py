from src.file.file_object import File


class download_session(object):
    def __init__(self, file_to_download: File):
        self.file = file_to_download
