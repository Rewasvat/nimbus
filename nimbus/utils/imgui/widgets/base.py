import click
from typing import Iterator
from imgui_bundle import imgui, ImVec2, imgui_node_editor  # type: ignore
import nimbus.utils.imgui.actions as actions
from nimbus.utils.imgui.math import Vector2, Rectangle
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.general import not_user_creatable, menu_item, object_creation_menu
from nimbus.utils.imgui.nodes import Node, NodePin, NodeLink, NodeEditor
import nimbus.utils.imgui.type_editor as types


def insert_base_init(sub_cls: type, base_cls: type):
    """Updates the SUB_CLS __init__ method to automatically call, without arguments, the BASE_CLS __init__ method.
    To be used in a ``__init__subclass__(cls)`` method.

    Args:
        sub_cls (type): The SubClass being updated. She may already have or not a __init__ method.
        base_cls (type): The BaseClass to use. This *MUST* be a base-class of the given SUB_CLS, and she must have a
        __init__ method of its own.
    """
    cls_init = getattr(sub_cls, "__init__", None)

    def new_init(self, *args, **kwargs):
        base_cls.__init__(self)
        if cls_init is not None:
            cls_init(self, *args, **kwargs)
    sub_cls.__init__ = new_init


def draw_widget_pin_icon(is_filled):
    """Draws the icon for a widget pin in the Node Editor. Either output (slot) or input (widget parent).

    Args:
        is_filled (bool): if the icon should be filled. This should be true if the widget pin is connected.
    """
    draw = imgui.get_window_draw_list()
    size = imgui.get_text_line_height()  # 24  # from node examples
    p1 = Vector2.from_cursor_screen_pos()
    p2 = p1 + (size, size * 0.5)
    p3 = p1 + (0, size)
    color = Colors.green.u32
    if is_filled:
        draw.add_triangle_filled(p1, p2, p3, color)
    else:
        thickness = 2
        draw.add_triangle(p1, p2, p3, color, thickness)
    imgui.dummy((size, size))


class WidgetParentPin(NodePin):
    """Node Pin for a widget's parent container."""

    def __init__(self, parent: 'BaseWidget'):
        super().__init__(parent, imgui_node_editor.PinKind.input)

    def draw_node_pin_contents(self):
        draw_widget_pin_icon(self.is_linked_to_any())
        imgui.text("Parent")

    def __str__(self):
        return f"{self.parent_node} Parent Slot"


