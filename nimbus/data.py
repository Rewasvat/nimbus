import os
import click
import pickle
import shutil
import keyring
import platform
import traceback
from nimbus.utils.command_utils import Singleton
from typing import Callable


def safe_pickle_save(file_path: str, data):
    """Saves the given data to the given file-path, using pickle to serialize the data.

    However, this does so in a safe manner. If pickle encounters an error while serializing, the file remains corrupted.
    So this backs up the file, if it existed, and restores it in the case of an error, while printing the error message
    for debugging.

    Args:
        file_path (str): Path to file where data will be serialized.
        data (any): The object to save. It must be pickable.

    Returns:
        bool: if the file was successfully saved.
    """
    backup_path = None
    if os.path.isfile(file_path):
        backup_path = file_path + "_BACKUP"
        shutil.copyfile(file_path, backup_path)

    success = False
    try:
        with open(file_path, 'wb') as file_obj:
            pickle.dump(data, file_obj)
            success = True
    except Exception:
        click.secho(f"Error while trying to save (pickle) object '{data}' to file '{file_path}':\n{traceback.format_exc()}", fg="red")

    if backup_path:
        if not success:
            shutil.copyfile(backup_path, file_path)
            click.secho("The file was restored to its state before trying to pickle.", fg="blue")
        if os.path.isfile(backup_path):
            os.remove(backup_path)
    return success


def update_module_path_in_pickled_object(pickle_path: str, old_module_path: str, new_module):
    """Update a python module's dotted path in a pickle dump if the corresponding file was renamed.

    Implements the advice in https://stackoverflow.com/a/2121918.

    Args:
        pickle_path (str): Path to the pickled object.
        old_module_path (str): The old.dotted.path.to.renamed.module.
        new_module (ModuleType): from new.location import module.
    """
    # NOTE: this might not be working...
    import sys
    sys.modules[old_module_path] = new_module
    dic = pickle.load(open(pickle_path, "rb"))
    del sys.modules[old_module_path]
    pickle.dump(dic, open(pickle_path, "wb"))


