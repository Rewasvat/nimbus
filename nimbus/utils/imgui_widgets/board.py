import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import BaseWidget, ContainerWidget
from imgui_bundle import imgui, ImVec2


class Board(ContainerWidget):
    """Table-like container of widgets.

    A board is a simple container widget, containing a ``identifier: child`` dict representing its childs.

    However, at any one time, only one of these childs is active and being displayed, while the others are hidden.
    Having no other UI elements of any kind, the board's contents are exactly that of its active child. So the child
    has the full region of the board to display itself.
    """

    def __init__(self, names: list[str] = None):
        self._children: dict[str, BaseWidget] = {}
        """Table of slots this board contains."""
        self._selected_name: str = None  # will be fixed by the update_slots()
        """ID of the selected slot (key of ``self.children``)"""
        self.update_slots(names)

    def get_children(self) -> list[BaseWidget]:
        return list(self._children.values())

    @imgui_utils.list_property(imgui_utils.StringEditor(), "default")
    def boards(self):
        """The list of available boards. Each board is a slot for a child widget that will take up
        our full available space. However, only a single slot is visible at any one time (see ``selected_name``).

        Updating this list changes the available slots. Note that this might delete child widgets if its slot was removed. [GET/SET]"""
        return list(self._children.keys())

    @boards.setter
    def boards(self, value: list[str]):
        self.update_slots(value)

    @property
    def selected_child(self):
        """Gets the selected child. Might be none of the slot is empty. [GET]"""
        return self._children.get(self._selected_name)

    @imgui_utils.enum_property([], flags=imgui.SelectableFlags_.dont_close_popups)
    def selected_name(self) -> str:
        """Gets the selected name. Change this to update which slot is displayed. [GET/SET]"""
        return self._selected_name

    @selected_name.setter
    def selected_name(self, value: str):
        if value in self._children:
            self._selected_name = value

    def update_slots(self, new_names: list[str]):
        """Updates our slots with the given new names.

        Any name in NEW_NAMES but not in our current names is made to create a new slot.
        Any namy in our current names but not in NEW_NAMES has its slot deleted.
        Existing names continue unchanged.

        If the selected slot was removed, it will default to the first in names.

        Args:
            new_names (list[str]): the list of slot names this board shall have.
            This will default to ``["Default"]`` if None or empty.
        """
        if new_names is None or len(new_names) <= 0:
            new_names = ["Default"]

        add_names = set(new_names) - set(self.boards)
        remove_names = set(self.boards) - set(new_names)

        for name in add_names:
            # No need to calculate slot area since the board's slots always have the full size of the board
            # However only one of those slots is enabled, so only one will be rendered.
            self._children[name] = None
        for name in remove_names:
            child = self._children.pop(name)  # returns widget that was removed, no need to do anything with it now
            if child is not None:
                child.delete()

        if self._selected_name not in self._children:
            self._selected_name = self.boards[0]
        self.selected_name = self._selected_name  # to update enabled slots.

    def set_child_in_slot(self, child: BaseWidget, name: str):
        """Sets a child widget in one of our slots.

        If the slot already had a child, it'll be deleted.

        Args:
            child (BaseWidget): Child widget to set, reparented to us.
            name (str): Name of the slot (board) to set the child in.

        Returns:
            bool: if the child was successfully added to the slot.
        """
        if name not in self._children:
            return False
        prev_child = self._children.get(name)
        if prev_child is not None:
            prev_child.delete()
        self._children[name] = child
        self.system.register_widget(child)
        child.reparent_to(self)
        return True

    def remove_child(self, child: BaseWidget):
        if super().remove_child(child):
            for name, slot_child in self._children.items():
                if slot_child == child:
                    self._children[name] = None
                    return True
        return False

    def render(self):
        self._handle_interaction()
        self._draw_selected_child()

    def _draw_selected_child(self, slot_pos: ImVec2 = None, slot_size: ImVec2 = None):
        """Renders the currently selected child widget of this board.

        Args:
            slot_pos (ImVec2, optional): Position of the slot (top-left corner), in local units. Defaults to (0,0).
            slot_size (ImVec2, optional): Size of the slot. Defaults to ``imgui.get_content_region_avail()``, which is all available space.
        """
        new_child = self._render_child(self.selected_child, slot_pos=slot_pos, slot_size=slot_size, name=self.selected_name)
        if new_child is not None:
            self.set_child_in_slot(new_child, self.selected_name)

    def _update_selected_name_editor(self, editor: imgui_utils.EnumEditor):
        """Method automatically called by our ``selected_name`` enum-property editor in order to dynamically
        update its settings before editing."""
        editor.options = self.boards
