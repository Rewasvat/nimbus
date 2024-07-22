import nimbus.utils.command_utils as cmd_utils
from contextlib import contextmanager
from imgui_bundle import imgui
from imgui_bundle import hello_imgui  # type: ignore
from enum import Enum


class Fonts(Enum):
    """Available fonts to use with FontDatabase and the Widgets system."""
    LCARS = "Antonio-Regular"
    LCARS_WIDE = "Federation_Wide"


# TODO: check bug: aparentemente carregar font MTO grande crasha.
#   STR: ProgressBar do tamanho da tela, texto pequeno (2-4 chars), scale max
class FontCache:
    """Cache of IMGUI's ImFont objects.

    This stores ImFonts that were loaded with different font-sizes for a specific
    TTF font.
    """

    def __init__(self, font: Fonts):
        self.font = font
        self.font_path = __file__.replace("fonts.py", f"{font.value}.ttf")
        self.fonts: dict[int, imgui.ImFont] = {}
        self.loading_fonts: set[int] = set()

    def get_font(self, size: int) -> tuple[imgui.ImFont, bool]:
        """Gets the cached ImFont object for the given size for our font.

        If the font isn't loaded for that size, it'll be loaded in a few frames (most likely by the next).

        Args:
            size (int): font-size to get the font for.

        Returns:
            tuple[ImFont,bool]: returns a ``(ImFont, bool)`` tuple. The boolean indicates if the requested font was
            loaded or not. The ImFont object will always be a valid one, however if the font wasn't loaded, the
            returned font might be the wrong one: it'll be a default font instead.
        """
        size = int(size)
        if size in self.fonts:
            return self.fonts[size], True
        font = imgui.get_font()
        self.loading_fonts.add(size)
        self.fonts[size] = font
        return font, False

    def load_fonts(self):
        """Loads our font at the requested sizes (from ``self.get_font``) that weren't loaded before."""
        for size in self.loading_fonts:
            font_params = hello_imgui.FontLoadingParams(merge_to_last_font=False, inside_assets=False)
            font = hello_imgui.load_font(self.font_path, size, font_params)
            # NOTE: using hello_imgui.load_font_dpi_responsive is erroring.
            self.fonts[size] = font
        self.loading_fonts.clear()


class FontDatabase(metaclass=cmd_utils.Singleton):
    """Singleton database of fonts to use with IMGUI.

    Allows dynamic loading of available fonts in required font-sizes.
    These ImFont objects can then be used with IMGUI to change the font
    used when drawing text.

    While IMGUI can load fonts from TTF, it stores and uses them as bitmap fonts.
    So we need to "re-load" a font for each font-size the program needs.
    """

    def __init__(self):
        self.fonts = {font: FontCache(font) for font in Fonts}

    def get_font(self, size: int, font: Fonts = Fonts.LCARS):
        """Gets the cached ImFont object for the given font and size.

        If the font isn't loaded for that size, it'll be loaded in a few frames (most likely by the next).

        Args:
            size (int): font-size to get the font for.
            font (Fonts, optional): Which font to get, amongst the available ones. Defaults to ``LCARS``.

        Returns:
            tuple[ImFont,bool]: returns a ``(ImFont, bool)`` tuple. The boolean indicates if the requested font was
            loaded or not. The ImFont object will always be a valid one, however if the font wasn't loaded, the
            returned font might be the wrong one: it'll be a default font instead.
        """
        cache = self.fonts[font]
        imfont, is_loaded = cache.get_font(size)
        if not is_loaded:
            run_params = hello_imgui.get_runner_params()
            run_params.callbacks.load_additional_fonts = self._load_fonts
        return imfont, is_loaded

    def _load_fonts(self):
        """Internal method to load all requested fonts from our caches.

        This is used with hello_imgui's runner_params ``load_additional_fonts`` callback in order
        to load additional fonts at the proper moment in the render-loop.
        """
        for cache in self.fonts.values():
            cache.load_fonts()

    @contextmanager
    def using_font(self, size: int = 16, font: Fonts = Fonts.LCARS):
        """Context manager to use a specific sized font with IMGUI.

        The request font will be pushed to imgui's stack (``push_font``), then this method will
        yield the ImFont object used, and finally on return we'll ``pop_font``.

        Note that if the requested font isn't loaded, this will use a default font instead. In a few frames
        (most likely the next) the requested font should be loaded, and thus will be properly used if this
        method is repeated.

        Args:
            size (int): font-size to use. Defaults to 16.
            font (Fonts, optional): Which font to get, amongst the available ones. Defaults to ``LCARS``.

        Yields:
            ImFont: the font object that was requested and used.
        """
        imfont, is_loaded = self.get_font(size, font)
        imgui.push_font(imfont)
        yield imfont
        imgui.pop_font()
