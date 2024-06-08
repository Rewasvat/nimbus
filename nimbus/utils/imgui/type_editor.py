from enum import Enum
from typing import Callable
from imgui_bundle import imgui
from nimbus.utils.imgui.math import Vector2
from nimbus.utils.imgui.colors import Color
from nimbus.utils.imgui.general import enum_drop_down, drop_down
from nimbus.utils.utils import get_all_properties


# TODO: mover classes de ImguiTypeEditors e afins pra outro módulo. Possivelmente pra vários outros módulos.
# TODO: refatorar esse sistema pra não ser tão rigido. Usando reflection pra ler as type_hints da property
#   pra pegar os editors certos automaticamente. Isso facilitaria muito o uso.
#   - Ter uma classe com propriedades bem tipadas seria suficiente pra gerar os editors dela. Não precisaria hardcodar imgui_properties e tal
#     mas ainda poderia ter uma "property" diferente que guarda um **kwargs de metadata de tal property, que seria usado como a config do
#     modelo de tal atributo
# TODO: refatorar pra permitir cascata facilmente (lista com listas com listas... ou dicts com dicts e por ai vai)
#   assim a funcionalidade ficaria mais próxima do TPLove TableEditor, permitindo estruturas de dados quaisquer.
# TODO: refatorar pra ser fácil poder ter valor None sem quebrar as coisas.
#   - talvez uma flag "can be None?" ou algo assim nos editors?
#   - editores saberem o type do que eles editam, ai podiam fazer type() pra criar o valor default (isso ficaria mais facil com a refatoração com
#     reflection definicao automatica dos editores)
class ImguiTypeEditor:
    """Basic class for a KEY: VALUE editor in imgui.

    Subclasses of this implement how to edit a single (fixed for that class) VALUE type.

    The ``@imgui_property()`` decorator can then be used instead of ``@property`` to mark a class' property
    as being "renderable" using the given ImguiTypeEditor. The ``render_all_properties()`` function can then
    be used to render all available properties in a object with their specified ImguiTypeEditors.

    Subclasses should override ``__call__``.
    """

    def __init__(self):
        self._prop: property = None
        self.add_tooltip_after_value = True
        """If true, ``self.draw_end()`` will add ``self.attr_doc`` as a tooltip for the last imgui control drawn."""
        self.value_getter: Callable[[any, any], any] = getattr
        """The "value getter" function this editor uses to get the value for editing from the object.
        This is a ``(object, value_id) -> value`` function. It receives the object itself and a "value_id", which is any kind of
        data used to identify the value in object, and then returns the value. The default getter function is ``getattr``, where
        "value_id" is a ``name`` string used to access the attribute by its name.
        """
        self.value_setter: Callable[[any, any, any], None] = setattr
        """The "value setter" function this editor uses to set the value in the object after editing. This is only called if the value was changed.
        This is a ``(object, value_id, new_value) -> None`` function. It receives the object itself, a "value_id" and the new value to set.
        The value_id is anything used to identify the value in object for setting. For attributes/properites, value_id is a string which
        is the name of the value/property. The default value_setter is ``setattr``.
        """

    def __call__(self, obj, name: str):
        """Renders the KEY:VALUE editor. Usually this is a text with the given name, and imgui controls for
        changing the value.

        The default implementation in ImguiTypeEditor does the basic rendering for key:value editor by calling in order:
        * ``self.draw_start()``: starts the drawing process and renders the "key" part.
        * ``self.draw_value_editor(..., value=self.value_getter(obj,name))``: draws the type-specific value editing control.
        * ``self.draw_end()``: ends the key:value editor render.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.

        Returns:
            tuple[bool, any]: returns a ``(changed, new_value)`` tuple.
            Note that ``self.draw_end()`` will already have set the new value in the parent object.
        """
        self.draw_start(obj, name)
        value = self.value_getter(obj, name)
        changed, new_value = self.draw_value_editor(obj, name, value)
        self.draw_end(obj, name, changed, new_value)
        return changed, new_value

    def draw_value_editor(self, obj, name: str, value):
        """Renders the controls for editing just the VALUE part of a key:value editor.

        This is type-specific, and thus should be overriden by subclasses to implement their logic.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
            value (any): the current value of ``obj.name``.

        Returns:
            tuple[bool, any]: returns a ``(changed, new_value)`` tuple.
        """
        raise NotImplementedError

    def set_prop(self, prop: property):
        """Sets the property object we're attached to."""
        self._prop = prop
        return self

    @property
    def attr_doc(self):
        """Gets the docstring of the property we're attached to."""
        if self._prop is not None:
            return self._prop.__doc__
        return "undefined"

    def draw_start(self, obj, name: str):
        """Utility method to draw the "start" of a key:value editor.

        This pushes an unique ID (based on ``obj`` and ``name``), draws ``{name}:``,
        with a tooltip equal to our ``self.attr_doc`` and calls ``imgui.same_line()``.
        Also calls ``self.update_from_obj(obj, name)`` to optionally update ourselves.

        This setups the "key" part of a key:value editor, allowing subclasses to more easily
        implement their custom value rendering logic by calling this, then drawing the value editing part,
        and finally calling ``self.draw_end()``.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
        """
        imgui.push_id(f"{obj}EditAttr{name}")
        self.update_from_obj(obj, name)
        imgui.text(f"{name}:")
        imgui.set_item_tooltip(self.attr_doc)
        imgui.same_line()

    def draw_end(self, obj, name: str, changed: bool, new_value):
        """Utility method to draw the "ending" of a key:value editor.

        This should come after a ``self.draw_start()`` call was made and custom rendering logic
        for editing the value was done.

        This sets the attribute value in the object, and then pops the ID that was pushed
        in ``self.draw_start()``.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
            changed (bool): if the value was changed
            new_value (any): the new value for the attribute
        """
        if self.add_tooltip_after_value:
            imgui.set_item_tooltip(self.attr_doc)
        if changed:
            self.value_setter(obj, name, new_value)
        imgui.pop_id()

    def update_from_obj(self, obj, name: str):
        """Calls a optional ``<OBJ>._update_<NAME>_editor(self)`` method from the given object,
        with the purpose of dynamically updating this editor's attributes before drawing the editor itself.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
        """
        updater_method_name = f"_update_{name}_editor"
        method = getattr(obj, updater_method_name, None)
        if method is not None:
            method(self)


