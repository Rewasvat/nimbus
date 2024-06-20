from imgui_bundle import imgui, ImVec4


class Color(ImVec4):
    """Color class.

    Expands on ``imgui.ImVec4``, allowing math operators and other utility methods related to COLORS.
    This can be used in place of ImVec4 objects when passing to ``imgui`` API functions.
    """

    @property
    def u32(self):
        """Gets this color as a ImU32 value, used by some low-level imgui API, such as DrawLists."""
        return imgui.get_color_u32(self)

    def __getstate__(self):
        """Pickle Protocol: overriding getstate to allow pickling this class.
        This should return a dict of data of this object to reconstruct it in ``__setstate__`` (usually ``self.__dict__``).
        """
        return {"x": self.x, "y": self.y, "z": self.z, "w": self.w}

    def __setstate__(self, state: dict[str, float]):
        """Pickle Protocol: overriding setstate to allow pickling this class.
        This receives the ``state`` data returned from ``self.__getstate__`` that was pickled, and now being unpickled.

        Use the data to rebuild this instance.
        NOTE: the class ``self.__init__`` was probably NOT called according to Pickle protocol.
        """
        self.x = state.get("x", 0)
        self.y = state.get("y", 0)
        self.z = state.get("z", 0)
        self.w = state.get("w", 0)


class ColorsClass:
    @property
    def red(self) -> Color:
        return Color(1, 0, 0, 1)

    @property
    def green(self) -> Color:
        return Color(0, 1, 0, 1)

    @property
    def blue(self) -> Color:
        return Color(0, 0, 1, 1)

    @property
    def transparent(self) -> Color:
        return Color(0, 0, 0, 0)

    @property
    def white(self) -> Color:
        return Color(1, 1, 1, 1)

    @property
    def black(self) -> Color:
        return Color(0, 0, 0, 1)

    @property
    def grey(self) -> Color:
        return Color(0.5, 0.5, 0.5, 1)

    @property
    def yellow(self) -> Color:
        return Color(1, 1, 0, 1)

    @property
    def cyan(self) -> Color:
        return Color(0, 1, 1, 1)

    @property
    def magenta(self) -> Color:
        return Color(1, 0, 1, 1)

    @property
    def background(self) -> Color:
        """The color of imgui window's background. Can be used to draw shapes on top of other object to make it seem
        they have a "hole" or something.

        NOTE: this is a hardcoded approximation of the background color! So it might not always be correct.
        Apparently there is no valid, working method to get the actual window background color in imgui. All apparently
        related methods in imgui's API I tried didn't work.
        """
        return Color(0.055, 0.055, 0.055, 1)


Colors = ColorsClass()
