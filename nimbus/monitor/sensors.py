import re
import math
import click
import itertools
from enum import Enum
from dataclasses import dataclass
from typing import Iterator
from imgui_bundle import ImVec2
from nimbus.monitor.native_api import SensorType, all_sensor_types, ISensor, Computer
import nimbus.utils.imgui.math as math_utils
from nimbus.utils.imgui.colors import Colors


# Local implementation of classes wrapping C# types.
# This is to allow us some documentation (intellisense) and some custom logic/API of ours.
class System:
    """Represents the Computer (or System) we're running from.

    This is the main class from which to access hardware and sensor data from the computer.

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.Computer`` class.
    """

    def __init__(self):
        self._pc: Computer = None
        self.hardwares: list[Hardware] = []
        self.all_sensors: dict[str, Sensor] = {}

    def open(self):
        """Starts the computer object, allowing us to query its hardware, sensors and more."""
        self._pc = Computer()
        self._pc.IsCpuEnabled = True
        self._pc.IsGpuEnabled = True
        self._pc.IsMemoryEnabled = True
        self._pc.IsMotherboardEnabled = True
        self._pc.IsStorageEnabled = True
        self._pc.IsNetworkEnabled = True
        # IsControllerEnabled  NOTE: tried this one, apparently was crashing due to missing assembly
        # IsBatteryEnabled
        # IsControllerEnabled
        self._pc.Open()

        for hw in self._pc.Hardware:
            self.hardwares.append(Hardware(hw))

        self.all_sensors = {sensor.id: sensor for sensor in self.get_all_sensors()}

    def close(self):
        """Stops the computer object, releasing resources."""
        self._pc.Close()
        click.secho("Closed Computer", fg="yellow")

    def update(self):
        """Updates our hardware, to update all of our sensors."""
        for hardware in self.hardwares:
            hardware.update()

    def get_all_sensors(self) -> list['Sensor']:
        """Gets a list of all sensors of this system.

        Returns:
            list[Sensor]: list of sensors
        """
        if self._pc is None:
            return []

        sensors = []
        for hardware in self.hardwares:
            sensors += list(hardware)
        return sensors

    def get_sensor_by_id(self, id_obj: str | ISensor):
        """Gets the sensor with the given ID.

        Args:
            id_obj (str | ISensor): the ID of the sensor to get. Can be an ID str to check, or a native ISensor
            object, in which case we'll use its ID.

        Returns:
            Sensor: the Sensor object, or None if no sensor exists with the given ID.
        """
        if isinstance(id_obj, str):
            id = id_obj
        else:
            id = str(id_obj.Identifier)
        return self.all_sensors.get(id)

    def setup_user_sensor_settings(self, settings: dict[str, dict[str, any]]):
        """Load user sensor-settings for all sensors.

        Args:
            settings (dict[str,dict[str,any]]): table of sensor-id => sensor-data.
        """
        for sensor in self.all_sensors.values():
            if sensor.id in settings:
                sensor.load_settings(settings[sensor.id])

    def check_user_sensor_settings(self):
        """Gets a dict with the user's sensor-settings for all sensors.

        Returns:
            dict[str,dict[str,any]]: dict of sensor-id => sensor-data
        """
        return {sensor.id: sensor.get_settings() for sensor in self.all_sensors.values()}

    def __iter__(self) -> Iterator['Hardware']:
        return iter(self.hardwares)