@not_user_creatable
class BaseWidget(Node):
    """Abstract Base Widget Class.

    Shouldn't be used on its own.

    NOTE: this class automatically sets up ``__init__()`` in sub-classes to call the initializer of this class before.
    """
    _widget_instance_count = 0
    """Internal instance counter used for unique IDs."""

    def __init__(self):
        super().__init__()
        BaseWidget._widget_instance_count += 1
        self._internal_id = f"{type(self).__name__}-{BaseWidget._widget_instance_count}"
        self._name: str = str(hash(self))
        self.slot: Slot = None
        """Parent slot containing this widget. Might be None."""
        self._system: WidgetSystem = None
        """Root System managing this widget."""
        self._area: Vector2 = Vector2()  # TODO: talvez tirar isso pq puxa do slot
        self._pos: Vector2 = Vector2()
        self.editable = True
        """If this widget is editable by the user during runtime. Depends on our WidgetSystem having edit enabled."""
        self.interactive = True
        """If this widget's common user interaction (via ``self._handle_interaction()``) is enabled."""
        self.edit_ignored_properties: set[str] = set()
        """Set of imgui-property names that shall be ignored when rendering this widget's imgui-properties through the
        default ``self.render_edit_details()`` implementation."""
        self.enabled = True
        """If this widget is enabled. Disabled widgets are not rendered by their parents."""
        self.parent_pin = WidgetParentPin(self)

    @property
    def id(self):
        """Fixed ID of this widget. IDs are uniquely generated at creation, according to widget type and overall instance count."""
        return self._internal_id

    @types.string_property(imgui.InputTextFlags_.enter_returns_true)
    def name(self) -> str:
        """Name of this widget. User can change this, but it should be unique amongst all existing widgets.
        By default it's ``str(hash(self))``. [GET/SET]"""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def system(self) -> 'WidgetSystem':
        """Root System managing this widget."""
        return self._system

    @system.setter
    def system(self, value: 'WidgetSystem'):
        self._system = value
        self._on_system_changed()

    @property
    def position(self):
        """The position (top-left corner) of this widget, in absolute coords. [GET]"""
        return self._pos.copy()

    @property
    def area(self):
        """The size of this widget. It's the available area size of our parent slot. [GET]"""
        return self._area.copy()

    @property
    def top_right_pos(self):
        """The position of this widget's top-right corner. [GET]"""
        return self._pos + (self._area.x, 0)

    @property
    def bottom_left_pos(self):
        """The position of this widget's bottom-left corner. [GET]"""
        return self._pos + (0, self._area.y)

    @property
    def bottom_right_pos(self):
        """The position of this widget's bottom-right corner. [GET]"""
        return self._pos + self._area

    def __init_subclass__(cls) -> None:
        insert_base_init(cls, BaseWidget)

    def render(self):
        """Renders this widget through imgui.

        This is called each frame if the widget is active.
        Subclasses should override this to implement their own rendering logic."""
        raise NotImplementedError

    def render_edit_details(self):
        """Renders the contents to EDIT this widget through imgui.

        This can be called by ``self.render_full_edit()``, our WidgetSystem or others sources in order to allow editing this widget.

        The BaseWidget default implementation does the following:
        * Displays the widget's ID for identification. The ID's text tooltip show the widget class's docstring.
        * Calls ``imgui_utils.render_all_properties(self)`` to automatically render the key:value editor for all imgui properties in the
        widget class. The editable properties of the base widget classes are implemented as imgui-properties.

        Subclasses may override this to add their own editing rendering logic or change the base one.
        """
        imgui.text(f"Widget {self.id}")
        imgui.set_item_tooltip(type(self).__doc__)
        types.render_all_properties(self, self.edit_ignored_properties)

    def render_full_edit(self):
        """Renders the EDIT menu for the entire hierarchy of widgets this one belongs to.

        This calls this function recursively for our parent, and then calls ``self.render_edit_details()`` inside a menu to render our edit menu.
        Therefore this will render a sequence of menus, each being the edit menu of a widget, from the first (root) widget in our hierarchy
        down to this widget.

        Subclasses should not override this.
        """
        if self.slot is not None and self.slot.parent is not None:
            self.slot.parent.render_full_edit()
        if not self.editable:
            return
        imgui.text(self.name)
        imgui.same_line()
        # NOTE: we can't have the begin_menu label include self.name, since it may change inside and then close the menu.
        #   Couldn't find any other way to fix this properly...
        if imgui.begin_menu(f"({self.id})"):
            self.render_edit_details()
            if self.can_be_deleted:
                imgui.spacing()
                imgui.separator()
                imgui.spacing()
                if menu_item("Remove Widget"):
                    self.reparent_to()
                imgui.set_item_tooltip("Removes this widget from its parent. Without a parent, it won't be rendered.")
            imgui.end_menu()

    def open_edit_menu(self):
        """Opens a context-menu popup if the last item was right-clicked.

        Will call ``self.render_full_edit()`` to populate the contents of the popup.
        """
        if not imgui.begin_popup_context_item(self.id):
            return
        self.render_full_edit()
        imgui.end_popup()

    def delete(self):
        """Deletes this widget, removing it from its parent (if any), and deregistering it from our root WidgetSystem."""
        self.reparent_to(None)
        if self.system is not None:
            self.system.deregister_widget(self)

    def reparent_to(self, slot: 'Slot' = None):
        """Changes our ``parent`` to the given value.

        If we had a parent, this will remove ourselves from him.

        Args:
            new_parent (Slot): the new parent slot to set. Might be None.
            If None, the widget will be left parentless. It wont be rendered until it has a parent.
        """
        if self.slot is not None:
            self.slot._child = None
            self.slot.remove_link_to(self.parent_pin)
        self.slot = slot
        if (slot is not None) and not slot.is_linked_to(self.parent_pin):
            slot._add_new_link(self.parent_pin)

    def _handle_interaction(self):
        """Handles common interaction for this widget. This should be called each frame on a ``render()``-like method.

        This creates a invisible-button (purely for interaction without visual) in imgui, expanding across the whole current
        content available region. If our WidgetSystem root has editing enabled, also allows right-clicking to open our edit-menu
        (using ``self.open_edit_menu()``).

        If ``self.interactive`` is False, this will do nothing and always return False.

        Subclasses should use this on their render, usually before any other elements are drawn, in order to enable interaction for this widget.
        They can also use this invisible-button to check for other interactions, such as regular clicks.

        Returns:
            bool: if the invisible button was clicked.
        """
        if not self.interactive:
            return False
        pos = imgui.get_cursor_pos()
        imgui.set_cursor_pos(ImVec2(0, 0))
        size = imgui.get_content_region_avail()
        clicked = imgui.invisible_button(f"{self}Interaction", size)
        if self.system is not None and self.system.edit_enabled:
            self.open_edit_menu()
        imgui.set_cursor_pos(pos)
        return clicked

    def _set_pos_and_size(self, pos: Vector2 = None, size: Vector2 = None):
        """Updates the area and position vectors this widget internally stores, according to the parent slot this widget is being
        drawn to.

        This is automatically called on child widgets by their ContainerWidget parents when they render their children.

        Args:
            pos (Vector2, optional): The absolute position of the widget. If None, will get imgui's current cursor position.
            Defaults to None.
            size (Vector2, optional): The size of the widget. If None, will get imgui's current available region size.
            Defaults to None.
        """
        if pos is None:
            pos = Vector2(*imgui.get_cursor_screen_pos())
        if size is None:
            size = Vector2(*imgui.get_content_region_avail())
        self._area = size
        self._pos = pos

    def _on_system_changed(self):
        """Internal callback called when our ``system`` attribute changes.

        Subclasses may override this to implement their own logic. Default implementation in BaseWidget does nothing.
        """
        pass

    def get_input_pins(self) -> list[NodePin]:
        """Gets list of all input pins in this widget. Used when the widget is represented in a Node Editor.
        BaseWidget only returns our parent pin.
        """
        return [self.parent_pin]

    def __str__(self):
        return f"{self.id}:{self.name}"


