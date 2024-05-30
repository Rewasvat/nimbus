import clr

# from C# .NET
from System.Reflection import Assembly  # type: ignore

dll_path = __file__.replace("native_api.py", "LibreHardwareMonitorLib.dll")
Assembly.UnsafeLoadFrom(dll_path)

from LibreHardwareMonitor.Hardware import Computer, ISensor, SensorType  # type: ignore
from System import Enum as CEnum  # type: ignore

all_sensor_types = [str(t) for t in CEnum.GetValues(SensorType)]
