# General utilities methods
# Note: these should be fairly independent and not require import of other nimbus modules, in order to prevent circular references.
import re
import os
import copy
import glob
import click
import importlib
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
    if type(vA) == type(vB):
        if type(vA) == dict:
            check_dict(vA, nameA, vB, nameB)
        elif type(vA) == list:
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
            click.secho(f"Mismatch: Key {key} from {nameA} not in {nameB}")
    for key, bal in dB.items():
        if key in checked_items:
            continue
        # key definately isn't on A
        click.secho(f"Mismatch: Key {key} from {nameB} not in {nameA}")


def str_to_bool(text):
    """Converts a textual value (case insensitive) to a boolean flag.

    This considers if the text itself matches some common flag names and if so returns the
    boolean value that matches that text. Otherwise returns the common Python `bool(text)`
    truthy conversion value.

    Supported flag names:
    * True: `true`, `truthy`, `yes`, `y`
    * False: `false`, `falsy`, `no`, `n`, `none`
    """
    if type(text) == bool:
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
    """A python dict with Lua Table-like functionalities"""

    def get(self, key, default=None):
        value = super().get(key, default)
        if isinstance(value, dict):
            return Table(**value)
        return value

    def __getattr__(self, name: str):
        return self.get(name)

    def __setattr__(self, key: str, value):
        self[key] = value
