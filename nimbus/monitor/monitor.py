import math
import click
import nimbus.monitor.sensors as sensors
import nimbus.utils.command_utils as cmd_utils
import nimbus.utils.utils as utils
import nimbus.utils.imgui.windows as windows
import nimbus.utils.imgui.general as imgui_utils
from nimbus.utils.imgui.popups import button_with_confirmation, TextInputPopup
from nimbus.utils.imgui.colors import Colors
from nimbus.data import DataCache
from imgui_bundle import imgui


@cmd_utils.main_command_group
class MonitorManager(metaclass=cmd_utils.Singleton):
    """MONITOR COMMANDS"""

    def __init__(self):
        pass

    @cmd_utils.object_identifier
    def name(self):
        return "monitor"

    @cmd_utils.instance_command()
    @click.option("--test", "-t", is_flag=True, help="Use dummy testing sensors")
    def open(self, test):
        """Opens the System Monitor GUI in DISPLAY mode."""
        if test:
            sensors.ComputerSystem().open(True)
        elif not utils.is_admin_user():
            click.secho("Can't run the System Monitor GUI without admin permissions!", fg="red")
            # return
        app = SystemMonitorApp(False)
        app.run()

    @cmd_utils.instance_command()
    @click.option("--test", "-t", is_flag=True, help="Use dummy testing sensors")
    def edit(self, test):
        """Opens the System Monitor GUI in EDIT mode."""
        if test:
            sensors.ComputerSystem().open(True)
        elif not utils.is_admin_user():
            click.secho("Can't run the System Monitor GUI without admin permissions!", fg="red")
            # return
        app = SystemMonitorApp(True)
        app.run()


class MonitorAppData:
    """Struct containing data and other user settings for the Monitor App window."""

    def __init__(self):
        self.update_time: float = 1.0
        """Amount of time (in secs) to update sensors."""
        self.selected_system: str = None
        """Name of the selected UISystem to display."""
        self.in_edit_mode: bool = True
        """If the Monitor is in Edit mode or in Display mode."""

    def save(self):
        """Saves the MonitorAppData to Nimbus' DataCache for persistence."""
        cache = DataCache()
        data = vars(self)
        cache.set_data("monitor_data", data)

    @classmethod
    def load(cls):
        """Loads a persisted MonitorAppData instance from Nimbus' DataCache."""
        cache = DataCache()
        data = cache.get_data("monitor_data", {})
        obj = cls()
        obj.__dict__.update(data)
        return obj


