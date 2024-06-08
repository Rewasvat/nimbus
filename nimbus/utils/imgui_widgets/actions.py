import click
import inspect
import traceback
from imgui_bundle import imgui, imgui_node_editor  # type: ignore
import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui import Node, NodePin, NodeLink, Colors, Vector2


class ActionFlow(NodePin):
    """A Flow pin for Action nodes.

    Flow pins control execution flow of actions.

    When a action executes, it triggers some of its output flow pins. These will then
    trigger the input-flow pins they're connected to, thus triggering those pin's actions.
    """

    def __init__(self, parent: Node, kind: imgui_node_editor.PinKind, name="FLOW"):
        super().__init__(parent, kind)
        self.parent_node: Action = parent  # to update type-hint.
        self.name = name

    def draw_node_pin_contents(self):
        if self.pin_kind == imgui_node_editor.PinKind.output:
            imgui.text_unformatted(self.name)
        draw = imgui.get_window_draw_list()
        size = imgui.get_text_line_height()
        p1 = imgui_utils.Vector2.from_cursor_screen_pos()
        draw.path_line_to(p1)
        draw.path_line_to(p1 + (size * 0.6, 0))
        draw.path_line_to(p1 + (size, size * 0.5))
        draw.path_line_to(p1 + (size * 0.6, size))
        draw.path_line_to(p1 + (0, size))
        draw.path_line_to(p1)
        color = imgui.get_color_u32(Colors.white)
        if self.is_linked_to_any():
            draw.path_fill_convex(color)
        else:
            thickness = 2
            draw.path_stroke(color, thickness=thickness)
        imgui.dummy((size, size))
        if self.pin_kind == imgui_node_editor.PinKind.input:
            imgui.text_unformatted(self.name)

    def can_link_to(self, pin: imgui_utils.NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, ActionFlow):
            return False, "Can only link to a Action's Flow pin."
        return True, "success"

    def trigger(self):
        """Triggers this Flow pin, which'll:
        * If this is a input flow pin, will ``execute()`` our parent Action. This happens inside a TRY/EXCEPT block, printing to
        terminal any Exceptions.
        * If this is a output flow pin, will call this same ``trigger()`` in all input flow-pins linked to us.

        So this executes one or more Actions, which in turn will execute other actions, thus starting a cascate of action processing.
        """
        if self.pin_kind == imgui_node_editor.PinKind.input:
            # If we are a input flow pin, we just execute our node.
            try:
                self.parent_node.execute()
            except Exception:
                # TODO: melhorar msg pra ser mais fácil identificar qual action node que falhou.
                click.secho(f"Error while executing action {self.parent_node}:\n{traceback.format_exc()}", fg="red")
        else:
            # If we are a output flow pin, we trigger all input pins we're connected to.
            # Since flow pins only connect to flow pins, they'll have this trigger() method.
            for in_pin in self._links.keys():
                in_pin.trigger()

    def render_edit_details(self):
        # TODO: THIS IS FOR TESTING! DELETE THIS AFTERWARDS
        if imgui_utils.menu_item("Trigger"):
            self.trigger()

    def __str__(self):
        return f"{self.pin_kind.name.capitalize()} ActionFlow {self.name}"