@not_user_creatable
class LeafWidget(BaseWidget):
    """Abstract Base Leaf Widget.

    These are widgets that do not have any child widgets - they are the a leaf in the widget-system tree hierarchy.

    NOTE: this class automatically sets up ``__init__()`` in sub-classes to call the initializer of this class before.
    """

    def __init__(self):
        super().__init__()

    def __init_subclass__(cls) -> None:
        insert_base_init(cls, LeafWidget)


class Slot(NodePin):
    """A Slot represents the association between a child widget and its parent ContainerWidget.

    In its basic form, a slot associates a single child widget with an area of the container where it can draw a child.
    Thus the slot allows the child to be rendered in a specific clipped area of the parent container.

    Slots also contain additional data/features, such as: drawing an outline around the area of the slot, creating a new child
    widget to fill a empty slot, limiting which types of widgets can be attached to the slot, and more.

    Containers can define which type of Slot they use, and thus they can define their own Slot classes with added logic
    for that container."""

    def __init__(self, parent: 'ContainerWidget', name: str):
        super().__init__(parent, imgui_node_editor.PinKind.output)
        self.parent: 'ContainerWidget' = parent  # will be the same as self.parent_node, but proper type-hint.
        self._child: BaseWidget = None
        self._name: str = name if name else f"#{parent.slot_counter}"
        self.area = Rectangle((0, 0), (1, 1))
        """The area of this slot. It's inside this area, as a imgui ChildRegion, that our child widget will be drawn.

        Container widgets usually update this value on all its slots as needed.
        Area position has to be in absolute coords.
        """
        self.accepted_child_types: list[type[BaseWidget]] = [BaseWidget]
        """The types accepted by this slot as children (subclasses of them are accepted as well). Subclasses of slots should
        override this as desired. Default is to allow ``BaseWidget`` and thus, all of its subclasses (all widgets)."""
        self._draw_area_outline = False
        self._area_outline_color: Color = Color(1, 1, 1, 1)
        self.enabled = True
        """If this slot is enabled. Disabled slots are not rendered."""
        self.edit_ignored_properties: set[str] = set()
        """Set of imgui-property names that shall be ignored when rendering this widget's imgui-properties through the
        default ``self.render_edit_details()`` implementation."""
        self.default_link_color = Colors.green  # same color used in draw_widget_pin_icon
        self.can_be_deleted = True

    @types.bool_property()
    def draw_area_outline(self) -> bool:
        """If true, when this slot is rendered by its parent, a thin outline will be drawn showing the slots's area outline.
        Essentially showing the slots's slot position and size. [GET/SET]"""
        return self._draw_area_outline

    @draw_area_outline.setter
    def draw_area_outline(self, value: bool):
        self._draw_area_outline = value

    @types.color_property()
    def area_outline_color(self):
        """The color of the area outline of this slot. See ``draw_area_outline``. [GET/SET]"""
        return self._area_outline_color

    @area_outline_color.setter
    def area_outline_color(self, value: Color):
        self._area_outline_color = value

    @property
    def child(self) -> BaseWidget:
        """The child widget attached to this slot."""
        return self._child

    @child.setter
    def child(self, value: BaseWidget):
        if (value is not None) and not self.accepts_widget(value):
            click.secho(f"{self.parent}'s {self} can't accept widget '{value}' (a {type(value)}) as child.", fg="red")
            return
        if self._child is not None:
            self._child.reparent_to()
        self._child = value
        if value is not None:
            if self.parent.system:
                self.parent.system.register_widget(value)
            value.reparent_to(self)

    def render(self):
        """Renders this slot.

        This may render the slot's outline, if enabled. Render the child, if any.
        And handle interaction to render the context menu in a empty-slot (see ``draw_open_slot_menu``).
        """
        if not self.enabled:
            return
        if min(*self.area.size) <= 0:
            # Can't render a slot that has no size. (actually crashes)
            return

        if self.draw_area_outline:
            imgui.get_window_draw_list().add_rect(self.area.position, self.area.bottom_right_pos, self.area_outline_color.u32)

        imgui.set_cursor_screen_pos(self.area.position)
        window_flags = imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
        id = f"{self.parent}Slot{self._name}"
        imgui.begin_child(id, self.area.size, window_flags=window_flags)
        imgui.push_id(id)
        if self.child:
            self.child._set_pos_and_size()
            if self.child.enabled:
                self.child.render()
        elif self.parent.system and self.parent.system.edit_enabled:
            self.draw_open_slot_menu()
        imgui.pop_id()
        imgui.end_child()

    def render_edit_details(self):
        """Renders the imgui controls to allow user editing of this Slot.

        The Slot default implementation only calls ``imgui_utils.render_all_properties(self)`` to automatically render the key:value editor
        for all imgui properties in this Slot's class.

        The slot's edit-rendering is handled by its parent ContainerWidget, in the widget's edit-rendering. The parent handles extra logic
        such as adding/removing slots.

        Subclasses may override this to add their own editing rendering logic or change the base one.
        """
        types.render_all_properties(self, self.edit_ignored_properties)

    def draw_open_slot_menu(self):
        """Allows opening a context-menu popup with right-click in this (empty) slot.

        The context-menu will render this slot's parent full-edit-menu, as well as the WidgetSystem's create new widget menu
        to allow creating a new widget in this slot.

        The created child (if any) is automatically added as the child of this slot.
        """
        imgui.invisible_button(f"{self}OpenSlotMenu", self.area.size)
        if not imgui.begin_popup_context_item("CreateNewWidgetMenu"):
            return
        self.parent.render_full_edit()
        imgui.separator()
        imgui.text(f"{self} - create new widget:")
        if self.parent.system:
            new_child = self.parent.system.render_create_widget_menu(self.accepted_child_types)
        else:
            new_child = None
            imgui.text_colored(Colors.red, "Widget has no root system!")
        if new_child:
            self.child = new_child
        imgui.end_popup()

    def delete(self):
        """Deletes this slot.

        Besides clearing and removing this slot from its parent container, this will also remove our attached child widget (if any)."""
        if self._child:
            self._child.reparent_to()
        self.parent._slots.remove(self)
        self.parent.on_slots_changed()

    def accepts_widget(self, widget: BaseWidget):
        """Checks if the given widget is accepted by this slot as a child.

        Args:
            widget (BaseWidget): the widget to check.

        Returns:
            bool: if the widget is accepted or not.
        """
        for accepted_type in self.accepted_child_types:
            if isinstance(widget, accepted_type):
                return True
        return False

    def draw_node_pin_contents(self):
        imgui.text(self._name)
        draw_widget_pin_icon(self.is_linked_to_any())

    def can_link_to(self, pin: NodePin) -> tuple[bool, str]:
        ok, why_not = super().can_link_to(pin)
        if not ok:
            return ok, why_not
        widget = pin.parent_node  # remember, nodes are widgets
        if not self.accepts_widget(widget):
            return False, f"{self.parent}'s {self} can't accept widget '{widget}' (a {type(widget)}) as child."
        if self.child == widget:
            return False, "Already linked to that widget."
        return True, "success"

    def on_new_link_added(self, link: NodeLink):
        # links for us are always:
        #   start-pin: the slot (us)
        #   end-pin: the baseWidget parent-node pin. (the child widget)
        # And if this was called, linking (setting this as child) was possible.
        self.child = link.end_pin.parent_node

    def on_link_removed(self, link: NodeLink):
        self.child = None

    def __str__(self):
        return f"Slot {self._name}"


