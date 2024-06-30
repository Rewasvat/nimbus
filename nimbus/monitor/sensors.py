import re
import math
import click
import itertools
import nimbus.utils.command_utils as cmd_utils
from enum import Enum
from dataclasses import dataclass
from typing import Iterator
from nimbus.data import DataCache
from nimbus.monitor.native_api import SensorType, ISensor, Computer
from nimbus.monitor.test_sensor import TestIHardware, TestIComputer
from nimbus.utils.imgui.math import Vector2, multiple_lerp_with_weigths
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.nodes import PinKind, Node, input_property, output_property


# Local implementation of classes wrapping C# types.
# This is to allow us some documentation (intellisense) and some custom logic/API of ours.

# TODO: update dos hardware era feito de forma async (no C#)
class ComputerSystem(metaclass=cmd_utils.Singleton):
    """Singleton class that represents the Computer System we're running from.

    This is the main class from which to access hardware and sensor data from the computer.

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.Computer`` class.
    """

    def __init__(self):
        self._pc: Computer = None
        self.hardwares: list[Hardware] = []
        self.all_sensors: dict[str, InternalSensor] = {}
        self.elapsed_time: float = 0
        """Internal counter of elapsed time, used for ``timed_update()`` (in seconds)."""
        self.update_time: float = 1.0
        """Amount of time that must pass for a ``timed_update()`` call to trigger an actual ``update()`` (in seconds)."""

    def open(self, dummy_test=False):
        """Starts the computer object, allowing us to query its hardware, sensors and more.

        Args:
            dummy_test (bool, optional): If true, will use a dummy internal Computer object, with dummy sensors that simulate actual
            sensors with changing values, for testing sensor-related code without needing to load sensors properly. Defaults to False.
        """
        if len(self.all_sensors) > 0:
            # Was already opened
            return
        if dummy_test:
            self._pc = TestIComputer()
        else:
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
        if not dummy_test:
            self.hardwares.append(Hardware(TestIHardware()))

        self.all_sensors = {sensor.id: sensor for sensor in self.get_all_isensors()}
        click.secho("Initialized Computer", fg="magenta")
        cache = DataCache()
        cache.add_shutdown_listener(self.close)

    def close(self):
        """Stops the computer object, releasing resources.

        This is automatically called on shutdown of Nimbus."""
        if len(self.all_sensors) <= 0:
            # Was already closed
            return
        self._pc.Close()
        click.secho("Closed Computer", fg="magenta")
        self.hardwares.clear()
        self.all_sensors.clear()

    def update(self):
        """Updates our hardware, to update all of our sensors."""
        for hardware in self.hardwares:
            hardware.update()

    def timed_update(self, delta_time: float):
        """Updates our hardware (calls ``self.update()``), but only after a set of time has elapsed.

        This instance stores how much time has elapsed, and updates it with the given ``delta_time``.
        When elapsed time passes the threshold of ``self.update_time``, then ``update()`` is triggered.

        Args:
            delta_time (float): Amount of time passed since the previous call to this method. In seconds.
        """
        self.elapsed_time += delta_time
        if self.elapsed_time >= self.update_time:
            self.update()
            self.elapsed_time = 0

    def get_all_isensors(self) -> list['InternalSensor']:
        """Gets a list of all internal sensors of this system.

        Returns:
            list[InternalSensor]: list of sensors
        """
        if self._pc is None:
            return []

        sensors = []
        for hardware in self.hardwares:
            sensors += list(hardware.get_all_isensors())
        return sensors

    def get_isensor_by_id(self, id_obj: str | ISensor):
        """Gets the sensor with the given ID.

        Args:
            id_obj (str | ISensor): the ID of the sensor to get. Can be an ID str to check, or a native ISensor
            object, in which case we'll use its ID.

        Returns:
            InternalSensor: the InternalSensor object, or None if no sensor exists with the given ID.
        """
        if isinstance(id_obj, str):
            id = id_obj
        elif id_obj is not None:
            id = str(id_obj.Identifier)
        return self.all_sensors.get(id)

    def __iter__(self) -> Iterator['Hardware']:
        return iter(self.hardwares)


