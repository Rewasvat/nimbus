import os
import pickle
import keyring
from nimbus.utils.command_utils import Singleton


class DataCache(metaclass=Singleton):
    """Singleton class that holds Nimbus's global state. This can be used by other scripts to store/access
    global data as a kind of cache."""

    def __init__(self):
        self.data: dict[str, any] = None
        self.service_id = "NimbusTool"
        self.data_path = ""  # Initialized in 'set_cache_path'
        self.set_cache_path(os.path.expanduser("~"))

    def set_cache_path(self, path):
        """Sets the folder in which this DataCache instance will save data. This defaults to the user's home folder ('~').
        Files saved have the same name independently of the folder in which they were saved."""
        self.data_path = os.path.join(path, "nimbus_datacache")

    def delete(self):
        """Deletes the data files saved by this DataCache instance in its cache-path.
        NOTE: this will DELETE our data cache, effectively erasing all configuration and stored data used by commands. USE AT OWN RISK."""
        if os.path.isfile(self.data_path):
            os.remove(self.data_path)

    def load_data(self):
        """Loads our internal persisted data cache, if it isn't loaded yet."""
        if self.data is None:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'rb') as file_obj:
                    self.data = pickle.load(file_obj)
            else:
                self.data = {}
        return self.data

    def get_data(self, key, default=None):
        """Gets a data object from the persisted data cache.
        If the object specified by KEY doesn't exist, DEFAULT is returned instead.

        The first time this is called will load the persisted cache from disk."""
        self.load_data()
        return self.data.get(key, default)

    def set_data(self, key, value, persist_data=True):
        """Sets a KEY/VALUE pair to the persisted data cache.

        KEY and VALUE must be pickable. KEY is recomended to be a string.
        If PERSIST_DATA is True (the default), this method will also call `save_data()` after setting the new pair.

        If VALUE is None, then the key is deleted from the dict."""
        self.load_data()
        if value is None:
            self.data.pop(key, None)
        else:
            self.data[key] = value
        if persist_data:
            self.save_data()

    def save_data(self):
        """Saves this data cache to disk."""
        if self.data is not None:
            with open(self.data_path, 'wb') as file_obj:
                pickle.dump(self.data, file_obj)

    def set_password(self, key, password):
        """Saves a value ("password") in the system's encrypted keyring service.
        This is a form of persisted data as well, but stored on the system itself, not on this DataCache.
        It's not foolproof but provides more security for saving sensitive data than the regular data cache (from methods
        get/set_data)."""
        user_key = f"nimbus_{key}"

        if password is not None:
            # If password value is something, save it (possibly overwriting previous value).
            keyring.set_password(self.service_id, user_key, password)
        elif self.get_password(key) is not None:
            # If password value is None, but the stored value is something, delete it instead.
            keyring.delete_password(self.service_id, user_key)

    def get_password(self, key):
        """Gets a value ("password") from the system's encrypted keyring service, that was saved with 'set_password'."""
        user_key = f"nimbus_{key}"
        return keyring.get_password(self.service_id, user_key)

    def shutdown(self):
        """Performs any actions necessary to release resources and shutdown this DataCache instance.
        Usually this is called by Nimbus before closing, after executing any commands."""
        pass
