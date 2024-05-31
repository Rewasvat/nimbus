import math
import click
from enum import Enum, Flag
from nimbus.data import DataCache
from imgui_bundle import imgui, immapp, ImVec2, ImVec4
from imgui_bundle import hello_imgui  # type: ignore
from typing import Annotated, get_type_hints, Callable
from collections import namedtuple


def imgui_splitter(split_vertically: bool, thickness: float, size0: float = 0, size1: float = 0, minSize0: float = 0, minSize1: float = 0):
    """Creates a splitter element in imgui.

    Helper method to create a "splitter" element with IMGUI, which is basically a bar separating two UI regions, and the user can drag this
    bar in order to resize the two UI regions.

    For vertical bars (horizontal spit: left/right regions), it's best to use IMGUI's Columns, which have separating bars with the same
    behavior but are easier to use.

    To use this:
    * call this method to obtain the size of both regions (in the dynamic axis)
    * draw the first region (with size0).
    * call `imgui.separator()` which will work/show as the splitter.
    * finally draw the second region (with size1).

    Args:
        split_vertically (bool): True for vertical splitter (top/bottom regions), False for horizontal splitter (left/right regions).
        thickness (float): Size in pixels of the splitter.
        size0 (float, optional): Previous size of the first region. Defaults to 0.
        size1 (float, optional): Previous size of the second region. Defaults to 0.
        minSize0 (float, optional): Minimum size in pixels of the first region. Defaults to 0.
        minSize1 (float, optional): Minimum size in pixels of the second region. Defaults to 0.

    Returns:
        tuple[float, float]: The new values of size0 and size1, which are the new sizes (for the current frame) of the two regions.
    """
    backup_pos = imgui.get_cursor_pos()
    splitter_width = thickness if (not split_vertically) else -1.0
    splitter_height = thickness if (split_vertically) else -1.0
    delta = imgui_custom_drag_area(
        width=splitter_width,
        height=splitter_height,
        x=(not split_vertically) and (backup_pos.x + size0),
        y=split_vertically and (backup_pos.y + size0)
    )
    if delta:
        mouse_delta = delta.y if split_vertically else delta.x

        # Minimum pane size
        mouse_delta = max(mouse_delta, minSize0 - size0)
        mouse_delta = min(mouse_delta, size1 - minSize1)

        # Apply resize
        size0 = size0 + mouse_delta
        size1 = size1 - mouse_delta
    return size0, size1


def imgui_custom_drag_area(width: float, height: float, pos: ImVec2 = None, color: ImVec4 = None, active_color: ImVec4 = None,
                           hovered_color: ImVec4 = None):
    """Creates a invisible drag-area on imgui to allow custom drag effects.

    Args:
        width (float): Width of the drag-area.
        height (float): Height of the drag-area.
        pos (ImVec2, optional): Position of drag-area in current imgui region. Defaults to None.
        color (ImVec4, optional): Base color of drag-area. Defaults to `[0,0,0,0]` (transparent black).
        active_color (ImVec4, optional): Color of drag-area when selected. Defaults to `[0,0,0,0]` (transparent black).
        hovered_color (ImVec4, optional): Color of drag-area when hovered. Defaults to `[0.6,0.6,0.6,0.1]` (semi-transparent gray).

    Returns:
        ImVec2: drag amount. This is the delta moved by the mouse when dragging this area.
        None if drag-area is not active.
    """
    if color is None:
        color = ImVec4(0, 0, 0, 0)
    if active_color is None:
        active_color = ImVec4(0, 0, 0, 0)
    if hovered_color is None:
        hovered_color = ImVec4(0.6, 0.6, 0.6, 0.1)
    backup_pos = imgui.get_cursor_pos()
    imgui.push_style_color("Button", color)
    imgui.push_style_color("ButtonActive", active_color)
    imgui.push_style_color("ButtonHovered", hovered_color)
    imgui.set_cursor_pos(pos or backup_pos)
    imgui.button("##Splitter", ImVec2(width, height))
    imgui.pop_style_color(3)
    imgui.set_next_item_allow_overlap()
    delta = None
    if imgui.is_item_active():
        delta = imgui.get_mouse_drag_delta()
        imgui.reset_mouse_drag_delta()
    imgui.set_cursor_pos(backup_pos)
    return delta


def menu_item(title: str):
    """Utility method to simplify `imgui.menu_item` usage.

    ```python
    # Use:
    if menu_item("Item"):
        doStuff()
    # instead of:
    if imgui.menu_item("Item", "", False)[0]:
        doStuff()
    """
    return imgui.menu_item(title, "", False)[0]


class BasicWindow(hello_imgui.DockableWindow):
    """Basic generic IMGUI Window.

    BasicWindow is a subclass of hello_imgui.DockableWindow, which is a struct providing several attributes to configure the window within imgui.
    Most of these attributes are only used when this window is used as a dockable window in a BasicWindow.
    """

    def __init__(self, title: str):
        super().__init__(label_=title, gui_function_=self.render)
        self.children: list[BasicWindow] = []
        """The children window (dockable sub-windows) of this container."""
        self.has_menu = False
        """If this window has a top-menu to be rendered by its parent window. If so, our `self.render_top_menu()` will be called by the parent."""

    def render(self):
        """Renders the contents of this window.

        Sub-classes should override this method to implement their own rendering. This default implementation calls render() on all children.
        """
        for child in self.children:
            child.render()

    def render_top_menu(self):
        """Renders the contents of the window's top menu-bar.

        Sub-classes can override this method to implement their own menus. Other IMGUI widgets are technically allowed but
        take care using them due to size limitations in the bar.

        The default implementation shows menus from children windows, if they have it enabled.

        Example for adding a new menu:
        ```python
        if imgui.begin_menu("My Menu"):
            if imgui.menu_item("Item 1", "", False)[0]:
                doStuff1()
            if imgui.menu_item("Item 2", "", False)[0]:
                doStuff2()
            imgui.end_menu()
        """
        for child in self.children:
            if child.has_menu:
                if imgui.begin_menu(child.label):
                    child.render_top_menu()
                    imgui.end_menu()


