import nimbus.utils.imgui.actions as actions
import nimbus.utils.command_utils as cmd_utils
from imgui_bundle import imgui
from nimbus.utils.imgui.general import object_creation_menu, menu_item
from nimbus.utils.imgui.nodes import Node, NodePin, NodeLink, NodeEditor, PinKind, output_property
from nimbus.utils.imgui.nodes.node_config import SystemConfig
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.widgets.base import BaseWidget, Slot, WidgetParentPin, draw_widget_pin_icon
from nimbus.monitor.sensors import Sensor, Hardware, ComputerSystem
from nimbus.data import DataCache


class SystemRootPin(NodePin):
    """Widget Root Pin for a UISystem's Root node."""

    def __init__(self, parent: 'SystemRootNode'):
        super().__init__(parent, PinKind.output, "Root")
        self.parent_node: SystemRootNode = parent
        self._child: BaseWidget = None
        self.default_link_color = Colors.green  # same color used in draw_widget_pin_icon

    @property
    def child(self):
        """Gets the widget that is set as the root of our UISystem. [GET/SET]"""
        return self._child

    @child.setter
    def child(self, value: BaseWidget):
        if self._child == value:
            return
        if self._child and self.is_linked_to(self._child.parent_pin):
            self.delete_link_to(self._child.parent_pin)
        self._child = value
        if value:
            value.reparent_to(None)  # root widgets have no Slot parent.
            if not self.is_linked_to(value.parent_pin):
                self.link_to(value.parent_pin)

    def draw_node_pin_contents(self):
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


class SystemRootNode(Node):
    """Root Node for a UISystem.

    Provides base output pins from which the system may be defined:
    * A root widget pin to create the widget hierarchy.
    * System level ActionFlows for logic triggering.
    * System level DataPins providing basic system data for the graph.
    """

    def __init__(self, system: 'UISystem' = None):
        super().__init__()
        self.system: UISystem = system
        self.node_bg_color = Color(0.12, 0.22, 0.1, 0.75)
        self.node_header_color = Color(0.32, 0.6, 0.04, 0.6)
        self.can_be_deleted = False
        if not self._is_unpickling():
            self.widget_root = SystemRootPin(self)
            self.on_update = actions.ActionFlow(self, PinKind.output, "On Update")
            self.add_pin(self.widget_root)
            self.add_pin(self.on_update)
            self.create_data_pins_from_properties()

    @property
    def system(self) -> 'UISystem':
        """Gets the UISystem that owns this root-node."""
        return self._system

    @system.setter
    def system(self, value: 'UISystem'):
        self._system = value
        self.node_title = str(value)

    @output_property(use_prop_value=True)
    def delta_time(self) -> float:
        """Gets the delta time, in seconds, between the current and last frames from IMGUI."""
        io = imgui.get_io()
        return io.delta_time

    def render_edit_details(self):
        if menu_item("Reposition Nodes"):
            self.reposition_nodes([actions.ActionFlow, Slot, SystemRootPin])
        imgui.set_item_tooltip("Rearranges all nodes following this one according to depth in the graph.")
        if menu_item("Save"):
            self.system.save_config()
        imgui.set_item_tooltip("Saves the configuration of this UISystem to disk. This config can be later used to recreate/reuse this UISystem.")