# TODO: transformar isso num node? ou melhor: ter action pra pegar os dados de um hardware, ai poderia pegar coisas do HW vindo de um sensor.
class Hardware:
    """Represents a Hardware device on the system.

    Hardware are the "building blocks" of the system: your CPU, GPU, Memory, etc.
    Amongst other things, a hardware may contain Sensors and other "children" sub-Hardware (which are other Hardware objects).

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.IHardware`` interface."""

    def __init__(self, hw, parent: 'Hardware' = None):
        self._parent = parent
        self._hw = hw
        """Internal IHardware object from native C#"""
        self._isensors: list[InternalSensor] = [InternalSensor(s, self) for s in hw.Sensors]
        """Sensors of this hardware. Note that sub-hardware may have other sensors as well."""
        self.children: list[Hardware] = [Hardware(subhw, self) for subhw in hw.SubHardware]
        """Sub-hardwares of this device."""

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

    @property
    def sensors(self):
        """Gets a list of all existing Sensor objects that use a InternalSensor from this hardware."""
        return [isen.sensor for isen in self._isensors if isen.sensor is not None]

    @property
    def isensors(self):
        """Gets a list of the InternalSensors of this hardware.
        Doesn't include sensors from sub-hardware, see ``self.get_all_isensors()`` for that."""
        return self._isensors.copy()

    def update(self):
        """Updates this hardware, updating all of our sensors."""
        if self.enabled:
            self._hw.Update()
            for sensor in self.sensors:
                sensor.update()
            for child in self.children:
                child.update()

    def __iter__(self) -> Iterator['Sensor']:
        return itertools.chain(iter(self.sensors), *(iter(child) for child in self.children))

    def get_all_isensors(self) -> Iterator['InternalSensor']:
        """Returns an iterator of all InternalSensors of this hardware and recursively of all sub-hardware we have."""
        return itertools.chain(iter(self._isensors), *(child.get_all_isensors() for child in self.children))

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

    def __str__(self):
        return f"{self.type} {self.full_name}"


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
    limits: Vector2
    types: set[SensorType]
    value_format: str


class SensorUnit(SensorUnitData, Enum):
    """Enum of all possible Sensor Units.

    Each item also associates its unit to the internal sensor types. A few sensor types share the same unit, while a few
    sensor types have the same unit but on different orders of magnitude (such as Hz and MHz). When possible the unit is from SI.

    Each unit also contains a few other attributes related to it, such as default min/max limits and more.
    """
    VOLTAGE = ("V", Vector2(1, 1.5), {SensorType.Voltage}, "{:.3f}")
    CURRENT = ("A", Vector2(5, 90), {SensorType.Current}, "{:.3f}")
    CLOCK = ("MHz", Vector2(1000, 6000), {SensorType.Clock}, "{:.1f}")
    PERCENT = ("%", Vector2(0, 100), {SensorType.Load, SensorType.Level, SensorType.Control}, "{:.1f}")
    TEMPERATURE = ("°C", Vector2(20, 90), {SensorType.Temperature}, "{:.1f}")
    FAN = ("RPM", Vector2(0, 10000), {SensorType.Fan}, "{:.0f}")
    FLOW = ("L/h", Vector2(), {SensorType.Flow}, "{:.1f}")
    POWER = ("W", Vector2(10, 200), {SensorType.Power}, "{:.1f}")
    DATA = ("GB", Vector2(0, math.inf), {SensorType.Data}, "{:.1f}")
    SMALLDATA = ("MB", Vector2(0, math.inf), {SensorType.SmallData}, "{:.1f}")
    FACTOR = (".", Vector2(-math.inf, math.inf), {SensorType.Factor}, "{:.3f}")
    FREQUENCY = ("Hz", Vector2(0, 4000), {SensorType.Frequency}, "{:.1f}")
    THROUGHPUT = ("B/s", Vector2(0, 1e9), {SensorType.Throughput}, "{:.1f}")
    # TODO: TIMESPAN VALUE FORMAT: no C#, era `{0:g}` que eh "general-short" format do elemento. Aparentemente isso muda de acordo com o tipo.
    # Se for numero normal, seria a mesma coisa. Mas se o valor for um time-span mesmo, ai o resultado eh "[-][d:]h:mm:ss[.FFFFFFF]"
    # Precisa arrumar isso aqui
    TIMESPAN = ("s", Vector2(-math.inf, math.inf), {SensorType.TimeSpan}, "{}")
    ENERGY = ("mWh", Vector2(), {SensorType.Energy}, "{:.0f}")
    UNKNOWN = ("<WAT>", Vector2(), {}, "{}")

    def __str__(self):
        return self.id

    @classmethod
    def from_type(self, stype: str):
        for unit in self:
            if stype in [str(t) for t in unit.types]:
                return unit
        return self.UNKNOWN