class RunnableAppMode(str, Enum):
    """Possible modes to run a App Window."""
    SIMPLE = "SIMPLE"
    """Runs the window as a single standalone window.

    The window will want to override ``self.render()`` to draw its content.
    """
    DOCK = "DOCK"
    """Runs the window as a container for dockable sub-windows.

    The window's ``self.render()`` may still be used, but in this case the actual GUI contents are usually
    located in the app-window's children windows.
    """


class AppWindow(BasicWindow):
    """Base 'App' window.

    App windows are the root of all IMGUI hierarchy, with their `run()` method that actually opens a GUI window in the user's system.

    The app window may be a standalone window with just its content, or may be a docking container, allowing multiple children windows
    to be organized in docks by the user.

    The window may provide a default layout of the docks/sub-windows, but the user may change this layout at will, and depending on window
    settings may change other GUI settings as well(such as themes). These 'IMGUI User Preferences' are persisted locally in our DataCache,
    and restored when the same window is reopened later.

    The App Window also optionally provides a menu-bar at the top and a status-bar at the bottom of the window.
    """

    def __init__(self, title: str, mode: RunnableAppMode):
        super().__init__(title)
        self.mode = mode
        """The Runnable Mode of this App Window"""
        self.restore_previous_window = True
        """If the window should restore its previous position/size from another run."""
        self.show_status_bar = True
        """If the window should have its bottom status-bar.

        The status-bar is usually used to show small, always available widgets.
        Its contents can be customized via overwriting `self.render_status_bar()`.
        Some default IMGUI elements may be selected in the status-bar using the VIEW Menu."""
        self.show_menu_bar = True
        """If the window should have its top menu-bar.

        The menu-bar is usually used to show menus for different functions of the app.
        Its contents can be customized via overwriting `self.render_menus()`."""
        self.show_app_menu = True
        """Enables the 'APP' menu in the menu-bar(needs the menu bar to be enabled).

        This is the first menu in the bar, and usually shows the most basic/central app features.
        The menu by default has the same name as the window, but that can be changed with `self.app_menu_title`. As for contents, the menu
        will always have a 'Quit' button at the end, and the rest of its contents can be customized via overwriting `self.render_app_menu_items()`.
        """
        self.app_menu_title: str = title
        """The title of the App Menu item. Defaults to the window's title. See `self.show_app_menu`."""
        self.show_view_menu = True
        """Enables the 'VIEW' menu in the menu-bar(needs the menu bar to be enabled).

        The View menu is a IMGUI-based menu that allows the user to change aspects of the window's layout/content, such as changing options of
        the status-bar, visibility of windows, and the overall UI theme.
        """

    def run(self):
        """Runs this window as a new IMGUI App.

        This will open a new GUI window in your system, with the settings of this object(title, top/bottom bars, internal sub-windows, etc).

        NOTE: this is a blocking method! It will block internally while it runs the GUI loop, until the app window is closed.
        """
        run_params = hello_imgui.RunnerParams()
        # App Window Params
        run_params.app_window_params.window_title = self.label
        run_params.app_window_params.restore_previous_geometry = self.restore_previous_window

        # IMGUI Window Params
        run_params.callbacks.show_gui = self.render
        run_params.imgui_window_params.menu_app_title = self.label
        run_params.imgui_window_params.show_status_bar = self.show_status_bar
        run_params.callbacks.show_status = self.render_status_bar

        run_params.imgui_window_params.show_menu_bar = self.show_menu_bar
        run_params.imgui_window_params.show_menu_app = self.show_app_menu
        run_params.imgui_window_params.show_menu_view = self.show_view_menu
        run_params.imgui_window_params.menu_app_title = self.app_menu_title
        run_params.callbacks.show_menus = self.render_top_menu
        run_params.callbacks.show_app_menu_items = self.render_app_menu_items

        # First, tell HelloImGui that we want full screen dock space (this will create "MainDockSpace")
        if self.mode == RunnableAppMode.DOCK:
            run_params.imgui_window_params.default_imgui_window_type = (
                hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
            )

        run_params.docking_params.dockable_windows = self.children

        run_params.ini_folder_type = hello_imgui.IniFolderType.home_folder
        run_params.callbacks.before_exit = self.on_before_exit
        run_params.callbacks.post_init = self.on_init

        run_params.fps_idling.enable_idling = True
        run_params.fps_idling.fps_idle = 1

        # For simplicity, we're using the common imgui settings ini-file. However we create it here and delete it on before-exit,
        # while saving the settings data in our DataCache. This way the settings should be persisted by the cache for every window,
        # without generating trash ini-files everywhere in the user's computer.
        # NOTE: Maybe there's a better way to do this? Disabling imgui's ini-file logic, and loading/saving imgui settings directly to memory?
        cache = DataCache()
        settings_data = cache.get_data(self.get_settings_key())
        if settings_data is not None:
            ini_path = hello_imgui.ini_settings_location(run_params)
            with open(ini_path, "w") as f:
                f.write(settings_data)

        immapp.run(
            runner_params=run_params
            # add_ons_params=addon_params
        )

    def render_status_bar(self):
        """Renders the contents of the window's bottom status-bar, if its enabled(see `self.show_status_bar`)

        The status bar is usually used to show small widgets like texts, buttons or checkboxes. Remember that
        all the content is limited to a single line(the bar), so use `imgui.same_line()` between your widgets!

        Sub-classes can override this method to implement their own status widgets. This default implementation
        does nothing, but the default bar in IMGUI itself can show the window's FPS and toggle FPS Idling and these
        widgets can be toggled on/off via the VIEW Menu.
        """
        pass

    def render_app_menu_items(self):
        """Renders the contents of the 'App' Menu, if its enabled(see `self.show_app_menu`.)

        Sub-classes can override this method to implement their own items in the App menu. The default implementation
        shows nothing. The App menu always has a Quit button at the end.

        Example for adding a new item:
        ```python
        if imgui.menu_item("Item", "", False)[0]:
            doStuff()
        """
        pass

    def on_init(self):
        """Callback executed once, after app (imgui, etc) initialization.

        Basically, this is called when the window is opened, after imgui initializes but before rendering frames begins.
        In other words, should be called shortly after ``self.run()`` is executed.

        Sub classes may override this to add their own initialization logic. The default implementation does nothing.
        """
        pass

    def on_before_exit(self):
        """Callback executed once before the app window exits.

        This is called when the window is closed and thus the app window will exit. The ``self.run()`` method that was blocking will finally continue.
        When this happens, imgui (and components, backend, etc) still exist.

        Sub classes may override this to add their own exit logic. The default implementation saves the Imgui settings data into our DataCache.
        """
        run_params = hello_imgui.get_runner_params()
        ini_path = hello_imgui.ini_settings_location(run_params)

        cache = DataCache()
        with open(ini_path) as f:
            settings_data = f.read()
            cache.set_data(self.get_settings_key(), settings_data)

        hello_imgui.delete_ini_settings(run_params)

    def get_settings_key(self) -> str:
        """Gets the DataCache key for this window's imgui settings data.

        Returns:
            str: the key for accesing the window's settings data in `cache.get_data(key)`.
        """
        return f"ImguiIniData_{self.label}"


