import click
import libasvat.command_utils as cmd_utils


@cmd_utils.main_command_group
class MediaManager(metaclass=cmd_utils.Singleton):
    """MEDIA COMMANDS"""

    def __init__(self):
        pass

    @cmd_utils.object_identifier
    def name(self):
        return "media"

    @cmd_utils.instance_command()
    def test(self):
        """TEST TODO"""
        click.secho("carambolas")


class MediaTypeHandler(metaclass=cmd_utils.Singleton):
    """TODO"""

    def __init__(self, type: str, source: 'MediaSource'):
        self.type = type
        self.source = source


class MediaSource(metaclass=cmd_utils.Singleton):
    """TODO"""

    def __init__(self):
        pass


class MediaEntry:
    """TODO"""

    def __init__(self, handler: MediaTypeHandler, imdb_id: str):
        self.handler = handler
        self.imdb_id = imdb_id

    def status(self):
        """TODO"""
        pass

    def delete(self):
        """TODO"""
        pass

    def update(self):
        """TODO"""
        pass
