import click
from nimbus.utils.imgui.actions.actions import Action, ActionColors
from nimbus.utils.imgui.nodes import input_property
from nimbus.utils.imgui.general import not_user_creatable


@not_user_creatable
class DebugAction(Action):
    """Base class for debug-related actions."""

    def __init__(self):
        super().__init__()
        self.node_header_color = ActionColors.Debug


class Print(DebugAction):
    """Prints a value to the terminal."""

    @input_property()
    def text(self) -> str:
        """Text to print."""

    def execute(self):
        click.secho(self.text)
        self.trigger_flow()
