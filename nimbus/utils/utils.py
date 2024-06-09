# General utilities methods
# Note: these should be fairly independent and not require import of other nimbus modules, in order to prevent circular references.
import re
import os
import copy
import glob
import click
import importlib
import traceback
import subprocess
from collections import namedtuple
from contextlib import contextmanager


MatchTuple = namedtuple("MatchTuple", "first second")


def copy_dict(obj, ignore=set()):
    """Performs a deepcopy of the OBJ's __dict__, while ignoring the attributes defined in the IGNORE set."""
    base = vars(obj)
    keys = set(base.keys())
    keys = keys - ignore
    d = {}
    for k in keys:
        d[k] = copy.deepcopy(base[k])
    return d


def check_value(vA, nameA, vB, nameB):
    """Compares two values `vA` and `vB` and prints differences between them.
    The `nameA` and `nameB` params respectively identify the vA and vB values for printing.

    If values are dicts or lists, this will check the items recursively."""
    if type(vA) is type(vB):
        if type(vA) is dict:
            check_dict(vA, nameA, vB, nameB)
        elif isinstance(vA, list):
            check_list(vA, nameA, vB, nameB)
        elif vA != vB:
            click.secho(f"Mismatch: {nameA}={vA} != {vB}={nameB}")
    else:
        click.secho(f"Mismatch: {nameA} has type {type(vA)}, but has type {type(vB)} in {nameB}")


def check_list(lA, nameA, lB, nameB):
    """Compares two lists `lA` and `lB` and prints differences between them.
    The `nameA` and `nameB` params respectively identify the lA and lB lists for printing.

    This will check the list's items recursively."""
    if len(lA) == len(lB):
        for i, val in enumerate(lA):
            check_value(val, f"{nameA}[{i}]", lB[i], f"{nameB}[{i}]")
    else:
        click.secho(f"Mismatch: lists {nameA} and {nameB} have different sizes: {len(lA)} and {len(lB)}")


def check_dict(dA, nameA, dB, nameB):
    """Compares two dicts `dA` and `dB` and prints differences between them.
    The `nameA` and `nameB` params respectively identify the dA and dB dicts for printing.

    This will check the dict's items recursively."""
    checked_items = []
    for key, val in dA.items():
        checked_items.append(key)
        if key in dB:
            bal = dB[key]
            check_value(val, f"{nameA}[{key}]", bal, f"{nameB}[{key}]")
        else:
            click.secho(f"Mismatch: Key {key} (='{dA[key]}') from {nameA} not in {nameB}")
    for key, bal in dB.items():
        if key in checked_items:
            continue
        # key definately isn't on A
        click.secho(f"Mismatch: Key {key} (='{dB[key]}') from {nameB} not in {nameA}")


def str_to_bool(text):
    """Converts a textual value (case insensitive) to a boolean flag.

    This considers if the text itself matches some common flag names and if so returns the
    boolean value that matches that text. Otherwise returns the common Python `bool(text)`
    truthy conversion value.

    Supported flag names:
    * True: `true`, `truthy`, `yes`, `y`
    * False: `false`, `falsy`, `no`, `n`, `none`
    """
    if isinstance(text, bool):
        return text

    text = text.lower()
    if text in ("false", "falsy", "no", "n", "none"):
        return False
    elif text in ("true", "truthy", "yes", "y"):
        return True
    return bool(text)


def read_tuples_from_file(file_path, pattern):
    """Reads the file given by FILE_PATH, matching regex PATTERN to each line.

    PATTERN should define 2 groups of values to be extracted from a matched line.

    A list of MatchTuples is returned, containing the `(first, second)` value of each matched line.
    """
    with open(file_path) as datafile:
        lines = datafile.readlines()
    pat = re.compile(pattern)
    adapters: list[MatchTuple] = []
    for line in lines:
        match = pat.match(line)
        if match is not None:
            name = match.group(1)
            version = match.group(2)
            adapters.append(MatchTuple(name, version))
    return adapters


@contextmanager
def current_working_dir(path):
    """Context manager that changes the current working directory to the given PATH,
    yields, and then returns to the original CWD when exiting.

    ```python
    with current_working_dir("myPath"):
        # read/write files in myPath
    """
    cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(cwd)


def load_all_modules(modules_path: str, import_path: str = None, ignore_paths=[]):
    """Reads and loads all modules within the given MODULES_PATH folder path.

    This reads all modules in `<modules_path>/*.py` (and internal sub-directories), and tries to load them
    as `<import_path>.<module_name>`.

    IMPORT_PATH then is the python-import-path prefix for the modules in MODULES_PATH. If None (the default),
    the IMPORT_PATH used will be the MODULES_PATH, with path-separators replaced by `.`
    """
    def filter(module):
        if ignore_paths and len(ignore_paths) > 0:
            for ig in ignore_paths:
                if module.startswith(ig):
                    return False
            return True
        return True

    if not os.path.isdir(modules_path):
        return
    if import_path is None:
        import_path = modules_path.replace(os.path.sep, ".")
    modules = glob.glob(os.path.join(modules_path, "**/*.py"), recursive=True)
    prefix = os.path.commonprefix(modules)
    modules = [filepath.replace(prefix, "") for filepath in modules if os.path.isfile(filepath)]
    modules = [name[:-3].replace(os.path.sep, ".") for name in modules if not name.endswith('__init__.py') and name.endswith(".py")]
    modules = [importlib.import_module(f"{import_path}.{name}") for name in modules if filter(name)]
    return modules


