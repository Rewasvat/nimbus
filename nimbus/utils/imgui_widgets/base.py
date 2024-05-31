import click
from typing import Iterator
from imgui_bundle import imgui, ImVec2, ImVec4
import nimbus.utils.imgui as imgui_utils


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


def not_user_creatable(cls):
    """Class-decorator to mark a Widget class as being "Not User Creatable".

    Which means the user won't be able to create a instance of this class using the runtime menu options.
    However, subclasses of this class will still show up in the widget-creation menu. This decorator only affects
    this class, repeat it on subclasses to disable user-creation of those as well."""
    if not hasattr(cls, "__class_tags"):
        cls.__class_tags = {}
    if cls.__name__ not in cls.__class_tags:
        # We need this since this attribute on a class would be inherited by subclasses.
        # We want each class to define the tag just on itself.
        cls.__class_tags[cls.__name__] = {}
    cls.__class_tags[cls.__name__]["not_user_creatable"] = True
    return cls


@not_user_creatable
class BaseWidget:
    """Abstract Base Widget Class.

    Shouldn't be used on its own.

    NOTE: this class automatically sets up ``__init__()`` in sub-classes to call the initializer of this class before.
    """
    _widget_instance_count = 0
    """Internal instance counter used for unique IDs."""

    def __init__(self):
        BaseWidget._widget_instance_count += 1
        self._internal_id = f"{type(self).__name__}-{BaseWidget._widget_instance_count}"
        self._name: str = str(hash(self))
        self.slot: Slot = None
        """Parent slot containing this widget. Might be None."""
        self._system: WidgetSystem = None
        """Root System managing this widget."""
        self._area: imgui_utils.Vector2 = imgui_utils.Vector2()  # TODO: talvez tirar isso pq puxa do slot
        self._pos: imgui_utils.Vector2 = imgui_utils.Vector2()
        self.editable = True
        """If this widget is editable by the user during runtime. Depends on our WidgetSystem having edit enabled."""
        self.interactive = True
        """If this widget's common user interaction (via ``self._handle_interaction()``) is enabled."""
        self.edit_ignored_properties: set[str] = set()
        """Set of imgui-property names that shall be ignored when rendering this widget's imgui-properties through the
        default ``self.render_edit()`` implementation."""
        self.allow_edit_delete = True
        """If a ``Remove Widget`` button will be added in this widget's Edit Menu. When clicked this button deletes this widget."""
        self.enabled = True
        """If this widget is enabled. Disabled widgets are not rendered by their parents."""

    @classmethod
    def is_user_creatable(cls):
        cls_tags = getattr(cls, "__class_tags", {})
        my_tags = cls_tags.get(cls.__name__, {})
        return not my_tags.get("not_user_creatable", False)

    @property
    def id(self):
        """Fixed ID of this widget. IDs are uniquely generated at creation, according to widget type and overall instance count."""
        return self._internal_id

    @imgui_utils.string_property(imgui.InputTextFlags_.enter_returns_true)
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

    def render_edit(self):
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
        imgui_utils.render_all_properties(self, self.edit_ignored_properties)

    def render_full_edit(self):
        """Renders the EDIT menu for the entire hierarchy of widgets this one belongs to.

        This calls this function recursively for our parent, and then calls ``self.render_edit()`` inside a menu to render our edit menu.
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
            self.render_edit()
            if self.allow_edit_delete:
                imgui.spacing()
                imgui.separator()
                imgui.spacing()
                if imgui_utils.menu_item("Remove Widget"):
                    self.delete()
                imgui.set_item_tooltip(self.delete.__doc__)
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

    def reparent_to(self, slot: 'Slot'):
        """Changes our ``parent`` to the given value.

        If we had a parent, this will remove ourselves from him.

        Args:
            new_parent (Slot): the new parent slot to set. Might be None.
        """
        if self.slot is not None:
            self.slot._child = None
        self.slot = slot

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

    def _set_pos_and_size(self, pos: imgui_utils.Vector2 = None, size: imgui_utils.Vector2 = None):
        """Updates the area and position vectors this widget internally stores, according to the parent slot this widget is being
        drawn to.

        This is automatically called on child widgets by their ContainerWidget parents when they render their children.

        Args:
            pos (imgui_utils.Vector2, optional): The absolute position of the widget. If None, will get imgui's current cursor position.
            Defaults to None.
            size (imgui_utils.Vector2, optional): The size of the widget. If None, will get imgui's current available region size.
            Defaults to None.
        """
        if pos is None:
            pos = imgui_utils.Vector2(*imgui.get_cursor_screen_pos())
        if size is None:
            size = imgui_utils.Vector2(*imgui.get_content_region_avail())
        self._area = size
        self._pos = pos

    def _on_system_changed(self):
        """Internal callback called when our ``system`` attribute changes.

        Subclasses may override this to implement their own logic. Default implementation in BaseWidget does nothing.
        """
        pass

    def __str__(self):
        return f"{self.id}:{self.name}"


@not_user_creatable
class LeafWidget(BaseWidget):
    """Abstract Base Leaf Widget.

    These are widgets that do not have any child widgets - they are the a leaf in the widget-system tree hierarchy.

    NOTE: this class automatically sets up ``__init__()`` in sub-classes to call the initializer of this class before.
    """

    def __init__(self):
        pass

    def __init_subclass__(cls) -> None:
        insert_base_init(cls, LeafWidget)


class Slot:
    """A Slot represents the association between a child widget and its parent ContainerWidget.

    In its basic form, a slot associates a single child widget with an area of the container where it can draw a child.
    Thus the slot allows the child to be rendered in a specific clipped area of the parent container.

    Slots also contain additional data/features, such as: drawing an outline around the area of the slot, creating a new child
    widget to fill a empty slot, limiting which types of widgets can be attached to the slot, and more.

    Containers can define which type of Slot they use, and thus they can define their own Slot classes with added logic
    for that container."""

    def __init__(self, parent: 'ContainerWidget', name: str):
        self.parent: 'ContainerWidget' = parent
        self._child: BaseWidget = None
        self._name: str = name if name else f"#{parent.slot_counter}"
        self.area = imgui_utils.Rectangle((0, 0), (1, 1))
        """The area of this slot. It's inside this area, as a imgui ChildRegion, that our child widget will be drawn.

        Container widgets usually update this value on all its slots as needed.
        Area position has to be in absolute coords.
        """
        self.accepted_child_types: list[type[BaseWidget]] = [BaseWidget]
        """The types accepted by this slot as children (subclasses of them are accepted as well). Subclasses of slots should
        override this as desired. Default is to allow ``BaseWidget`` and thus, all of its subclasses (all widgets)."""
        self._draw_area_outline = False
        self._area_outline_color: ImVec4 = ImVec4(1, 1, 1, 1)
        self.enabled = True
        """If this slot is enabled. Disabled slots are not rendered."""
        self.edit_ignored_properties: set[str] = set()
        """Set of imgui-property names that shall be ignored when rendering this widget's imgui-properties through the
        default ``self.render_edit()`` implementation."""

    @imgui_utils.bool_property()
    def draw_area_outline(self) -> bool:
        """If true, when this slot is rendered by its parent, a thin outline will be drawn showing the slots's area outline.
        Essentially showing the slots's slot position and size. [GET/SET]"""
        return self._draw_area_outline

    @draw_area_outline.setter
    def draw_area_outline(self, value: bool):
        self._draw_area_outline = value

    @imgui_utils.color_property()
    def area_outline_color(self):
        """The color of the area outline of this slot. See ``draw_area_outline``. [GET/SET]"""
        return self._area_outline_color

    @area_outline_color.setter
    def area_outline_color(self, value: ImVec4):
        self._area_outline_color = value

    @property
    def child(self) -> BaseWidget:
        """The child widget attached to this slot."""
        return self._child

    @child.setter
    def child(self, value: BaseWidget):
        if not self.accepts_widget(value):
            click.secho(f"{self.parent}'s {self} can't accept widget '{value}' (a {type(value)}) as child.", fg="red")
            return
        if self._child is not None:
            self._child.delete()
        self._child = value
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
            outline_color = imgui.get_color_u32(self.area_outline_color)
            imgui.get_window_draw_list().add_rect(self.area.position, self.area.bottom_right_pos, outline_color)

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

    def render_edit(self):
        """Renders the imgui controls to allow user editing of this Slot.

        The Slot default implementation only calls ``imgui_utils.render_all_properties(self)`` to automatically render the key:value editor
        for all imgui properties in this Slot's class.

        The slot's edit-rendering is handled by its parent ContainerWidget, in the widget's edit-rendering. The parent handles extra logic
        such as adding/removing slots.

        Subclasses may override this to add their own editing rendering logic or change the base one.
        """
        imgui_utils.render_all_properties(self, self.edit_ignored_properties)

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
            imgui.text_colored(imgui_utils.Colors.red, "Widget has no root system!")
        if new_child:
            self.child = new_child
        imgui.end_popup()

    def delete(self):
        """Deletes this slot.

        Besides clearing and removing this slot from its parent container, this will also delete our attached child widget (if any)."""
        if self._child:
            self._child.delete()
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
            slot.area.position = imgui_utils.Vector2(*imgui.get_cursor_screen_pos())
            slot.area.size = imgui_utils.Vector2(*imgui.get_content_region_avail())

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

    def render_edit(self):
        super().render_edit()

        imgui.spacing()
        imgui.separator_text("Slots")
        imgui.spacing()
        for slot in self.slots:
            opened, exists = imgui.collapsing_header(slot._name, p_visible=True)
            imgui.set_item_tooltip(type(slot).__doc__)
            if opened:
                slot.render_edit()
            if not exists:
                slot.delete()

        if imgui.button("Add New Slot"):
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


