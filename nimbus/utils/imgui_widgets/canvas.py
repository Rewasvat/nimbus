import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import BaseWidget, ContainerWidget, Slot
from imgui_bundle import imgui, ImVec2, ImVec4


# TODO: permitir drag&drop pra alterar pos dos slots no canvas
# TODO: permitir drag&drop pra alterar size dos slots no canvas (tipo com aqueles markers de canto pra puxar mudar tamanho)
class CanvasSlot(Slot):
    """Slot for a Canvas Container.

    Allows user-selection of the slot's position, size and few other attributes.
    """

    def __init__(self, parent: ContainerWidget, name: str):
        super().__init__(parent, name)
        self.position = (0, 0)
        self.size = parent.slot.area.size * 0.5

    @imgui_utils.string_property(imgui.InputTextFlags_.enter_returns_true)
    def name(self) -> str:
        """Name of this slot. User can change this, but it should be unique amongst all slots of this container. [GET/SET]"""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @imgui_utils.vector2_property(flags=imgui.SliderFlags_.always_clamp)
    def position(self) -> imgui_utils.Vector2:
        """The position of the slot, in local coords. [GET/SET]"""
        return self.area.position - self.parent.position

    @position.setter
    def position(self, value: imgui_utils.Vector2):
        self.area.position = self.parent.position + value

    @imgui_utils.vector2_property(flags=imgui.SliderFlags_.always_clamp)
    def size(self) -> imgui_utils.Vector2:
        """The size of the slot. [GET/SET]"""
        return self.area.size

    @size.setter
    def size(self, value: imgui_utils.Vector2):
        self.area.size = value

    def _update_position_editor(self, editor: imgui_utils.Vector2Editor):
        """Method automatically called by our ``position`` Vector2-property editor in order to dynamically
        update its settings before editing."""
        size = self.parent.slot.area.size
        editor.x_range = (0, size.x)
        editor.y_range = (0, size.y)

    def _update_size_editor(self, editor: imgui_utils.Vector2Editor):
        """Method automatically called by our ``size`` Vector2-property editor in order to dynamically
        update its settings before editing."""
        size = self.parent.slot.area.size
        editor.x_range = (0, size.x)
        editor.y_range = (0, size.y)


class Canvas(ContainerWidget):
    """A Canvas widget container.

    User can control position and size of each slot individually, the container has no logic automatically setting
    the slot's area. Also allows arbitrary number of slots.
    """

    def __init__(self):
        self._slot_class = CanvasSlot

    def update_slots(self):
        # Do not update slots since we let user select their area.
        pass
