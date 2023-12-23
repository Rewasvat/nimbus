
import nimbus.media.media as media


class EZTV(media.MediaSource):
    """TODO"""

    def __init__(self):
        super().__init__(self)


class SeriesHandler(media.MediaTypeHandler):
    """TODO"""

    def __init__(self):
        super().__init__("serie", EZTV())


class Serie(media.MediaEntry):
    """TODO"""

    def __init__(self, imdb_id):
        super().__init__(handler=SeriesHandler(), imdb_id=imdb_id)

    def status(self):
        """TODO"""
        pass

    def delete(self):
        """TODO"""
        pass

    def update(self):
        """TODO"""
        pass
