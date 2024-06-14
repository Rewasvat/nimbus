import re
import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget
from nimbus.utils.imgui.colors import Colors, Color
from nimbus.utils.imgui.nodes_common import input_property
from imgui_bundle import imgui, ImVec2
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

    @input_property()
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
        """Internal utility to render our label text."""
        if self.text is not None and len(self.text) > 0:
            text = self._format_text(self.text)
            area_size = imgui.get_content_region_avail()
            wrap_width = area_size.x if self._wrapped else 0
            text_size = imgui.calc_text_size(text, wrap_width=wrap_width)

            font = imgui.get_font()
            font_height = font.font_size
            max_font_scale_h = area_size.y / text_size.y
            max_font_scale_w = area_size.x / text_size.x
            max_font_scale = min(max_font_scale_w, max_font_scale_h)

            actual_scale = 1.0
            if self.scale > 1:
                actual_scale += (self.scale - 1) * (max_font_scale - 1)
            elif self.scale > 0:
                actual_scale = self.scale

            text_size.x *= actual_scale
            text_size.y *= actual_scale
            text_pos = self._get_text_pos(area_size, text_size)

            draw_list = imgui.get_window_draw_list()
            draw_list.add_text(
                font=font,
                font_size=font_height*actual_scale,
                pos=text_pos,
                col=self.text_color.u32,
                text_begin=text,
                text_end=None,
                wrap_width=wrap_width,
                cpu_fine_clip_rect=None
            )

    def _get_text_pos(self, area_size: ImVec2, text_size: ImVec2):
        """Calculates the position (top-left corner) of our text-rect (given by its size) for drawing in our
        area, given the the area size and our text alignment setting.

        Returns the position in absolute coords, for use with Imgui.DrawLists.
        """
        pos = imgui.get_cursor_screen_pos()
        if self.align == TextAlignment.TOP_LEFT:
            return pos

        # Update Pos X
        if self.align in (TextAlignment.TOP_RIGHT, TextAlignment.RIGHT, TextAlignment.BOTTOM_RIGHT):
            pos.x += area_size.x - text_size.x
        elif self.align in (TextAlignment.TOP, TextAlignment.CENTER, TextAlignment.BOTTOM):
            pos.x += area_size.x * 0.5 - text_size.x * 0.5

        # Update Pos Y
        if self.align in (TextAlignment.BOTTOM_LEFT, TextAlignment.BOTTOM, TextAlignment.BOTTOM_RIGHT):
            pos.y += area_size.y - text_size.y - 1
        elif self.align in (TextAlignment.LEFT, TextAlignment.CENTER, TextAlignment.RIGHT):
            pos.y += area_size.y * 0.5 - text_size.y * 0.5

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

    def _substitute(self, text: str, tags: dict[str, any]):
        """Utility method to substitute ``{key}`` (or ``{key:format}``) tags in the given TEXT with the
        value for ``key`` in TAGS, using the ``format``, if any.

        Args:
            text (str): the text to check for tags.
            tags (dict[str, any]): a ``{tag key -> tag value}`` dict, used to match values for the tag keys found
            in the TEXT. If a key isn't found, the key itself is used as default value.

        Returns:
            str: text with tags replaced with their value.
        """
        def replacer(m: re.Match):
            pack: str = m.group(1)
            parts = pack.split(":")
            key = parts[0]
            if len(parts) <= 1:
                value_format = "{}"
            else:
                value_format = f"{{0:{parts[1]}}}"
            value = tags.get(key, key)
            try:
                return value_format.format(value)
            except Exception:
                return str(value)

        return re.sub(r"{([^}]+)}", replacer, text)


class Label(TextMixin, LeafWidget):
    """Simple text widget."""

    def __init__(self, text: str = ""):
        TextMixin.__init__(self, text)

    def render(self):
        self._draw_text()
        self._handle_interaction()
