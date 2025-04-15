import os
import click
import shutil
import pickle
import traceback
import libasvat.command_utils as cmd_utils
from libasvat.data import DataCache
from imgui_bundle import imgui, immapp


@cmd_utils.main_command_group
class SystemBackupManager(metaclass=cmd_utils.Singleton):
    """BACKUP COMMANDS"""

    def __init__(self):
        self.data = DataCache()
        self.backups: list[Backup] = self.data.get_data("backups", [])

    @cmd_utils.object_identifier
    def name(self):
        return "backup"

    @cmd_utils.sub_groups()
    def get_backups(self):
        return self.backups

    def get_backup_by_name(self, name):
        """Gets the Backup object with the given name"""
        for backup in self.backups:
            if backup.name == name:
                return backup

    def save(self):
        """Saves our data to Nimbus' DataCache"""
        self.data.set_data("backups", self.backups)

    @cmd_utils.instance_command()
    @click.argument("name")
    @click.option("--edit", "-e", is_flag=True, help="Edit config after creation")
    def create_backup(self, name, edit=False):
        """Creates a new Backup object with the given name.

        The backup will have a default configuration, which can be updated by running
        the backup's `edit` command. If EDIT is true, `edit` will be called right after creating
        the backup in order to update it.
        """
        prev = self.get_backup_by_name(name)
        if prev is not None:
            click.secho(f"Can't create backup '{name}'. It already exists.", fg="red")
            return
        # TODO: passar config default
        back = Backup(name)
        self.backups.append(back)
        self.save()
        if edit:
            back.edit()
        return back

    @cmd_utils.instance_command()
    @click.argument("filepath", type=click.Path(exists=True, file_okay=True, dir_okay=False))
    def load_backup(self, filepath):
        """Loads a Backup object from its exported saved file."""
        try:
            with open(filepath, 'rb') as file_obj:
                obj: Backup = pickle.load(file_obj)
        except Exception:
            click.secho(f"Error loading backup '{filepath}': {traceback.format_exc()}", fg="red")
            return
        if not isinstance(obj, Backup):
            click.secho(f"Error loading backup '{filepath}': file is not a valid Backup object.", fg="red")
            return
        prev = self.get_backup_by_name(obj.name)
        if prev is not None:
            click.secho(f"Can't load {obj}' (from '{filepath}'). A backup object with the same name already exists.", fg="red")
            return
        self.backups.append(obj)
        self.save()
        return obj

    def remove_backup(self, backup: 'Backup'):
        """Removes BACKUP from this manager."""
        if backup not in self.backups:
            click.secho(f"Can't remove {backup} since it's not saved.")
            return
        self.backups.remove(backup)
        self.save()


class Backup:
    """Represents a Backup config and features"""

    def __init__(self, name: str, sources: list['Source'] = None, path: str = None):
        self.name = name
        self.sources = sources if sources is not None else []
        self.backup_path: str = path

    @cmd_utils.object_identifier
    def get_name(self):
        return self.name

    @cmd_utils.instance_command()
    def backup(self):
        """Backs up the files from our sources into the backup location."""
        if not os.path.isdir(self.backup_path):
            click.secho(f"{self} location directory doesn't exist", fg="red")
            return
        raise NotImplementedError()
        self.export()

    @cmd_utils.instance_command()
    def restore(self):
        """Restores the files from this backup to their original locations."""
        if not os.path.isdir(self.backup_path):
            click.secho(f"{self} location directory doesn't exist", fg="red")
            return
        raise NotImplementedError()

    @cmd_utils.instance_command()
    def status(self):
        """Checks the status of this backup, verifying the existence and comparing the files
        between the sources and backup location."""
        if not os.path.isdir(self.backup_path):
            click.secho(f"{self} location directory doesn't exist", fg="red")
            return
        raise NotImplementedError()

    @cmd_utils.instance_command()
    @click.confirmation_option(prompt="Are you sure you want to delete this Backup?")
    def delete(self):
        """Deletes this Backup object and all backed-up data."""
        if not os.path.isdir(self.backup_path):
            click.secho(f"{self} location directory doesn't exist", fg="red")
            return
        shutil.rmtree(self.backup_path, ignore_errors=True)
        manager = SystemBackupManager()
        manager.remove_backup(self)
        click.secho(f"Successfully deleted {self}", fg="green")

    @cmd_utils.instance_command()
    def export(self):
        """Exports this backup to a binary file named `<name>BackupObj` in our backup location.

        This can then be used to load the backup config from this file when it can't be loaded
        from Nimbus' DataCache. For example, when restoring in a new computer.
        """
        if not os.path.isdir(self.backup_path):
            click.secho(f"{self} location directory doesn't exist", fg="red")
            return
        export_path = os.path.join(self.backup_path, f"{self.name}BackupObj")
        with open(export_path, 'wb') as file_obj:
            pickle.dump(self, file_obj)
        click.secho(f"Successfully exported {self}", fg="green")

    @cmd_utils.instance_command()
    def edit(self):
        """Opens a GUI to edit this Backup's config."""
        immapp.run(
            gui_function=self.render,
            window_size_auto=True,
            window_title="Nimbus: Backup Config Editor",
            window_restore_previous_geometry=True
        )
        manager = SystemBackupManager()
        manager.save()

    def render(self):
        """TODO"""
        imgui.text("hello world")

    def __str__(self):
        return f"{self.name}Backup"


class Source:
    """A source of files for backing up"""

    def __init__(self, path):
        self.path = path
        self.blacklist = []

    def get_paths(self):
        pass

    def copy(self, backup_path: str):
        """TODO"""
        # os.makedirs(targetPath, exist_ok=True)
        # shutil.copyfile(path, targetFilepath)
        pass

    def restore(self, backup_path: str):
        """TODO"""
        pass

    def compare(self, backup_path: str):
        """TODO"""
        pass