def lerp(a: float | ImVec2 | ImVec4, b: float | ImVec2 | ImVec4, f: float, clamp=False):
    """Performs linear interpolation between A and B values.

    This may interpolate floats, ImVec2 or ImVec4. Both A and B must be of the same type
    for them to be interpolated. Otherwise, None will be returned.

    Args:
        a (float|ImVec2|ImVec4): The initial value.
        b (float|ImVec2|ImVec4): The end value.
        f (float): The factor between A and B. Should be a value in range [0,1], but this is not enforced.
        clamp (bool): if true, F will be clamped to the [0,1] range. Defaults to False.

    Returns:
        float|ImVec2|ImVec4: the interpolated value between A and B according to F.
        Returns None if interpolation was not possible (A and B types didn't match).
    """
    if clamp:
        f = min(1, max(f, 0))
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return a + f*(b-a)
    elif isinstance(a, ImVec2) and isinstance(b, ImVec2):
        return ImVec2(
            lerp(a.x, b.x, f),
            lerp(a.y, b.y, f)
        )
    elif isinstance(a, ImVec4) and isinstance(b, ImVec4):
        return ImVec4(
            lerp(a.x, b.x, f),
            lerp(a.y, b.y, f),
            lerp(a.z, b.z, f),
            lerp(a.w, b.w, f),
        )


def multiple_lerp_with_weigths(targets: list[tuple[float | ImVec2 | ImVec4, float]], f: float):
    """Performs linear interpolation across a range of "target"s.

    Each target is a value (float, ImVec2 or ImVec4) and its associated factor (or weight). This will then
    find the two targets A and B such that: ``A_factor < F <= B_factor`` and then return the interpolation
    of the values of A and B according to F.

    Args:
        targets (list[tuple[float|ImVec2|ImVec4, float]]): list of (value, factor) tuples. Each tuple
        is a interpolation "target". The list may be unordered - this function will order the list
        based on the factor of each item. Values may be any float, ImVec2 or ImVec4, while factors may be
        any floats.
        f (float): interpolation factor. Can be any float - there's no restrictions on range. If F is smaller
        than the first factor in targets, or if F is larger than the last factor in targets, this will return the
        first or last value, respectively.

    Returns:
        float|ImVec2|ImVec4: the interpolated value between A and B according to F.
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


def multiple_lerp(values: list[float | ImVec2 | ImVec4], f: float, min=0.0, max=1.0):
    """Performs linear interpolation across a range of values.

    Each value is given a factor distributed uniformly between the MIN and MAX values for interpolation.
    This is done in a way that the first value will always have ``factor=MIN`` and the last value will
    have ``factor=MAX``.

    This will then return the interpolation between the closest values A and B such that ``A_factor < F <= B_factor``.

    Args:
        values (list[float|ImVec2|ImVec4]): list of values to interpolate on. This should be
        ordered as you want them in the [min,max] interpolation range.
        f (float): interpolation factor. Can be any float, BUT it needs to be in the given range [MIN, MAX].
        min (float, optional): Minimum factor for interpolation. Defaults to 0.0.
        max (float, optional): Maximum factor for interpolation. Defaults to 1.0.

    Returns:
        float|ImVec2|ImVec4: the interpolated value between A and B according to F.
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


