import re
import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.nodes import input_property
from nimbus.utils.imgui.math import Vector2, Rectangle
from imgui_bundle import imgui
from enum import Enum


class TextAlignment(Enum):
    """How to align a label to its parent slot."""
    TOP_LEFT = "TOP_LEFT"
    TOP = "TOP"
    TOP_RIGHT = "TOP_RIGHT"
    RIGHT = "RIGHT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM = "BOTTOM"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    LEFT = "LEFT"
    CENTER = "CENTER"


# TODO: implementar margin pra renderizar texto pouco mais longe das bordas qdo não no CENTER
class TextMixin:
    """Simple text widget."""

    def __init__(self, text: str = ""):
        self.text = text
        self._wrapped = False
        self._align: TextAlignment = TextAlignment.CENTER

    @input_property(multiline=True)
    def text(self) -> str:
        """The text being displayed [GET/SET]"""
        return ""  # this is essentially the default value.

    @input_property()
    def text_color(self) -> Color:
        """The color of the text [GET/SET]"""
        return Colors.white  # this is essentially the default value.

    @types.bool_property()
    def is_wrapped(self):
        """If the text will wrap around to not exceed our available width space [GET/SET]"""
        return self._wrapped

    @is_wrapped.setter
    def is_wrapped(self, value: bool):
        self._wrapped = value

    @types.enum_property()
    def align(self):
        """How the text is aligned to our area [GET/SET]"""
        return self._align

    @align.setter
    def align(self, value: TextAlignment):
        self._align = value

    @input_property(min=0.0, max=2.0, is_slider=True, flags=imgui.SliderFlags_.always_clamp)
    def scale(self) -> float:
        """The scale of the text. [GET/SET]
        * 0 (min): impossible. Since we can't have scale=0, at this value scale will behave as if it was =1.
        * close to 0: theoretical min size possible, pratically invisible/unreadable.
        * [0, 1]: scaled down text
        * 1.0: regular text size
        * [1, 2]: scaled up text
        * 2 (max): max size possible in current label slot area.

        Note that scaling won't work properly when text is long, since its regular size might already match our slot size.
        """
        return 1.0  # this is essentially the default value.

    def _draw_text(self):
        """Internal utility to render our label's text."""
        if self.text is not None and len(self.text) > 0:
            lines = self._format_text(self.text).split("\n")
            wrap_width = self._area.x if self._wrapped else 0
            line_rects: list[Rectangle] = []
            for line in lines:
                y = line_rects[-1].bottom_left_pos.y if len(line_rects) > 0 else 0
                line_rect = Rectangle((0, y), imgui.calc_text_size(line, wrap_width=wrap_width))
                line_rects.append(line_rect)
            text_rect = sum(line_rects, line_rects[0])

            font = imgui.get_font()
            font_height = font.font_size
            max_font_scale = (self._area / text_rect.size).min_component()

            actual_scale = 1.0
            if self.scale > 1:
                actual_scale += (self.scale - 1) * (max_font_scale - 1)
            elif self.scale > 0:
                actual_scale = self.scale

            text_rect = self._update_line_rects(line_rects, actual_scale)

            draw_list = imgui.get_window_draw_list()
            # draw_list.add_rect(text_rect.position, text_rect.bottom_right_pos, Colors.green.u32)
            for line, line_rect in zip(lines, line_rects):
                # draw_list.add_rect(line_rect.position, line_rect.bottom_right_pos, Colors.red.u32)
                draw_list.add_text(
                    font=font,
                    font_size=font_height*actual_scale,
                    pos=line_rect.position,
                    col=self.text_color.u32,
                    text_begin=line,
                    text_end=None,
                    wrap_width=wrap_width,
                    cpu_fine_clip_rect=None
                )

    def _update_line_rects(self, line_rects: list[Rectangle], scale: float):
        """Updates the position and size of each line rectangle according to our current text alignment
        and given scale.

        The line rectangles will be updated in-place. After this, these lines will be ready for text-drawing.

        Args:
            line_rects (list[Rectangle]): list of line rectangles of this label. At this point passed as input here,
            each line's position means nothing, but its size is the text line's size in regular font-size (no scaling)
            with text-wrap applied. After this method, these rectangles will've been updated in-place with their proper
            positions and scaled sizes.
            scale (float): The current actual scale for drawing text in this label.

        Returns:
            Rectangle: the rectangle bounding all updated line rectangles.
        """
        pos = Vector2.from_cursor_screen_pos()
        prev_y = 0.0
        # Adjust positions of each line.
        for rect in line_rects:
            rect.size = rect.size * scale
            rect.position = self._get_text_pos(rect.size) + (0, prev_y)
            prev_y += rect.size.y

        # Adjust position of whole group of lines
        text_rect = sum(line_rects, line_rects[0])
        group_offset = text_rect.position
        text_rect.position = pos + self._get_text_pos(text_rect.size)
        for rect in line_rects:
            rect.position += text_rect.position - group_offset
        return text_rect

    def _get_text_pos(self, text_size: Vector2):
        """Calculates the position offset (top-left corner) of the given text size for drawing in our
        area, given the area size and our text alignment setting.

        Returns the offset in absolute coords.
        """
        pos = Vector2()
        if self.align == TextAlignment.TOP_LEFT:
            return pos

        # Update Pos X
        if self.align in (TextAlignment.TOP_RIGHT, TextAlignment.RIGHT, TextAlignment.BOTTOM_RIGHT):
            pos.x += self._area.x - text_size.x
        elif self.align in (TextAlignment.TOP, TextAlignment.CENTER, TextAlignment.BOTTOM):
            pos.x += self._area.x * 0.5 - text_size.x * 0.5

        # Update Pos Y
        if self.align in (TextAlignment.BOTTOM_LEFT, TextAlignment.BOTTOM, TextAlignment.BOTTOM_RIGHT):
            pos.y += self._area.y - text_size.y - 1
        elif self.align in (TextAlignment.LEFT, TextAlignment.CENTER, TextAlignment.RIGHT):
            pos.y += self._area.y * 0.5 - text_size.y * 0.5

        return pos

    def _format_text(self, text: str):
        """Formats the given text and returns an updated string.

        Widget classes that use this mixin may override this method to implement their own logic for formatting text.
        A common implementation may use ``self._substitute()`` to update tags in the text for actual values dynamically.
        The default implementation of this method just returns TEXT itself.

        Args:
            text (str): text to format. When drawing this TextMixin, this is called with ``self.text``.

        Returns:
            str: updated text. When drawing this TextMixin, this return value is what will be rendered.
        """
        return text


class Label(TextMixin, LeafWidget):
    """Simple text widget."""

    def __init__(self, text: str = ""):
        LeafWidget.__init__(self)
        TextMixin.__init__(self, text)
        self.node_header_color = WidgetColors.Primitives

    def render(self):
        self._draw_text()
        self._handle_interaction()
