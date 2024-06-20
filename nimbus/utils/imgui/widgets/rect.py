import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget
from nimbus.utils.imgui.colors import Color, Colors
from nimbus.utils.imgui.nodes_common import input_property
from imgui_bundle import imgui


# TODO: alterar cor de acordo com hovered (clicked talvez? ou só no button?).
class RectMixin:
    """Widget mixin class to add Rect features to a widget."""

    def __init__(self, color: Color = None):
        if color:
            self.color = color
        self._rounding: float = 0.0
        self._is_top_left_round = False
        self._is_top_right_round = False
        self._is_bottom_right_round = False
        self._is_bottom_left_round = False

    @input_property()
    def color(self) -> Color:
        """The color of this rect. [GET/SET]"""
        return Colors.white

    @types.float_property(min=0, max=1, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def rounding(self):
        """Corner rounding value, used when any corner is rounded.

        This is a scaling value, from 0 (no rounding) to 1 (max rounding). The maximum rounding value is half of the minimum
        rect dimension. When using max rounding and both corners of a side of the rect are rounded, that side will form a perfect
        half-circle between the corners. [GET/SET]"""
        return self._rounding

    @rounding.setter
    def rounding(self, value: float):
        self._rounding = value

    @types.bool_property()
    def is_top_left_round(self):
        """If the top-left corner is rounded. [GET/SET]"""
        return self._is_top_left_round

    @is_top_left_round.setter
    def is_top_left_round(self, value: bool):
        self._is_top_left_round = value

    @types.bool_property()
    def is_top_right_round(self):
        """If the top-right corner is rounded. [GET/SET]"""
        return self._is_top_right_round

    @is_top_right_round.setter
    def is_top_right_round(self, value: bool):
        self._is_top_right_round = value

    @types.bool_property()
    def is_bottom_right_round(self):
        """If the bottom-right corner is rounded. [GET/SET]"""
        return self._is_bottom_right_round

    @is_bottom_right_round.setter
    def is_bottom_right_round(self, value: bool):
        self._is_bottom_right_round = value

    @types.bool_property()
    def is_bottom_left_round(self):
        """If the bottom-left corner is rounded. [GET/SET]"""
        return self._is_bottom_left_round

    @is_bottom_left_round.setter
    def is_bottom_left_round(self, value: bool):
        self._is_bottom_left_round = value

    @property
    def actual_rounding(self):
        """Actual value of corner roundness, used for drawing the rectangle.
        This converts our ``self.rounding`` scaling factor to the actual range of pixel values for the rounding. [GET]"""
        max_value = min(self._area.x, self._area.y) * 0.5
        return max_value * self.rounding

    def _draw_rect(self):
        """Internal utility to render our rectangle."""
        draw = imgui.get_window_draw_list()
        flags = self._get_draw_flags()
        draw.add_rect_filled(self.position, self.bottom_right_pos, self.color.u32, self.actual_rounding, flags)

    def _get_draw_flags(self):
        """Gets the imgui ImDrawFlags for our rectangle drawing according to our attributes.

        Returns:
            imgui.ImDrawFlags: drawing flags
        """
        flags = imgui.ImDrawFlags_.round_corners_none
        if self._is_top_left_round:
            flags |= imgui.ImDrawFlags_.round_corners_top_left
        if self._is_top_right_round:
            flags |= imgui.ImDrawFlags_.round_corners_top_right
        if self._is_bottom_right_round:
            flags |= imgui.ImDrawFlags_.round_corners_bottom_right
        if self._is_bottom_left_round:
            flags |= imgui.ImDrawFlags_.round_corners_bottom_left
        return flags


class Rect(RectMixin, LeafWidget):
    """Simple colored Rectangle widget."""

    def __init__(self, color: Color = None):
        LeafWidget.__init__(self)
        RectMixin.__init__(self, color)

    def render(self):
        self._draw_rect()
        self._handle_interaction()
