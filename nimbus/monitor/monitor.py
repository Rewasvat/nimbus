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


class MonitorAppData:
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
        self.data: MonitorAppData = MonitorAppData()
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


# TODO: ter uma lista de WidgetSystem existente, e ai:
#   - permitir user escolher qual system vai ver/editar
#   - permitir user criar/deletar system (ao deletar um system, reciclar todos nodes/pins/links)
#   - deixar só um system carregado por vez. (vai precisar de algum delete()/clear() no WidgetSystem pra deletar todos seus nodes,
#     pros Sensores limpares os InternalSensor...)
#   - isso pode casar com a idéia de ter um Node que roda um graph internamente, pra poder separar coisas em grafos diferentes.
#     então ai probs seria numa classe-singleton a parte... e melhor pensar melhor nisso.
#       - poderia ter problemas com SensorNodes por exemplo, já que atualmente só pode existir 1 deles por sensor-ID
class WidgetsTestApp(windows.AppWindow):
    """TODO teste pro sistema de Widgets, talvez deletar depois?"""

    def __init__(self):
        super().__init__("Widgets Test", windows.RunnableAppMode.SIMPLE)
        self.show_app_menu = False
        self.show_menu_bar = False
        self.show_status_bar = False
        self.enable_viewports = True
        from nimbus.utils.imgui.widgets import WidgetSystem
        self.system: WidgetSystem = None
        self.elapsed = 0.0

    def render(self):
        if imgui.is_key_pressed(imgui.Key.escape):
            self.close()
        self.system.render()

    def on_init(self):
        super().on_init()
        sensors.ComputerSystem().open()
        from nimbus.utils.imgui.widgets import WidgetSystem
        self.system = WidgetSystem.load_from_cache("Test")

    def on_before_exit(self):
        self.system.save_to_cache()
        super().on_before_exit()
