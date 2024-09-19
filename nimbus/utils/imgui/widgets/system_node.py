import click
import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.math import Vector2, multiple_lerp_with_weigths
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.nodes import PinKind, Node, input_property, output_property
from nimbus.utils.imgui.widgets.system import UIManager, UISystem
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from imgui_bundle import imgui


class UseSystem(LeafWidget):
    """Executes a UISystem.

    This allows to execute one of the saved UISystem configs as single node in another graph.
    The system's input/output properties (data values, widget connections, etc) are connected to equivalent
    pins in this node, thus allowing to pass/receive data from the contained UISystem.

    Allowing re-use of a UISystem in other systems may simplify a lot of work to create complex graphs.
    """

    def __init__(self):
        super().__init__()
        self.node_bg_color = Color(0.1, 0.25, 0.15, 0.75)
        self.node_header_color = WidgetColors.External
        self._system: UISystem = None

    @types.string_property()
    def system_name(self) -> str:
        """Name of UISystem Config to use."""
        return self._system.name if self._system is not None else ""

    @system_name.setter
    def system_name(self, value: str):
        if self._system is not None:
            if self._system.name == value:
                return
            self._system.clear()
            self._system = None
        manager = UIManager()
        config = manager.get_config(value)
        if config:
            self._system = config.instantiate()

    @property
    def system(self):
        """Gets our internal UISystem being used.

        This depends on our ``system_name`` property.
        """
        return self._system

    def render(self):
        self._handle_interaction()
        if self._system is not None:
            self._system.render()

    def delete(self):
        self._system.clear()
        self._system = None
        return super().delete()

    def _update_system_name_editor(self, editor: types.StringEditor):
        """Method automatically called by our ``system_name`` enum-property editor in order to dynamically
        update its settings before editing."""
        manager = UIManager()
        editor.options = manager.get_all_config_names()
