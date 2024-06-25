import nimbus.utils.imgui.type_editor as types
from imgui_bundle import imgui
from nimbus.utils.utils import get_all_properties
from nimbus.utils.imgui.nodes import Node, NodePin, NodeLink, PinKind
from nimbus.utils.imgui.colors import Colors
from nimbus.utils.imgui.math import Vector2


# TODO: permitir tipo generic (qualquer coisa), consegue linkar com qualquer outro DataPin
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
        super().__init__(parent, kind, name)
        self.prettify_name = True
        self.value = initial_value
        """Value set in this pin. This is the user-configurable value (in the node editor), which is usually the default value of the pin.

        The proper actual value of the pin may change due to links with other data-pins, in which case this value isn't used. To get the actual
        value, see ``self.get_value()``.
        """
        self.value_type = value_type
        self._pin_tooltip: str = None
        self._editor: types.TypeEditor = None
        self._property: NodeDataProperty = None
        """The NodeDataProperty of our parent node that created this pin.

        Remember that a Property object belongs to the class, not to the individual instance.
        """
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

    @property
    def accepted_input_types(self) -> type | types.types.UnionType | tuple[type]:
        """The types this Input DataPin can accept as links, either as a single type object, a union of types, or
        as a tuple of types. If a link being connected to this input pin is of a type (the output type) that is a subclass
        of one of these accepted input types, then the connection will be accepted.

        By default, accepted input types always contain our ``self.value_type``. Depending on our TypeEditor's
        ``extra_accepted_input_types``, there will be extra types and this might return a type-union or a tuple of types.

        This only applies to input pins. Usually for pins of types that can receive values from other types and convert
        them to their type (such as strings and booleans, or ints/floats between themselves)."""
        if self._editor:
            extra_types = self._editor.extra_accepted_input_types
            if extra_types is not None:
                if isinstance(extra_types, tuple):
                    return tuple([self.value_type] + list(extra_types))
                else:
                    return self.value_type | extra_types
        return self.value_type

    def can_link_to(self, pin: NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, DataPin):
            return False, "Can only link to a Data pin."
        # Type Check: output-pin type must be same or subclass of input-pin type
        if self.pin_kind == PinKind.input:
            out_type = pin.value_type
            in_type = self.accepted_input_types
        else:
            out_type = self.value_type
            in_type = pin.accepted_input_types
        if not issubclass(out_type, in_type):
            return False, f"Can't pass '{out_type}' to '{in_type}'"
        # Logic in on_new_link_added ensures we only have 1 link, if we're a input pin.
        return True, "success"

    def get_value(self):
        """Gets the value of this DataPin. This can be:
        * For OUTPUT Pins that are associated with a NodeDataProperty with use_prop_value=True: returns the property's value.
        * For regular OUTPUT Pins: return our ``value``.
        * For INPUT Pins with a link to another data pin: return the value of the output pin we're linked to.
        * For INPUT Pins without a link: return our ``value``, which serves as a default value.
        """
        if self.pin_kind == PinKind.output:
            if self._property and self._property.use_prop_value:
                return self._property.get_prop_value(self.parent_node, type(self.parent_node))
            return self.value
        elif self.is_linked_to_any():
            link = self.get_all_links()[0]
            value = link.start_pin.get_value()
            if self._editor:
                value = self._editor._check_value_type(value)
            return value
        else:
            return self.value  # the input pin's default value

    def set_value(self, value):
        """Sets our value to the given object. This should be the same type as it's expected by this DataPin.
        However, that isn't enforced.

        If this pin is associated with a NodeDataProperty, will also set the value to the property.
        """
        self.value = value
        if self._property:
            self._property.set_prop_value(self.parent_node, value)

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
            self._editor.update_from_obj(self.parent_node, self.pin_name)
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
                    other_link.delete()

    def __str__(self):
        return f"{self.pin_kind.name.capitalize()} Data {self.pin_name}"

    def __getstate__(self):
        state = super().__getstate__()
        if self._property and self._property.use_prop_value:
            # No need to save our value if we directly use the value from the property.
            state["value"] = None
        state["_property"] = self._property is not None
        if isinstance(self._editor, types.NoopEditor):
            # TODO: how to properly persist noop editor objects? They fail to pickle because the decorator creates local classes.
            state["_editor"] = None
        # Property will be updated on self._update_state_after_recreation()
        # We can't update it normally on self.__setstate__(state) since on that point, we would have no parent node.
        return state

    def _update_state_after_recreation(self, parent: Node):
        super()._update_state_after_recreation(parent)
        if self._property is True:
            props: dict[str, NodeDataProperty] = get_all_properties(type(parent), NodeDataProperty)
            self._property = props[self.pin_name]
            self._property.data_pins[parent] = self
        if self._editor and self._property:
            self._property.editors[parent] = self._editor