class Hardware:
    """Represents a Hardware device on the system.

    Hardware are the "building blocks" of the system: your CPU, GPU, Memory, etc.
    Amongst other things, a hardware may contain Sensors and other "children" sub-Hardware (which are other Hardware objects).

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.IHardware`` interface."""

    def __init__(self, hw, parent: 'Hardware' = None):
        self._hw = hw
        """Internal IHardware object from native C#"""
        self.sensors: list[Sensor] = [Sensor(s, self) for s in hw.Sensors]
        """Sensors of this hardware. Note that sub-hardware may have other sensors as well."""
        self.children: list[Hardware] = [Hardware(subhw, self) for subhw in hw.SubHardware]
        """Sub-hardwares of this device."""
        self._parent = parent

    @property
    def id(self):
        """Gets the unique identifier of this hardware"""
        return str(self._hw.Identifier)

    @property
    def type(self):
        """Gets the type of this hardware"""
        return str(self._hw.HardwareType)

    @property
    def root_type(self) -> str:
        """Gets the type of our 'root' parent hardware, which is the parent of our parent and so on, until reaching the parent with no parent."""
        if self._parent is not None:
            return self._parent.root_type
        return self.type

    @property
    def name(self):
        """Gets the name of this hardware"""
        return str(self._hw.Name)

    @property
    def full_name(self):
        """Gets the full name of this hardware, which is ``parent_name / our_name``, recursively
        checking all parent hardware up to the root."""
        if self._parent is not None:
            return f"{self._parent.full_name} / {self.name}"
        return self.name

    @property
    def parent(self):
        """Gets the parent hardware of this device. May be None if we don't have a parent (root hardware)."""
        return self._parent

    @property
    def enabled(self):
        """Checks if this hardware is enabled. That is, if at least one of its sensors (recursively through sub-hardware)
        is enabled"""
        for sensor in self:
            if sensor.enabled:
                return True
        return False

    @enabled.setter
    def enabled(self, value: bool):
        """Sets the 'enabled' flag on all of our sensors to the given value.

        Args:
            value (bool): if sensors will be enabled or not
        """
        for sensor in self:
            sensor.enabled = value

    def update(self):
        """Updates this hardware, updating all of our sensors."""
        if self.enabled:
            self._hw.Update()
            for child in self.children:
                child.update()

    def __iter__(self) -> Iterator['Sensor']:
        return itertools.chain(iter(self.sensors), *(iter(child) for child in self.children))

    def get_sensors_by_type(self, stype: str, recursive=False):
        """Gets all of our sensors of the given type.

        Args:
            stype (str): Type of sensors to acquire.
            recursive (bool, optional): If true, will also check sensors of all sub-hardware recursively. Defaults to False.

        Returns:
            list[Sensor]: the sensors of the given type.
        """
        if recursive:
            return [s for s in self if s.type == stype]
        return [s for s in self.sensors if s.type == stype]


class SensorLimitsType(str, Enum):
    """Methods to acquire the min/max limits of a sensor.
    * CRITICAL: limits from sensor's device critical limits (if they exist).
    * LIMITS: limits from sensor's device limits (if they exist).
    * MINMAX: limits are the same as the sensor's measured min/max values (always available).
    * MINMAX_EVER: limits are the same as the sensor's measured min/max values ever, across all times this has been run.
    * FIXED: limits are those set by the user. Defaults to values based on the sensor's unit (always available).
    * AUTO: limits are acquired automatically. Tries getting from the following methods, using the first that is
    available: CRITICAL > LIMITS > FIXED.
    """
    # NOTE: duplicated value's docs in the Enum class doc since at moment in python, we can't programmatically get these docstrings.
    #   How then, you may ask, does VSCode gets them? Magic I tell you!
    CRITICAL = "CRITICAL"
    """Limits from the sensor's ICriticalSensorLimits interface (not all sensors implement this)."""
    LIMITS = "LIMITS"
    """Limits from the sensor's ISensorLimits interface (not all sensors implement this)."""
    MINMAX = "MINMAX"
    """Limits are the same as the sensor's measured min/max values."""
    MINMAX_EVER = "MINMAX_EVER"
    """Limits are the same as the sensor's measured min/max values ever - across all times this sensor was updated and saved."""
    FIXED = "FIXED"
    """Limits are hardcoded in the sensor object. Can be changed by user. Default values are based on the sensor's unit."""
    AUTO = "AUTO"
    """Limits are acquired automatically. The options are checked for availability following a specific order (CRITICAL > LIMITS > FIXED),
    and the first option that is valid will be used. This is the default limits type used."""


@dataclass
class SensorUnitData:
    id: str
    limits: ImVec2
    types: set[SensorType]
    value_format: str


