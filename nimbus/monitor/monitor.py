import math
import click
import nimbus.monitor.sensors as sensors
import nimbus.utils.command_utils as cmd_utils
import nimbus.utils.utils as utils
import nimbus.utils.imgui.windows as windows
import nimbus.utils.imgui.general as imgui_utils
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
    def open(self):
        """Opens the System Monitor GUI."""
        if not utils.is_admin_user():
            click.secho("Can't run the System Monitor GUI without admin permissions!", fg="red")
            return
        monitor = MonitorApp()
        monitor.run()

    @cmd_utils.instance_command()
    @click.option("--test", "-t", is_flag=True, help="Use dummy testing sensors")
    def widgets(self, test):
        """Opens a debug GUI for testing the Widget System."""
        if test:
            sensors.ComputerSystem().open(True)
        app = WidgetsTestApp()
        app.run()


class MonitorAppDataOLDIES:
    """Struct containing data and other user settings for the Monitor App window."""

    def __init__(self):
        self.user_sensor_settings: dict[str, dict[str, any]] = {}
        self.update_time: float = 1
        self.show_update_progress: bool = True

    def load(self):
        cache = DataCache()
        data = cache.get_data("monitor_data")
        if data is not None:
            self.__dict__.update(vars(data))

        sensors.ComputerSystem().setup_user_sensor_settings(self.user_sensor_settings)

    def save(self):
        self.user_sensor_settings = sensors.ComputerSystem().check_user_sensor_settings()

        cache = DataCache()
        cache.set_data("monitor_data", self)


