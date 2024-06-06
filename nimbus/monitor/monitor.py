import math
import click
import traceback
import nimbus.utils.imgui as imgui_utils
import nimbus.utils.command_utils as cmd_utils
import nimbus.utils.utils as utils
from nimbus.data import DataCache
import nimbus.monitor.sensors as sensors
from imgui_bundle import imgui


@cmd_utils.main_command_group
class MonitorManager(metaclass=cmd_utils.Singleton):
    """MONITOR COMMANDS"""

    def __init__(self):
        self.computer: sensors.System = None
        """Main System instance for querying hardware and sensor data. Use only after initializing this manager!"""
        cache = DataCache()
        cache.add_shutdown_listener(self.on_shutdown)

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

    def initialize(self):
        """Initializes this manager."""
        self.computer = sensors.System()
        self.computer.open()

    def on_shutdown(self):
        """Callback for when Nimbus is shutdown."""
        if self.computer is not None:
            self.computer.close()

    @cmd_utils.instance_command()
    def teste(self):
        self.initialize()
        self.computer.update()

        for sensor in self.computer.get_all_sensors():
            print(sensor.format("{id} ({unit}) = {limits}"))

    @cmd_utils.instance_command()
    def widgets(self):
        """Opens a debug GUI for testing the Widget System."""
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
            for key, value in vars(data).items():
                if hasattr(self, key):
                    setattr(self, key, value)

        monitor = MonitorManager()
        monitor.computer.setup_user_sensor_settings(self.user_sensor_settings)

    def save(self):
        monitor = MonitorManager()
        self.user_sensor_settings = monitor.computer.check_user_sensor_settings()

        cache = DataCache()
        cache.set_data("monitor_data", self)


class MonitorApp(imgui_utils.AppWindow):
    """System Monitor App.

    This is the main System Monitor App Window, opened by the ``monitor open`` command.
    It opens a GUI that shows the state of the system's sensors, allowing the user to configure
    how to see them, amongst other things.
    """
    # TODO: feature pra user poder "criar" seu sensor:
    #   - podendo juntar valores de sensores diferentes, pra juntar values com algum calculo, tipo média por exemplo
    #   - talvez algo de poder pegar um "sensor" do user? algo pra dar query em algo do user?
    #   * user poderia definir/criar esses custom sensors, e ai usar eles normalmente no Monitor, como se fosse um sensor como os outros.
    # TODO: ter modo de "user custom layout", onde user define quais widgets (com quais sensores) vai aparecer (seria tipo a UI do LCARS)
    # TODO: poder mudar tema pra LCARS
    # TODO: arrumar uso da interface (UI do IMGUI) com touch no monitor touch
    # TODO: arrumar save dos settings da imgui: parece que não ta salvando mudancas de theme, config das colunas da table, e mais umas coisinhas assim

    def __init__(self):
        super().__init__("System Monitor", imgui_utils.RunnableAppMode.SIMPLE)
        self.monitor = MonitorManager()
        self.data: MonitorAppData = MonitorAppData()
        self.elapsed_time: float = 0

    def on_init(self):
        self.monitor.initialize()
        self.data.load()

    def on_before_exit(self):
        self.data.save()
        return super().on_before_exit()

    def update(self):
        # TODO: update dos hardware era feito de forma async (no C#)
        io = imgui.get_io()
        self.elapsed_time += io.delta_time
        if self.elapsed_time >= self.data.update_time:
            self.monitor.computer.update()
            self.elapsed_time = 0

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

            for sensor in self.monitor.computer.get_all_sensors():
                if not sensor.enabled:
                    continue

                imgui.push_style_color(imgui.Col_.text, sensor.state_color)

                imgui.push_id(f"table_row_{sensor.id}")
                imgui.table_next_row(0, 1)

                imgui.table_next_column()  # antes de começar cada coluna
                imgui.text(sensor.hardware.full_name)

                imgui.table_next_column()
                imgui.text(sensor.name)
                imgui.push_style_color(imgui.Col_.text, imgui_utils.Colors.white)
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
            for hardware in self.monitor.computer:
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


class WidgetsTestApp(imgui_utils.AppWindow):
    """TODO teste pro sistema de Widgets, talvez deletar depois?"""

    def __init__(self):
        super().__init__("Widgets Test", imgui_utils.RunnableAppMode.SIMPLE)
        self.show_app_menu = False
        self.show_menu_bar = False
        self.show_status_bar = False
        self.enable_viewports = True
        from nimbus.utils.imgui_widgets import WidgetSystem
        self.root = WidgetSystem()
        self.elapsed = 0.0
        self.create_contents()

    def create_contents(self):
        from nimbus.utils.imgui_widgets import Board, AxisList, Rect, Label, Corner, Panel, ProgressBar
        pnl = Panel()
        self.root.register_widget(pnl)

        brd = Board(["Default", "Other"])
        pnl.content.child = brd

        other = Rect(imgui_utils.Colors.purple)
        other.is_top_rounded = other.is_bottom_rounded = other.is_left_rounded = other.is_right_rounded = True
        other.name = "OtherStuff"
        brd.get_slot("Other").child = other

        list1 = AxisList([1, 1])
        list1.is_horizontal = True
        list1.name = "HoriList"
        brd.get_slot("Default").child = list1
        brd.selected_name = "Default"

        # r1 = Rect(imgui_utils.Colors.red)
        # r1.is_bottom_rounded = True
        # r2 = Rect(imgui_utils.Colors.green)
        # r2.is_top_rounded = True
        r3 = Rect(imgui_utils.Colors.blue)
        r3.name = "BlueRect"
        r3.is_left_rounded = True
        r4 = Rect(imgui_utils.Colors.yellow)
        r4.name = "YellowRect"
        r4.is_right_rounded = True

        col1 = AxisList([1, 1])
        col1.name = "Column1"
        list1.slots[0].child = col1
        # col1.margin = 15
        col1.slots[0].child = ProgressBar()
        c = Corner()
        c.name = "Fukthis"
        col1.slots[1].child = c

        col2 = AxisList([1, 1])
        col2.name = "Column2"
        list1.slots[1].child = col2
        col2.slots[0].child = r3
        col2.slots[1].child = r4

    def render(self):
        if imgui.is_key_pressed(imgui.Key.escape):
            from imgui_bundle import hello_imgui  # type: ignore
            run_params = hello_imgui.get_runner_params()
            run_params.app_shall_exit = True

        # io = imgui.get_io()
        # self.elapsed += io.delta_time
        # if self.elapsed >= 1.0:
        #     num = len(self.root.names)
        #     index = self.root.names.index(self.root.selected_name)
        #     next_index = (index + 1) % num
        #     self.root.selected_name = self.root.names[next_index]
        self.root.render()
