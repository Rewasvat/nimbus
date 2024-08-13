import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from nimbus.utils.imgui.colors import Color, Colors
from nimbus.utils.imgui.nodes import input_property
from imgui_bundle import imgui
from enum import Flag


class RectCorners(Flag):
    """Corners of the Rectangle that should be rounded.

    This is a FLAG enumeration, so multiple values can be aggregated with ``|``.
    """
    NONE = imgui.ImDrawFlags_.round_corners_none.value
    TOP_LEFT = imgui.ImDrawFlags_.round_corners_top_left.value
    TOP_RIGHT = imgui.ImDrawFlags_.round_corners_top_right.value
    BOTTOM_RIGHT = imgui.ImDrawFlags_.round_corners_bottom_right.value
    BOTTOM_LEFT = imgui.ImDrawFlags_.round_corners_bottom_left.value
    TOP = TOP_LEFT | TOP_RIGHT
    BOTTOM = BOTTOM_LEFT | BOTTOM_RIGHT
    RIGHT = TOP_RIGHT | BOTTOM_RIGHT
    LEFT = TOP_LEFT | BOTTOM_LEFT
    ALL = TOP_LEFT | TOP_RIGHT | BOTTOM_LEFT | BOTTOM_RIGHT

    def get_flags(self) -> imgui.ImDrawFlags_:
        """Gets the value of this RectCorners enum object as a imgui ImDrawFlags value (int)."""
        val = self.value
        if val == 0:
            val = RectCorners.NONE.value
        return val


# TODO: alterar cor de acordo com hovered (clicked talvez? ou só no button?).
class RectMixin:
    """Widget mixin class to add Rect features to a widget."""

    def __init__(self, color: Color = None):
        if color:
            self.color = color
        self._rounding: float = 0.0
        self._corners: RectCorners = RectCorners.NONE

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

    @types.enum_property()
    def corners(self) -> RectCorners:
        """Which corners to round on this rect. [GET/SET]"""
        return self._corners

    @corners.setter
    def corners(self, value: RectCorners):
        self._corners = value

    @property
    def actual_rounding(self):
        """Actual value of corner roundness, used for drawing the rectangle.
        This converts our ``self.rounding`` scaling factor to the actual range of pixel values for the rounding. [GET]"""
        max_value = min(self._area.x, self._area.y) * 0.5
        return max_value * self.rounding

    def _draw_rect(self):
        """Internal utility to render our rectangle."""
        draw = imgui.get_window_draw_list()
        draw.add_rect_filled(self.position, self.bottom_right_pos, self.color.u32, self.actual_rounding, self.corners.get_flags())


class Rect(RectMixin, LeafWidget):
    """Simple colored Rectangle widget."""

    def __init__(self, color: Color = None):
        LeafWidget.__init__(self)
        RectMixin.__init__(self, color)
        self.node_header_color = WidgetColors.Primitives

    def render(self):
        self._draw_rect()
        self._handle_interaction()