class MonitorApp(windows.AppWindow):
    """System Monitor App.

    This is the main System Monitor App Window, opened by the ``monitor open`` command.
    It opens a GUI that shows the state of the system's sensors, allowing the user to configure
    how to see them, amongst other things.
    """
    # TODO: poder mudar tema pra LCARS
    # TODO: arrumar uso da interface (UI do IMGUI) com touch no monitor touch

    def __init__(self):
        super().__init__("System Monitor", windows.RunnableAppMode.SIMPLE)
        self.computer = sensors.ComputerSystem()
        self.data: MonitorAppDataOLDIES = MonitorAppDataOLDIES()
        self.elapsed_time: float = 0

    def on_init(self):
        self.computer.open()
        self.data.load()

    def on_before_exit(self):
        self.data.save()
        return super().on_before_exit()

    def update(self):
        io = imgui.get_io()
        # TODO: precisa setar o update_time do computer.
        self.computer.timed_update(io.delta_time)

    def render(self):
        self.update()

        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_h | imgui.TableFlags_.resizable
        flags |= imgui.TableFlags_.hideable | imgui.TableFlags_.sortable
        if imgui.begin_table("Sensors", 6, flags):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("Hardware")
            imgui.table_setup_column("Sensor")
            imgui.table_setup_column("Type")
            imgui.table_setup_column("Value")
            imgui.table_setup_column("Min")
            imgui.table_setup_column("Max")

            imgui.table_headers_row()

            for sensor in self.computer.get_all_sensors():
                if not sensor.enabled:
                    continue

                imgui.push_style_color(imgui.Col_.text, sensor.state_color)

                imgui.push_id(f"table_row_{sensor.id}")
                imgui.table_next_row(0, 1)

                imgui.table_next_column()  # antes de começar cada coluna
                imgui.text(sensor.hardware.full_name)

                imgui.table_next_column()
                imgui.text(sensor.name)
                imgui.push_style_color(imgui.Col_.text, Colors.white)
                self._draw_sensor_context_menu(sensor)
                imgui.pop_style_color()

                imgui.table_next_column()
                imgui.text(sensor.type)
                imgui.pop_style_color()

                imgui.table_next_column()
                limits = sensor.limits
                range = limits.y - limits.x
                if limits is not None and (not math.isinf(range)) and (not math.isnan(range)) and range > 0:
                    imgui.progress_bar(sensor.percent_value, overlay=sensor.format("{fvalue}{unit}"))
                else:
                    imgui.text(sensor.format("{fvalue}{unit}"))

                # TODO: fazer um display especifico pra sensor, seria basicamente uma barra com 5 markers:
                #   |min-limit  |min |value |max |max-limit
                #   com mudança adequada de cor (de sei la o que) de acordo com estado
                #   possivelmente com labels em cada marker (tipo `min X` e por ai vai)

                imgui.table_next_column()
                imgui.push_style_color(imgui.Col_.text, sensor.get_color_for_value(sensor.minimum))
                imgui.text(sensor.format("{minimum}{unit}"))
                imgui.pop_style_color()

                imgui.table_next_column()
                imgui.push_style_color(imgui.Col_.text, sensor.get_color_for_value(sensor.maximum))
                imgui.text(sensor.format("{maximum}{unit}"))
                imgui.pop_style_color()

                imgui.pop_id()

            imgui.end_table()

    def render_top_menu(self):
        if imgui.begin_menu("Sensors"):
            for hardware in self.computer:
                if not imgui.begin_menu(hardware.name):
                    continue
                imgui.push_id(f"hw_menu_{hardware.id}")

                def draw_hw_sensors(hw: sensors.Hardware):
                    changed, enabled = imgui.checkbox("Toggle All", hw.enabled)
                    if changed:
                        hw.enabled = enabled

                    if len(hw.children):
                        for sub_hw in hw.children:
                            if imgui.begin_menu(sub_hw.name):
                                imgui.push_id(f"sub_hw_menu_{sub_hw.id}")
                                draw_hw_sensors(sub_hw)
                                imgui.pop_id()
                                imgui.end_menu()

                    for sensor_type in sensors.all_sensor_types:
                        all_sensors = hw.get_sensors_by_type(sensor_type)
                        if len(all_sensors) > 0:
                            unit = sensors.SensorUnit.from_type(sensor_type)
                            if imgui.begin_menu(f"{sensor_type} ({unit})"):
                                for sensor in all_sensors:
                                    self._draw_sensor_enable_box(sensor)
                                imgui.end_menu()
                draw_hw_sensors(hardware)

                imgui.pop_id()
                imgui.end_menu()

            imgui.end_menu()

    def render_app_menu_items(self):
        imgui.push_id("UpdateTimeSetting")
        imgui.text("Sensor Update Time: ")
        imgui.same_line()
        changed, update_time = imgui.slider_float("##value", self.data.update_time, 1.0/30, 10.0, "%.3f s")
        if changed:
            self.data.update_time = update_time
        imgui.pop_id()

        imgui.push_id("ShowProgressSetting")
        imgui.text("Show Update Progress: ")
        imgui.same_line()
        changed, show_progress = imgui.checkbox("##value", self.data.show_update_progress)
        if changed:
            self.data.show_update_progress = show_progress
        imgui.pop_id()

    def render_status_bar(self):
        height = imgui.get_text_line_height_with_spacing()
        width = imgui.get_content_region_avail().x

        if self.data.show_update_progress:
            imgui.text("Update Progress:")
            imgui.same_line()
            progress = self.elapsed_time / self.data.update_time
            imgui.progress_bar(progress, (width*0.25, height*0.9), overlay=f"{progress*100:.2f}%")

    def _draw_sensor_enable_box(self, sensor: sensors.Sensor, label: str = None):
        """Renders a checkbox to enable/disable showing the given sensor.

        Args:
            sensor (Sensor): sensor to show.
            label (str, optional): label to show in the checkbox. If not given (the default), shows sensor name.
        """
        imgui.push_id(f"sensor_enable_box_{sensor.id}")
        title = label or sensor.name
        changed, selected = imgui.checkbox(title, sensor.enabled)
        if changed:
            sensor.enabled = selected
        imgui.pop_id()

    def _draw_sensor_context_menu(self, sensor: sensors.Sensor):
        """Renders the context-menu for right-clicking a Sensor.

        Args:
            sensor (Sensor): the sensor
        """
        if not imgui.begin_popup_context_item(sensor.id):
            return

        self._draw_sensor_enable_box(sensor, "Enabled?")

        imgui.separator()
        imgui.text("Sensor Limits:")

        imgui.push_id("SensorLimitTypeCombo")
        if imgui.begin_combo("##", f"Limits Type: {sensor.limits_type.name}"):
            for ltype in sensors.SensorLimitsType:
                if imgui.selectable(ltype.name, ltype == sensor.limits_type)[0]:
                    sensor.limits_type = ltype
                imgui.set_item_tooltip(ltype.__doc__)
            imgui.end_combo()
        imgui.pop_id()

        limits = sensor.limits
        changed, new_min, new_max = imgui.drag_float_range2("##", limits.x, limits.y, flags=imgui.SliderFlags_.always_clamp)
        if changed:
            limits.x = new_min
            limits.y = new_max
            sensor.limits = limits

        if imgui_utils.menu_item("Reset Limits to Default"):
            sensor.limits = None

        imgui.end_popup()