# TODO: refatorar MonitorApp pra ter 2 modos de display: EDIT e DISPLAY (names pending)
#   * DISPLAY:
#       - Atalho teclado e right-click-menu permitem só dar QUIT e trocar pro modo EDIT.
#       - talvez fullscreen? Se der pode ter setting separado pra ligar isso (e atalho/menu permitem mudar).
#   - COMMAND LINE ARGS:
#       + arg pra forcar abrir em um modo ou outro
#       - arg pra forcar o UISystem selecionado
#   - Pra trocar de um modo pra outro tem que recriar a janela:
#       - salva dados ou valores no objeto, dá close() na janela. Altera attrs da janela, faz um run() de novo.
#       - se fizer um overwrite do run(), daria pra ter tipo um while dentro dele sempre rodando o super.run(), então
#         marcando certo attr/flag e fechando a janela, a nova seria aberta automatico.
class SystemMonitorApp(windows.AppWindow):
    """System Monitor App.

    This is the main System Monitor App, opened by the ``monitor open`` or ``monitor edit`` commands, which allows
    the use of UI Systems. A UI System is a user-configurable GUI system that can display widgets, sensor data (from
    the local machine), supports interactions, and more.

    Which actual window is opened along with this App depends if `edit_mode`  is selected or not. According to it, the opened window is:
    * The EDIT Window: allows user to create, edit, visualize and delete UI Systems, as well as select the `main` system.
    This is a regular window, that supports viewports and docking nodes to allow user to see/edit multiple systems at once
    across several monitors.
    * The DISPLAY Window: only allows user to visualize (and interact with) the selected `main` system. This is a borderless
    window.

    NOTE: for now, while the edit_mode flag is persisted, it must be used manually by passing it as arg to the constructor,
    forcing to use one mode or the other. The two different commands (``open``/``edit``) do this. Its because trying to change
    the mode (and window) programatically during the same Nimbus session caused several issues... So for now this way it works.
    """

    def __init__(self, force_edit_mode=None):
        data = MonitorAppData.load()
        if force_edit_mode is not None:
            data.in_edit_mode = force_edit_mode
        title_suffix = "Edit" if data.in_edit_mode else "Display"
        super().__init__(f"System Monitor {title_suffix}", windows.RunnableAppMode.DOCK)
        self.data = data
        self.do_restart = False
        from nimbus.utils.imgui.widgets import UISystem, UIManager
        self.system_manager = UIManager()
        self.opened_systems: dict[str, UISystem] = {}
        self._reset_window_attrs()

    @property
    def _in_edit_mode(self):
        """If the Monitor app is in Edit mode (or in Display mode)."""
        return self.data.in_edit_mode

    @_in_edit_mode.setter
    def _in_edit_mode(self, value: bool):
        self.data.in_edit_mode = value

    def _reset_window_attrs(self):
        """Sets Basic/AppWindow attributes we inherit."""
        self.mode = windows.RunnableAppMode.DOCK if self._in_edit_mode else windows.RunnableAppMode.SIMPLE
        self.show_app_menu = self._in_edit_mode
        self.show_menu_bar = self._in_edit_mode
        self.show_status_bar = self._in_edit_mode
        self.enable_viewports = self._in_edit_mode
        self.use_borderless = not self._in_edit_mode
        self.debug_menu_enabled = True

    def render(self):
        if imgui.is_key_pressed(imgui.Key.escape):
            self.close()
        if imgui.is_key_down(imgui.Key.left_ctrl) and imgui.is_key_pressed(imgui.Key.end):
            self.change_mode()

        delta_t = imgui.get_io().delta_time
        sensors.ComputerSystem().timed_update(delta_t)

        if self._in_edit_mode:
            self.update_closed_systems()
        else:
            display_window = self.get_display_window(self.data.selected_system)
            if display_window:
                display_window.render()

    def on_init(self):
        super().on_init()
        computer = sensors.ComputerSystem()
        computer.open()
        computer.update_time = self.data.update_time
        self.children.clear()
        self.update_closed_systems()
        if self._in_edit_mode:
            self.add_child_window(MonitorMainWindow(self))
        else:
            self.open_system_display(self.data.selected_system)

    def on_before_exit(self):
        for system in self.opened_systems.values():
            system.save_config()
        self.system_manager.save()
        # TODO: persistir systems abertos pra edicao/display?
        self.data.save()
        super().on_before_exit()

    def change_mode(self):
        """TODO"""
        self._in_edit_mode = not self._in_edit_mode
        self.do_restart = True
        self.close()

    def create_new_system(self, name: str):
        """Creates a new UISystem config with the given NAME, if available.

        This will also instantiate the (empty) system, and open its Display and Edit windows.
        """
        if self.system_manager.has_config(name):
            click.secho(f"Can't create new system named '{name}'", fg="red")
            return False
        from nimbus.utils.imgui.widgets import UISystem
        system = UISystem(name)
        self.opened_systems[name] = system
        self.system_manager.update_system(system)
        this_dock_id = imgui.get_window_dock_id()
        self.open_system_display(name).force_dock_id = this_dock_id
        self.open_system_edit(name).force_dock_id = this_dock_id
        click.secho(f"Created new system {name}!", fg="green")
        return True

    def delete_system(self, name: str):
        """Deletes the UISystem with the given NAME.

        The system's config is deleted and removed from the UIManager and persisted configs.
        If the system was opened, it is stopped/deleted, and if its Display or Edit window were opened,
        they are closed as well.
        """
        # Delete instantiated system
        system = self.opened_systems.pop(name, None)
        if system is not None:
            system.clear()
        # Delete system config from manager
        self.system_manager.remove_config(name)
        # Remove system windows, if opened
        display_window = self.get_display_window(name)
        if display_window:
            display_window.hide()
        edit_window = self.get_edit_window(name)
        if edit_window:
            edit_window.hide()
        # If system was the selected one, clear that
        if self.data.selected_system == name:
            self.data.selected_system = None
        click.secho(f"Deleted system {name}", fg="green")

    def open_system_display(self, name: str):
        """Opens a System Display window for the system with the given NAME.
        This allows visualization and interaction with the UI System.

        Only works if the window isn't already opened (see `has_display_window`).
        Will use the same opened system instance if available, otherwise will instantiate the system
        and store it."""
        if self.update_opened_system(name) and not self.has_display_window(name):
            window = MonitorDisplaySystemWindow(name, self)
            self.add_child_window(window)
            return window

    def get_display_window(self, name: str):
        """Gets a System Display window for the given system NAME, if opened."""
        for window in self.children:
            if isinstance(window, MonitorDisplaySystemWindow):
                if window.system_name == name:
                    return window

    def has_display_window(self, name: str):
        """Checks if a System Display window for the given system name is already opened."""
        return self.get_display_window(name) is not None

    def open_system_edit(self, name: str):
        """Opens a System Edit window for the system with the given NAME.
        This allow editing of the UISystem.

        If the System Display window is also opened for this same system, then the changes can be seen in real-time.

        Only works if the window isn't already opened (see `has_edit_window`).
        Will use the same opened system instance if available, otherwise will instantiate the system
        and store it.
        """
        if self.update_opened_system(name) and not self.has_edit_window(name):
            window = MonitorEditSystemWindow(name, self)
            self.add_child_window(window)
            return window

    def get_edit_window(self, name: str):
        """Gets a System Edit window for the given system NAME, if opened."""
        for window in self.children:
            if isinstance(window, MonitorEditSystemWindow):
                if window.system_name == name:
                    return window

    def has_edit_window(self, name: str):
        """Checks if a System Edit window for the given system name is already opened."""
        return self.get_edit_window(name) is not None

    def update_opened_system(self, name: str):
        """Checks if the UISystem with the given name is opened (instantiated).

        If it isn't, then the system will be instantiated and stored for use by the Display or Edit windows.

        Args:
            name (str): name of the UISystem to check

        Returns:
            bool: if the system exists (or was successfully instantiated). False if system isn't opened and couldn't
            be instantiated.
        """
        if name in self.opened_systems:
            return True
        config = self.system_manager.get_config(name)
        if config is not None:
            system = config.instantiate()
            self.opened_systems[name] = system
            return True
        return False

    def update_closed_systems(self):
        """Checks for and closes any opened systems that are no longer being used."""
        for name in list(self.opened_systems.keys()):
            if (not self.has_display_window(name)) and (not self.has_edit_window(name)):
                if system := self.opened_systems.pop(name, None):
                    system.save_config()
                    system.clear()


