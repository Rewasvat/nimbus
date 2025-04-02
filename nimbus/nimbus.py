#!/usr/bin/env python3
import os
import sys
import click
import traceback
import nimbus.utils.command_utils as cmd_utils
import nimbus.utils.utils as utils
from nimbus.data import DataCache


# TODO: Esse set_assets_folder() devia ser automático, em algum módulo do `utils.imgui`... Talvez no AppWindow antes do run()? Ou no __init__?
from imgui_bundle import hello_imgui  # type: ignore
hello_imgui.set_assets_folder(os.path.join(os.path.dirname(__file__), "assets"))


# TODO: Refatorar essa classe pra ser parte do Utils, que poderia ser refatorado como uma lib externa.
#   assim facilitaria usar esse sistema em outros projetos.
#   - o código abaixo aqui, que instancia o DynamicGroup com essa classe, e adiciona o help-options e tal
#     poderia ser um class-method. Ai o uso disso em outros projetos seria instanciar a classe (ou herdar dela),
#     e usar tal class-method pra criar o objeto do grupo em si que seria o main do projeto.
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

    @cmd_utils.group_callback
    def on_group_callback(self, ctx: click.Context, debug):
        """Group callback, called when a subcommand/subgroup is executed or if this group is executed as a
        command (and has invoke_without_command=True)."""
        if debug:
            import debugpy
            port = 5678
            debugpy.listen(port)
            click.secho(f"[DEBUGGER] Waiting connection at port {port}...", fg="magenta")
            debugpy.wait_for_client()
            click.secho("[DEBUGGER] CONNECTED!", fg="magenta")

    @cmd_utils.result_callback
    def finalize(self, result, **kwargs):
        """Handles processing performed *after* the group has executed its desired command(s)."""
        data = DataCache()
        data.shutdown()


debug_help = "Initializes Nimbus with Python Debugger (debugpy) active, "
debug_help += "listening in localhost at port 5678."

main = cmd_utils.DynamicGroup(NimbusCommands(), "nimbus", context_settings={"help_option_names": ["-h", "--help"]})
# TODO: idealmente essa debug option devia ser definida junto com o on_group_callback lá.
click.option("-d", "--debug", is_flag=True, help=debug_help)(main)
click.version_option()(main)


if utils.is_frozen():
    click.secho("Running NIMBUS in standalone executable mode.", fg="green")
    cmd_line_args = sys.argv[1:]
    if len(cmd_line_args) <= 0:
        cmd_line_args = ["monitor", "edit"]
    try:
        main(cmd_line_args)
    except Exception:
        click.secho(f"{traceback.format_exc()}\nUNHANDLED EXCEPTION / Closing Nimbus.", fg="red")
        input("Press ENTER to close...")
