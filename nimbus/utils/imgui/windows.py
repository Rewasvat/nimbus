import click
from enum import Enum
from nimbus.data import DataCache
from imgui_bundle import imgui, immapp
from imgui_bundle import hello_imgui, imgui_node_editor  # type: ignore


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
        self.enable_viewports: bool = False
        """Enables 'viewports'.

        Viewports allow imgui windows to be dragged outside the AppWindow, becoming other OS GUI windows (with a imgui style).
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
        run_params.imgui_window_params.enable_viewports = self.enable_viewports
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
            click.secho(f"Loaded IMGUI Settings from cache. Using temp settings file '{ini_path}'", fg="green")
        else:
            click.secho("Couldn't load IMGUI Settings from cache.", fg="yellow")

        addons = immapp.AddOnsParams()
        addons.with_markdown = True
        addons.with_node_editor = True

        node_config = imgui_node_editor.Config()
        # node_config.settings_file = ""
        addons.with_node_editor_config = node_config

        immapp.run(
            runner_params=run_params,
            add_ons_params=addons
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
        click.secho(f"Saved IMGUI Settings from '{ini_path}' to cache.", fg="green")

        hello_imgui.delete_ini_settings(run_params)

    def get_settings_key(self) -> str:
        """Gets the DataCache key for this window's imgui settings data.

        Returns:
            str: the key for accesing the window's settings data in `cache.get_data(key)`.
        """
        return f"ImguiIniData_{self.label}"