# TODO: render-edit: permitir drag&drop pra mudar ordem dos slots, arrastando eles no menu.
@not_user_creatable
class ContainerWidget(BaseWidget):
    """Abstract Base Container Widget.

    These are widgets that may have child widgets - they are nodes in the widget-system tree hierarchy, containing
    other widgets.

    Logically, a ContainerWidget is a collection of Slots. Each slot defines where and how to render a optional child widget.
    The container itself handles adding, removing, updating and rendering slots. Container widgets implementations thus mostly
    handle defining its slots, and how to update them.

    NOTE: this class automatically sets up ``__init__()`` in sub-classes to call the initializer of this class before.
    """

    def __init__(self):
        super().__init__()
        self._slot_class: type[Slot] = Slot
        """Type of Slot used by this container."""
        self._slots: list[Slot] = []
        """List of slots this container contains. This should be a list of ``self._slot_class`` instances."""
        self.slot_counter: int = 0
        """Counter of how many different slots this container ever had.

        Used to provide a default unique name for new slots, if one wasn't provided when instantiating it.
        This is incremented automatically when a new slot is added, but subclasses should update this on their constructors
        when creating/adding new slots in the constructor.
        """
        self.accepts_new_slots = True
        """If user-interaction (while editing) can add new slots to this container."""
        self._edit_slot_header_color = Color(0.1, 0.5, 0.3, 1)

    def __init_subclass__(cls) -> None:
        insert_base_init(cls, ContainerWidget)

    @property
    def slots(self):
        """Gets the list of slots this container contains."""
        return self._slots.copy()

    def get_children(self) -> list[BaseWidget]:
        """Gets a list of children widgets from the slots of this container.

        Note that some of the itens returned here might be ``None``, representing empty slots."""
        return [slot.child for slot in self._slots]

    def get_slot(self, name: str):
        """Gets the slot with the given name, if any.

        Args:
            name (str): name of the slot to get.

        Returns:
            Slot: the with the given name, or None.
        """
        for slot in self._slots:
            if slot._name == name:
                return slot

    def update_slots(self):
        """Updates all of ours slots.

        This is called by ContainerWidget on every frame, before calling rendering all our slots, in order to update them
        before drawing them. Usually, we need to update the slot's area (position and size) before drawing.

        Subclasses should override this to implement their own logic for updating its slots.
        The default implementation in ContainerWidget sets the position and size on all slots to the current
        imgui's cursor (absolute) and available content region.
        """
        for slot in self._slots:
            slot.area.position = Vector2(*imgui.get_cursor_screen_pos())
            slot.area.size = Vector2(*imgui.get_content_region_avail())

    def render(self):
        """Renders this Container widget through imgui.

        This is called each frame if the widget is active.

        Default ContainerWidget render() implementation does:
        * Calls ``self._handle_interaction()``
        * Calls ``self.update_slots()``
        * Iterates through all slots (``self._slots``), calling ``slot.render()``.

        Subclasses can override this to implement their own child rendering logic, however usually just adding their own slots and updating
        them in ``update_slots()`` should be enough.
        """
        self._handle_interaction()
        self.update_slots()
        for slot in self._slots:
            slot.render()

    def render_edit_details(self):
        super().render_edit_details()

        imgui.spacing()
        imgui.separator_text("Slots")
        imgui.spacing()
        for slot in self.slots:
            imgui.push_style_color(imgui.Col_.header, self._edit_slot_header_color)
            if slot.can_be_deleted:
                opened, exists = imgui.collapsing_header(f"Slot: {slot._name}", p_visible=True)
            else:
                opened = imgui.collapsing_header(f"Slot: {slot._name}")
                exists = True
            imgui.pop_style_color()
            imgui.set_item_tooltip(type(slot).__doc__)
            if opened:
                slot.render_edit_details()
            if not exists:
                slot.delete()

        if self.accepts_new_slots and imgui.button("Add New Slot"):
            self.add_new_slot()

    def add_new_slot(self, slot: Slot = None, name: str = None):
        """Adds a new slot to this container.

        Args:
            slot (Slot, optional): The slot instance to add. If its None, a new slot instance will be created with
            ``self._slot_class(self, name)``.
            name (str, optional): Optional name to give to the slot, if a slot is being created with this method (arg ``slot`` is None).
            If no name is given, the slot'll have a default ``#N`` name, where ``N`` is our ``self.slot_counter`` value, which is
            incremented with this method.

        Returns:
            Slot: the slot object that was added to this container.
        """
        self.slot_counter += 1
        if slot is None:
            slot = self._slot_class(self, name)
        self._slots.append(slot)
        self.on_slots_changed()
        return slot

    def get_output_pins(self) -> list[NodePin]:
        return self.slots

    def on_slots_changed(self):
        """Internal callback called when our list of slots changed - either adding or removing a slot.

        Default implementation on ContainerWidget does nothing. Subclasses should override this as needed.
        """
        pass

    def _on_system_changed(self):
        super()._on_system_changed()
        for slot in self._slots:
            if slot.child:
                slot.child.system = self.system

    def __iter__(self) -> Iterator[BaseWidget]:
        return iter(self.get_children())


