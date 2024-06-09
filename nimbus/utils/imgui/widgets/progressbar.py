import math
import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget
from nimbus.utils.imgui.widgets.rect import RectMixin
from nimbus.utils.imgui.widgets.label import TextMixin
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.math import Vector2
from imgui_bundle import imgui
from enum import Enum


class BarType(Enum):
    """Type of Progress Bar."""
    HORIZONTAL = "Bar is a rect, filled in the horizontal (left -> right) direction."
    INVERTED_HORIZONTAL = "Bar is a rect, filled in the inverted horizontal (right -> left) direction."
    VERTICAL = "Bar is a rect, filled in the vertical (top -> bottom) direction."
    INVERTED_VERTICAL = "Bar is a rect, filled in the inverted vertical (bottom -> top) direction."
    CIRCLE = "Bar is a circle, filled in a clockwise direction."
    ANTI_CIRCLE = "Bar is a circle, filled in a anti-clockwise direction."


# TODO: rounded rect bars ta quebrado qdo valor é pequeno (tamanho proximo da borda inicial da barra, se borda inicial tiver curva).
# TODO: circle bars fica com uma pequena fresta entre as duas metades da barra...
class ProgressBar(RectMixin, TextMixin, LeafWidget):
    """A Progress Bar widget.

    Shows a shape (according to bar config) that can be filled according to a %-value in order to show progress or amount of something.

    This widget has Rect and Label properties as well:
    * Rect color is used as the bar's background color (seen when bar is empty), in any bar type.
    * Most other Rect properties are only used when the bar type is a rect-based type.
    * Label allows the bar to show a label on top of the bar itself. The label's ``text`` property will allow a ``{value}`` tag
    that may be used to insert the current bar value (*100, so in a [0,100] range) in the label.
    """

    def __init__(self):
        RectMixin.__init__(self)
        TextMixin.__init__(self)
        self.color = Colors.grey
        self._bar_color: Color = Colors.yellow
        self._frame_color: Color = Colors.white
        self._frame_thickness: float = 5.0
        self._bar_type: BarType = BarType.HORIZONTAL
        self._value: float = 0.0
        self._inner_hole_ratio: float = 0.0

    # Editable Properties
    @types.color_property()
    def bar_color(self) -> Color:
        """The color of the bar fill. [GET/SET]"""
        return self._bar_color

    @bar_color.setter
    def bar_color(self, value: Color):
        self._bar_color = value

    @types.color_property()
    def frame_color(self) -> Color:
        """The color of the bar frame outline. [GET/SET]"""
        return self._frame_color

    @frame_color.setter
    def frame_color(self, value: Color):
        self._frame_color = value

    @types.float_property()
    def frame_thickness(self) -> float:
        """The thickness, in pixels, of the bar's frame outline. [GET/SET]"""
        return self._frame_thickness

    @frame_thickness.setter
    def frame_thickness(self, value: float):
        self._frame_thickness = value

    @types.enum_property()
    def bar_type(self) -> BarType:
        """The type of this progress bar. [GET/SET]"""
        return self._bar_type

    @bar_type.setter
    def bar_type(self, value: BarType):
        self._bar_type = value

    @types.float_property(max=1.0, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def value(self) -> float:
        """The current value of the bar [GET/SET]"""
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value

    @types.float_property(max=1.0, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def inner_hole_ratio(self) -> float:
        """The ratio of the circle radius that will be a hole. [GET/SET]

        This is only used when the Bar Type is any of the circle types. When this is > 0, the rendered bar will resemble a donut:
        a circle bar with a empty hole in the middle. This value is the percentage of the circle radius that will be the hole radius.
        """
        return self._inner_hole_ratio

    @inner_hole_ratio.setter
    def inner_hole_ratio(self, value: float):
        self._inner_hole_ratio = value

    # Methods
    def _draw_bar(self):
        """Internal method to draw the progress bar - the bar itself and its label."""
        if "circle" in self._bar_type.name.lower():
            self._draw_circle_bar()
        else:
            self._draw_rect_bar()
        self._draw_text()

    def _draw_rect_bar(self):
        """Draws the rectangle-type bars."""
        is_horizontal = "horizontal" in self._bar_type.name.lower()
        is_inverted = "inverted" in self._bar_type.name.lower()

        draw = imgui.get_window_draw_list()
        pos = self.position
        bottom_right = self.bottom_right_pos
        draw.add_rect_filled(pos, bottom_right, self.color.u32, self.rounding, self._get_draw_flags())

        hor_fraction = self._value if is_horizontal else 1.0
        ver_fraction = self._value if (not is_horizontal) else 1.0
        if is_inverted:
            bar_start_pos = pos + self._area * (1-hor_fraction, 1-ver_fraction)
            bar_end_pos = bottom_right
        else:
            bar_start_pos = pos
            bar_end_pos = pos + self._area * (hor_fraction, ver_fraction)
        draw.add_rect_filled(bar_start_pos, bar_end_pos, self._bar_color.u32, self.rounding, self._get_draw_flags())

        draw.add_rect(pos, bottom_right, self._frame_color.u32, self.rounding, self._get_draw_flags(), self._frame_thickness)

    def _draw_circle_bar(self):
        """Draws the circle-type bars."""
        is_clockwise = self._bar_type == BarType.CIRCLE

        draw = imgui.get_window_draw_list()
        center = self.position + self._area * 0.5
        radius = min(*self._area) * 0.5

        draw.add_circle_filled(center, radius, self.color.u32)

        first_half = min(0.5, self._value) / 0.5
        secnd_half = max(0, self._value - 0.5) / 0.5

        if is_clockwise:
            draw.path_line_to(center - (0, radius))
            draw.path_arc_to(center, radius, math.pi*1.5, math.pi*1.5 + first_half * math.pi)
        else:
            angle = math.pi*1.5 - math.pi * first_half
            draw.path_line_to(center + Vector2.from_angle(angle) * radius)
            draw.path_arc_to(center, radius, angle, math.pi*1.5)
        draw.path_line_to(center)
        draw.path_fill_convex(self._bar_color.u32)

        if secnd_half > 0:
            if is_clockwise:
                draw.path_line_to(center + (0, radius))
                draw.path_arc_to(center, radius, math.pi*0.5, (0.5 + secnd_half) * math.pi)
            else:
                angle = math.pi * 0.5 - secnd_half * math.pi
                draw.path_line_to(center + Vector2.from_angle(angle) * radius)
                draw.path_arc_to(center, radius, angle, math.pi*0.5)
            draw.path_line_to(center)
            draw.path_fill_convex(self._bar_color.u32)

        if self._inner_hole_ratio > 0:
            draw.add_circle_filled(center, radius*self._inner_hole_ratio, Colors.background.u32)
            draw.add_circle(center, radius*self._inner_hole_ratio, self._frame_color.u32, thickness=self._frame_thickness)
        draw.add_circle(center, radius, self._frame_color.u32, thickness=self._frame_thickness)

    # Method Overrides
    def render(self):
        self._draw_bar()
        self._handle_interaction()

    def _format_text(self, text: str):
        return self._substitute(text, {"value": self._value * 100})