# TODO: mover pro UTILS. Idéia é o utils ser uma libzinha de coisas que poderiam ser reusadas em outros projetos.
class DataCache(metaclass=Singleton):
    """Singleton class that holds Nimbus's global state. This can be used by other scripts to store/access
    global data as a kind of cache."""

    def __init__(self):
        self._cache_data: dict[str, any] = None
        """Dict of data of the main cache. This is persisted via pickle to the common nimbus-datacache file."""
        self._custom_data: dict[str, any] = {}
        """Dict of custom data to persist. Each item will be persisted via pickle to a separate cache file, with name
        based on the item's key."""
        self.service_id = "NimbusTool"
        self.shutdown_listeners: list[Callable[[], None]] = []
        self.data_path = ""  # Initialized in 'set_cache_path'
        self.base_path = ""
        self.set_cache_path(os.path.expanduser("~"))

    # TODO: refatorar esses prefixos de chave `nimbus_` como tem aqui e em vários outros lugares (e talvez em outros módulos), pra ser dinamico.
    #   isso facilitaria usar essa classe em outros projetos.
    #   o ideal seria conseguir pegar o nome do projeto/pacote ou aplicativo que tá usando essa lib somehow.
    def set_cache_path(self, path):
        """Sets the folder in which this DataCache instance will save data. This defaults to the user's home folder ('~').
        Files saved have the same name independently of the folder in which they were saved."""
        self.base_path = path
        self.data_path = os.path.join(path, "nimbus_datacache")

    def delete(self):
        """Deletes the data files saved by this DataCache instance in its cache-path.
        NOTE: this will DELETE our data cache, effectively erasing all configuration and stored data used by commands. USE AT OWN RISK."""
        custom_data_keys: set[str] = self.get_data("custom_data_keys", set())
        for custom_key in custom_data_keys:
            custom_cache_path = self._get_custom_cache_path(custom_key)
            if os.path.isfile(custom_cache_path):
                os.remove(custom_cache_path)

        if os.path.isfile(self.data_path):
            os.remove(self.data_path)

    def load_data(self):
        """Loads our internal persisted data cache, if it isn't loaded yet.

        Since data is saved/loaded with pickle, when the cache is loaded, all pickled objects in it will be recreated."""
        if self._cache_data is None:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'rb') as file_obj:
                    self._cache_data = pickle.load(file_obj)
            else:
                self._cache_data = {}
        return self._cache_data

    def get_data(self, key, default=None):
        """Gets a data object from the persisted data cache.
        If the object specified by KEY doesn't exist, DEFAULT is returned instead.

        The first time this is called will load the persisted cache from disk.
        Since data is saved/loaded with pickle, when the cache is loaded, all pickled objects in it will be recreated."""
        self.load_data()
        return self._cache_data.get(key, default)

    def set_data(self, key, value, persist_data=True):
        """Sets a KEY/VALUE pair to the persisted data cache.

        KEY and VALUE must be pickable. KEY is recomended to be a string.
        If PERSIST_DATA is True (the default), this method will also call `save_data()` after setting the new pair.

        If VALUE is None, then the key is deleted from the dict."""
        self.load_data()
        if value is None:
            self._cache_data.pop(key, None)
        else:
            self._cache_data[key] = value
        if persist_data:
            self.save_data()

    def save_data(self):
        """Saves this data cache to disk."""
        if self._cache_data is not None:
            safe_pickle_save(self.data_path, self._cache_data)

    def get_custom_cache(self, key: str, default=None):
        """Gets the custom cache data for the given key.

        Custom caches are data saved to disk in cache files (pickled files) different than our main cache data and each other.
        In essence, each custom cache is saved (pickled) to its own file.

        The first time this is called for a custom cache, it'll be loaded from disk (and thus, its objects will be recreated by pickle).
        Afterwards, the DataCache keeps a local ref of the data, so subsequent calls to this will return the stored object without re-loading
        from disk. ``save_custom_cache()`` changes this stored object while also saving it to disk.

        Args:
            key (str): Key identifying the custom cache.
            default (any, optional): Default object to return in case we don't have the data already loaded and the custom cache doesn't exist
            for loading. Defaults to None.

        Returns:
            any: the object loaded from the custom cache.
        """
        custom_data_keys: set[str] = self.get_data("custom_data_keys", set())
        data = self._custom_data.get(key)
        if data is None and key in custom_data_keys:
            cache_path = self._get_custom_cache_path(key)
            if os.path.isfile(cache_path):
                with open(cache_path, 'rb') as file_obj:
                    data = pickle.load(file_obj)
                self._custom_data[key] = data
            else:
                click.secho(f"[ERROR] Custom Cache file for '{key}' doesn't exist.", fg="red")
        return data or default

    def save_custom_cache(self, key: str, value):
        """Saves the given data in a custom data cache.

        The data is pickled and saves in its own file, separated from our main cache and the other custom caches.

        Args:
            key (str): Key identifying the custom cache. Generated file will have this name, so prefer small keys without spaces or punctuation.
            value (any): Data to be saved. Must be pickable.
        """
        custom_data_keys: set[str] = self.get_data("custom_data_keys", set())
        if value is None:
            self._custom_data.pop(key)
            custom_data_keys.remove(key)
        else:
            self._custom_data[key] = value
            if safe_pickle_save(self._get_custom_cache_path(key), value):
                custom_data_keys.add(key)
        self.set_data("custom_data_keys", custom_data_keys)

    def _get_custom_cache_path(self, key: str):
        """Gets the path for the custom cache file for the given key.

        Args:
            key (str): key of the custom cache data.

        Returns:
            str: path to the file.
        """
        return os.path.join(self.base_path, f"nimbus_customcache_{key}")

    def set_password(self, key, password):
        """Saves a value ("password") in the system's encrypted keyring service.
        This is a form of persisted data as well, but stored on the system itself, not on this DataCache.
        It's not foolproof but provides more security for saving sensitive data than the regular data cache (from methods
        get/set_data)."""
        user_key = f"nimbus_{key}"

        if password is None:
            self.delete_password(key)
        elif platform.system() == "Windows" and len(password) > 1200:
            # Windows Keyring implementation has a issue saving passwords longer than 1280 characters.
            # Something like `win32ctypes.pywin32.pywintypes.error: (1783, 'CredWrite', 'O fragmento de código recebeu dados incorretos')`
            # So we have a workaround here: if in windows, and the password is long, we split it into smaller chunks.
            chunks = [password[i:i+1000] for i in range(0, len(password), 1000)]
            keyring.set_password(self.service_id, f"{user_key}_chunk0", str(len(chunks)))
            for i, chunk in enumerate(chunks):
                chunk_key = f"{user_key}_chunk{i+1}"
                keyring.set_password(self.service_id, chunk_key, chunk)
        else:
            keyring.set_password(self.service_id, user_key, password)

    def delete_password(self, key):
        """Deletes a saved password from the system's encrypted keyring service, that was previously saved with 'set_password'."""
        if self.get_password(key) is not None:
            user_key = f"nimbus_{key}"
            base_chunk_key = f"{user_key}_chunk0"
            num_chunks = keyring.get_password(self.service_id, base_chunk_key)
            if num_chunks is not None:
                for i in range(int(num_chunks)):
                    chunk_key = f"{user_key}_chunk{i+1}"
                    keyring.delete_password(self.service_id, chunk_key)
                keyring.delete_password(self.service_id, base_chunk_key)
            else:
                keyring.delete_password(self.service_id, user_key)

    def get_password(self, key):
        """Gets a value ("password") from the system's encrypted keyring service, that was saved with 'set_password'."""
        user_key = f"nimbus_{key}"

        num_chunks = keyring.get_password(self.service_id, f"{user_key}_chunk0")
        if num_chunks is not None:
            num_chunks = int(num_chunks)
            chunks = []
            for i in range(num_chunks):
                chunk_key = f"{user_key}_chunk{i+1}"
                chunk = keyring.get_password(self.service_id, chunk_key)
                chunks.append(chunk)
            return "".join(chunks)

        return keyring.get_password(self.service_id, user_key)

    def shutdown(self):
        """Performs any actions necessary to release resources and shutdown this DataCache instance.
        Usually this is called by the app before closing, after executing any commands."""
        self.save_data()
        for listener in self.shutdown_listeners:
            listener()

    def add_shutdown_listener(self, listener: Callable[[], None]):
        """Registers the given callable to be called when the DataCache is shut down.

        This method may be used as a decorator.
        """
        self.shutdown_listeners.append(listener)
        return listener