class SystemRootPin(NodePin):
    """Node Pin for a WidgetSystem's Root widget."""

    def __init__(self, parent: 'WidgetSystem'):
        super().__init__(parent, imgui_node_editor.PinKind.output)
        self.parent_node: WidgetSystem = parent
        self._child: BaseWidget = None
        self.default_link_color = Colors.green  # same color used in draw_widget_pin_icon

    @property
    def child(self):
        """Gets the widget that is set as the root of our WidgetSystem. [GET/SET]"""
        return self._child

    @child.setter
    def child(self, value: BaseWidget):
        if self._child == value:
            return
        if self._child and self.is_linked_to(self._child.parent_pin):
            self.remove_link_to(self._child.parent_pin)
        self._child = value
        if value:
            value.reparent_to(None)  # root widgets have no Slot parent.
            if not self.is_linked_to(value.parent_pin):
                self.link_to(value.parent_pin)

    def draw_node_pin_contents(self):
        imgui.text("Root")
        draw_widget_pin_icon(self.is_linked_to_any())

    def can_link_to(self, pin: NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, WidgetParentPin):
            return False, "Can only link to a Widget's Parent pin."
        return True, "success"

    def on_new_link_added(self, link: NodeLink):
        # kinda the same as in the Slot class
        self.child = link.end_pin.parent_node

    def on_link_removed(self, link: NodeLink):
        self.child = None


