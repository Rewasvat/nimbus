import nimbus.utils.imgui as imgui_utils
import nimbus.utils.imgui_widgets.actions as actions
from nimbus.utils.imgui_widgets.base import LeafWidget
from nimbus.utils.imgui_widgets.rect import RectMixin
from nimbus.utils.imgui_widgets.label import TextMixin
from imgui_bundle import imgui_node_editor  # type: ignore


class Button(RectMixin, TextMixin, LeafWidget):
    """A simple button widget.

    Visually, its a ``Rect`` + ``Label`` widget.
    Allows to set a command that will be executed when clicked.
    """

    def __init__(self):
        RectMixin.__init__(self)
        TextMixin.__init__(self)
        self._on_clicked = actions.ActionFlow(self, imgui_node_editor.PinKind.output, "On Click")
        self._out_pins = [self._on_clicked]

    def render(self):
        self._draw_rect()
        self._draw_text()
        if self._handle_interaction():
            self._on_clicked.trigger()

    def get_output_pins(self) -> list[imgui_utils.NodePin]:
        return self._out_pins