class MonitorAppData:
    """Struct containing data and other user settings for the Monitor App window."""

    def __init__(self):
        self.update_time: float = 1.0
        """Amount of time (in secs) to update sensors."""
        self.selected_system: str = None
        """Name of the selected UISystem to display."""

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


# TODO: ter uma lista de UISystem existente, e ai:
#   - permitir user escolher qual system vai ver/editar
#   - permitir user criar/deletar system (ao deletar um system, reciclar todos nodes/pins/links)
#   - deixar só um system carregado por vez. (vai precisar de algum delete()/clear() no UISystem pra deletar todos seus nodes,
#     pros Sensores limpares os InternalSensor...)
#   - isso pode casar com a idéia de ter um Node que roda um graph internamente, pra poder separar coisas em grafos diferentes.
#     então ai probs seria numa classe-singleton a parte... e melhor pensar melhor nisso.
#       - poderia ter problemas com SensorNodes por exemplo, já que atualmente só pode existir 1 deles por sensor-ID
# TODO: refatorar MonitorApp pra ter 2 modos de display: EDIT e DISPLAY (names pending)
#   * DISPLAY:
#       - unica borderless-window, mostra só o UISystem selecionado.
#           - mostra warning caso nenhum UISystem esteja selecionado, e dropdown pra selecionar um.
#       - Atalho teclado e right-click-menu permitem só dar QUIT e trocar pro modo EDIT.
#       - talvez fullscreen? Se der pode ter setting separado pra ligar isso (e atalho/menu permitem mudar).
#   * EDIT:
#       - uma dockable window, com:
#           * permite viewports, pra poder mover as abas pra fora (criando viewports)
#           - Settings tab:
#               - visualizador/editor de settings gerais do app
#           - Main ou AllSystems tab:
#               - lista todos systems existentes
#                   - permite deletar system
#                   - permite ligar pra editar tal system (abre tab/window nova)
#                   - permite ligar pra visualizar tal system (abre tab/window nova)
#               - permite criar system novo
#               - permite selecionar um system: ou via a lista ou via um dropdown separado
#               * talvez dê pra "mergar" essa tab com a de Settings, já que a de settings deve ser pouca coisa a principio
#           - Visualiza System X tab:
#               - simplesmente faz render() de um system especifico que tá instanciado
#               - user pode fechar essa janela/tab
#           - Edit System X tab:
#               - mostra o edit_render() de um system especifico.
#               - user pode fechar essa janela/tab
#               - ao editar o system, recriar ele na aba de Visualiza X, caso ela exista.
#               - permite salvar o system
#   - COMMAND LINE ARGS:
#       - arg pra forcar abrir em um modo ou outro
#       - arg pra forcar o UISystem selecionado
#   - Pra trocar de um modo pra outro tem que recriar a janela:
#       - salva dados ou valores no objeto, dá close() na janela. Altera attrs da janela, faz um run() de novo.
#       - se fizer um overwrite do run(), daria pra ter tipo um while dentro dele sempre rodando o super.run(), então
#         marcando certo attr/flag e fechando a janela, a nova seria aberta automatico.
class WidgetsTestApp(windows.AppWindow):
    """TODO teste pro sistema de Widgets, talvez deletar depois?"""

    def __init__(self):
        self._in_edit_mode = True
        super().__init__("System Monitor", windows.RunnableAppMode.DOCK)
        self.data = MonitorAppData.load()
        self._reset_window_attrs()
        from nimbus.utils.imgui.widgets import UISystem, UIManager
        self.system_manager = UIManager()
        self.system: UISystem = None
        self.opened_systems: dict[str, UISystem] = {}
        self.children.append(MonitorMainWindow(self))

    def _reset_window_attrs(self):
        """Sets Basic/AppWindow attributes we inherit."""
        self.mode = windows.RunnableAppMode.DOCK if self._in_edit_mode else windows.RunnableAppMode.SIMPLE
        self.show_app_menu = self._in_edit_mode
        self.show_menu_bar = self._in_edit_mode
        self.show_status_bar = self._in_edit_mode
        self.enable_viewports = self._in_edit_mode

    def render(self):
        if imgui.is_key_pressed(imgui.Key.escape):
            self.close()
        if self._in_edit_mode:
            self.update_closed_systems()
            super().render()
        else:
            # TODO: this
            if self.system is not None:
                sensors.ComputerSystem().timed_update(self.system._root_node.delta_time)  # TODO: melhorar daonde/como pega esse deltaT
                self.system.render()

    def on_init(self):
        super().on_init()
        computer = sensors.ComputerSystem()
        computer.open()
        computer.update_time = self.data.update_time
        if not self._in_edit_mode:
            # selected_config = self.system_manager.get_config(self.data.selected_system)
            # if selected_config is not None:
            #     self.system = selected_config.instantiate()
            pass  # TODO: display mode initialization

    def on_before_exit(self):
        for system in self.opened_systems.values():
            system.save_config()
        self.system_manager.save()
        # TODO: persistir systems abertos pra edicao/display?
        self.data.save()
        super().on_before_exit()

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
        self.open_system_display(name)
        self.open_system_edit(name)
        click.secho(f"Created new system {name}!", fg="green")
        return True

    def delete_system(self, name: str):
        """Deletes the UISystem with the given NAME.

        The system's config is deleted and removed from the UIManager and persisted configs.
        If the system was opened, it is stopped/deleted, and if its Display or Edit window were opened,
        they are closed as well.
        """
        # Delete instantiated system
        self.opened_systems.pop(name, None)
        # Delete system config from manager
        self.system_manager.remove_config(name)
        # Remove system windows, if opened
        display_window = self.get_display_window(name)
        if display_window:
            display_window.hide()
        edit_window = self.get_edit_window(name)
        if edit_window:
            edit_window.hide()
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
            window.force_dock_id = imgui.get_window_dock_id()

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
            window.force_dock_id = imgui.get_window_dock_id()

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