class InternalSensor:
    """Represents a single ISensor object from C# for a hardware device.

    This is a simple wrapper of ``LibreHardwareMonitorLib.Hardware.ISensor`` interface, providing some basic identification values.

    A ComputerSystem will always have all of its InternalSensors objects upod loading. Since we contain native C# objects, this class
    can't be pickled.

    A InternalSensor may contain a ref to a single ``Sensor`` object that uses that InternalObject internally for accessing the C# sensor.
    The ``Sensor`` class for the proper API to use sensor data.
    """

    def __init__(self, internal_sensor: ISensor, parent_hw: Hardware):
        # FIXED SENSOR-RELATED ATTRIBUTES
        self.isensor = internal_sensor  # LibreHardwareMonitor.Hardware.ISensor
        """Internal, fixed, ISensor object from LibreHardwareMonitor to access sensor data."""
        self.parent = parent_hw
        """Parent hardware of this sensor."""
        self.unit: SensorUnit = SensorUnit.from_type(self.type)
        """Unit of this sensor, based on its type (usually SI units)."""
        self._sensor: Sensor = None

    @property
    def id(self) -> str:
        """Gets the sensor ID. This uniquely identifies this sensor (and is reasonably human-readable)."""
        return str(self.isensor.Identifier)

    @property
    def name(self) -> str:
        """Gets the sensor name. Some different sensors may have the same name."""
        return str(self.isensor.Name)

    @property
    def type(self) -> str:
        """Gets the type of this sensor. This specifies which kind of data it measures/returns, such
        as Temperature, Power, Frequency, Load, etc"""
        # TODO: trocar isso pra uma enum? ou usar a própria enum do C#? Como funcionaria?
        return str(self.isensor.SensorType)

    @property
    def critical_limits(self):
        """Tries to get the sensor's limits from the ICriticalSensorLimits interface."""
        low = getattr(self.isensor, "CriticalLowLimit", None)
        high = getattr(self.isensor, "CriticalHighLimit", None)
        if low is not None and high is not None:
            # TODO: in C#, we used to cast the ISensor object to ICriticalSensorLimits to see if we could access these attributes.
            #   maybe should've done something like that here? Not sure if this `hasattr` method works...
            #   On the other hand, apparently no sensors implement the Limits interfaces anyway...
            return Vector2(low, high)

    @property
    def basic_limits(self):
        """Tries to get the sensor's limits from the ISensorLimits interface."""
        low = getattr(self.isensor, "LowLimit", None)
        high = getattr(self.isensor, "HighLimit", None)
        if low is not None and high is not None:
            return Vector2(low, high)

    @property
    def sensor(self):
        """Gets the Sensor object associated with this InternalSensor/ID.

        The Sensor object is the proper API for accessing/changing sensor data, while this InternalSensor is only a bare
        ISensor wrapper providing minimal identification values.

        This might be None if no Sensor object is associated. See ``self.create()`` to create and associate a Sensor
        to this InternalSensor.
        """
        return self._sensor

    def create(self):
        """Creates a Sensor object associated with this InternalSensor/ID.

        Returns:
            Sensor: newly created Sensor object, or None if a associated sensor already existed.
            See ``self.sensor`` for getting the associated sensor afterwards.
        """
        if self._sensor:
            return
        self._sensor = Sensor(self.id)
        return self._sensor

    def clear(self):
        """Clears our associated Sensor object, if any.

        This will reset the ID of the Sensor object, and remove it from this InternalSensor.
        """
        if self._sensor:
            self._sensor._isensor = None
            self._sensor = None