class SensorUnit(SensorUnitData, Enum):
    """Enum of all possible Sensor Units.

    Each item also associates its unit to the internal sensor types. A few sensor types share the same unit, while a few
    sensor types have the same unit but on different orders of magnitude (such as Hz and MHz). When possible the unit is from SI.

    Each unit also contains a few other attributes related to it, such as default min/max limits and more.
    """
    VOLTAGE = ("V", ImVec2(1, 1.5), {SensorType.Voltage}, "{:.3f}")
    CURRENT = ("A", ImVec2(5, 90), {SensorType.Current}, "{:.3f}")
    CLOCK = ("MHz", ImVec2(1000, 6000), {SensorType.Clock}, "{:.1f}")
    PERCENT = ("%", ImVec2(0, 100), {SensorType.Load, SensorType.Level, SensorType.Control}, "{:.1f}")
    TEMPERATURE = ("°C", ImVec2(20, 90), {SensorType.Temperature}, "{:.1f}")
    FAN = ("RPM", ImVec2(0, 10000), {SensorType.Fan}, "{:.0f}")
    FLOW = ("L/h", ImVec2(), {SensorType.Flow}, "{:.1f}")
    POWER = ("W", ImVec2(10, 200), {SensorType.Power}, "{:.1f}")
    DATA = ("GB", ImVec2(0, math.inf), {SensorType.Data}, "{:.1f}")
    SMALLDATA = ("MB", ImVec2(0, math.inf), {SensorType.SmallData}, "{:.1f}")
    FACTOR = (".", ImVec2(-math.inf, math.inf), {SensorType.Factor}, "{:.3f}")
    FREQUENCY = ("Hz", ImVec2(0, 4000), {SensorType.Frequency}, "{:.1f}")
    THROUGHPUT = ("B/s", ImVec2(0, 1e9), {SensorType.Throughput}, "{:.1f}")
    # TODO: TIMESPAN VALUE FORMAT: no C#, era `{0:g}` que eh "general-short" format do elemento. Aparentemente isso muda de acordo com o tipo.
    # Se for numero normal, seria a mesma coisa. Mas se o valor for um time-span mesmo, ai o resultado eh "[-][d:]h:mm:ss[.FFFFFFF]"
    # Precisa arrumar isso aqui
    TIMESPAN = ("s", ImVec2(-math.inf, math.inf), {SensorType.TimeSpan}, "{}")
    ENERGY = ("mWh", ImVec2(), {SensorType.Energy}, "{:.0f}")
    UNKNOWN = ("<WAT>", ImVec2(), {}, "{}")

    def __str__(self):
        return self.id

    @classmethod
    def from_type(self, stype: str):
        for unit in self:
            if stype in [str(t) for t in unit.types]:
                return unit
        return self.UNKNOWN


