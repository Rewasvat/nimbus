import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import LeafWidget
from nimbus.utils.imgui_widgets.rect import RectMixin
from nimbus.utils.imgui_widgets.label import TextMixin
from imgui_bundle import imgui, ImVec2, ImVec4


class Button(RectMixin, TextMixin, LeafWidget):
    """A simple button widget.

    Visually, its a ``Rect`` + ``Label`` widget.
    Allows to set a command that will be executed when clicked.
    """

    def __init__(self):
        RectMixin.__init__(self)
        TextMixin.__init__(self)

    def render(self):
        self._draw_rect()
        self._draw_text()
        if self._handle_interaction():
            # TODO: parametrizar comandos!
            print(f"BUTTON {self} CLICKED!")
