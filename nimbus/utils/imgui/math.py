import math
from imgui_bundle import imgui, ImVec2, ImVec4


class Vector2(ImVec2):
    """2D Vector class.

    Expands on ``imgui.ImVec2``, allowing math operators and other utility methods.
    This can be used in place of ImVec2 objects when passing to ``imgui`` API functions.
    """

    def __add__(self, other):
        """ADDITION: returns a new Vector2 instance with our values and ``other`` added.

        ``other`` may be:
        * scalar value (float, int): adds the value to X and Y.
        * Vector2/ImVec2/tuples/list: adds other[0] to our [0], other[1] to our [1].
        """
        if isinstance(other, (float, int)):
            return self.__class__(self.x + other, self.y + other)
        return self.__class__(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other):
        """SUBTRACTION: returns a new Vector2 instance with our values and ``other`` subtracted.

        ``other`` may be:
        * scalar value (float, int): subtracts the value from X and Y.
        * Vector2/ImVec2/tuples/list: subtracts other[0] from our [0], other[1] from our [1].
        """
        if isinstance(other, (float, int)):
            return self.__class__(self.x - other, self.y - other)
        return self.__class__(self[0] - other[0], self[1] - other[1])

    def __mul__(self, other):
        """MULTIPLICATION: returns a new Vector2 instance with our values and ``other`` multiplied.

        ``other`` may be:
        * scalar value (float, int): multiply the value to X and Y.
        * Vector2/ImVec2/tuples/list: multiply other[0] to our [0], other[1] to our [1].
        """
        if isinstance(other, (float, int)):
            return self.__class__(self.x * other, self.y * other)
        return self.__class__(self[0] * other[0], self[1] * other[1])

    def length_squared(self):
        """Gets the sum of our components to the potency of 2."""
        return self.x ** 2 + self.y ** 2

    def length(self):
        """Gets the length of this vector. (the square root of ``length_squared``)."""
        return math.sqrt(self.length_squared())

    def normalize(self):
        """Normalizes this vector inplace, transforming it into a unit-vector."""
        size = self.length()
        self.x /= size
        self.y /= size

    def normalized(self):
        """Returns a normalized (unit-length) copy of this vector."""
        v = self.copy()
        v.normalize()
        return v

    def signed_normalize(self):
        """Normalizes this vector inplace using its own components (not the length!).

        So this only retains the sign of each compoenent. They will become ``1``, ``0`` or ``-1``.
        """
        if self.x != 0:
            self.x /= abs(self.x)
        if self.y != 0:
            self.y /= abs(self.y)

    def copy(self):
        """Returns a copy of this vector."""
        return self.__class__(self.x, self.y)

    def max(self, *args: 'Vector2'):
        """Get a new Vector2 object where each component is the maximum component
        value amongst ourselves and all given vectors.

        Returns:
            Vector2: a new Vector2 instance with the maximum component values.
            Essentially ``x = max(self.x, v.x for v in args)`` (and for Y).
        """
        x = max(self.x, *[v[0] for v in args])
        y = max(self.y, *[v[1] for v in args])
        return self.__class__(x, y)

    def min(self, *args: 'Vector2'):
        """Get a new Vector2 object where each component is the minimum component
        value amongst ourselves and all given vectors.

        Returns:
            Vector2: a new Vector2 instance with the minimum component values.
            Essentially ``x = min(self.x, v.x for v in args)`` (and for Y).
        """
        x = min(self.x, *[v[0] for v in args])
        y = min(self.y, *[v[1] for v in args])
        return self.__class__(x, y)

    @classmethod
    def from_angle(cls, angle: float):
        """Returns a unit-vector based on the given ANGLE (in radians)."""
        return cls(math.cos(angle), math.sin(angle))

    @classmethod
    def from_cursor_pos(cls):
        """Returns a vector with the values of imgui's current cursor position, in local coords (from ``imgui.get_cursor_pos()``)"""
        return cls(*imgui.get_cursor_pos())

    @classmethod
    def from_cursor_screen_pos(cls):
        """Returns a vector with the values of imgui's current cursor position, in absolute coords (from ``imgui.get_cursor_screen_pos()``)"""
        return cls(*imgui.get_cursor_screen_pos())

    @classmethod
    def from_available_content_region(cls):
        """Returns a vector with the values of imgui's available content region (from ``imgui.get_content_region_avail()``)"""
        return cls(*imgui.get_content_region_avail())