class Sensor:
    """Represents a single Sensor for a hardware device.

    A Sensor measures a single numeric value of some kind about the hardware, such as: temperature, power usage, fan speed,
    usage (%), and so on.
    The hardware itself and its drivers provide these values. LibreHardwareMonitorLib uses native APIs to query these values,
    and we can see and use here those that the lib (and your hardware) supports.

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.ISensor`` interface.
    """

    def __init__(self, internal_sensor: ISensor, parent_hw: Hardware):
        self._sensor = internal_sensor  # LibreHardwareMonitor.Hardware.ISensor
        self._parent = parent_hw
        self.limits_type: SensorLimitsType = SensorLimitsType.AUTO
        """How to define the sensor's min/max limits."""
        self.custom_limits: ImVec2 = None
        """Custom sensor limits range. Used when ``self.limits_type`` is ``FIXED``. If None, a default limit range, based
        on the sensor's unit will be used."""
        self._unit: SensorUnit = SensorUnit.from_type(self.type)
        self.enabled: bool = True
        """If this sensor is enabled. So it can be shown in any GUI, and its parent hardware will be updated in order to update this sensor."""
        self._minmax_ever: ImVec2 = ImVec2(math.inf, -math.inf)

    @property
    def unit(self):
        """The sensor's unit (usually SI units)."""
        return self._unit

    @property
    def id(self):
        """Gets the sensor ID. This uniquely identifies this sensor (and is reasonably human-readable)."""
        return str(self._sensor.Identifier)

    @property
    def name(self):
        """Gets the sensor name. Some different sensors may have the same name."""
        return str(self._sensor.Name)

    @property
    def hardware(self):
        """Gets the parent hardware of this sensor."""
        return self._parent

    @property
    def value(self) -> float:
        """The current value of this sensor."""
        return self._sensor.Value

    @property
    def formatted_value(self):
        """Gets the sensor's value, but formatted to the common value-format for this sensor's type."""
        try:
            if self.value is not None:
                return self.unit.value_format.format(self.value)
            return "None"
        except Exception:
            click.secho(f"FVALUE CRASH: value='{self.value}' realType='{type(self.value)}' format='{self.unit.value_format}'", fg="red")
            raise

    @property
    def type(self):
        """Gets the type of this sensor. This specifies which kind of data it measures/returns, such
        as Temperature, Power, Frequency, Load, etc"""
        # TODO: trocar isso pra uma enum? ou usar a própria enum do C#? Como funcionaria?
        return str(self._sensor.SensorType)

    @property
    def minimum(self) -> float:
        """The minimun value this sensor has reached since measurements started."""
        return self._sensor.Min

    @property
    def maximum(self) -> float:
        """The maximum value this sensor has reached since measurements started."""
        return self._sensor.Max

    @property
    def value_range(self):
        """Gets the minimum/maximum sensor values as a (min, max) vector2.

        These are the min/max values recorded by the sensor since the start of this our measurement."""
        return ImVec2(self.minimum, self.maximum)

    @property
    def min_limit(self):
        """Gets the sensor's minimum limit.

        This is the "theoretical" minimum value of this sensor. If the sensor's value is lower than this, most likely
        the sensor is broken or something is (or will be) really wrong in your computer.

        The limit depends on the Limits Type of this sensor. See ``self.limits_type``.

        For example, percent values shouldn't pass the limit of 0."""
        return self.limits.x

    @property
    def max_limit(self):
        """Gets the sensor's maximum limit.

        This is the "theoretical" maximum value of this sensor. If the sensor's value is larger than this, most likely
        the sensor is broken or something is (or will be) really wrong in your computer.

        The limit depends on the Limits Type of this sensor. See `self.limits_type`.

        For example, percent values shouldn't pass the limit of 100. Temperatures shouldn't pass the device's set limits
        in order to prevent thermal throttling."""
        return self.limits.y

    @property
    def limits(self):
        """Gets the sensor limits as a (min, max) limit vector2.

        These are the "theoretical" limits of this sensor. If the sensor's value is outside this range, most likely
        the sensor is broken or something is (or will be) really wrong in your computer.

        The limit depends on the Limits Type of this sensor. See ``self.limits_type``.

        For example, percent values shouldn't pass the limit of 100. Temperatures shouldn't pass the device's set limits
        in order to prevent thermal throttling.

        When setting the value of this property, this changes the sensor's user custom limits, which is only used
        when using FIXED limits.
        """
        if self.limits_type == SensorLimitsType.CRITICAL:
            return self._get_critical_limits()
        elif self.limits_type == SensorLimitsType.LIMITS:
            return self._get_basic_limits()
        elif self.limits_type == SensorLimitsType.MINMAX:
            return self.value_range
        elif self.limits_type == SensorLimitsType.MINMAX_EVER:
            return self.minmax_ever
        elif self.limits_type == SensorLimitsType.FIXED:
            return self._get_custom_limits()
        # else is only AUTO
        return self._get_critical_limits() or self._get_basic_limits() or self._get_custom_limits()

    @limits.setter
    def limits(self, value: ImVec2):
        self.custom_limits = value

    @property
    def limits_diff(self):
        if self.value is None or self.limits is None:
            return 0.0
        return self.max_limit - self.min_limit

    @property
    def percent_value(self):
        """Gets the sensor value as a percent (in [0,1]) between the sensor's min/max limits.
        Return is clamped to [0,1] range."""
        return self.get_percent_of_value(self.value)

    @property
    def state_color(self):
        """Gets the imgui color of this sensor, based on its current value and limits.

        This uses a few color ranges according to our unit, to interpolate from using ``self.percent_value``
        and generate the final color. Not all units supports this, in which case color defaults to white.
        """
        return self.get_color_for_value(self.value)

    @property
    def minmax_ever(self):
        """Gets the minimum/maximum sensor values ever recorded as a (min, max) vector2.

        These are the min/max values ever recorded by the sensor, across all times this app was executed.
        Previous min/max values are stored along with user sensor settings to check later."""
        return ImVec2(min(self.minimum, self._minmax_ever.x), max(self.maximum, self._minmax_ever.y))

    def get_attribute(self, key: str):
        """Gets the property of this sensor whose name matches the given key"""
        conversions = {
            "min": "minimum",
            "max": "maximum",
            "identifier": "id",
            "fvalue": "formatted_value"
        }
        key = key.lower()
        key = conversions.get(key, key)
        if hasattr(self, key):
            return getattr(self, key)

    def format(self, format: str):
        """Utility to generate a string of formatted data from this sensor.

        Args:
            format (str): Format of string to generate. ``{key}`` tags in the string are substituted for
            the value of the sensor property ``key``. Any property from this Sensor class can be used.
            The tag can include python format specifiers. For example, to get the sensor's value with 3
            decimal plates: ``{value:.3f}``.

        Returns:
            str: the generated formatted string.
        """
        def replace(m: re.Match):
            pack: str = m.group(1)
            parts = pack.split(":")
            var_name = parts[0]
            if len(parts) <= 1:
                entry_format = "{}"
            else:
                entry_format = f"{{:{parts[1]}}}"
            return entry_format.format(self.get_attribute(var_name))

        return re.sub(r"{([^}]+)}", replace, format)

    def _get_critical_limits(self):
        """Internal method to try to get the sensor's limits from the ICriticalSensorLimits interface."""
        if hasattr(self._sensor, "CriticalLowLimit"):
            # TODO: in C#, we used to cast the ISensor object to ICriticalSensorLimits to see if we could access these attributes.
            #   maybe should've done something like that here? Not sure if this `hasattr` method works...
            #   On the other hand, apparently no sensors implement the Limits interfaces anyway...
            return ImVec2(self._sensor.CriticalLowLimit, self._sensor.CriticalHighLimit)

    def _get_basic_limits(self):
        """Internal method to try to get the sensor's limits from the ISensorLimits interface."""
        if hasattr(self._sensor, "LowLimit"):
            return ImVec2(self._sensor.LowLimit, self._sensor.HighLimit)

    def _get_custom_limits(self):
        """Internal method to get the sensor's custom (FIXED) limits."""
        return self.custom_limits or self.unit.limits

    def get_settings(self):
        """Gets the settings from this sensor that can be changed by the user. This can then by stored/persisted,
        sent via network or whatever. A (possibly another) Sensor object can then be updated with ``load_settings()`` to
        set these values back to the sensor.

        Returns:
            dict[str,any]: _description_
        """
        def convert_vec(v: ImVec2):
            if isinstance(v, tuple):
                return (v[0], v[1])
            return (v.x, v.y) if v is not None else None
        return {
            "enabled": self.enabled,
            "custom_limits": convert_vec(self.custom_limits),
            "limits_type": self.limits_type,
            "_minmax_ever": convert_vec(self._minmax_ever),
        }

    def load_settings(self, data: dict[str, any]):
        """Loads user-persisted settings into this sensor instance.

        Args:
            data (dict[str, any]): settings values to apply to this sensor. Should have been previously acquired with ``sensor.get_settings()``.
        """
        for key, value in data.items():
            if hasattr(self, key):
                vec2_keys = {"custom_limits", "_minmax_ever"}
                if key in vec2_keys and value is not None:
                    value = ImVec2(*value)
                setattr(self, key, value)

    def get_percent_of_value(self, value: float):
        """Gets the percent of the given value between the sensor's min/max limits.

        Args:
            value (float): any float value to calculate percent. Preferably, a past or expected
            value of the sensor.

        Returns:
            float: the percent value, in the range [0,1]  (clamped).
        """
        range = self.limits_diff
        if range == 0.0:
            return 0.0
        factor = (value - self.min_limit) / range
        return min(1.0, max(0.0, factor))

    def get_color_for_value(self, value: float):
        """Gets the imgui color of this sensor, based on the given value and limits.

        This uses a few color ranges according to our unit, to interpolate from using ``self.get_percent_of_value(value)``
        and generate the final color. Not all units supports this, in which case color defaults to white.

        Args:
            value (float): any float value to calculate percent. Preferably, a past or expected
            value of the sensor.

        Returns:
            ImVec4: sensor color based on the value.
        """
        targets = None
        if self.unit in (SensorUnit.PERCENT, SensorUnit.FAN):
            targets = [
                (Colors.purple, 0),
                (Colors.green, 0.0001),
                (Colors.white, 0.5),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]
        elif self.unit in (SensorUnit.TEMPERATURE, ):
            targets = [
                (Colors.red, 0),
                (Colors.green, 0.001),
                (Colors.white, 0.5),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]
        elif self.unit in (SensorUnit.POWER, SensorUnit.VOLTAGE, SensorUnit.CURRENT):
            targets = [
                (Colors.green, 0),
                (Colors.white, 0.5),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]
        elif self.unit in (SensorUnit.THROUGHPUT, SensorUnit.CLOCK):
            targets = [
                (Colors.white, 0),
                (Colors.white, 0.5),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]

        if targets is not None:
            return math_utils.multiple_lerp_with_weigths(targets, self.get_percent_of_value(value))
        return Colors.white