class MonitorMainWindow(windows.BasicWindow):
    """Main sub-window of `MonitorApp`.

    Used mainly when the Monitor is opened in EDIT mode, this allows setting app options, handling available UISystems, and more.
    """

    def __init__(self, parent: SystemMonitorApp):
        super().__init__("Monitor Main")
        self.parent = parent
        self.system_manager = parent.system_manager
        self.can_be_closed = False
        self.new_system_popup = TextInputPopup(
            "Create New System",
            "New UI System Popup",
            "Choose the name for this new UI System.",
            validator=self.validate_new_system_name
        )

    def render(self):
        new_system_name = self.new_system_popup.render()
        if new_system_name is not None:
            self.parent.create_new_system(new_system_name)
            self.new_system_popup.value = ""

        imgui.separator()
        imgui.text("UI Systems:")
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_h | imgui.TableFlags_.resizable
        flags |= imgui.TableFlags_.hideable | imgui.TableFlags_.sortable
        if imgui.begin_table("SystemConfigs", 7, flags):
            imgui.table_setup_scroll_freeze(1, 1)
            imgui.table_setup_column("Name")
            imgui.table_setup_column("Num Nodes")
            imgui.table_setup_column("Main")
            imgui.table_setup_column("Display")
            imgui.table_setup_column("Edit")
            imgui.table_setup_column("Initialized")
            imgui.table_setup_column("Delete")

            imgui.table_headers_row()

            for config in self.system_manager.get_all_configs():
                imgui.push_id(f"table_row_{repr(config)}")
                imgui.table_next_row(0, 1)

                imgui.table_next_column()
                imgui.text(config.name)

                imgui.table_next_column()
                imgui.text(str(config.num_nodes))

                imgui.table_next_column()
                if imgui.radio_button("##", self.parent.data.selected_system == config.name):
                    self.parent.data.selected_system = config.name
                imgui.set_item_tooltip("\n".join([
                    "Selects the 'main' UI System.",
                    "",
                    "The main system is the one used by default by the Monitor app when running in DISPLAY mode.",
                ]))

                imgui.table_next_column()
                if self.parent.has_display_window(config.name):
                    imgui.text_colored(Colors.green, "<DISPLAYED>")
                else:
                    if imgui.button("Open Display"):
                        self.parent.open_system_display(config.name)

                imgui.table_next_column()
                if self.parent.has_edit_window(config.name):
                    imgui.text_colored(Colors.green, "<EDITING>")
                else:
                    if imgui.button("Open Edit"):
                        self.parent.open_system_edit(config.name)

                imgui.table_next_column()
                if config.name in self.parent.opened_systems:
                    imgui.text_colored(Colors.green, "running")
                else:
                    imgui.text("-")

                imgui.table_next_column()
                title = f"Confirm {config.name} System Delete"
                if button_with_confirmation("Delete", title, "Are you sure you want to delete this UISystem config?"):
                    self.parent.delete_system(config.name)

                imgui.pop_id()

            imgui.end_table()

    def validate_new_system_name(self, value: str) -> tuple[bool, str]:
        """Checks if the given value is valid for a new system name.

        Args:
            value (str): possible new UISystem name to check

        Returns:
            tuple[bool, str]: a (valid, reason) tuple, which indicates if the given name is valid
            and the reason why it's invalid.
        """
        if value is None or len(value) <= 0:
            return False, "empty name."
        if self.parent.system_manager.has_config(value):
            return False, f"A System with name '{value}' already exists."
        return True, "valid"