class Table(dict):
    """Python Dict subclass to have behavior similar to Lua Tables.

    Notably, values can be accessed as attributes `obj.x` besides as regular dict itens `obj["x"]`.
    These tables are still python dicts so they behave exactly like dicts with extra table-like features.
    """

    def __getattr__(self, key: str):
        # No use of 'self.' here to prevent infinite-recursion of getting attributes
        value = super().get(key, None)
        return convert_to_table(value)

    def __setattr__(self, key: str, value):
        self[key] = value

    def get(self, key, default=None):
        value = super().get(key, default)
        return convert_to_table(value)

    # These get/setstate operators are required to make pickling work properly when the object has a
    # modified getattr op, that may return None
    def __getstate__(self):
        return vars(self)

    def __setstate__(self, d):
        vars(self).update(d)


def convert_to_table(value) -> list | Table:
    """Converts the given value to a Table, if possible.
    For lists, this converts the items."""
    if isinstance(value, dict) and not isinstance(value, Table):
        return Table(**value)
    elif isinstance(value, list):
        return [convert_to_table(item) for item in value]
    return value


def convert_data_table(data: dict[str, str], model: dict[str, type]):
    """Converts a str-only DATA table to a properly typed table, following the definitions in MODEL.

    MODEL is a `key -> type()` dict that defines the type for each key in DATA.
    The `type()` value should be a type/function that receives a string and converts it to the expected type, or raises an exception if
    conversion fails (such as `int`, `float`, `bool`).

    Only the DATA keys defined in MODEL are converted, any other existing keys are maintained in their original string values. As such,
    MODEL may only define the non-string types to convert.

    This returns a Table with the properly typed values. However if any conversion fails, this will return None.
    """
    obj = Table(**copy.deepcopy(data))
    for attribute_name, type in model.items():
        value = obj.get(attribute_name)
        try:
            obj[attribute_name] = type(value)
        except Exception:
            click.secho(f"Error while converting attribute '{attribute_name}' (value '{value}') from Data Table: {traceback.format_exc()}", fg="red")
            return
    return obj


def update_and_sum_dicts(d1: dict[str, list], d2: dict[str, list]) -> dict[str, list]:
    """Updates D1 with D2, but summing up values that exist in both dicts.

    Returns D1.
    """
    for key, values in d2.items():
        if key not in d1:
            d1[key] = values
        else:
            d1[key] += values
    return d1


def is_admin_user(no_prints=False) -> bool:
    """Checks if we're running as an admin/sudo user.

    Returns a boolean indicating if current running user has admin/sudo privileges.
    Otherwise, returns None when user privilege state can't be determined and prints message
    to console indicating it (this can be disabled by passing the NO_PRINTS flag)."""
    import ctypes
    try:
        # This should work on Unix (maybe Macs too?)
        return os.getuid() == 0
    except Exception:
        pass
    try:
        # This should work on Windows
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        pass
    if not no_prints:
        click.secho("Could not determine if we're running as an admin/sudo user.", fg="red")
    return None


def get_connected_device_ip():
    """Gets a connected Android device IP using ADB.

    This gets the IP address of a connected Android device in your local (wireless) network.

    Returns:
        str: the IP address of the connected Android device, or None if the IP couldn't be found.
        In failure cases, a message is printed to the output.
    """
    try:
        cmd = ["adb", "shell", "ip", "-f", "inet", "-br", "a", "show", "wlan0"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.split()
        ip = parts[-1].split("/")[0]
        return ip
    except subprocess.CalledProcessError as e:
        click.secho(f"[ADB] failed with code {e.returncode}: {e.stderr + e.stdout}", fg="red")
    except FileNotFoundError:
        click.secho("[ADB] Couldn't find Android ADB tool", fg="red")
    except Exception as e:
        click.secho(f"[ADB] Unexpected error ({type(e)}): {e}", fg="red")
    return None


class AdvProperty(property):
    """Advanced Property: python @property with an extra ``metadata`` dict, containing values passed in the property decorator.

    See the ``@adv_property`` decorator.
    """

    @property
    def metadata(self) -> dict[str, any]:
        """Gets the metadata dict of this property."""
        return getattr(self, "cls_metadata", {})


def adv_property(metadata: dict[str, any], base_prop=AdvProperty):
    """``@adv_property`` decorator to annotate a function as a class property.

    This property is used/defined in the same way as a regular python ``@property``.
    However, this allows to pass a dict of metadata to associate with this property, and possibly change
    the underlying property class, when using this decorator when creating the property (defining the getter).

    Args:
        metadata (dict[str, any]): dict of metadata to associate with this property.
        base_prop (_type_, optional): Property class to use. Defaults to AdvProperty, which is our base property class
        that supports the ``metadata`` value.
    """
    class SpecificAdvProperty(base_prop):
        cls_metadata = metadata
    return SpecificAdvProperty


def get_all_properties(cls: type) -> dict[str, property]:
    """Gets all ``@property``s of a class. This includes properties of parent classes.

    Args:
        cls (type): The class to get the properties from.

    Returns:
        dict[str, property]: a "property name" => "property object" dict with all properties.
    """
    props = {}
    for kls in reversed(cls.mro()):
        props.update({key: value for key, value in kls.__dict__.items() if isinstance(value, property)})
    return props
