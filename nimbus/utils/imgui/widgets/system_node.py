import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.colors import Color
from nimbus.utils.imgui.general import not_user_creatable
from nimbus.utils.imgui.nodes import PinKind, input_property, output_property
from nimbus.utils.imgui.nodes.nodes_data import DataPin, DataPinState, SyncedDataPropertyState
from nimbus.utils.imgui.widgets.system import UIManager, UISystem, SystemConfig
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from nimbus.utils.imgui.actions.actions import Action
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
        self._system_pins: list[DataPin] = []

    @types.string_property()
    def system_name(self) -> str:
        """Name of UISystem Config to use."""
        return self._system.name if self._system is not None else ""

    @system_name.setter
    def system_name(self, value: str):
        if self._system is not None:
            if self._system.name == value:
                return
            self._clear_system()
        manager = UIManager()
        config = manager.get_config(value)
        if config:
            self._set_system(config)

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
        if self._system is not None:
            self._clear_system()
        return super().delete()

    def get_custom_config_data(self):
        data = super().get_custom_config_data()
        data["system_name"] = self.system_name
        for pin in self._system_pins:
            if pin.pin_kind is PinKind.output:
                # No need to store output data
                continue
            data[f"Input_{pin.pin_name}"] = pin.get_value()
        return data

    def setup_from_config(self, data):
        super().setup_from_config(data)
        system_name = data.get("system_name", None)
        if system_name is None:
            # Stored data is incomplete, probably was saved before this implementation.
            return
        # NodeConfig logic would set the system-name value automatically, since `self.system_name` is a Data Property.
        # However, that would happend AFTER this method, and we need it at this point in order to instantiate the UISystem now,
        # so we can properly restore its input values.
        self.system_name = system_name

        # Load the subsystem's input data.
        prefix = "Input_"
        for name, value in data.items():
            if not name.startswith(prefix):
                continue
            pin: DataPin = self.get_input_pin(name[len(prefix):])
            pin.set_value(value)

    def _update_system_name_editor(self, editor: types.StringEditor):
        """Method automatically called by our ``system_name`` enum-property editor in order to dynamically
        update its settings before editing."""
        manager = UIManager()
        editor.options = manager.get_all_config_names()

    def _clear_system(self):
        """Clears and removes our instantiated UISystem and all other related objects (such as Pins, etc)."""
        if self._system is None:
            return
        # Remove dynamic pins from the system
        for pin in self._system_pins:
            pin.delete()
        self._system_pins.clear()
        # Clear the system itself
        self._system.clear()
        self._system = None

    def _set_system(self, config: SystemConfig):
        """Instantiates the UISystem from the given config and sets it up as our system, updating our pins, etc to match the system."""
        self._system = config.instantiate()
        # Create input-pin (for us) synced to the value output-pin of the sub-system's Input nodes.
        for innode in self._system.input_nodes:
            state = SyncedToState(innode)
            pin = DataPin(self, state)
            self.add_pin(pin)
            self._system_pins.append(pin)
        # Create output-pin (for us) synced to the value input-pin of the sub-system's Output nodes.
        for outnode in self._system.output_nodes:
            state = SyncedToState(outnode)
            pin = DataPin(self, state)
            self.add_pin(pin)
            self._system_pins.append(pin)


@not_user_creatable
class SystemAction(Action):
    """Base class for UISystem input/output actions."""

    def __init__(self):
        super().__init__(False)
        self.node_bg_color = Color(0.1, 0.25, 0.15, 0.75)
        self.node_header_color = WidgetColors.External

    @input_property()
    def name(self) -> str:
        """Name to identify this System Input/Output parameter when using this UISystem elsewhere."""
        return "param"

    @input_property()
    def description(self) -> str:
        """Description of this System Input/Output property. Used as a tooltip for the pin in a UseSystem
        node that is connected to this Input/Output node."""


for cls in types.TypeDatabase().get_creatable_types():
    # Create SystemInput<T> node
    @output_property(value_type=cls, allow_sync=True)
    def value(self):
        """Input value for this UISystem."""

    sysinput_action_cls = type(f"SystemInput-{cls.__name__.capitalize()}", (SystemAction,), {"value": value})
    sysinput_action_cls.__doc__ = f"Allows receiving a {cls.__name__} value from outside, as input to this system.\n\
        Other UISystems using this system with a UseSystem node can pass data to its input, which will be available to this system via this node."

    globals()[sysinput_action_cls.__name__] = sysinput_action_cls

    # Create SystemOutput<T> node
    @input_property(value_type=cls, allow_sync=True)
    def value(self):
        """Value to output from this UISystem."""

    sysoutput_action_cls = type(f"SystemOutput-{cls.__name__.capitalize()}", (SystemAction,), {"value": value})
    sysoutput_action_cls.__doc__ = f"Outputs a {cls.__name__} value to other UISystems using this system with a UseSystem node. "

    globals()[sysoutput_action_cls.__name__] = sysoutput_action_cls


class SyncedToState(DataPinState):
    """Specialized DataPin state for the dynamic input/output pins of a UseSystem node.

    This state connects to a SystemAction in the internal subsystem of a UseSystem node,
    thus syncing input-pins from the UseSystem node with system output-pins in the subsystem, and vice-versa.
    """

    def __init__(self, target_node: SystemAction):
        value_pin: DataPin = target_node.get_input_pin("value")
        if value_pin is None:
            value_pin: DataPin = target_node.get_output_pin("value")

        if value_pin.pin_kind is PinKind.output:
            kind = PinKind.input
            desc = "Input data for the internal UISystem being executed by this node."
        else:
            kind = PinKind.output
            desc = "Output data from the internal UISystem being executed by this node."
        if target_node.description:
            desc = f"{target_node.description}\n\n{desc}"

        self.target_state: SyncedDataPropertyState = value_pin.state
        self.target_state.synced_state = self
        super().__init__(target_node.name, kind, desc)

    def get(self):
        return self.target_state.parent_pin.get_value()

    def set(self, value):
        return self.target_state.set(value)

    def type(self):
        return self.target_state.type()

    def subtypes(self):
        return self.target_state.subtypes()