def drop_down(value: str, options: list[str], docs: list[str] | dict[str, str] = None, default_doc: str = None, flags: imgui.SelectableFlags_ = 0):
    """Renders a simple "drop-down" control for selecting a value amongst a list of possible options.

    This is a simple combo-box that lists the options and allows one to be selected.
    Allows each value to have its own tooltip to document it on the UI.

    Args:
        value (str): The currently selected value.
        options (list[str]): The list of possible values.
        docs (list[str] | dict[str, str], optional): Optional documentation for each value. Can be, in order of priority, one of the given types:
        * Dict (``{value: doc}``): If a value isn't found on the dict, then ``default_doc`` is used in its place.
        * List: for any index, we get the value from options and its doc from here. If the list doesn't have the index, ``default_doc`` is used.
        default_doc (str, optional): Optional default docstring to use as tooltips for any option. If ``docs`` is None, and this is valid,
        this docstring will be used for all options.
        flags (imgui.SelectableFlags_, optional): imgui Selectable flags for use in each value selectable.

    Returns:
        tuple[bool, str]: returns a ``(changed, new_value)`` tuple.
    """
    changed = False
    new_value = value
    if imgui.begin_combo("##", value):
        for i, option in enumerate(options):
            if imgui.selectable(option, option == value, flags=flags)[0]:
                changed = True
                new_value = option
            if docs is not None:
                if isinstance(docs, dict):
                    imgui.set_item_tooltip(docs.get(option, str(default_doc)))
                elif isinstance(docs, list):
                    imgui.set_item_tooltip(docs[i] if i < len(docs) else str(default_doc))
            elif default_doc is not None:
                imgui.set_item_tooltip(default_doc)
        imgui.end_combo()
    return changed, new_value


def enum_drop_down(value: Enum, fixed_doc: str = None, flags: imgui.SelectableFlags_ = 0):
    """Renders a simple "drop-down" control for selecting a value from a Enum type.

    This is a simple combo-box that lists all options in the enum from value's type, and allows one to be selected.
    Each item will have a tooltip that follows the format ``{fixed_doc or type(value).__doc__}\n\n{item.name}: {item.value}``.
    So enum values can be used as their documentation.

    This also supports Flag enums. In such a case, the control allows selecting multiple options. All selected options are ``|``ed
    together.

    Args:
        value (Enum): a Enum value (a option of an enum). So ``type(value)`` should be a subclass of ``Enum``.
        fixed_doc (str, optional): Fixed docstring to show as a "prefix" in the tooltip of all items. Defaults to enum type docstring.
        flags (imgui.SelectableFlags_, optional): imgui Selectable flags for use in each value selectable. Not used when using a Flag enum.

    Returns:
        tuple[bool, Enum]: returns a ``(changed, new_value)`` tuple. The new-value has the same type as the given ``value``, but may be a different
        value if it was changed by the control.
    """
    new_value = value
    enum_cls = type(value)

    is_enum_flags = issubclass(enum_cls, Flag)
    if is_enum_flags:
        opened = imgui.begin_list_box("##")
    else:
        opened = imgui.begin_combo("##", value.name)

    if opened:
        if is_enum_flags:
            new_value = enum_cls(0)
        for i, option in enumerate(enum_cls):
            if is_enum_flags:
                selected = imgui.checkbox(option.name, option in value)[1]
            else:
                selected = imgui.selectable(option.name, option == value, flags=flags)[0]
            imgui.set_item_tooltip(f"{fixed_doc or enum_cls.__doc__}\n\n{option.name}: {option.value}")
            if selected:
                new_value = new_value | option if is_enum_flags else option
        if is_enum_flags:
            imgui.end_list_box()
        else:
            imgui.end_combo()
    return value != new_value, new_value


class ColorsClass:
    @property
    def red(self) -> ImVec4:
        return ImVec4(1, 0, 0, 1)

    @property
    def green(self):
        return ImVec4(0, 1, 0, 1)

    @property
    def blue(self):
        return ImVec4(0, 0, 1, 1)

    @property
    def transparent(self):
        return ImVec4(0, 0, 0, 0)

    @property
    def white(self):
        return ImVec4(1, 1, 1, 1)

    @property
    def black(self):
        return ImVec4(0, 0, 0, 1)

    @property
    def grey(self):
        return ImVec4(0.5, 0.5, 0.5, 1)

    @property
    def yellow(self):
        return ImVec4(1, 1, 0, 1)

    @property
    def cyan(self):
        return ImVec4(0, 1, 1, 1)

    @property
    def purple(self):
        return ImVec4(1, 0, 1, 1)

    @property
    def background(self):
        """The color of imgui window's background. Can be used to draw shapes on top of other object to make it seem
        they have a "hole" or something.

        NOTE: this is a hardcoded approximation of the background color! So it might not always be correct.
        Apparently there is no valid, working method to get the actual window background color in imgui. All apparently
        related methods in imgui's API I tried didn't work.
        """
        return ImVec4(0.055, 0.055, 0.055, 1)


Colors = ColorsClass()


class Vector2(imgui.ImVec2):
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

