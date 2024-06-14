#########################################################
# Common utilities and classes for using the Nodes system
#########################################################
import nimbus.utils.imgui.type_editor as types
from imgui_bundle import imgui
from nimbus.utils.utils import get_all_properties
from nimbus.utils.imgui.nodes import Node, NodePin, NodeLink, PinKind
from nimbus.utils.imgui.colors import Colors
from nimbus.utils.imgui.math import Vector2
from nimbus.utils.imgui.general import menu_item, not_user_creatable


# TODO: permitir tipo generic (qualquer coisa), consegue linkar com qualquer outro DataPin
# TODO: pins de input string devem aceitar qualquer coisa (da pra fazer str(value) pra qualquer value)
# TODO: pins de input bool devem aceitar qualquer coisa (qualquer objeto tem valor booleano).
class DataPin(NodePin):
    """A DataPin for nodes.

    DataPins allows a node to send data (via output pins) to other nodes that need to receive that data as input (input pins).
    Input data-pins also allow the node to set a default value for that pin, according to its type.

    Using ``@input_property()`` or ``@output_property()`` in an Action class, it can define a property that is linked to a data-pin
    in that action. Thus the Action can easily define and use its input/output data.

    A Action, for example, using this can receive some data as input, process that data when the action is triggered, and then output
    the result of a calculation as data for other nodes to use.
    """

    def __init__(self, parent: Node, kind: PinKind, name: str, value_type: type, initial_value=None):
        super().__init__(parent, kind)
        self.name = name
        self.value = initial_value
        self.value_type = value_type
        self._pin_tooltip: str = None
        self._editor: types.TypeEditor = None
        self.setup_editor()

    @property
    def pin_tooltip(self) -> str:
        """Pin Tooltip, displayed when the pin is hovered in the Node Editor.

        This sets a fixed tooltip text, but gets a formatted string, containing the fixed text and the pin's value for display.
        """
        return f"{self._pin_tooltip}\n\nLocal Value: {self.value}\nActual Value: {self.get_value()}"

    @pin_tooltip.setter
    def pin_tooltip(self, value: str):
        self._pin_tooltip = value

    def draw_node_pin_contents(self):
        if self.pin_kind == PinKind.output:
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
        if self.pin_kind == PinKind.input:
            imgui.text_unformatted(self.name)

    def can_link_to(self, pin: NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, DataPin):
            return False, "Can only link to a Data pin."
        # Type Check: output-pin type must be same or subclass of input-pin type
        if self.pin_kind == PinKind.input:
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
        if self.pin_kind == PinKind.output:
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

    def setup_editor(self, editor: types.TypeEditor = None, data: dict = None):
        """Sets up our TypeEditor instance, used for editing this pin's value in IMGUI.

        Regardless of how the editor is setup, our parent Node can have the ``_update_<property name>_editor(editor)`` methods
        to dynamically update the editor's config.

        When set up with a valid TypeEditor, this pin's default link color will be set to the editor's type color.

        Args:
            editor (TypeEditor, optional): a TypeEditor instance. Should match our value type. Defaults to None.
            This is used by ``NodeDataProperty`` when creating its DataPin to associate the property's editor
            with the pin. This way, property and pin will share the same editor, properly configured with the property's
            metadata.
            data (dict, optional): Metadata dict used as argument to create a new TypeEditor instance. Used only when given
            ``editor`` is None. TypeEditor class will be the registered class in the TypeDatabase for our value_type. Defaults to None,
            which means we won't try to create a TypeEditor instance.
        """
        if editor is not None:
            self._editor = editor
        elif data is not None:
            editor_cls = types.TypeDatabase().get_editor_type(self.value_type)
            if editor_cls:
                data["value_type"] = self.value_type
                self._editor = editor_cls(data)
        if self._editor:
            self.default_link_color = self._editor.color

    def render_edit_details(self):
        # Let output pins have their value edited/set as well. That will enable setting a output pin's default value.
        # And also allow nodes without flow connections that only output static values!
        if self._editor:
            self._editor.update_from_obj(self.parent_node, self.name)
            changed, new_value = self._editor.render_value_editor(self.value)
            if changed:
                self.set_value(new_value)
        else:
            imgui.text_colored(Colors.red, "No Editor for updating the value of this pin")

    def on_new_link_added(self, link: NodeLink):
        if self.pin_kind == PinKind.input:
            # Remove all other links, only allow the new one. Input DataPins can only have 1 link.
            for pin, other_link in list(self._links.items()):
                if other_link != link:
                    self.remove_link_to(pin)

    def __str__(self):
        return f"{self.pin_kind.name.capitalize()} Data {self.name}"


