#!/usr/bin/env python3
import os
import click
import nimbus.utils.command_utils as cmd_utils
import nimbus.utils.utils as utils
from nimbus.data import DataCache


class NimbusCommands:
    """Collection of personal scripts and other utilities organized in a simple to use CLI.

    Check each sub-group/sub-command using `--help` for specific information on them.
    """

    def __init__(self):
        self.command_objects = []
        self.load_all_command_groups()

    def load_all_command_groups(self):
        """Loads all modules from Nimbus in order to check for all command modules to add to CLI."""
        # Ignore main nimbus module (this script), data module and utils folder, since we shouldn't
        # define main commands in them.
        ignore_paths = [
            "nimbus",
            "data",
            "utils",
        ]
        utils.load_all_modules(os.path.dirname(__file__), "nimbus", ignore_paths=ignore_paths)
        self.command_objects = [cls() for cls in cmd_utils._main_commands]

    @cmd_utils.sub_groups()
    def get_commands(self):
        """Gets the command objects."""
        return self.command_objects

    @cmd_utils.result_callback
    def finalize(self, result, **kwargs):
        """Handles processing performed *after* the group has executed its desired command(s)."""
        data = DataCache()
        data.shutdown()


main = cmd_utils.DynamicGroup(NimbusCommands(), "nimbus", context_settings={"help_option_names": ["-h", "--help"]})
click.version_option()(main)