class MonitorMainWindow(windows.BasicWindow):
    """Main sub-window of `MonitorApp`.

    Used mainly when the Monitor is opened in EDIT mode, this allows setting app options, handling available UISystems, and more.
    """

    def __init__(self, parent: WidgetsTestApp):
        super().__init__("Monitor Main")
        self.parent = parent
        self.system_manager = parent.system_manager
        self._new_system_name = ""
        self.can_be_closed = False

    def render(self):
        # TODO: refatorar esse esquema de criar sistemas pra ser um popup pra selecionar nome, mostrar se é valido ou não, e criar ou desistir.
        #   - fazer um comando genérico que permita fazer esses popups de input de str seria util (como tem na Tapps)
        imgui.text("New System Name:")
        imgui.same_line()
        self._new_system_name = imgui.input_text("##", self._new_system_name)[1]
        imgui.same_line()
        if imgui.button("Create New System"):
            if self.parent.create_new_system(self._new_system_name):
                self._new_system_name = ""

        imgui.separator()
        imgui.text("UI Systems:")
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_h | imgui.TableFlags_.resizable
        flags |= imgui.TableFlags_.hideable | imgui.TableFlags_.sortable
        if imgui.begin_table("SystemConfigs", 6, flags):
            imgui.table_setup_scroll_freeze(1, 1)
            imgui.table_setup_column("Name")
            imgui.table_setup_column("Num Nodes")
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
                if imgui.button("Delete"):
                    # TODO: confirmation-popup pra isso
                    self.parent.delete_system(config.name)

                imgui.pop_id()

            imgui.end_table()


class MonitorDisplaySystemWindow(windows.BasicWindow):
    """Sub-window used by `MonitorApp` to render a UISystem."""

    def __init__(self, system_name: str, parent: WidgetsTestApp):
        super().__init__(f"Display: {system_name}")
        # self.remember_is_visible = False
        self.user_closable = True
        self.parent = parent
        self.system_name = system_name

    def render(self):
        region_id = repr(self)
        imgui.begin_child(region_id)
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

    def __init__(self, system_name: str, parent: WidgetsTestApp):
        super().__init__(f"Edit: {system_name}")
        # self.remember_is_visible = False
        self.user_closable = True
        self.parent = parent
        self.system_name = system_name
        self._perform_fit = True

    def render(self):
        region_id = repr(self)
        imgui.begin_child(region_id)
        imgui.push_id(region_id)
        system = self.parent.opened_systems.get(self.system_name)
        if system:
            system.render_edit()
            if self._perform_fit:
                system.node_editor.fit_to_window()
                self._perform_fit = False
        else:
            imgui.text_colored(Colors.red, "SYSTEM NOT INITIALIZED")
        imgui.pop_id()
        imgui.end_child()
