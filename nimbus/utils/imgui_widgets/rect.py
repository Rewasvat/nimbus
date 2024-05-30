import nimbus.utils.imgui as imgui_utils
from nimbus.utils.imgui_widgets.base import LeafWidget
from imgui_bundle import imgui, ImVec2, ImVec4


class RectMixin:
    """Widget mixin class to add Rect features to a widget."""

    def __init__(self, color: ImVec4 = None):
        self._color = color or imgui_utils.Colors.white
        self._rounding: float = 0.0
        self._is_top_left_round = False
        self._is_top_right_round = False
        self._is_bottom_right_round = False
        self._is_bottom_left_round = False

    @imgui_utils.color_property()
    def color(self) -> ImVec4:
        """The color of this rect. [GET/SET]"""
        return self._color

    @color.setter
    def color(self, value: ImVec4):
        self._color = value

    @imgui_utils.float_property(min=0, is_slider=True)
    def rounding(self):
        """Corner rounding value, used when any corner is rounded. This is the length of the (original) corner point to
        the start of the curve, on either side. So the minimum value is 0 (no rounding), and the maximum is ``min(width, height)/2``,
        which means the curve will go to the midpoint of the smallest side. In this maximum case, if both corners on that side are
        rounded, the curve will be a perfect half-circle between them. [GET/SET]"""
        return self._rounding

    @rounding.setter
    def rounding(self, value: float):
        self._rounding = value

    @imgui_utils.bool_property()
    def is_top_left_round(self):
        """If the top-left corner is rounded. [GET/SET]"""
        return self._is_top_left_round

    @is_top_left_round.setter
    def is_top_left_round(self, value: bool):
        self._is_top_left_round = value

    @imgui_utils.bool_property()
    def is_top_right_round(self):
        """If the top-right corner is rounded. [GET/SET]"""
        return self._is_top_right_round

    @is_top_right_round.setter
    def is_top_right_round(self, value: bool):
        self._is_top_right_round = value

    @imgui_utils.bool_property()
    def is_bottom_right_round(self):
        """If the bottom-right corner is rounded. [GET/SET]"""
        return self._is_bottom_right_round

    @is_bottom_right_round.setter
    def is_bottom_right_round(self, value: bool):
        self._is_bottom_right_round = value

    @imgui_utils.bool_property()
    def is_bottom_left_round(self):
        """If the bottom-left corner is rounded. [GET/SET]"""
        return self._is_bottom_left_round

    @is_bottom_left_round.setter
    def is_bottom_left_round(self, value: bool):
        self._is_bottom_left_round = value

    def _draw_rect(self):
        """Internal utility to render our rectangle."""
        draw = imgui.get_window_draw_list()
        flags = self._get_draw_flags()
        color = imgui.get_color_u32(self.color)
        # TODO: alterar cor de acordo com hovered (clicked talvez? ou só no button?).
        draw.add_rect_filled(self.position, self.bottom_right_pos, color, self.rounding, flags)

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

    def _update_rounding_editor(self, editor: imgui_utils.FloatEditor):
        """Method automatically called by our ``rounding`` float-property editor in order to dynamically
        update its settings before editing."""
        editor.max = min(self._area.x, self._area.y) * 0.5


class Rect(RectMixin, LeafWidget):
    """Simple colored Rectangle widget."""

    def __init__(self, color: ImVec4 = None):
        RectMixin.__init__(self, color)

    def render(self):
        self._draw_rect()
        self._handle_interaction()
