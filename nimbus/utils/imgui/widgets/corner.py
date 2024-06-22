import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.math import Vector2
from nimbus.utils.imgui.nodes import input_property
from imgui_bundle import imgui
from enum import Enum


class CornerType(Enum):
    """Enumeration of possible corner types for the Corner widget."""
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"


# TODO: talvez trocar pra usar imgui style var/colors pra definir curvatura e cor?
class Corner(LeafWidget):
    """Colored "corner" UI widget.

    This widget shows a 90 degree rounded corner between a vertical and a horizontal side of its area.
    Optionally the user may define the corner's width/height ratios, which define the amount of width/height
    of its area that will be used to draw the corner. If the ratios are < 1, then the remaining space in the
    inside (or internal) area-corner of this widget is left blank.
    """

    def __init__(self, type=CornerType.TOP_LEFT):
        super().__init__()
        self._type: CornerType = type
        self._width_ratio: float = 0.5
        self._height_ratio: float = 0.5
        self._use_absolute_values: bool = False
        self.node_header_color = WidgetColors.Primitives

    @types.enum_property()
    def type(self) -> CornerType:
        """The type of this corner [GET/SET]"""
        return self._type

    @type.setter
    def type(self, value: CornerType):
        self._type = value

    @types.float_property(max=1.0, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def width_ratio(self):
        """The ratio of our available horizontal space that is used as the corner column width. [GET/SET]

        This is the ratio (in [0,1]) of our area width that will be our column width. If ``self.use_absolute_values``
        is True, then this value will be our column width directly.
        """
        return self._width_ratio

    @width_ratio.setter
    def width_ratio(self, value: float):
        self._width_ratio = value

    @types.float_property(max=1.0, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def height_ratio(self):
        """The ratio of our available vertical space that is used as the corner bar height. [GET/SET]

        This is the ratio (in [0,1]) of our area height that will be our bar height. If ``self.use_absolute_values``
        is True, then this value will be our bar height directly.
        """
        return self._height_ratio

    @height_ratio.setter
    def height_ratio(self, value: float):
        self._height_ratio = value

    @types.bool_property()
    def use_absolute_values(self):
        """If our width/height ratios are absolute values instead of ratios to our area size. [GET/SET]"""
        return self._use_absolute_values

    @use_absolute_values.setter
    def use_absolute_values(self, value: bool):
        self._use_absolute_values = value

    @input_property()
    def color(self) -> Color:
        """The color of the corner [GET/SET]"""
        return Colors.white

    @property
    def size(self):
        """Gets the size of the corner, according to the last frame's available area. [GET]

        * `size.x`: represents the corner column's width - the horizontal space taken by the corner when going up/down.
        * `size.y`: represents the corner bar's height - the vertical space taken by the corner when going left/right.
        """
        size = Vector2(self._width_ratio, self._height_ratio)
        if not self._use_absolute_values:
            size *= self._area
        return size

    @property
    def top_bar_pos(self) -> Vector2:
        """The position of the top corner-point of the bar that would extend horizontally from this corner. [GET]"""
        if self._type == CornerType.TOP_LEFT:
            return self.top_right_pos
        elif self._type == CornerType.TOP_RIGHT:
            return self._pos.copy()
        elif self._type == CornerType.BOTTOM_RIGHT:
            return self.bottom_left_pos - (0, self.size.y)
        elif self._type == CornerType.BOTTOM_LEFT:
            return self.bottom_right_pos - (0, self.size.y)

    @property
    def bottom_bar_pos(self) -> Vector2:
        """The position of the bottom corner-point of the bar that would extend horizontally from this corner. [GET]"""
        return self.top_bar_pos + (0, self.size.y)

    @property
    def left_column_pos(self) -> Vector2:
        """The position of the left corner-point of the column that would extend vertically from this corner. [GET]"""
        if self._type == CornerType.TOP_LEFT:
            return self.bottom_left_pos
        elif self._type == CornerType.TOP_RIGHT:
            return self.bottom_right_pos - (self.size.x, 0)
        elif self._type == CornerType.BOTTOM_RIGHT:
            return self.top_right_pos - (self.size.x, 0)
        elif self._type == CornerType.BOTTOM_LEFT:
            return self._pos.copy()

    @property
    def right_column_pos(self) -> Vector2:
        """The position of the right corner-point of the column that would extend vertically from this corner. [GET]"""
        return self.left_column_pos + (self.size.x, 0)

    @property
    def inner_curve_center_pos(self) -> Vector2:
        """Gets the position of the center of the inner curve's circle [GET]"""
        if self._type == CornerType.TOP_LEFT:
            pos = self.position
        elif self._type == CornerType.TOP_RIGHT:
            pos = self.top_right_pos
        elif self._type == CornerType.BOTTOM_RIGHT:
            pos = self.bottom_right_pos
        elif self._type == CornerType.BOTTOM_LEFT:
            pos = self.bottom_left_pos
        dir = self.corner_direction * -1
        dir.signed_normalize()
        return pos + dir * (self.size + self.inner_curve_radius)

    @property
    def inner_curve_radius(self):
        """Gets the radius of the inner curve [GET]"""
        rest = self._area - self.size
        return min(*rest)

    @property
    def corner_direction(self) -> Vector2:
        """Gets the normalized direction vector pointing away from this corner. Should be at an 45deg angle in 2D. [GET]"""
        if self._type == CornerType.TOP_LEFT:
            dir = Vector2(-1, -1)
        elif self._type == CornerType.TOP_RIGHT:
            dir = Vector2(1, -1)
        elif self._type == CornerType.BOTTOM_RIGHT:
            dir = Vector2(1, 1)
        elif self._type == CornerType.BOTTOM_LEFT:
            dir = Vector2(-1, 1)
        dir.normalize()
        return dir

    def render(self):
        self._draw_corner_path()
        self._handle_interaction()

    def _draw_corner_path(self):
        """Draws the corner visual elements with imgui."""
        draw = imgui.get_window_draw_list()
        pos = self._pos.copy()
        size = self.size
        rest = self._area - size

        small = min(*rest)  # radius of inner (small) curve
        big = small + min(*size)  # radius of outer (large) curve

        if self._type == CornerType.TOP_LEFT:
            flags = imgui.ImDrawFlags_.round_corners_top_left
            small_start = pos + size
            small_end = pos + self._area
        elif self._type == CornerType.TOP_RIGHT:
            flags = imgui.ImDrawFlags_.round_corners_top_right
            small_start = pos + (0, size.y)
            small_end = pos + (rest.x, self._area.y)
        elif self._type == CornerType.BOTTOM_RIGHT:
            flags = imgui.ImDrawFlags_.round_corners_bottom_right
            small_start = pos.copy()
            small_end = pos + rest
        elif self._type == CornerType.BOTTOM_LEFT:
            flags = imgui.ImDrawFlags_.round_corners_bottom_left
            small_start = pos + (size.x, 0)
            small_end = pos + (self._area.x, rest.y)

        draw.add_rect_filled(pos, pos + self._area, self.color.u32, big, flags)
        draw.add_rect_filled(small_start, small_end, Colors.background.u32, small, flags)

    @classmethod
    def get_min_area(cls, width: float, height: float, small: float):
        """Calculates the minimum ("ideal") area size for a corner with the given values.

        If a Corner with the given width/height is drawn in the returned area size,
        its small curve will be the same as the given one.

        Args:
            width (float): The desired width of the corner. That is, the width of the corner's vertical column.
            height (float): The desired height of the corner. That is, the height of the corner's horizontal bar.
            small (float): The desired radius of the corner's small (inner) curve.

        Returns:
            Vector2: size vector depicting the width/height of an area to drawn a Corner with the given desired
            values.
        """
        return Vector2(width+small, height+small)

    def _update_width_ratio_editor(self, editor: types.FloatEditor):
        """Method automatically called by our ``width_ratio`` float-property editor in order to dynamically
        update its settings before editing."""
        if self._use_absolute_values:
            editor.max = self._area.x
        else:
            editor.max = 1.0

    def _update_height_ratio_editor(self, editor: types.FloatEditor):
        """Method automatically called by our ``height_ratio`` float-property editor in order to dynamically
        update its settings before editing."""
        if self._use_absolute_values:
            editor.max = self._area.y
        else:
            editor.max = 1.0