class NodeDataProperty(types.ImguiProperty):
    """Advanced python Property that associates a DataPin with the property.

    This also expands on type_editor.ImguiProperty, which allows the property to have an associated TypeEditor for editing its value.
    The property's TypeEditor is used by the DataPin as its editor, to change its value.

    The associated DataPin is configured (name, pin-kind, type, editor (and color), tooltip, initial value, etc) according to metadata
    from the property.
    """

    @property
    def name(self) -> str:
        """Gets the name of this property, as defined in its owner class."""
        return self.fget.__name__

    @property
    def pin_kind(self) -> PinKind:
        """Gets the pin kind of this property."""
        return self.metadata.get("pin_kind", PinKind.input)

    @property
    def pin_class(self) -> type[DataPin]:
        """Gets the DataPin class to use as pin for this property."""
        return self.metadata.get("pin_class", DataPin)

    def __get__(self, obj: Node, owner: type | None = None):
        ret = super().__get__(obj, owner)
        pin = self.get_pin(obj)
        if pin:
            return pin.get_value()
        return ret

    def __set__(self, obj: Node, value):
        pin = self.get_pin(obj)
        if pin:
            pin.set_value(value)
        if self.fset:
            return super().__set__(obj, value)

    def get_pin(self, obj: Node):
        """Gets the DataPin associated with this property for the given owner Node.

        If it doesn't exist, it'll be created. But the pin is not added to the node, the Node should do
        that (see ``create_data_pins_from_properties``).
        """
        pins = getattr(self, "_data_pins", {})
        self._data_pins = pins

        pin: DataPin = pins.get(obj)
        if pin is None:
            value_type = self.get_value_type(obj)
            initial_value = super().__get__(obj, type(obj))
            pin = self.pin_class(obj, self.pin_kind, self.name, value_type, initial_value)
            pin.pin_tooltip = self.__doc__
            pin.setup_editor(editor=self.get_editor(obj))
            pins[obj] = pin
        return pin


def input_property(**kwargs):
    """Decorator to create a input NodeDataProperty.

    Node Data Properties expand upon ImguiProperties by also associating a DataPin with the property.
    So the property will be editable in regular IMGUI and visible/editable in IMGUI's Node System.

    The ``kwargs`` will be used mostly to define the metadata for the TypeEditor of this property (from ImguiProperty).

    Only the property getter is required to define name, type and docstring.
    The setter is defined automatically by the NodeDataProperty."""
    kwargs.update(pin_kind=PinKind.input)
    return types.adv_property(kwargs, NodeDataProperty)


def output_property(**kwargs):
    """Decorator to create a output NodeDataProperty.

    Node Data Properties expand upon ImguiProperties by also associating a DataPin with the property.
    So the property will be editable in regular IMGUI and visible/editable in IMGUI's Node System.

    The ``kwargs`` will be used mostly to define the metadata for the TypeEditor of this property (from ImguiProperty).

    Only the property getter is required to define name, type and docstring.
    The setter is defined automatically by the NodeDataProperty."""
    kwargs.update(pin_kind=PinKind.output)
    return types.adv_property(kwargs, NodeDataProperty)


def create_data_pins_from_properties(node: Node):
    """Creates input and output DataPins for the given node based on its ``@input/output_property``s.

    Args:
        node (Node): The node to create data pins for.

    Returns:
        tuple[list[DataPin], list[DataPin]]: a (inputs, outputs) tuple, where each item is a list of
        DataPins for that kind of pin. Lists might be empty if the node has no properties of that kind.
    """
    props: dict[str, NodeDataProperty] = get_all_properties(type(node), NodeDataProperty)
    inputs: list[DataPin] = []
    outputs: list[DataPin] = []
    for prop in props.values():
        pin = prop.get_pin(node)
        if pin.pin_kind == PinKind.input:
            inputs.append(pin)
        else:
            outputs.append(pin)
    return inputs, outputs


# TODO: pq tudo isso não fazer parte do Node normal?
@not_user_creatable
class CommonNode(Node):
    """Common Node. This is a simple base Node class that expands on Node with a few simple utilities:
    * Has internal lists for input and output pins.
    * Base ``get_input_pins()``/``get_output_pins()`` implementation of simply returning the list of input or output pins.
    * Base ``delete()`` implementation of simply removing ourselves from our parent NodeEditor's list of nodes.
    * Base ``render_edit_details()`` implementation of rendering for editing all our input DataPins.
    * Method to directly create and add DataPins based on class properties.
    * Default node title as class name.
    """

    def __init__(self):
        super().__init__()
        self._inputs: list[NodePin] = []
        """List of input pins of this node."""
        self._outputs: list[NodePin] = []
        """List of output pins of this node."""
        self.node_title = self.__class__.__name__

    def create_data_pins_from_properties(self):
        """Creates input and output DataPins based on our ``@input/output_property``s.
        The pins are appended directly to our lists of input and output pins."""
        data_inputs, data_outputs = create_data_pins_from_properties(self)
        self._inputs += data_inputs
        self._outputs += data_outputs

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
            self.editor.remove_node(self)
            self.editor = None

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
            imgui.set_item_tooltip(pin.pin_tooltip)
            imgui.same_line()
            pin.render_edit_details()