class WidgetSystem(Node):
    """Root object managing a Widget and Action hierarchy."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.widgets: dict[str, BaseWidget] = {}
        self.root = SystemRootPin(self)
        self.edit_enabled = True
        self.edit_window_title = "Edit Widgets System"
        self.can_be_deleted = False
        self._output_pins = [
            self.root,
            actions.ActionFlow(self, imgui_node_editor.PinKind.output, "Test")
        ]
        self.node_editor = NodeEditor(self.render_node_editor_context_menu)
        self.node_editor.nodes.append(self)

    def render(self):
        imgui.begin_child("AppRootWidget")
        if self.root.child is not None:
            self.root.child._set_pos_and_size()
            self.root.child.render()
        else:
            if self.edit_enabled and imgui.begin_popup_context_window("CreateRootWidgetMenu"):
                imgui.text("Create Root Widget:")
                self.render_create_widget_menu()
                imgui.end_popup()
        imgui.end_child()

        if not self.edit_enabled:
            if imgui.begin_popup("AppRootNoEditMenu"):
                if imgui.button("Open EDIT Mode?"):
                    self.edit_enabled = True
                # TODO: opcao pra abrir edit, substituindo render-widgets. (não abre outra janela, nao mostra widgets).
                # TODO: opcao pra abrir edit em cima do render-widgets, tipo um overlay (nao abre outra janela, mostra widgets)
                lines = [
                    "EDIT Mode opens a separate window for editing your widget settings,",
                    "and allow right-click interaction with some widgets.",
                    "\n\nClose the EDIT window to close the EDIT Mode and go back to normal widgets display."
                ]
                imgui.set_item_tooltip(" ".join(lines))
                imgui.end_popup()
            if imgui.is_mouse_clicked(imgui.MouseButton_.right):
                # NOTE: For some reason, the `imgui.begin_popup_context_*` functions were not working here...
                # Had to do this to open the popup manually.
                imgui.open_popup("AppRootNoEditMenu", imgui.PopupFlags_.mouse_button_right)
        else:
            edit_window_flags = imgui.WindowFlags_.no_collapse
            opened, self.edit_enabled = imgui.begin(self.edit_window_title, self.edit_enabled, edit_window_flags)
            if opened:
                self.render_edit_window()
            imgui.end()

    def render_edit_window(self):
        """Renders the contents of the system edit window."""
        self.node_editor.render_system()

    def load(self):
        # TODO
        pass

    def save(self):
        # TODO
        pass

    def register_widget(self, widget: BaseWidget):
        """Registers the given widget with this system.

        Sets the widget's root system as this system, and adds it to our table of widgets.
        If we didn't have a root widget, this widget will be set as the root.

        Args:
            widget (BaseWidget): the widget to register

        Returns:
            bool: True if the widget was successfully registered to us, or was already registered to us.
            False otherwise (a different widget with same ID already exists).
        """
        if widget.id in self.widgets:
            return self.widgets[widget.id] == widget
        if widget.system is not None:
            widget.system.deregister_widget(widget)
        widget.system = self
        self.widgets[widget.id] = widget
        self.node_editor.nodes.append(widget)
        if self.root.child is None:
            self.root.child = widget
        return True

    def deregister_widget(self, widget: BaseWidget):
        """Deregisters the given widget from this system.

        This should only be used internally by ``register_widget()`` when change a widget between systems,
        since a widget without a root system may lead to errors.
        This sets ``widget.system = None``.

        Args:
            widget (BaseWidget): the widget to remove.

        Returns:
            bool: True if the widget was successfully deregistered from us.
            False otherwise (widget was not registered to us).
        """
        if widget.system != self or widget.id not in self.widgets:
            return False
        if self.widgets[widget.id] != widget:
            return False
        self.widgets.pop(widget.id)
        self.node_editor.nodes.remove(widget)
        widget.system = None
        if self.root.child == widget:
            self.root.child = None
        return True

    def render_create_widget_menu(self, accepted_bases: list[type[BaseWidget]] = [BaseWidget]) -> BaseWidget | None:
        """Renders the contents for a menu that allows the user to create a new widget, given the possible options.

        Args:
            accepted_bases (list[type[BaseWidget]]): list of base types accepted as the options of new widgets to create.
            The menu will search for all possible subclasses of these given accepted types and display them for selection.
            Options in the menu are organized following the same tree-hierarchy as the classes themselves.
            Classes marked with the ``@not_user_creatable`` decorator will won't be allowed to be created by the user, but their subclasses may.
            The default list of ``[BaseWidget]`` basically allows all widgets since the only base is the base for all widgets.

        Returns:
            BaseWidget: the newly created instance of a widget, if any. None otherwise.
            Any created widget is auto-registered with this system.
        """
        new_child = None
        for cls in accepted_bases:
            new_child = object_creation_menu(cls, lambda cls: cls.__name__.replace("Widget", ""))
            if new_child is not None:
                break
        if new_child:
            self.register_widget(new_child)
        return new_child

    def render_create_action_menu(self) -> actions.Action | None:
        """Renders the contents for a menu that allows the user to create a new action, given the possible options.

        Returns:
            Action: the newly created instance of a action, if any. None otherwise.
        """
        new_action: actions.Action = object_creation_menu(actions.Action)
        if new_action:
            self.node_editor.nodes.append(new_action)
            new_action.editor = self.node_editor
        return new_action

    def render_node_editor_context_menu(self, linked_to_pin: NodePin):
        """Context-menu contents for the node-editor's background menu.

        This is used when right-clicking the editor's background or pulling a link to create a new node.
        This is usually used as a menu to create a new node.

        Args:
            linked_to_pin (NodePin): If given, this is the pin from which the user pulled a link to
            create a new node. So it can be used to limit the contents of the menu, or of which new nodes can be created.
            The NodeEditor will take care of properly positioning the new node and linking it to this pin.

        Returns:
            Node: the new node that was created, if any new node was created.
        """
        if isinstance(linked_to_pin, Slot):
            return self.render_create_widget_menu(linked_to_pin.accepted_child_types)
        if isinstance(linked_to_pin, actions.ActionFlow):
            return self.render_create_action_menu()
        else:
            new_widget = self.render_create_widget_menu()
            new_action = self.render_create_action_menu()
            return new_widget or new_action

    def get_output_pins(self) -> list[NodePin]:
        return self._output_pins

    def __str__(self):
        return f"Widget System: {self.name}"