class DataPin(NodePin):
    """A DataPin for nodes.

    DataPins allows a node to send data (via output pins) to other nodes that need to receive that data as input (input pins).
    Input data-pins also allow the node to set a default value for that pin, according to its type.

    Using ``@input_property()`` or ``@output_property()`` in an Action class, it can define a property that is linked to a data-pin
    in that action. Thus the Action can easily define and use its input/output data.

    A Action, for example, using this can receive some data as input, process that data when the action is triggered, and then output
    the result of a calculation as data for other nodes to use.
    """

    def __init__(self, parent: Node, kind: imgui_node_editor.PinKind, name: str, value_type: type, initial_value=None):
        super().__init__(parent, kind)
        self.name = name
        self.value = initial_value
        self.value_type = value_type
        self.default_link_color = Colors.red  # TODO: parametrizar

    def draw_node_pin_contents(self):
        if self.pin_kind == imgui_node_editor.PinKind.output:
            imgui.text_unformatted(self.name)
        draw = imgui.get_window_draw_list()
        size = imgui.get_text_line_height()
        center = Vector2.from_cursor_screen_pos() + (size * 0.5, size * 0.5)
        radius = size * 0.3
        color = imgui.get_color_u32(self.default_link_color)
        if self.is_linked_to_any():
            draw.add_circle_filled(center, radius, color)
        else:
            thickness = 2
            draw.add_circle(center, radius, color, thickness=thickness)
        imgui.dummy((size, size))
        if self.pin_kind == imgui_node_editor.PinKind.input:
            imgui.text_unformatted(self.name)

    def can_link_to(self, pin: imgui_utils.NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, DataPin):
            return False, "Can only link to a Data pin."
        # Type Check: output-pin type must be same or subclass of input-pin type
        if self.pin_kind == imgui_node_editor.PinKind.input:
            out_type = pin.value_type
            in_type = self.value_type
        else:
            out_type = self.value_type
            in_type = pin.value_type
        if not issubclass(out_type, in_type):
            return False, f"Can't pass '{out_type}' to '{in_type}'"
        # Logic in on_new_link_added ensures we only have 1 link, if we're a input pin.
        return True, "success"

    def get_value(self):
        """Gets the value of this DataPin. This can be:
        * For OUTPUT Pins: return our ``value``.
        * For INPUT Pins with a link to another data pin: return the value of the output pin we're linked to.
        * For INPUT Pins without a link: return our ``value``, which serves as a default value.
        """
        if self.pin_kind == imgui_node_editor.PinKind.output:
            return self.value
        elif self.is_linked_to_any():
            link = self.get_all_links()[0]
            return link.start_pin.get_value()
        else:
            return self.value  # the input pin's default value

    def set_value(self, value):
        """Sets our value to the given object. This should be the same type as it's expected by this DataPin.
        However, that isn't enforced."""
        self.value = value

    def render_edit_details(self):
        # Let output pins have their value edited/set as well. That will enable setting a output pin's default value.
        # And also allow nodes without flow connections that only output static values!
        # TODO: editor for our value_type
        changed, t = imgui.input_text("##", self.value or "")
        if changed:
            self.set_value(t)

    def on_new_link_added(self, link: NodeLink):
        if self.pin_kind == imgui_node_editor.PinKind.input:
            # Remove all other links, only allow the new one. Input DataPins can only have 1 link.
            for pin, other_link in list(self._links.items()):
                if other_link != link:
                    self.remove_link_to(pin)

    def __str__(self):
        return f"{self.pin_kind.name.capitalize()} Data {self.name}"

    @classmethod
    def from_property(cls, prop: property, parent: Node, kind: imgui_node_editor.PinKind, name: str):
        """Creates a DataPin based on the given property.

        The pin's name, tooltip, type and value are linked to the property.

        Args:
            prop (property): The property to use.
            parent (Node): The node. The PROP property should be from this node.
            kind (imgui_node_editor.PinKind): The kind of this pin.
            name (str): name of the property.

        Returns:
            DataPin: the pin
        """
        sig = inspect.signature(prop.fget)
        value_type = sig.return_annotation
        initial_value = getattr(parent, name)
        pin = cls(parent, kind, name, value_type, initial_value)
        pin.pin_tooltip = prop.__doc__
        return pin


def node_data_property(kind: imgui_node_editor.PinKind):
    """Node Data Property attribute. Can be used to create node data properties the same way as a regular @property.

    A Node Data property behaves exactly the same way as a regular python @property, but also includes associated
    data that is used to create DataPin associated with this property in its parent Node class."""
    class NodeDataProperty(property):
        pin_kind = kind

        def __get__(self, obj: 'Action', owner: type | None = None):
            ret = super().__get__(obj, owner)
            name = self.fget.__name__
            pin = obj.get_input_data_pin(name) if self.pin_kind == imgui_node_editor.PinKind.input else obj.get_output_data_pin(name)
            if pin:
                return pin.get_value()
            return ret

        def __set__(self, obj: 'Action', value):
            name = self.fget.__name__
            pin = obj.get_input_data_pin(name) if self.pin_kind == imgui_node_editor.PinKind.input else obj.get_output_data_pin(name)
            if pin:
                pin.set_value(value)
            else:
                return super().__set__(obj, value)
    return NodeDataProperty


def input_property():
    """Node-Data Property attribute for a input data value.

    Only the property getter is required to define name, type and docstring.
    The setter is defined automatically by the NodeDataProperty."""
    return node_data_property(imgui_node_editor.PinKind.input)


def output_property():
    """Node-Data Property attribute for a output data value.

    Only the property getter is required to define name, type and docstring.
    The setter is defined automatically by the NodeDataProperty."""
    return node_data_property(imgui_node_editor.PinKind.output)


