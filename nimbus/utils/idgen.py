import nimbus.utils.command_utils as cmd_utils
from nimbus.data import DataCache


class IDGenerator:
    """Unique integer ID generator.

    This class generates a incrementing int value to be used as an ID for other objects.
    Because generated value is always incremented, it'll always be unique for this same IDGenerator instance.
    """

    def __init__(self):
        self._associations: dict[str, int] = {}
        self._last_id: int = 0
        self._recycled: set[int] = set()

    def create(self, name: str = None):
        """Creates and returns a new int ID value.

        Args:
            name (str, optional): a string to identify the ID. If name is valud, and this method creates a new ID, it'll be
            associated (see ``self.associate``) with this name.

        Returns:
            int: a ID value to use, with the following rules (in order of priority):
            * The ID associated with the given name, if any exists.
            * A ID waiting to be recycled, if any exists. This is essentially reusing an ID, but if it was recycled
            (see ``self.recycle``), then nothing should be using it anyway.
            * A new ID value. This creates a new ID.
        """
        if name in self._associations:
            return self._associations[name]
        if len(self._recycled):
            new_id = self._recycled.pop()
        else:
            self._last_id += 1
            new_id = self._last_id
        self.associate(new_id, name)
        return new_id

    def associate(self, id: int, name: str):
        """Associates the given ID to the given name.

        IDs associated with a name can be re-acquired with its name in the ``self.create`` method.
        Associations are persisted with this IDGenerator object, when its saved in the IDManager singleton.

        Args:
            id (int): ID to associate. Must be a valid value that could belong to us (less than our next ID value).
            name (str): Name to associate with the ID. Must be a valid string. Could overwrite previous association for the same name.
        """
        if id and name and id <= self._last_id:
            self._associations[name] = id

    def recycle(self, id: int):
        """Recycles the given ID that we generated.

        When recycled, this ID shouldn't identify any kind of thing. If it had any associations, they are removed.
        Recycled IDs are REUSED by ``self.create`` when generating a new ID.

        Args:
            id (int): ID to recycle. Must be a valid value that could belong to us (less than our next ID value).
        """
        if id and id <= self._last_id:
            # Add to recycled set
            self._recycled.add(id)
            # Remove association
            for name, ass_id in self._associations.copy().items():
                if ass_id == id:
                    self._associations.pop(name)


class IDManager(metaclass=cmd_utils.Singleton):
    """Singleton manager that handles ID Generator objects.

    These are objects that can generate unique integer IDs for the same generator object.
    This manager can persist generators in order for their IDs to remain unique across
    multiple executions of this tool.
    """

    def __init__(self):
        cache = DataCache()
        self._cache_key = "IDManager_Generators"
        self._generators: dict[str, IDGenerator] = cache.get_data(self._cache_key, {})
        cache.add_shutdown_listener(self.on_shutdown)

    def get(self, name: str):
        """Gets the persisted IDGenerator for the given name.

        If a generator doesn't exist for the name, a new instance will be created. If the name is valid,
        the generator object will be saved with this manager, to be persisted for future uses.

        Args:
            name (str): name of generator to get.

        Returns:
            IDGenerator: a ID generator object.
        """
        gen = self._generators.get(name, IDGenerator())
        if name:
            self._generators[name] = gen
        return gen

    def save(self):
        """Saves the data of this IDManager single (all of our ID Generators) do the DataCache."""
        cache = DataCache()
        cache.set_data(self._cache_key, self._generators)

    def on_shutdown(self):
        """Callback for DataCache shutdown."""
        self.save()