class Sensor(Node):
    """Represents a single Sensor for a hardware device.

    A Sensor measures a single numeric value of some kind about the hardware, such as: temperature, power usage, fan speed,
    usage (%), and so on.
    The hardware itself and its drivers provide these values. LibreHardwareMonitorLib uses native APIs to query these values,
    and we can see and use here those that the lib (and your hardware) supports.

    Wraps and builds upon ``LibreHardwareMonitorLib.Hardware.ISensor`` interface.

    This class uses an InternalSensor for accessing the C# ISensor interface for the sensor with its given ID.
    As such, while technically more than one SensorInstance could exist for the same sensor-id, the InternalSensor object
    for said id restricts for a single object at any given time. Creating a new Sensor would reset the ID of the previous sensor
    for that sensor-id.

    However, this class is pickable as a Node should be, and thus can be easily saved to maintain internal sensor user settings.
    """

    def __init__(self, id: str = None):
        super().__init__()
        # FIXED SENSOR-RELATED ATTRIBUTES
        self._isensor: InternalSensor = None
        self._set_id(id)
        # USER-UPDATABLE SENSOR-RELATED ATTRIBUTES
        self.limits_type: SensorLimitsType = SensorLimitsType.AUTO  # TODO: deixar setar via input-pin somehow
        """How to define the sensor's min/max limits."""
        self.custom_limits: Vector2 = None  # TODO: deixar setar via input-pin somehow
        """Custom sensor limits range. Used when ``self.limits_type`` is ``FIXED``. If None, a default limit range, based
        on the sensor's unit will be used."""
        self._enabled: bool = None
        self._minmax_ever: Vector2 = Vector2(math.inf, -math.inf)
        # NODE-RELATED ATTRIBUTES
        self.node_header_color = Color(0.3, 0, 0, 0.6)
        self.node_bg_color = Color(0.2, 0.12, 0.12, 0.75)
        self.node_title = f"{self.hardware.full_name}\n{self.name} {self.type}"
        from nimbus.utils.imgui.actions import ActionFlow
        self._on_update_pin = ActionFlow(self, PinKind.output, "On Update")
        self._on_update_pin.pin_tooltip = "Triggered when this Sensor is updated, getting a new value from the hardware."
        self.add_pin(self._on_update_pin)
        self.create_data_pins_from_properties()

    @property  # TODO: deixar setar via input-pin?
    def enabled(self) -> bool:
        """If this sensor is enabled. [GET/SET]

        When enabled, we can be shown in any GUI, and our parent hardware will be updated in order to update this sensor
        when the SensorSystem is updated.

        This property has an internal flag which might be None (the default).
        * When setting, the value is set to the internal flag and thus might be boolean or None.
        * When getting, if the internal flag is not None, its value is returned.
        * When getting, if the internal flag is None, True will be returned if we're currently active as a node in a Node Editor system.
        Otherwise, returns False.
        """
        if self._enabled is None:
            return self.editor is not None
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool | None):
        self._enabled = value

    @output_property(use_prop_value=True)
    def id(self) -> str:
        """Gets the sensor ID. This uniquely identifies this sensor (and is reasonably human-readable)."""
        return self._isensor and self._isensor.id

    @output_property(use_prop_value=True)
    def name(self) -> str:
        """Gets the sensor name. Some different sensors may have the same name."""
        return self._isensor and self._isensor.name

    @output_property(use_prop_value=True)
    def hardware(self) -> Hardware:
        """Gets the parent hardware of this sensor."""
        return self._isensor and self._isensor.parent

    @output_property(use_prop_value=True)
    def percent_value(self) -> float:
        """Gets the sensor value as a percent (in [0,1]) between the sensor's min/max limits.
        Return is clamped to [0,1] range.

        Always 0 if we have no limits (``self.limits`` is None) or if the difference between the maximum and minimum limits is 0."""
        return self.get_percent_of_value(self.value)

    @output_property(use_prop_value=True)
    def value(self) -> float:
        """The current value of this sensor."""
        return self._isensor and self._isensor.isensor.Value

    @output_property(use_prop_value=True)
    def formatted_value(self) -> str:
        """Gets the sensor's value, but formatted to the common value-format for this sensor's type."""
        try:
            if self.value is not None:
                return self.unit.value_format.format(self.value)
            return "None"
        except Exception:
            click.secho(f"FVALUE CRASH: value='{self.value}' realType='{type(self.value)}' format='{self.unit.value_format}'", fg="red")
            raise

    @output_property(use_prop_value=True)
    def minimum(self) -> float:
        """The minimum value this sensor has reached since measurements started."""
        return self._isensor and self._isensor.isensor.Min or math.inf

    @output_property(use_prop_value=True)
    def maximum(self) -> float:
        """The maximum value this sensor has reached since measurements started."""
        return self._isensor and self._isensor.isensor.Max or -math.inf

    @property
    def value_range(self):
        """Gets the minimum/maximum sensor values as a (min, max) vector2.

        These are the min/max values recorded by the sensor since the start of this our measurement."""
        return Vector2(self.minimum, self.maximum)

    @output_property(use_prop_value=True)
    def type(self) -> str:
        """Gets the type of this sensor. This specifies which kind of data it measures/returns, such
        as Temperature, Power, Frequency, Load, etc"""
        # TODO: trocar isso pra uma enum? ou usar a própria enum do C#? Como funcionaria?
        return self._isensor and self._isensor.type

    @output_property(use_prop_value=True)
    def unit(self) -> SensorUnit:
        """The sensor's unit (usually SI units)."""
        return self._isensor and self._isensor.unit

    @output_property(use_prop_value=True)
    def min_limit(self) -> float:
        """Gets the sensor's minimum limit.

        This is the "theoretical" minimum value of this sensor. If the sensor's value is lower than this, most likely
        the sensor is broken or something is (or will be) really wrong in your computer.

        The limit depends on the Limits Type of this sensor. See ``self.limits_type``.

        For example, percent values shouldn't pass the limit of 0."""
        return self.limits.x

    @output_property(use_prop_value=True)
    def max_limit(self) -> float:
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
    def limits(self, value: Vector2):
        self.custom_limits = value

    @property
    def limits_diff(self):
        """Gets the difference between our minimum and maximum limits.
        Returns 0 if ``self.limits`` is None."""
        if self.limits is None:
            return 0.0
        return self.max_limit - self.min_limit

    @output_property(use_prop_value=True)
    def state_color(self) -> Color:
        """Gets the imgui color of this sensor, based on its current value and limits.

        This uses a few color ranges according to our unit, to interpolate from using ``self.percent_value``
        and generate the final color. Not all units supports this, in which case color defaults to white.
        """
        return self.get_color_for_value(self.value)

    @output_property(use_prop_value=True)
    def minmax_ever(self) -> Vector2:
        """Gets the minimum/maximum sensor values ever recorded as a (min, max) vector2.

        These are the min/max values ever recorded by the sensor, across all times this app was executed.
        Previous min/max values are stored along with user sensor settings to check later."""
        return Vector2(min(self.minimum, self._minmax_ever.x), max(self.maximum, self._minmax_ever.y))

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

    # TODO: virar action
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
        return self._isensor and self._isensor.critical_limits

    def _get_basic_limits(self):
        """Internal method to try to get the sensor's limits from the ISensorLimits interface."""
        return self._isensor and self._isensor.basic_limits

    def _get_custom_limits(self):
        """Internal method to get the sensor's custom (FIXED) limits."""
        return self.custom_limits or (self.unit and self.unit.limits or Vector2())

    def get_settings(self):
        """Gets the settings from this sensor that can be changed by the user. This can then by stored/persisted,
        sent via network or whatever. A (possibly another) Sensor object can then be updated with ``load_settings()`` to
        set these values back to the sensor.

        Returns:
            dict[str,any]: _description_
        """
        def convert_vec(v: Vector2):
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
                    value = Vector2(*value)
                setattr(self, key, value)

    # TODO: virar action
    def get_percent_of_value(self, value: float):
        """Gets the percent of the given value between the sensor's min/max limits.

        Args:
            value (float): any float value to calculate percent. Preferably, a past or expected
            value of the sensor.

        Returns:
            float: the percent value, in the range [0,1]  (clamped).
            Always 0 if we have no limits (``self.limits`` is None) or if the difference between the maximum and minimum limits is 0.
        """
        range = self.limits_diff
        if range == 0.0:
            return 0.0
        factor = (value - self.min_limit) / range
        return min(1.0, max(0.0, factor))

    # TODO: virar action
    def get_color_for_value(self, value: float) -> Color:
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
                (Colors.magenta, 0),
                (Colors.green, 0.0001),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]
        elif self.unit in (SensorUnit.TEMPERATURE, ):
            targets = [
                (Colors.red, 0),
                (Colors.green, 0.001),
                (Colors.yellow, 0.75),
                (Colors.red, 1),
            ]
        elif self.unit in (SensorUnit.POWER, SensorUnit.VOLTAGE, SensorUnit.CURRENT):
            targets = [
                (Colors.green, 0),
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
            return multiple_lerp_with_weigths(targets, self.get_percent_of_value(value))
        return Colors.white

    def update(self):
        """Updates this Sensor object.

        Called by our parent Hardware when he is updated.
        Does nothing if this sensor is not enabled.
        """
        if not self.enabled:
            return
        # TODO: pegar valores dos inputs? (pra atualizar node)
        self._on_update_pin.trigger()

    def delete(self):
        super().delete()
        if self._isensor:
            self._isensor.clear()

    def _set_id(self, id: str):
        """Internal method to reset the ID of this sensor. This changes our InternalSensor object, and therefore may change
        our id, name, type, value and other properties.

        NOTE: this is used internally by Sensor when it is (re)created. Dont call this outside!

        Args:
            id (str): sensor ID to set.
        """
        self._isensor = ComputerSystem().get_isensor_by_id(id)
        if self._isensor:
            self._isensor._sensor = self

    def __getstate__(self):
        state = super().__getstate__()
        state["__picklestate_sensor_id"] = self.id
        state["_isensor"] = None
        return state

    def __setstate__(self, state: dict[str]):
        sensor_id = state.pop("__picklestate_sensor_id")
        super().__setstate__(state)
        self._set_id(sensor_id)