def imgui_property(type_editor: ImguiTypeEditor):
    """Imgui Property attribute. Can be used to create imgui properties the same way as a regular @property.

    A imgui-property behaves exactly the same way as a regular python @property, but also includes an associated
    ImguiTypeEditor object that can be used to change the value of this property in imgui.

    There are also related ``<type>_property`` decorators defined here, as an utility to call this passing the
    ImguiTypeEditor for a specific type.
    """
    class ImguiProperty(property):
        editor = type_editor
    return ImguiProperty


class StringEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a STRING value."""

    def __init__(self, flags: imgui.InputTextFlags_ = imgui.InputTextFlags_.none):
        super().__init__()
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: str):
        if value is None:
            value = ""
        return imgui.input_text("##", value, flags=self.flags)


def string_property(flags: imgui.InputTextFlags_ = imgui.InputTextFlags_.none):
    """Imgui Property attribute for a STRING type.

    Behaves the same way as a property, but includes a StringEditor object for allowing changing this string's value in imgui.

    Args:
        flags (imgui.InputTextFlags_, optional): flags to pass along to ``imgui.input_text``. Defaults to None.
    """
    editor = StringEditor(flags=flags)
    return imgui_property(editor)


class EnumEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a ENUM value."""

    def __init__(self, options: list[str] | Enum, docs: list | dict = None, is_enum_type=False, flags: imgui.SelectableFlags_ = 0):
        """
        Args:
            options (list[str] | Enum): The list of possible options. This can be:
            * A Enum type. Each item (shown by its ``name``) will be a possible option.
            * A Enum Flags type. Works similarly to the above, but allows selecting multiple enum options at once.
            * A ``list[str]`` (or any other iterable[str]): each string in the list will be an option.
            * None: can be used as an shortcut for a ``Enum`` type. The Enum type is taken from the property's current value the first
            time it is edited.
            docs (list | dict, optional): Optional definition of documentation for each option, shown as a tooltip (for that option) in the editor
            * Should be a ``list[str]`` matching the length of ``options``, or a ``{option: doc}`` dict.
            * If ``options`` is a Enum type, and this is None, then this will be set as the ``value`` of each enum-item.
            * The property's docstring is used as a default tooltip for all options.
            is_enum_type (bool, optional): If this property is a Enum type. So the current value being edited is a Enum object. Default value is
            if ``options`` is a Enum type.
            flags (imgui.SelectableFlags_, optional): Flags passed down to the drop-down selectable.
        """
        super().__init__()
        self.add_tooltip_after_value = False
        self.options = options
        self.docs = docs
        self.is_enum_type = is_enum_type or (isinstance(options, type) and issubclass(options, Enum))
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value):
        if self.options is None and isinstance(value, Enum):
            self.options = type(value)
            self.is_enum_type = True
        if self.is_enum_type:
            return enum_drop_down(value, self.attr_doc, self.flags)
        else:
            return drop_down(value, self.options, self.docs, default_doc=self.attr_doc, flags=self.flags)


