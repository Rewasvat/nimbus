import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.actions import Action, input_property, output_property
from nimbus.utils.imgui.nodes import PinKind
from nimbus.utils.imgui.widgets import Board


class SetBoard(Action):
    """Changes the selected child slot in a Board widget to the given name."""

    @input_property()
    def board(self) -> Board:
        """Board to change selected slot."""

    @input_property()
    def slot_name(self) -> str:
        """Name of slot to select in the board."""

    @output_property()
    def success(self) -> bool:
        """If changing selected slot on the board was successful."""

    def execute(self):
        self.success = False
        if self.board and self.slot_name:
            if self.slot_name in self.board.boards:
                self.board.selected_name = self.slot_name
                self.success = True
        self.trigger_flow()

    def _update_slot_name_editor(self, editor: types.StringEditor):
        """Callback to update TypeEditor object from our ``name`` property."""
        if self.board:
            if editor.options is None:
                # Node has just received a Board link.
                if self.slot_name not in self.board.boards:
                    self.slot_name = self.board.selected_name
            editor.options = self.board.boards
        else:
            editor.options = None
