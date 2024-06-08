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
        self.pos_ratio: imgui_utils.Vector2 = imgui_utils.Vector2()
        self.size_ratio: imgui_utils.Vector2 = imgui_utils.Vector2(0.5, 0.5)

    @imgui_utils.string_property(imgui.InputTextFlags_.enter_returns_true)
    def name(self) -> str:
        """Name of this slot. User can change this, but it should be unique amongst all slots of this container. [GET/SET]"""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @imgui_utils.vector2_property(x_range=(0, 1), y_range=(0, 1), flags=imgui.SliderFlags_.always_clamp)
    def position(self) -> imgui_utils.Vector2:
        """The position of the slot, as a ratio of the canvas's size. [GET/SET]"""
        return self.pos_ratio

    @position.setter
    def position(self, value: imgui_utils.Vector2):
        self.pos_ratio = value

    @imgui_utils.vector2_property(x_range=(0, 1), y_range=(0, 1), flags=imgui.SliderFlags_.always_clamp)
    def size(self) -> imgui_utils.Vector2:
        """The size of the slot, as a ratio of the canvas's size. [GET/SET]"""
        return self.size_ratio

    @size.setter
    def size(self, value: imgui_utils.Vector2):
        self.size_ratio = value


class Canvas(ContainerWidget):
    """A Canvas widget container.

    User can control position and size of each slot individually, the container has no logic automatically setting
    the slot's area. Also allows arbitrary number of slots.
    """

    def __init__(self):
        self._slot_class = CanvasSlot

    def update_slots(self):
        for slot in self._slots:
            slot.area.position = self.position + self.area * slot.pos_ratio
            slot.area.size = self.area * slot.size_ratio
