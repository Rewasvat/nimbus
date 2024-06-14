import nimbus.utils.imgui.actions as actions
from imgui_bundle import imgui
from nimbus.utils.imgui.general import object_creation_menu, menu_item
from nimbus.utils.imgui.nodes import Node, NodePin, NodeLink, NodeEditor, PinKind
from nimbus.utils.imgui.colors import Colors
from nimbus.monitor.sensors import Sensor, Hardware
from nimbus.monitor.monitor import MonitorManager

from nimbus.utils.imgui.widgets.base import BaseWidget, Slot, WidgetParentPin, draw_widget_pin_icon


class SystemRootPin(NodePin):
    """Node Pin for a WidgetSystem's Root widget."""

    def __init__(self, parent: 'WidgetSystem'):
        super().__init__(parent, PinKind.output)
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


# TODO: opcao pra abrir edit, substituindo render-widgets. (não abre outra janela, nao mostra widgets).
# TODO: opcao pra abrir edit em cima do render-widgets, tipo um overlay (nao abre outra janela, mostra widgets)
# TODO: mudar nome disso? afinal agora junta widgets+actions+sensors
# TODO: talvez de pra separar o "WidgetSystem" em classes diferentes. Uma basica que seria só widgets, outra com widgets+actions,
#       e finalmente uma com widget+actions+sensores
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
            actions.ActionFlow(self, PinKind.output, "Test")
        ]
        self.node_editor = NodeEditor(self.render_node_editor_context_menu)
        self.node_editor.nodes.append(self)

    def render(self):
        io = imgui.get_io()
        MonitorManager().computer.timed_update(io.delta_time)

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
        # TODO: load nodes from cache
        pass

    def save(self):
        # TODO: save nodes from cache
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
        self.node_editor.add_node(widget)
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
        self.node_editor.remove_node(widget)
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
        return object_creation_menu(actions.Action)

    def render_create_sensor_menu(self) -> Sensor | None:
        """Renders the contents for a menu that allows the user to create a Sensor node.

        Note that each Sensor is a unique object - for a given sensor from the computer, only ONE instance of Sensor
        will exist that represents it. This method therefore doesn't create a new Sensor node, it merely returns the
        selected Sensor.

        Returns:
            Sensor: the sensor object from the MonitorManager singleton.
        """
        computer = MonitorManager().computer

        def render_hw(hw: Hardware) -> Sensor:
            ret = None
            opened = imgui.begin_menu(hw.name)
            imgui.set_item_tooltip(f"ID: {hw.id}\nTYPE: {hw.type}\n\n{hw.__doc__}")
            if opened:
                for sub_hw in hw.children:
                    sub_ret = render_hw(sub_hw)
                    if sub_ret:
                        ret = sub_ret
                for sensor in hw.sensors:
                    if sensor not in self.editor.nodes:
                        if menu_item(f"{sensor.name} ({sensor.type}: {sensor.unit})"):
                            ret = sensor
                        imgui.set_item_tooltip(f"ID: {sensor.id}\n\n{sensor.__doc__}")
                imgui.end_menu()
            return ret

        new_sensor = None
        opened = imgui.begin_menu("Sensors:")
        imgui.set_item_tooltip("Select a sensor to create as node.\n\nOnly one node of a specific sensor may exist at any given time.")
        if opened:
            for hardware in computer:
                ret = render_hw(hardware)
                if ret:
                    new_sensor = ret
            imgui.end_menu()

        return new_sensor

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
            new_sensor = self.render_create_sensor_menu()
            return new_widget or new_action or new_sensor

    def get_output_pins(self) -> list[NodePin]:
        return self._output_pins

    def render_edit_details(self):
        if menu_item("Reposition Nodes"):
            self.reposition_nodes([actions.ActionFlow, Slot, SystemRootPin])

    def __str__(self):
        return f"Widget System: {self.name}"