# TODO: opcao pra abrir edit, substituindo render-widgets. (não abre outra janela, nao mostra widgets).
# TODO: opcao pra abrir edit em cima do render-widgets, tipo um overlay (nao abre outra janela, mostra widgets)
# TODO: mudar nome disso? afinal agora junta widgets+actions+sensors
# TODO: talvez de pra separar o "UISystem" em classes diferentes. Uma basica que seria só widgets, outra com widgets+actions,
#       e finalmente uma com widget+actions+sensores
# TODO: atalho de teclado pro save
# TODO: widget novo: imagem. Scala a imagem para a area do slot. Pode escolher UV-coords usadas (sub-frames). Escolher imagem por path anywhere?
# TODO: widget novo: polygon. Tipo o XAMLPath. User pode configurar vários shapes em runtime.
#   - pra cada shape, user vai configurando segmentos, fill color, stroke color, stroke thickness, etc.
class UISystem:
    """Represents a complete user-configurable UI and logic system.

    * Contains a Widget hierarchy for configuring the UI. The widgets are fully-configurable by the user.
    * Supports Actions for defining logic that can be executed on events.
    * Supports system level events and widgets events for triggering actions.
    * Widgets and Actions are defined in a single NodeEditor, allowing easy user configuration by visual node "programming" in a single graph.
    * Supports the Sensors System as nodes for providing sensor data and events to the graph.
    * User configuration is persisted in Nimbus' DataCache (key based on system name).
    """

    def __init__(self, name: str, nodes: list[Node] = None):
        self.name = name
        self.edit_enabled: bool = True
        """If editing the graph is enabled in this system."""
        self.edit_window_title = f"Edit {name} UISystem"
        self.node_editor = NodeEditor(self.render_node_editor_context_menu)
        if nodes is None:
            self._root_node = SystemRootNode(self)
            self.node_editor.nodes.append(self._root_node)
        else:
            self._root_node: SystemRootNode = nodes[0]
            self._root_node.system = self
            self.node_editor.nodes = nodes

    @property
    def root_widget(self) -> BaseWidget:
        """Gets the root widget of this system."""
        return self._root_node.widget_root.child

    @root_widget.setter
    def root_widget(self, root: BaseWidget):
        self._root_node.widget_root.child = root

    def render(self):
        """Renders this system in the current region."""
        self._root_node.on_update.trigger()

        imgui.begin_child(f"{repr(self)}AppRootWidget")
        if self.root_widget is not None:
            self.root_widget._set_pos_and_size()
            self.root_widget.render()
        else:
            if self.edit_enabled and imgui.begin_popup_context_window(f"{repr(self)}CreateRootWidgetMenu"):
                imgui.text("Create Root Widget:")
                self.render_create_widget_menu()
                imgui.end_popup()
        imgui.end_child()

    def render_edit(self):
        """Renders the contents of the system edit window.

        This draws the system's graph editor, and as such would benefit from a large window/region to render in.
        """
        self.node_editor.render_system()

    def save_config(self):
        """Saves this UISystem's config to the UIManager singleton, thus persisting its data for future use."""
        manager = UIManager()
        manager.update_system(self)

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
        return new_child

    def render_create_action_menu(self) -> actions.Action | None:
        """Renders the contents for a menu that allows the user to create a new action, given the possible options.

        Returns:
            Action: the newly created instance of a action, if any. None otherwise.
        """
        return object_creation_menu(actions.Action)

    def render_create_sensor_menu(self) -> Sensor | None:
        """Renders the contents for a menu that allows the user to create a Sensor node.

        Note that only one Sensor object may exist for any given sensor ID.

        Returns:
            Sensor: the sensor object from the MonitorManager singleton.
        """
        def render_hw(hw: Hardware) -> Sensor:
            ret = None
            opened = imgui.begin_menu(hw.name)
            imgui.set_item_tooltip(f"ID: {hw.id}\nTYPE: {hw.type}\n\n{hw.__doc__}")
            if opened:
                for sub_hw in hw.children:
                    sub_ret = render_hw(sub_hw)
                    if sub_ret:
                        ret = sub_ret
                for isensor in hw.isensors:
                    if not isensor.sensor:
                        if menu_item(f"{isensor.name} ({isensor.type}: {isensor.unit})"):
                            ret = isensor.create()
                        imgui.set_item_tooltip(f"ID: {isensor.id}\n\n{Sensor.__doc__}")
                imgui.end_menu()
            return ret

        new_sensor = None
        opened = imgui.begin_menu("Sensors:")
        imgui.set_item_tooltip("Select a sensor to create as node.\n\nOnly one node of a specific sensor may exist at any given time.")
        if opened:
            for hardware in ComputerSystem():
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

    def __str__(self):
        return f"Widget System: {self.name}"


class UIManager(metaclass=cmd_utils.Singleton):
    """Singleton manager of UISystems.

    Handles high-level, project-wide, operations regarding UISystems and related features.

    Most notably, handles the persistent storage of SystemConfigs: the persistence of the configuration
    objects that allow saving and recreation of any saved UISystems.
    """

    def __init__(self):
        cache = DataCache()
        self._config_cache_key = "UIManagerData"
        self._configs: dict[str, SystemConfig] = cache.get_custom_cache(self._config_cache_key, {})

    def get_all_configs(self):
        """Gets a list of all stored SystemConfigs."""
        return list(self._configs.values())

    def get_all_config_names(self):
        """Gets a sorted list of all stored config names."""
        return sorted(self._configs.keys())

    def get_config(self, name: str):
        """Gets the stored SystemConfig with the given NAME. May return None if no config exists for the NAME."""
        return self._configs.get(name)

    def has_config(self, name: str):
        """Checks if a SystemConfig with the given NAME exists."""
        return name in self._configs

    def update_config(self, config: SystemConfig):
        """Updates the manager with the given UISystem config (a SystemConfig instance).

        Configs are indexed by their name (``config.name``). If any config existed previously with
        the same name, it'll be overwritten by this new given config.

        This will thus save the config in persisten storage.

        Args:
            config (SystemConfig): the SystemConfig to store.
        """
        self._configs[config.name] = config
        self.save()

    def update_system(self, system: UISystem):
        """Updates the saved UISystem configs with the config of the given system.
        This will thus save the given system's config in persistent storage.

        Args:
            system (UISystem): the system to save its config.
        """
        config = SystemConfig.from_system(system)
        self.update_config(config)

    def remove_config(self, config: SystemConfig | str):
        """Removes the given config from persistent storage, effectively deleting it.

        Args:
            config (SystemConfig | str): which config to remove. Can be the SystemConfig object itself
            or its name.
        """
        name = config if isinstance(config, str) else config.name
        if self.has_config(name):
            self._configs.pop(name)
            self.save()

    def save(self):
        """Saves the UIManager data (saved UISystem configs and so on) to disk."""
        cache = DataCache()
        cache.save_custom_cache(self._config_cache_key, self._configs)
