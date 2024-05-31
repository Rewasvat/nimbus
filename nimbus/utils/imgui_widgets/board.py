import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import BaseWidget, ContainerWidget, Slot
from imgui_bundle import imgui, ImVec2


class BoardSlot(Slot):
    """Slot for a Board container.

    Allows user-selection of the board's displayed slot through its name.
    """

    def __init__(self, parent: ContainerWidget, name: str):
        super().__init__(parent, name)
        self.parent: Board = parent  # Just to change the type-hint

    @imgui_utils.string_property(imgui.InputTextFlags_.enter_returns_true)
    def name(self) -> str:
        """Name of this slot. User can change this, but it should be unique amongst all slots of this container. [GET/SET]"""
        return self._name

    @name.setter
    def name(self, value):
        was_selected = self.parent.selected_name == self._name
        self._name = value
        if was_selected:
            self.parent.selected_name = value


class Board(ContainerWidget):
    """Table-like container of widgets.

    A board is a simple container widget, containing a ``identifier: child`` dict representing its childs.

    However, at any one time, only one of these childs is active and being displayed, while the others are hidden.
    Having no other UI elements of any kind, the board's contents are exactly that of its active child. So the child
    has the full region of the board to display itself.
    """

    def __init__(self, names: list[str] = None):
        self._slot_class = BoardSlot
        self._slots = [BoardSlot(self, name) for name in (names or ["Default"])]
        self.slot_counter = len(self._slots)
        self._selected_name: str = None  # will be fixed by the update_slots()
        """Name of the selected slot."""
        self.on_slots_changed()

    @property
    def boards(self):
        """The list of available boards. Each board is a slot for a child widget that will take up
        our full available space. However, only a single slot is visible at any one time (see ``selected_name``). [GET]"""
        return [slot.name for slot in self._slots]

    @property
    def selected_slot(self):
        """Gets the selected slot. [GET]"""
        return self.get_slot(self._selected_name)

    @imgui_utils.enum_property([], flags=imgui.SelectableFlags_.dont_close_popups)
    def selected_name(self) -> str:
        """Gets the selected name. Change this to update which slot is displayed. [GET/SET]"""
        return self._selected_name

    @selected_name.setter
    def selected_name(self, value: str):
        for slot in self._slots:
            slot.enabled = slot._name == value
        self._selected_name = value

    def on_slots_changed(self):
        if self._selected_name not in self.boards:
            self._selected_name = self.boards[0] if len(self.boards[0]) > 0 else ""
        self.selected_name = self._selected_name  # to update enabled slots.

    def _update_selected_name_editor(self, editor: imgui_utils.EnumEditor):
        """Method automatically called by our ``selected_name`` enum-property editor in order to dynamically
        update its settings before editing."""
        editor.options = self.boards