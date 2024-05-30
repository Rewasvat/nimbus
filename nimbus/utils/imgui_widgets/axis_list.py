import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import BaseWidget, LeafWidget, ContainerWidget
from imgui_bundle import imgui, ImVec2


# TODO: refatorar pra children ser uma lista de (slice_size, child), tipo um slot mesmo
#   assim facilitaria associar o slice-size com seu slot/child. E mais importante, arrumaria problemas de ao editar os slices e apagar um item,
#   apagar o child errado. Pq atualmente se vc mudar o slices (list[float]) e tirar items de qualquer jeito, vc perde os ultimos childs da lista
#   children, pq não tem como saber qual "index" do slices foi apagado pra tirar o equivalente do children.
# TODO: permitir um separator entre os itens? tipo uma linha, como imgui.separator()
class AxisList(ContainerWidget):
    """List-like container of widgets.

    An AxisList contains and displays a list of child widgets, distributed either horizontally or vertically amongst the container's region.
    By default the space is divided uniformly amongst all childs, but this can be changed so that some children get a larger or lesser slice
    of space.
    """

    def __init__(self, slices: list[float] = None, is_horizontal=False):
        self._children: list[BaseWidget] = []
        """List of children."""
        self._is_horizontal: bool = is_horizontal
        self._margin: float = 0.0
        self._slices: list[float] = []
        self.update_slots(slices)

    def get_children(self) -> list[BaseWidget]:
        return self._children.copy()

    @imgui_utils.bool_property()
    def only_accept_leafs(self) -> bool:
        """If this List only accepts LeafWidgets as children, otherwise accept any BaseWidget. Default is false. [GET/SET]"""
        return self._accepted_child_types[0] == LeafWidget

    @only_accept_leafs.setter
    def only_accept_leafs(self, value: bool):
        if value:
            self._accepted_child_types = [LeafWidget]
        else:
            self._accepted_child_types = [BaseWidget]

    @imgui_utils.float_property()
    def margin(self) -> float:
        """The space between each children, and between the children and our borders. Default is 0. [GET/SET]"""
        return self._margin

    @margin.setter
    def margin(self, value: float):
        self._margin = value

    @imgui_utils.bool_property()
    def is_horizontal(self) -> bool:
        """If this list orders its children horizontally. If not, it'll order them vertically. Default is vertical. [GET/SET]"""
        return self._is_horizontal

    @is_horizontal.setter
    def is_horizontal(self, value: bool):
        self._is_horizontal = value

    @imgui_utils.list_property(imgui_utils.FloatEditor(min=1, flags=imgui.SliderFlags_.always_clamp), 1.0)
    def slices(self):
        """Gets the list of 'slices' of this list.

        Each slice is the size factor for a child slot. So defining the list of slices not only defines
        how many childs this list may have, it also configures how the list space will be divided amongst the slots.

        The sum of all slices correspond to our full size in the axis this list will order children into. So each size
        factor represents the size of that slice in relation to other.

        For example, if all slices are the same number, then the list space will be divided uniformly amongs all childs (which
        is the default). But if using ``2, 1, 1`` slices, the list will have 3 slots, with the first being 50% of the available
        size, while the remaining slots will each be 25% of the available size.
        ``total_space = sum(slices)``

        Note that changing this may cause the deletion of child widgets that were located in removed slots. [GET/SET]
        """
        return self._slices.copy()

    @slices.setter
    def slices(self, value: list[float]):
        self.update_slots(value)

    def update_slots(self, slices: list[float]):
        if slices is None or len(slices) <= 0:
            slices = [1.0]
        # Check if we're setting less slots than we had before, to remove the extra ones.
        while len(self._children) > len(slices):
            child = self._children.pop()  # returns widget that was removed, no need to do anything with it now
            if child is not None:
                child.delete()
        # Check if we're setting more slots than we had before, to add the extra ones.
        while len(self._children) < len(slices):
            self._children.append(None)

        self._slices = slices

    def set_child_in_slot(self, child: BaseWidget, index: int):
        """Sets a child widget in one of our slots.

        If the slot already had a child, it'll be deleted.

        Args:
            child (BaseWidget): Child widget to set, reparented to us.
            index (int): Index of the slot to set the child in.

        Returns:
            bool: if the child was successfully added to the slot.
        """
        if not (0 <= index < len(self._children)):
            return False
        if self.only_accept_leafs and not isinstance(child, LeafWidget):
            return False
        if self._children[index] is not None:
            self._children[index].delete()
        self._children[index] = child
        self.system.register_widget(child)
        child.reparent_to(self)
        return True

    def remove_child(self, child: BaseWidget):
        if not super().remove_child(child):
            return False
        try:
            index = self._children.index(child)
            self._children[index] = None
            return True
        except ValueError:
            pass
        return False

    def render(self):
        current_slices = self._slices.copy()
        current_children = self._children.copy()
        total_slices_size = sum(current_slices)

        axis_size = self._area.x if self._is_horizontal else self._area.y
        axis_size -= self._margin * (len(current_children) + 1)
        piece_size = axis_size / total_slices_size
        pos = self._margin

        self._handle_interaction()

        for i, child in enumerate(current_children):
            slice_size = current_slices[i]
            size = piece_size * slice_size

            if self._is_horizontal:
                slot_pos = ImVec2(pos, self._margin)
                slot_size = ImVec2(max(10, size), max(10, self._area.y - self._margin*2))
            else:
                slot_pos = ImVec2(self._margin, pos)
                slot_size = ImVec2(max(10, self._area.x - self._margin*2), max(10, size))

            new_child = self._render_child(child, slot_pos, slot_size, f"#{i+1}")
            if new_child is not None:
                self.set_child_in_slot(new_child, i)

            pos += size + self._margin
