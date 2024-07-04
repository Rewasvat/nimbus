from nimbus.utils.imgui.actions.actions import Action, ActionColors
from nimbus.utils.imgui.nodes import input_property, output_property, DataPin
from nimbus.utils.imgui.general import not_user_creatable


@not_user_creatable
class Operation(Action):
    """Base class for math-related actions."""

    def __init__(self):
        super().__init__(False)
        self.node_header_color = ActionColors.Operations


class Sum(Operation):
    """Sum values together."""

    @input_property(dynamic_input_pins=True)
    def values(self) -> list[float]:
        """The values to sum"""
        return []

    @output_property(use_prop_value=True)
    def result(self) -> float:
        """The result of the sum of our input values"""
        return sum(self.values, 0.0)


class Concatenate(Operation):
    """Concatenate various strings together.

    Equivalent to Python's ``string.join`` method.
    """

    @input_property(dynamic_input_pins=True)
    def strings(self) -> list[str]:
        """The strings to join."""
        return []

    @input_property()
    def separator(self) -> str:
        """The text to use as separator when joining the strings."""
        return ""

    @output_property(use_prop_value=True)
    def result(self) -> str:
        """The concatenated string."""
        return self.separator.join(self.strings)
