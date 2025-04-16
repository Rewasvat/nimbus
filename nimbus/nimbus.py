#!/usr/bin/env python3
import libasvat.command_utils as cmd_utils


class NimbusCommands(cmd_utils.RootCommands):
    """Collection of personal scripts and other utilities organized in a simple to use CLI.

    Check each sub-group/sub-command using `--help` for specific information on them.
    """

    def initialize(self):
        self.app_name = "nimbus"
        self.module_ignore_paths.append("nimbus")
        return super().initialize()


main = NimbusCommands().click_group