class MonitorDisplaySystemWindow(windows.BasicWindow):
    """Sub-window used by `MonitorApp` to render a UISystem."""

    def __init__(self, system_name: str, parent: SystemMonitorApp):
        super().__init__(f"Display: {system_name}")
        self.user_closable = True
        self.parent = parent
        self.system_name = system_name

    def render(self):
        region_id = repr(self)
        window_flags = imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
        imgui.begin_child(region_id, window_flags=window_flags)
        imgui.push_id(region_id)
        system = self.parent.opened_systems.get(self.system_name)
        if system:
            system.render()
        else:
            imgui.text_colored(Colors.red, "SYSTEM NOT INITIALIZED")
        imgui.pop_id()
        imgui.end_child()


class MonitorEditSystemWindow(windows.BasicWindow):
    """Sub-window used by `MonitorApp` to render a UISystem's EDIT contents (graph, etc)."""

    def __init__(self, system_name: str, parent: SystemMonitorApp):
        super().__init__(f"Edit: {system_name}")
        self.user_closable = True
        self.parent = parent
        self.system_name = system_name
        self._perform_fit = 3

    def render(self):
        region_id = repr(self)
        imgui.begin_child(region_id)
        imgui.push_id(region_id)
        system = self.parent.opened_systems.get(self.system_name)
        if system:
            system.render_edit()
            if self._perform_fit > 0:
                # This is being done for 3 frames since using a boolean to trigger this in a single frame wasn't working on the first time
                # this window was opened in a session.
                system.node_editor.fit_to_window()
                self._perform_fit -= 1
        else:
            imgui.text_colored(Colors.red, "SYSTEM NOT INITIALIZED")
        imgui.pop_id()
        imgui.end_child()