def create_data_pins_from_properties(node: Node):
    """Creates input and output DataPins for the given node based on its ``@node_data_property``s.

    Args:
        node (Node): The node to create data pins for.

    Returns:
        tuple[list[DataPin], list[DataPin]]: a (inputs, outputs) tuple, where each item is a list of
        DataPins for that kind of pin. Lists might be empty if the node has no properties of that kind.
    """
    props = imgui_utils.get_all_properties(type(node))
    inputs: list[DataPin] = []
    outputs: list[DataPin] = []
    for name, prop in props.items():
        kind: imgui_node_editor.PinKind = getattr(prop, "pin_kind", None)
        if kind is None:
            continue
        pin = DataPin.from_property(prop, node, kind, name)
        if kind == imgui_node_editor.PinKind.input:
            inputs.append(pin)
        else:
            outputs.append(pin)
    return inputs, outputs


@imgui_utils.not_user_creatable
class Action(Node):
    """TODO"""

    def __init__(self):
        super().__init__()
        self.editor: imgui_utils.NodeEditor = None
        self._inputs: list[NodePin] = [ActionFlow(self, imgui_node_editor.PinKind.input, "Execute")]
        """List of input pins of this action node."""
        self._outputs: list[NodePin] = [ActionFlow(self, imgui_node_editor.PinKind.output, "Trigger")]
        """List of output pins of this action node."""
        data_inputs, data_outputs = create_data_pins_from_properties(self)
        self._inputs += data_inputs
        self._outputs += data_outputs

    def execute(self):
        """Executes the logic of this action.

        Subclasses should overwrite this method to implement their logic. Default behavior in ``Action`` base class is to
        raise an error.

        To receive dynamic data from the node system as input, the Action should define ``@input_property()`` properties.
        The action can then use this properties to get its input value. Input data can come from the input data pin's default value,
        or from the output data pin it is connected to.

        To send dynamic data from the action's logic as output, the Action should define ``@output_property()`` properties.
        The action can then use the property's setter to set its output value.

        When implementing its logic in this method, the Action subclass should then:
        * Use its input property's getters to get its input data.
        * Process its data, do its work, etc.
        * Set its output data using its output property's setters.
        * Use ``trigger_flow(name)`` to trigger the next node, connected to our ActionFlow output pin with the given name.
        """
        raise NotImplementedError

    def trigger_flow(self, name: str = "Trigger"):
        """Triggers our ActionFlow output pin of the given name.

        The ``execute`` implementation of Action subclasses should call this to trigger the next actions in the hierarchy
        (after setting any output data!).

        Args:
            name (str, optional): Name of the output flow pin to trigger. Defaults to "Trigger", which is Action's
            default output pin.
        """
        for flow in [pin for pin in self._outputs if isinstance(pin, ActionFlow)]:
            if flow.name == name:
                flow.trigger()

    def get_input_data_pin(self, name: str):
        """Gets our INPUT DataPin with the given name.

        Args:
            name (str): name to check for.

        Returns:
            DataPin: The DataPin with the given name, or None if no pin exists.
        """
        for data in [pin for pin in self._inputs if isinstance(pin, DataPin)]:
            if data.name == name:
                return data

    def get_output_data_pin(self, name: str):
        """Gets our OUTPUT DataPin with the given name.

        Args:
            name (str): name to check for.

        Returns:
            DataPin: The DataPin with the given name, or None if no pin exists.
        """
        for data in [pin for pin in self._outputs if isinstance(pin, DataPin)]:
            if data.name == name:
                return data

    def delete(self):
        if self.editor:
            self.editor.nodes.remove(self)

    def get_input_pins(self) -> list[NodePin]:
        return self._inputs

    def get_output_pins(self) -> list[NodePin]:
        return self._outputs

    def render_edit_details(self):
        if len(self._inputs) > 1:
            imgui.text("Input Pins Default Values:")
        for pin in self._inputs:
            if not isinstance(pin, DataPin):
                continue
            imgui.text(pin.name)
            imgui.same_line()
            pin.render_edit_details()

    def __str__(self) -> str:
        return self.__class__.__name__


class Print(Action):
    """TODO"""

    @input_property()
    def text(self) -> str:
        """TEST DOC TEXT"""

    @output_property()
    def out(self) -> str:
        pass

    def execute(self):
        print(self.text)
        self.trigger_flow()
