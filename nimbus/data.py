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


class DataCache(metaclass=Singleton):
    """Singleton class that holds Nimbus's global state. This can be used by other scripts to store/access
    global data as a kind of cache."""

    def __init__(self):
        self._cache_data: dict[str, any] = None
        """Dict of data of the main cache. This is persisted via pickle to the common nimbus-datacache file."""
        self.service_id = "NimbusTool"
        self.shutdown_listeners: list[Callable[[], None]] = []
        self.data_path = ""  # Initialized in 'set_cache_path'
        self.base_path = ""
        self.set_cache_path(os.path.expanduser("~"))

    def set_cache_path(self, path):
        """Sets the folder in which this DataCache instance will save data. This defaults to the user's home folder ('~').
        Files saved have the same name independently of the folder in which they were saved."""
        self.base_path = path
        self.data_path = os.path.join(path, "nimbus_datacache")

    def delete(self):
        """Deletes the data files saved by this DataCache instance in its cache-path.
        NOTE: this will DELETE our data cache, effectively erasing all configuration and stored data used by commands. USE AT OWN RISK."""
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
        """Performs any actions necessary to release resources and shutdown this MaestroState instance.
        Usually this is called by Maestro before closing, after executing any commands."""
        self.save_data()
        for listener in self.shutdown_listeners:
            listener()

    def add_shutdown_listener(self, listener: Callable[[], None]):
        """Registers the given callable to be called when Maestro is shut down.

        This method may be used as a decorator.
        """
        self.shutdown_listeners.append(listener)
        return listener