# ============== Base Widgets (generic for any theme?)
# TODO: suportar drag&drop pra mover widgets? simple (ou base) widgets seriam objetos moviveis, enquanto
#   os "slots" pra filhos nos container widgets seriam os possiveis alvos pra drop.
# TODO: suportar "temas" somehow? Daria pra ser só os temas da imgui? <ver Elbow>

# ============== Sensor-enabled Widgets (tb genericas, mas separadas das widgets normais caso queira usar elas num app sem sensors)
# TODO: [widget] SensorRect: 1 sensor, associa cor do rect ao state-color do sensor.
# TODO: [widget] SensorLabel: 1 sensor, associa texto da label ao format() do sensor (possivelmente color tb?).
# TODO: [widget] SensorButton: SensorRect+SensorLabel, usando mesmo sensor.
# TODO: [widget] SensorBar: 1 sensor, associa percent_value do sensor à barra, somehow
#   - deve envolver várias labels diferentes: limite min, limite max, valor min, valor max, valor atual, nome da bar

# ============== LCARS Only: (?)
# TODO: [widget] Communicator: que me lembro, eram puramente visuais (e com animação...)
# TODO: [widget] MainControls: que me lembro, era uma coleção de vários botões em formatos diferentes.
# TODO: [widget] RedAlert: que me lembro, eram puramente visuais (e com animação...)
# TODO: [widget] YellowAlert: que me lembro, eram puramente visuais (e com animação...)
# TODO: [widget] ReactorBar: seriam 2 sensores, meio que 2 ProgressBars juntas.
# TODO: [widget] WavesBar: seriam 2 sensores, meio que 2 ProgressBars juntas.
# TODO: [widget] SFCM (?)


# ============== EDITORS
# TODO: mover classes de ImguiTypeEditors e afins pra outro módulo. Possivelmente pra vários outros módulos.
# TODO: refatorar esse sistema pra não ser tão rigido. Usando reflection pra ler as type_hints da property
#   pra pegar os editors certos automaticamente. Isso facilitaria muito o uso.
#   - Ter uma classe com propriedades bem tipadas seria suficiente pra gerar os editors dela. Não precisaria hardcodar imgui_properties e tal
#     mas ainda poderia ter uma "property" diferente que guarda um **kwargs de metadata de tal property, que seria usado como a config do
#     modelo de tal atributo
# TODO: refatorar pra permitir cascata facilmente (lista com listas com listas... ou dicts com dicts e por ai vai)
#   assim a funcionalidade ficaria mais próxima do TPLove TableEditor, permitindo estruturas de dados quaisquer.
# TODO: refatorar pra ser fácil poder ter valor None sem quebrar as coisas.
#   - talvez uma flag "can be None?" ou algo assim nos editors?
#   - editores saberem o type do que eles editam, ai podiam fazer type() pra criar o valor default (isso ficaria mais facil com a refatoração com
#     reflection definicao automatica dos editores)
class ImguiTypeEditor:
    """Basic class for a KEY: VALUE editor in imgui.

    Subclasses of this implement how to edit a single (fixed for that class) VALUE type.

    The ``@imgui_property()`` decorator can then be used instead of ``@property`` to mark a class' property
    as being "renderable" using the given ImguiTypeEditor. The ``render_all_properties()`` function can then
    be used to render all available properties in a object with their specified ImguiTypeEditors.

    Subclasses should override ``__call__``.
    """

    def __init__(self):
        self._prop: property = None
        self.add_tooltip_after_value = True
        """If true, ``self.draw_end()`` will add ``self.attr_doc`` as a tooltip for the last imgui control drawn."""
        self.value_getter: Callable[[any, any], any] = getattr
        """The "value getter" function this editor uses to get the value for editing from the object.
        This is a ``(object, value_id) -> value`` function. It receives the object itself and a "value_id", which is any kind of
        data used to identify the value in object, and then returns the value. The default getter function is ``getattr``, where
        "value_id" is a ``name`` string used to access the attribute by its name.
        """
        self.value_setter: Callable[[any, any, any], None] = setattr
        """The "value setter" function this editor uses to set the value in the object after editing. This is only called if the value was changed.
        This is a ``(object, value_id, new_value) -> None`` function. It receives the object itself, a "value_id" and the new value to set.
        The value_id is anything used to identify the value in object for setting. For attributes/properites, value_id is a string which
        is the name of the value/property. The default value_setter is ``setattr``.
        """

    def __call__(self, obj, name: str):
        """Renders the KEY:VALUE editor. Usually this is a text with the given name, and imgui controls for
        changing the value.

        The default implementation in ImguiTypeEditor does the basic rendering for key:value editor by calling in order:
        * ``self.draw_start()``: starts the drawing process and renders the "key" part.
        * ``self.draw_value_editor(..., value=self.value_getter(obj,name))``: draws the type-specific value editing control.
        * ``self.draw_end()``: ends the key:value editor render.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.

        Returns:
            tuple[bool, any]: returns a ``(changed, new_value)`` tuple.
            Note that ``self.draw_end()`` will already have set the new value in the parent object.
        """
        self.draw_start(obj, name)
        value = self.value_getter(obj, name)
        changed, new_value = self.draw_value_editor(obj, name, value)
        self.draw_end(obj, name, changed, new_value)
        return changed, new_value

    def draw_value_editor(self, obj, name: str, value):
        """Renders the controls for editing just the VALUE part of a key:value editor.

        This is type-specific, and thus should be overriden by subclasses to implement their logic.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
            value (any): the current value of ``obj.name``.

        Returns:
            tuple[bool, any]: returns a ``(changed, new_value)`` tuple.
        """
        raise NotImplementedError

    def set_prop(self, prop: property):
        """Sets the property object we're attached to."""
        self._prop = prop
        return self

    @property
    def attr_doc(self):
        """Gets the docstring of the property we're attached to."""
        if self._prop is not None:
            return self._prop.__doc__
        return "undefined"

    def draw_start(self, obj, name: str):
        """Utility method to draw the "start" of a key:value editor.

        This pushes an unique ID (based on ``obj`` and ``name``), draws ``{name}:``,
        with a tooltip equal to our ``self.attr_doc`` and calls ``imgui.same_line()``.
        Also calls ``self.update_from_obj(obj, name)`` to optionally update ourselves.

        This setups the "key" part of a key:value editor, allowing subclasses to more easily
        implement their custom value rendering logic by calling this, then drawing the value editing part,
        and finally calling ``self.draw_end()``.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
        """
        imgui.push_id(f"{obj}EditAttr{name}")
        self.update_from_obj(obj, name)
        imgui.text(f"{name}:")
        imgui.set_item_tooltip(self.attr_doc)
        imgui.same_line()

    def draw_end(self, obj, name: str, changed: bool, new_value):
        """Utility method to draw the "ending" of a key:value editor.

        This should come after a ``self.draw_start()`` call was made and custom rendering logic
        for editing the value was done.

        This sets the attribute value in the object, and then pops the ID that was pushed
        in ``self.draw_start()``.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
            changed (bool): if the value was changed
            new_value (any): the new value for the attribute
        """
        if self.add_tooltip_after_value:
            imgui.set_item_tooltip(self.attr_doc)
        if changed:
            self.value_setter(obj, name, new_value)
        imgui.pop_id()

    def update_from_obj(self, obj, name: str):
        """Calls a optional ``<OBJ>._update_<NAME>_editor(self)`` method from the given object,
        with the purpose of dynamically updating this editor's attributes before drawing the editor itself.

        Args:
            obj (any): the object being updated
            name (str): the name of the attribute in object we're editing.
        """
        updater_method_name = f"_update_{name}_editor"
        method = getattr(obj, updater_method_name, None)
        if method is not None:
            method(self)