def enum_property(options: list[str] | Enum, docs: list | dict = None, is_enum_type=False, flags: imgui.SelectableFlags_ = 0):
    """Imgui Property attribute for a ENUM type.

    Behaves the same way as a property, but includes a EnumEditor object for allowing changing this enum's value in imgui.

    Args:
        flags (imgui.SelectableFlags_, optional): flags to pass along to ``imgui.selectable``. Defaults to None.
    """
    editor = EnumEditor(options, docs=docs, is_enum_type=is_enum_type, flags=flags)
    return imgui_property(editor)


class BoolEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a BOOLEAN value."""

    def draw_value_editor(self, obj, name: str, value: bool):
        return imgui.checkbox("##", value)


def bool_property():
    """Imgui Property attribute for a BOOL type.

    Behaves the same way as a property, but includes a BoolEditor object for allowing changing this bool's value in imgui.
    """
    editor = BoolEditor()
    return imgui_property(editor)


class FloatEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a BOOLEAN value."""

    def __init__(self, min=0.0, max=0.0, format="%.2f", speed=1.0, is_slider=False, flags: imgui.SliderFlags_ = 0):
        """
        Args:
            min (float, optional): Minimum allowed value for this float property. Defaults to 0.0.
            max (float, optional): Maximum allowed value for this float property. Defaults to 0.0. If MIN >= MAX then we have no bounds.
            format (str, optional): Text format of the value to decorate the control with. Defaults to "%.2f". Apparently this needs to be a valid
            python format, otherwise the float control wont work properly.
            speed (float, optional): Speed to apply when changing values. Only applies when dragging the value and IS_SLIDER=False. Defaults to 1.0.
            is_slider (bool, optional): If we'll use a SLIDER control for editing. It contains a marker indicating the value along the range between
            MIN<MAX (if those are valid). Otherwise defaults to using a ``drag_float`` control. Defaults to False.
            flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
        """
        super().__init__()
        self.is_slider: bool = is_slider
        self.speed: float = speed
        self.min: float = min
        self.max: float = max
        self.format: str = format
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: float):
        if value is None:
            value = 0.0
        if self.is_slider:
            return imgui.slider_float("##value", value, self.min, self.max, self.format, self.flags)
        else:
            return imgui.drag_float("##value", value, self.speed, self.min, self.max, self.format, self.flags)


