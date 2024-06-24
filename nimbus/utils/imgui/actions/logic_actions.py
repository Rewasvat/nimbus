from nimbus.utils.imgui.actions.actions import Action, ActionFlow, ActionColors
from nimbus.utils.imgui.nodes import PinKind, input_property, output_property
from nimbus.utils.imgui.general import not_user_creatable


@not_user_creatable
class LogicAction(Action):
    """Base class for logic flow related actions."""

    def __init__(self):
        super().__init__()
        self.node_header_color = ActionColors.Logic


class Branch(LogicAction):
    """Action Flow IF branching"""

    def __init__(self):
        super().__init__()
        default_trigger = self.get_output_pin("Trigger")
        default_trigger.pin_name = "True"
        default_trigger.pin_tooltip = "Triggered when the condition is True (truthy)."
        false_trigger = ActionFlow(self, PinKind.output, "False")
        false_trigger.pin_tooltip = "Triggered when the condition is False (falsy)."
        self._outputs.append(false_trigger)

    @input_property()
    def condition(self) -> bool:
        """Boolean value for the condition."""

    def execute(self):
        if self.condition:
            self.trigger_flow("True")
        else:
            self.trigger_flow("False")