def imgui_property(type_editor: ImguiTypeEditor):
    """Imgui Property attribute. Can be used to create imgui properties the same way as a regular @property.

    A imgui-property behaves exactly the same way as a regular python @property, but also includes an associated
    ImguiTypeEditor object that can be used to change the value of this property in imgui.

    There are also related ``<type>_property`` decorators defined here, as an utility to call this passing the
    ImguiTypeEditor for a specific type.
    """
    class ImguiProperty(property):
        editor = type_editor
    return ImguiProperty


class StringEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a STRING value."""

    def __init__(self, flags: imgui.InputTextFlags_ = imgui.InputTextFlags_.none):
        super().__init__()
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: str):
        if value is None:
            value = ""
        return imgui.input_text("##", value, flags=self.flags)


def string_property(flags: imgui.InputTextFlags_ = imgui.InputTextFlags_.none):
    """Imgui Property attribute for a STRING type.

    Behaves the same way as a property, but includes a StringEditor object for allowing changing this string's value in imgui.

    Args:
        flags (imgui.InputTextFlags_, optional): flags to pass along to ``imgui.input_text``. Defaults to None.
    """
    editor = StringEditor(flags=flags)
    return imgui_property(editor)


class EnumEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a ENUM value."""

    def __init__(self, options: list[str] | Enum, docs: list | dict = None, is_enum_type=False, flags: imgui.SelectableFlags_ = 0):
        """
        Args:
            options (list[str] | Enum): The list of possible options. This can be:
            * A Enum type. Each item (shown by its ``name``) will be a possible option.
            * A Enum Flags type. Works similarly to the above, but allows selecting multiple enum options at once.
            * A ``list[str]`` (or any other iterable[str]): each string in the list will be an option.
            * None: can be used as an shortcut for a ``Enum`` type. The Enum type is taken from the property's current value the first
            time it is edited.
            docs (list | dict, optional): Optional definition of documentation for each option, shown as a tooltip (for that option) in the editor
            * Should be a ``list[str]`` matching the length of ``options``, or a ``{option: doc}`` dict.
            * If ``options`` is a Enum type, and this is None, then this will be set as the ``value`` of each enum-item.
            * The property's docstring is used as a default tooltip for all options.
            is_enum_type (bool, optional): If this property is a Enum type. So the current value being edited is a Enum object. Default value is
            if ``options`` is a Enum type.
            flags (imgui.SelectableFlags_, optional): Flags passed down to the drop-down selectable.
        """
        super().__init__()
        self.add_tooltip_after_value = False
        self.options = options
        self.docs = docs
        self.is_enum_type = is_enum_type or (isinstance(options, type) and issubclass(options, Enum))
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value):
        if self.options is None and isinstance(value, Enum):
            self.options = type(value)
            self.is_enum_type = True
        if self.is_enum_type:
            return enum_drop_down(value, self.attr_doc, self.flags)
        else:
            return drop_down(value, self.options, self.docs, default_doc=self.attr_doc, flags=self.flags)