class Rectangle:
    """Geometrical Rectangle class

    Represents a rect in pure geometry/math values - its position, size, and so one.
    Contains methods and properties related to rectangle math.
    """

    def __init__(self, pos: Vector2, size: Vector2):
        self._pos = Vector2(*pos)
        self._size = Vector2(*size)

    @property
    def position(self):
        """The position (top-left corner) of this rect. [GET/SET]"""
        return self._pos.copy()

    @position.setter
    def position(self, value: Vector2):
        self._pos = Vector2(*value)

    @property
    def size(self):
        """The size of this rect. [GET/SET]"""
        return self._size.copy()

    @size.setter
    def size(self, value: Vector2):
        self._size = Vector2(*value)

    @property
    def top_left_pos(self):
        """The position of this rect's top-left corner (same as ``position``). [GET]"""
        return self.position

    @property
    def top_right_pos(self):
        """The position of this rect's top-right corner. [GET]"""
        return self._pos + (self._size.x, 0)

    @property
    def bottom_left_pos(self):
        """The position of this rect's bottom-left corner. [GET]"""
        return self._pos + (0, self._size.y)

    @property
    def bottom_right_pos(self):
        """The position of this rect's bottom-right corner. [GET]"""
        return self._pos + self._size

    @property
    def as_imvec4(self) -> ImVec4:
        """Returns this rectangle as a ``ImVec4(pos.x, pos.y, width, height)`` instance."""
        return ImVec4(self._pos.x, self._pos.y, self._size.x, self._size.y)

    def copy(self):
        """Returns a new rectangle instance with the same values as this one."""
        return type(self)(self._pos, self._size)


def lerp[T](a: T, b: T, f: float, clamp=False) -> T:
    """Performs linear interpolation between A and B values.

    This may interpolate ints, floats, ImVec2 (and its subtypes, such as Vector2) or ImVec4 (and its subtypes, such as Color).
    Both A and B must be of the same type for them to be interpolated. Otherwise, None will be returned.

    Args:
        a (T): The initial value.
        b (T): The end value.
        f (float): The factor between A and B. Should be a value in range [0,1], but this is not enforced.
        clamp (bool): if true, F will be clamped to the [0,1] range. Defaults to False.

    Returns:
        T: the interpolated value between A and B according to F.
        Returns None if interpolation was not possible (A and B types didn't match).
    """
    if clamp:
        f = min(1, max(f, 0))
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return a + f*(b-a)
    elif isinstance(a, ImVec2) and isinstance(b, ImVec2):  # Will accept Vector2
        return type(a)(
            lerp(a.x, b.x, f),
            lerp(a.y, b.y, f)
        )
    elif isinstance(a, ImVec4) and isinstance(b, ImVec4):  # Will accept Color
        return type(a)(
            lerp(a.x, b.x, f),
            lerp(a.y, b.y, f),
            lerp(a.z, b.z, f),
            lerp(a.w, b.w, f),
        )


def multiple_lerp_with_weigths[T](targets: list[tuple[T, float]], f: float) -> T:
    """Performs linear interpolation across a range of "target"s.

    Each target is a value and its associated factor (or weight). This will then
    find the two targets A and B such that: ``A_factor < F <= B_factor`` and then return the interpolation
    of the values of A and B according to F.

    Args:
        targets (list[tuple[T, float]]): list of (value, factor) tuples. Each tuple
        is a interpolation "target". The list may be unordered - this function will order the list
        based on the factor of each item. Values may be any int, float, ImVec2 or ImVec4, while factors may be
        any floats.
        f (float): interpolation factor. Can be any float - there's no restrictions on range. If F is smaller
        than the first factor in targets, or if F is larger than the last factor in targets, this will return the
        first or last value, respectively.

    Returns:
        T: the interpolated value between A and B according to F.
        Returns None if interpolation was not possible (targets is empty).
    """
    if len(targets) <= 0:
        return

    targets.sort(key=lambda x: x[1])

    if f <= targets[0][1]:
        # F is lower or equal than first stage, so return it.
        return targets[0][0]

    for i in range(len(targets) - 1):
        a_value, a_factor = targets[i]
        b_value, b_factor = targets[i+1]
        if a_factor < f <= b_factor:
            lerp_f = (f - a_factor)/(b_factor - a_factor)
            return lerp(a_value, b_value, lerp_f)

    # F is higher than last stage, so return it.
    return targets[-1][0]


def multiple_lerp[T](values: list[T], f: float, min=0.0, max=1.0) -> T:
    """Performs linear interpolation across a range of values.

    Each value is given a factor distributed uniformly between the MIN and MAX values for interpolation.
    This is done in a way that the first value will always have ``factor=MIN`` and the last value will
    have ``factor=MAX``.

    This will then return the interpolation between the closest values A and B such that ``A_factor < F <= B_factor``.

    Args:
        values (list[T]): list of values to interpolate on. This should be
        ordered as you want them in the [min,max] interpolation range.
        f (float): interpolation factor. Can be any float, BUT it needs to be in the given range [MIN, MAX].
        min (float, optional): Minimum factor for interpolation. Defaults to 0.0.
        max (float, optional): Maximum factor for interpolation. Defaults to 1.0.

    Returns:
        T: the interpolated value between A and B according to F.
        Returns None if interpolation was not possible (values is empty).
    """
    if len(values) <= 0:
        return

    step = (max - min) / (len(values) - 1)
    targets = []
    for i, value in enumerate(values):
        factor = min + step*i
        targets.append((value, factor))
    return multiple_lerp_with_weigths(targets, f)