def float_property(min=0.0, max=0.0, format="%.2f", speed=1.0, is_slider=False, flags: imgui.SliderFlags_ = imgui.SliderFlags_.none):
    """Imgui Property attribute for a FLOAT type.

    Behaves the same way as a property, but includes a FloatEditor object for allowing changing this float's value in imgui.

    Args:
        min (float, optional): Minimum allowed value for this float property. Defaults to 0.0.
        max (float, optional): Maximum allowed value for this float property. Defaults to 0.0. If MIN >= MAX then we have no bounds.
        format (str, optional): Text format of the value to decorate the control with. Defaults to "%.3". Apparently this needs to be a valid
        python format, otherwise the float control wont work properly.
        speed (float, optional): Speed to apply when changing values. Only applies when dragging the value and IS_SLIDER=False. Defaults to 1.0.
        is_slider (bool, optional): If we'll use a SLIDER control for editing. It contains a marker indicating the value along the range between
        MIN<MAX (if those are valid). Otherwise defaults to using a ``drag_float`` control. Defaults to False.
        flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
    """
    editor = FloatEditor(min=min, max=max, format=format, speed=speed, is_slider=is_slider, flags=flags)
    return imgui_property(editor)


class ColorEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a COLOR value."""

    def __init__(self, flags: imgui.ColorEditFlags_ = imgui.ColorEditFlags_.none):
        super().__init__()
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: Color):
        changed, new_value = imgui.color_edit4("##", value, self.flags)
        return changed, Color(*new_value)


def color_property(flags: imgui.ColorEditFlags_ = imgui.ColorEditFlags_.none):
    """Imgui Property attribute for a COLOR type.

    Behaves the same way as a property, but includes a ColorEditor object for allowing changing this color's value in imgui.
    """
    editor = ColorEditor(flags=flags)
    return imgui_property(editor)


class ListEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a LIST value."""

    def __init__(self, item_editor: ImguiTypeEditor, default_item=None):
        super().__init__()
        self.default_item = default_item
        self.item_editor = item_editor
        item_editor.value_getter = lambda obj, i: obj[i]

        def item_setter(obj, i, item):
            obj[i] = item
        item_editor.value_setter = item_setter

    def __call__(self, obj, name: str):
        changed = False
        value = self.value_getter(obj, name)
        if self.draw_start(obj, name):
            changed, value = self.draw_value_editor(obj, name, value)
            self.draw_end(obj, name, changed, value)
        return changed, value

    def draw_start(self, obj, name: str):
        self.update_from_obj(obj, name)
        opened = imgui.tree_node(f"{obj}EditAttr{name}", f"{name} ({len(self.value_getter(obj, name))} items)")
        imgui.set_item_tooltip(self.attr_doc)
        return opened

    def draw_value_editor(self, obj, name: str, value: list):
        changed = False
        size = len(value)
        for i in range(size):
            if i >= len(value):
                break  # required since the X button might remove a item, changing the size of value.
            item = value[i]
            # "start" part
            imgui.push_id(f"{obj}EditAttr{name}ListItem{i}")
            imgui.text(f"#{i}:")
            imgui.same_line()
            # item value editing
            item_changed, new_item = self.item_editor.draw_value_editor(obj, name, item)
            # item handling (move/delete)
            imgui.same_line()
            if imgui.button("^") and i >= 1:
                value[i-1], value[i] = value[i], value[i-1]
                item_changed = False
                changed = True
            imgui.same_line()
            if imgui.button("v") and i < size-1:
                value[i], value[i+1] = value[i+1], value[i]
                item_changed = False
                changed = True
            imgui.same_line()
            if imgui.button("X"):
                value.pop(i)
                item_changed = True
            # "end" part
            elif item_changed:
                value[i] = new_item
            changed = changed or item_changed
            imgui.pop_id()
        if imgui.button("Add Item"):
            value.append(self.default_item)
            changed = True
        return changed, value

    def draw_end(self, obj, name: str, changed: bool, new_value: list):
        if changed:
            self.value_setter(obj, name, new_value)
        imgui.tree_pop()