class WidgetSystem:
    """Root object managing a Widget hierarchy."""

    def __init__(self):
        self.widgets: dict[str, BaseWidget] = {}
        self.root: BaseWidget = None
        self.edit_enabled = True

    def render(self):
        imgui.begin_child("AppRootWidget")
        if self.root is not None:
            self.root._set_pos_and_size()
            self.root.render()
        else:
            if imgui.begin_popup_context_window("CreateRootWidgetMenu"):
                imgui.text("Create Root Widget:")
                self.render_create_widget_menu()
                imgui.end_popup()
        imgui.end_child()

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
        if self.root is None:
            self.root = widget
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
        widget.system = None
        if self.root == widget:
            self.root = None
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
            name = cls.__name__.replace("Widget", "")
            if cls.is_user_creatable():
                if imgui_utils.menu_item(name):
                    new_child = cls()
                imgui.set_item_tooltip("Creates a Widget of this class.\n" + cls.__doc__)

            subs = cls.__subclasses__()
            if len(subs) > 0:
                subs_opened = imgui.begin_menu(f"{name} Subtypes")
                imgui.set_item_tooltip(cls.__doc__)
                if subs_opened:
                    new_child = self.render_create_widget_menu(subs)
                    imgui.end_menu()
        if new_child:
            self.register_widget(new_child)
        return new_child