def enum_property(options: list[str] | Enum, docs: list | dict = None, is_enum_type=False, flags: imgui.SelectableFlags_ = 0):
    """Imgui Property attribute for a ENUM type.

    Behaves the same way as a property, but includes a EnumEditor object for allowing changing this enum's value in imgui.

    Args:
        flags (imgui.SelectableFlags_, optional): flags to pass along to ``imgui.selectable``. Defaults to None.
    """
    editor = EnumEditor(options, docs=docs, is_enum_type=is_enum_type, flags=flags)
    return imgui_property(editor)


class BoolEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a BOOLEAN value."""

    def draw_value_editor(self, obj, name: str, value: bool):
        return imgui.checkbox("##", value)


def bool_property():
    """Imgui Property attribute for a BOOL type.

    Behaves the same way as a property, but includes a BoolEditor object for allowing changing this bool's value in imgui.
    """
    editor = BoolEditor()
    return imgui_property(editor)


class FloatEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a BOOLEAN value."""

    def __init__(self, min=0.0, max=0.0, format="%.2f", speed=1.0, is_slider=False, flags: imgui.SliderFlags_ = 0):
        """
        Args:
            min (float, optional): Minimum allowed value for this float property. Defaults to 0.0.
            max (float, optional): Maximum allowed value for this float property. Defaults to 0.0. If MIN >= MAX then we have no bounds.
            format (str, optional): Text format of the value to decorate the control with. Defaults to "%.2f". Apparently this needs to be a valid
            python format, otherwise the float control wont work properly.
            speed (float, optional): Speed to apply when changing values. Only applies when dragging the value and IS_SLIDER=False. Defaults to 1.0.
            is_slider (bool, optional): If we'll use a SLIDER control for editing. It contains a marker indicating the value along the range between
            MIN<MAX (if those are valid). Otherwise defaults to using a ``drag_float`` control. Defaults to False.
            flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
        """
        super().__init__()
        self.is_slider: bool = is_slider
        self.speed: float = speed
        self.min: float = min
        self.max: float = max
        self.format: str = format
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: float):
        if value is None:
            value = 0.0
        if self.is_slider:
            return imgui.slider_float("##value", value, self.min, self.max, self.format, self.flags)
        else:
            return imgui.drag_float("##value", value, self.speed, self.min, self.max, self.format, self.flags)


def float_property(min=0.0, max=0.0, format="%.2f", speed=1.0, is_slider=False, flags: imgui.SliderFlags_ = imgui.SliderFlags_.none):
    """Imgui Property attribute for a FLOAT type.

    Behaves the same way as a property, but includes a FloatEditor object for allowing changing this float's value in imgui.

    Args:
        min (float, optional): Minimum allowed value for this float property. Defaults to 0.0.
        max (float, optional): Maximum allowed value for this float property. Defaults to 0.0. If MIN >= MAX then we have no bounds.
        format (str, optional): Text format of the value to decorate the control with. Defaults to "%.3". Apparently this needs to be a valid
        python format, otherwise the float control wont work properly.
        speed (float, optional): Speed to apply when changing values. Only applies when dragging the value and IS_SLIDER=False. Defaults to 1.0.
        is_slider (bool, optional): If we'll use a SLIDER control for editing. It contains a marker indicating the value along the range between
        MIN<MAX (if those are valid). Otherwise defaults to using a ``drag_float`` control. Defaults to False.
        flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
    """
    editor = FloatEditor(min=min, max=max, format=format, speed=speed, is_slider=is_slider, flags=flags)
    return imgui_property(editor)


class ColorEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a COLOR (ImVec4) value."""

    def __init__(self, flags: imgui.ColorEditFlags_ = imgui.ColorEditFlags_.none):
        super().__init__()
        self.flags = flags

    def draw_value_editor(self, obj, name: str, value: ImVec4):
        changed, new_value = imgui.color_edit4("##", value, self.flags)
        return changed, ImVec4(*new_value)


def color_property(flags: imgui.ColorEditFlags_ = imgui.ColorEditFlags_.none):
    """Imgui Property attribute for a COLOR type.

    Behaves the same way as a property, but includes a ColorEditor object for allowing changing this color's value in imgui.
    """
    editor = ColorEditor(flags=flags)
    return imgui_property(editor)


class ListEditor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a LIST value."""

    def __init__(self, item_editor: ImguiTypeEditor, default_item=None):
        super().__init__()
        self.default_item = default_item
        self.item_editor = item_editor
        item_editor.value_getter = lambda obj, i: obj[i]

        def item_setter(obj, i, item):
            obj[i] = item
        item_editor.value_setter = item_setter

    def __call__(self, obj, name: str):
        changed = False
        value = self.value_getter(obj, name)
        if self.draw_start(obj, name):
            changed, value = self.draw_value_editor(obj, name, value)
            self.draw_end(obj, name, changed, value)
        return changed, value

    def draw_start(self, obj, name: str):
        self.update_from_obj(obj, name)
        opened = imgui.tree_node(f"{obj}EditAttr{name}", f"{name} ({len(self.value_getter(obj, name))} items)")
        imgui.set_item_tooltip(self.attr_doc)
        return opened

    def draw_value_editor(self, obj, name: str, value: list):
        changed = False
        size = len(value)
        for i in range(size):
            if i >= len(value):
                break  # required since the X button might remove a item, changing the size of value.
            item = value[i]
            # "start" part
            imgui.push_id(f"{obj}EditAttr{name}ListItem{i}")
            imgui.text(f"#{i}:")
            imgui.same_line()
            # item value editing
            item_changed, new_item = self.item_editor.draw_value_editor(obj, name, item)
            # item handling (move/delete)
            imgui.same_line()
            if imgui.button("^") and i >= 1:
                value[i-1], value[i] = value[i], value[i-1]
                item_changed = False
                changed = True
            imgui.same_line()
            if imgui.button("v") and i < size-1:
                value[i], value[i+1] = value[i+1], value[i]
                item_changed = False
                changed = True
            imgui.same_line()
            if imgui.button("X"):
                value.pop(i)
                item_changed = True
            # "end" part
            elif item_changed:
                value[i] = new_item
            changed = changed or item_changed
            imgui.pop_id()
        if imgui.button("Add Item"):
            value.append(self.default_item)
            changed = True
        return changed, value

    def draw_end(self, obj, name: str, changed: bool, new_value: list):
        if changed:
            self.value_setter(obj, name, new_value)
        imgui.tree_pop()