def list_property(item_editor: ImguiTypeEditor, default_item=None):
    """Imgui Property attribute for a LIST type.

    Behaves the same way as a property, but includes a ListEditor object for allowing changing this list's value in imgui.
    """
    editor = ListEditor(item_editor, default_item)
    return imgui_property(editor)


class Vector2Editor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a Vector2 value."""

    def __init__(self, x_range=(0, 0), y_range=(0, 0), format="%.2f", speed=1.0, flags: imgui.SliderFlags_ = 0):
        super().__init__()
        self.speed: float = speed
        self.format: str = format
        self.flags = flags
        self.x_range: Vector2 = x_range
        self.y_range: Vector2 = y_range
        self.add_tooltip_after_value = False

    def draw_value_editor(self, obj, name: str, value):
        if value is None:
            value = Vector2()
        imgui.push_id("XComp")
        x_changed, value.x = self._component_edit(value.x, self.x_range)
        imgui.set_item_tooltip(f"X component of the Vector2.\n\n{self.attr_doc}")
        imgui.pop_id()
        imgui.same_line()
        imgui.push_id("YComp")
        y_changed, value.y = self._component_edit(value.y, self.y_range)
        imgui.set_item_tooltip(f"Y component of the Vector2.\n\n{self.attr_doc}")
        imgui.pop_id()
        return x_changed or y_changed, value

    def _component_edit(self, value: float, range: tuple[float, float]):
        min, max = range
        if max > min:
            return imgui.slider_float("##value", value, min, max, self.format, self.flags)
        else:
            return imgui.drag_float("##value", value, self.speed, min, max, self.format, self.flags)


def vector2_property(x_range=(0, 0), y_range=(0, 0), format="%.2f", speed=1.0, flags: imgui.SliderFlags_ = 0):
    """Imgui Property attribute for a Vector2 type.

    Behaves the same way as a property, but includes a Vector2Editor object for allowing changing this Vector2's value in imgui.

    Args:
        x_range (tuple[float, float], optional): (min, max) range of possible values for the X component of the vector.
        y_range (tuple[float, float], optional): (min, max) range of possible values for the Y component of the vector.
        format (str, optional): Text format of the value to decorate the control with. Defaults to "%.3". Apparently this needs to be a valid
        python format, otherwise the float control wont work properly.
        speed (float, optional): Speed to apply when changing values. Only applies when dragging the value. Defaults to 1.0.
        flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
    """
    editor = Vector2Editor(x_range=x_range, y_range=y_range, format=format, speed=speed, flags=flags)
    return imgui_property(editor)


def get_all_renderable_properties(cls: type) -> dict[str, ImguiTypeEditor]:
    """Gets all "Imgui Properties" of a class. This includes properties of parent classes.

    Imgui Properties are properties with an associated ImguiTypeEditor object created with the
    ``@imgui_property(editor)`` and related decorators.

    Args:
        cls (type): the class to get all imgui properties from.

    Returns:
        dict[str, ImguiTypeEditor]: a "property name" => "ImguiTypeEditor object" dict with all imgui properties.
        All editors returned by this will have had their "parent properties" set accordingly.
    """
    props = get_all_properties(cls)
    return {k: v.editor.set_prop(v) for k, v in props.items() if hasattr(v, "editor")}


def render_all_properties(obj, ignored_props: set[str] = None):
    """Renders the KEY:VALUE editors for all imgui properties of the given object.

    This allows seeing and editing the values of all imgui properties in the object.
    See ``get_all_renderable_properties()``.

    Args:
        obj (any): the object to render all imgui properties.
        ignored_props (set[str], optional): a set (or any other object that supports ``X in IGNORED`` (contains protocol)) that indicates
        property names that we should ignore when rendering their editors. This way, if the name of a imgui-property P is in ``ignored_props``,
        its editor will not be rendered. Defaults to None (shows all properties).
    """
    props = get_all_renderable_properties(type(obj))
    for name, editor in props.items():
        if (ignored_props is None) or (name not in ignored_props):
            editor(obj, name)