class NodeDataProperty(types.ImguiProperty):
    """Advanced python Property that associates a DataPin with the property.

    This also expands on type_editor.ImguiProperty, which allows the property to have an associated TypeEditor for editing its value.
    The property's TypeEditor is used by the DataPin as its editor, to change its value.

    The associated DataPin is configured (name, pin-kind, type, editor (and color), tooltip, initial value, etc) according to metadata
    from the property.
    """

    @property
    def pin_kind(self) -> PinKind:
        """Gets the pin kind of this property."""
        return self.metadata.get("pin_kind", PinKind.input)

    @property
    def pin_class(self) -> type[DataPin]:
        """Gets the DataPin class to use as pin for this property."""
        return self.metadata.get("pin_class", DataPin)

    @property
    def use_prop_value(self) -> bool:
        """If this property, and our DataPin, should always get/set value from the property itself.

        Instead of getting/setting from the DataPin, which is the default behavior so that common data-properties don't need to
        implement proper getters/setters."""
        return self.metadata.get("use_prop_value", False)

    @property
    def data_pins(self) -> dict[Node, DataPin]:
        """Internal mapping of Nodes to the DataPins that this property has created.
        The nodes are the instances of the class that owns this property."""
        pins = getattr(self, "_data_pins", {})
        self._data_pins = pins
        return pins

    def __get__(self, obj: Node, owner: type | None = None):
        ret = self.get_prop_value(obj, owner)
        pin = self.get_pin(obj)
        if pin and not self.use_prop_value:
            return pin.get_value()
        return ret

    def __set__(self, obj: Node, value):
        pin = self.get_pin(obj)
        if pin:
            pin.set_value(value)
            # DataPin.set_value should call self.set_prop_value().
        else:
            self.set_prop_value(obj, value)

    def get_prop_value(self, obj: Node, owner: type | None = None):
        """Calls this property's getter on obj, to get its value.

        This is the property's common behavior (``return obj.property``).
        The NodeDataProperty adds logic to the getter, which is not called here.
        """
        return super().__get__(obj, owner)

    def set_prop_value(self, obj: Node, value):
        """Calls this property's setter on obj to set the given value.

        This is essentially calling ``obj.property = value``, with one important difference: this calls the BASE setter!
        This does NOT call our associated DataPin ``set_value()`` method.
        """
        if self.fset:
            return super().__set__(obj, value)

    def get_pin(self, obj: Node):
        """Gets the DataPin associated with this property for the given owner Node.

        If it doesn't exist, it'll be created. But the pin is not added to the node, the Node should do
        that (see ``create_data_pins_from_properties``).
        """
        pin: DataPin = self.data_pins.get(obj)
        if pin is None:
            value_type = self.get_value_type(obj)
            initial_value = super().__get__(obj, type(obj))
            pin = self.pin_class(obj, self.pin_kind, self.name, value_type, initial_value)
            pin.pin_tooltip = self.__doc__
            pin._property = self
            pin.setup_editor(editor=self.get_editor(obj))
            self.data_pins[obj] = pin
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