def list_property(item_editor: ImguiTypeEditor, default_item=None):
    """Imgui Property attribute for a LIST type.

    Behaves the same way as a property, but includes a ListEditor object for allowing changing this list's value in imgui.
    """
    editor = ListEditor(item_editor, default_item)
    return imgui_property(editor)


class Vector2Editor(ImguiTypeEditor):
    """ImguiTypeEditor for editing a Vector2 value."""

    def __init__(self, x_range=(0, 0), y_range=(0, 0), format="%.2f", speed=1.0, flags: imgui.SliderFlags_ = 0):
        super().__init__()
        self.speed: float = speed
        self.format: str = format
        self.flags = flags
        self.x_range: Vector2 = x_range
        self.y_range: Vector2 = y_range
        self.add_tooltip_after_value = False

    def draw_value_editor(self, obj, name: str, value):
        if value is None:
            value = Vector2()
        imgui.push_id("XComp")
        x_changed, value.x = self._component_edit(value.x, self.x_range)
        imgui.set_item_tooltip(f"X component of the Vector2.\n\n{self.attr_doc}")
        imgui.pop_id()
        imgui.same_line()
        imgui.push_id("YComp")
        y_changed, value.y = self._component_edit(value.y, self.y_range)
        imgui.set_item_tooltip(f"Y component of the Vector2.\n\n{self.attr_doc}")
        imgui.pop_id()
        return x_changed or y_changed, value

    def _component_edit(self, value: float, range: tuple[float, float]):
        min, max = range
        if max > min:
            return imgui.slider_float("##value", value, min, max, self.format, self.flags)
        else:
            return imgui.drag_float("##value", value, self.speed, min, max, self.format, self.flags)


def vector2_property(x_range=(0, 0), y_range=(0, 0), format="%.2f", speed=1.0, flags: imgui.SliderFlags_ = 0):
    """Imgui Property attribute for a Vector2 type.

    Behaves the same way as a property, but includes a Vector2Editor object for allowing changing this Vector2's value in imgui.

    Args:
        x_range (tuple[float, float], optional): (min, max) range of possible values for the X component of the vector.
        y_range (tuple[float, float], optional): (min, max) range of possible values for the Y component of the vector.
        format (str, optional): Text format of the value to decorate the control with. Defaults to "%.3". Apparently this needs to be a valid
        python format, otherwise the float control wont work properly.
        speed (float, optional): Speed to apply when changing values. Only applies when dragging the value. Defaults to 1.0.
        flags (imgui.SliderFlags_, optional): Flags for the Slider/Drag float controls. Defaults to imgui.SliderFlags_.none.
    """
    editor = Vector2Editor(x_range=x_range, y_range=y_range, format=format, speed=speed, flags=flags)
    return imgui_property(editor)


def get_all_properties(cls: type) -> dict[str, property]:
    """Gets all ``@property``s of a class. This includes properties of parent classes.

    Args:
        cls (type): The class to get the properties from.

    Returns:
        dict[str, property]: a "property name" => "property object" dict with all properties.
    """
    props = {}
    for kls in reversed(cls.mro()):
        props.update({key: value for key, value in kls.__dict__.items() if isinstance(value, property)})
    return props


def get_all_renderable_properties(cls: type) -> dict[str, ImguiTypeEditor]:
    """Gets all "Imgui Properties" of a class. This includes properties of parent classes.

    Imgui Properties are properties with an associated ImguiTypeEditor object created with the
    ``@imgui_property(editor)`` and related decorators.

    Args:
        cls (type): the class to get all imgui properties from.

    Returns:
        dict[str, ImguiTypeEditor]: a "property name" => "ImguiTypeEditor object" dict with all imgui properties.
        All editors returned by this will have had their "parent properties" set accordingly.
    """
    props = get_all_properties(cls)
    return {k: v.editor.set_prop(v) for k, v in props.items() if hasattr(v, "editor")}


def render_all_properties(obj, ignored_props: set[str] = None):
    """Renders the KEY:VALUE editors for all imgui properties of the given object.

    This allows seeing and editing the values of all imgui properties in the object.
    See ``get_all_renderable_properties()``.

    Args:
        obj (any): the object to render all imgui properties.
        ignored_props (set[str], optional): a set (or any other object that supports ``X in IGNORED`` (contains protocol)) that indicates
        property names that we should ignore when rendering their editors. This way, if the name of a imgui-property P is in ``ignored_props``,
        its editor will not be rendered. Defaults to None (shows all properties).
    """
    props = get_all_renderable_properties(type(obj))
    for name, editor in props.items():
        if (ignored_props is None) or (name not in ignored_props):
            editor(obj, name)
