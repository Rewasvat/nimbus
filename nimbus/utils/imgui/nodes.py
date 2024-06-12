from typing import Callable
from nimbus.utils.imgui.general import menu_item
from nimbus.utils.imgui.colors import Color, Colors
from imgui_bundle import imgui, ImVec2, imgui_node_editor  # type: ignore


# TODO: mudar cor de background do node header.
class Node:
    """Utility class to represent a Node in imgui's Node Editor.

    Has the basic layout of a Node and allows users or subclasses to extend it.
    Simple node only needs to define the node's input and output pins.

    The basic layout divides the node in 4 regions:
    * Header: horizontal region in the top of the node. Has the node's name and tooltip.
    * Inputs: vertical region as a column below the header, to the left. Has the node's input pins.
    * Middle: vertical region as a column below the header, in the middle.
    * Outputs: vertical region as a column below the header, to the right. Has the node's output pins.
    """

    def __init__(self):
        self.node_id = imgui_node_editor.NodeId.create()
        self.can_be_deleted = True
        """If this object can be deleted by user-interaction."""
        self.is_selected = False
        """If this node is selected by the user in the node-editor."""

    def draw_node(self):
        """Draws the node in imgui's Node Editor.

        This should only be called inside a imgui-node-editor rendering context.
        """
        imgui_node_editor.begin_node(self.node_id)
        imgui.push_id(self.node_id.id())
        imgui.begin_vertical(f"{repr(self)}NodeMain")
        self.draw_node_header()
        imgui.begin_horizontal(f"{repr(self)}NodeContent")
        imgui.spring(0, 0)

        self.draw_node_inputs()

        imgui.spring(1)
        imgui.begin_vertical(f"{repr(self)}NodeMiddle")
        self.draw_node_middle()
        imgui.end_vertical()

        imgui.spring(1)
        self.draw_node_outputs()

        imgui.end_horizontal()  # content
        imgui.end_vertical()  # node
        # footer? como?
        imgui_node_editor.end_node()
        imgui.pop_id()

        self.is_selected = imgui_node_editor.is_node_selected(self.node_id)

    def draw_node_header(self):
        """Used internally to draw the node's header region.

        This is a horizontally aligned region in the top part of the node.
        Displays the node's name (``str(self)``), and a tooltip when the name is hovered, containing
        the docstring of this object's type.
        """
        imgui.begin_horizontal(f"{repr(self)}NodeHeader")
        imgui.spring(1)
        imgui.text_unformatted(str(self))
        imgui_node_editor.suspend()
        imgui.set_item_tooltip(type(self).__doc__)
        imgui_node_editor.resume()
        imgui.spring(1)
        imgui.end_horizontal()
        # space between header and node content
        imgui.spring(0, imgui.get_style().item_spacing.y * 2)

    def draw_node_inputs(self):
        """Used internally to draw the node's input region.

        This is a vertically aligned region, below the header to the left (left/bottom of the node).
        It displays all input pins from the node (see ``self.get_input_pins()``)
        """
        imgui.begin_vertical(f"{repr(self)}NodeInputs", align=0)
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_alignment, ImVec2(0, 0.5))
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_size, ImVec2(0, 0))
        for i, pin in enumerate(self.get_input_pins()):
            if i > 0:
                imgui.spring(0)
            pin.draw_node_pin()
        imgui_node_editor.pop_style_var(2)
        imgui.spring(1, 0)
        imgui.end_vertical()

    def draw_node_outputs(self):
        """Used internally to draw the node's output region.

        This is a vertically aligned region, below the header to the right (right/bottom of the node).
        It displays all output pins from the node (see ``self.get_output_pins()``)
        """
        imgui.begin_vertical(f"{repr(self)}NodeOutputs", align=1)
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_alignment, ImVec2(1, 0.5))
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_size, ImVec2(0, 0))
        for i, pin in enumerate(self.get_output_pins()):
            if i > 0:
                imgui.spring(0)
            pin.draw_node_pin()
        imgui_node_editor.pop_style_var(2)
        imgui.spring(1, 0)
        imgui.end_vertical()

    def draw_node_middle(self):
        """Used internally to draw the node's middle region.

        This is vertically aligned region below the header, between the input and output regions.

        The default implementation does nothing - subclasses can overwrite this at will to change the contents of this region.
        """
        pass

    def get_input_pins(self) -> list['NodePin']:
        """Gets a list of all input pins of this node.

        The default implementation returns an empty list. Implementations should overwrite this in order to return
        their proper list of input pins.
        """
        return []

    def get_output_pins(self) -> list['NodePin']:
        """Gets a list of all output pins of this node.

        The default implementation returns an empty list. Implementations should overwrite this in order to return
        their proper list of output pins.
        """
        return []

    def get_all_links(self) -> list['NodeLink']:
        """Gets all links to/from this node."""
        links = []
        for pin in self.get_input_pins():
            links += pin.get_all_links()
        for pin in self.get_output_pins():
            links += pin.get_all_links()
        return links

    def render_edit_details(self):
        """Renders the controls for editing this Node's details.

        This is used as the contents of the context-menu when this node is right-clicked,
        is displayed on the side panel when the node is selected, and anywhere else we need to edit the node.

        Implementations should override this to draw what they want. Default is nothing.
        """
        pass

    def delete(self):
        """Deletes this node.

        Implementations should override this to have their logic for deleting the node and removing it from the editor's nodes list.
        Default does nothing.
        """
        pass


class NodePin:
    """An Input or Output Pin in a Node.

    A pin is the point in a node used to make connections (links - see ``NodeLink``) to other node (to pins in other nodes).

    Implementations should override the method ``draw_node_pin_contents()`` to draw the pin's contents.
    """

    def __init__(self, parent: Node, kind: imgui_node_editor.PinKind):
        self.parent_node: Node = parent
        self.pin_id = imgui_node_editor.PinId.create()
        self.pin_kind = kind
        self._links: dict[NodePin, NodeLink] = {}
        """Dict of all links this pin have. Keys are the opposite pins, which along with us forms the link."""
        self.default_link_color: Color = Colors.white
        """Default color for link created from this pin (used when this is an output pin)."""
        self.default_link_thickness: float = 1
        """Default thickness for link lines created from this pin (used when this is an output pin)."""
        self.can_be_deleted: bool = False
        """If this object can be deleted by user-interaction."""
        self.pin_tooltip: str = None
        """Tooltip text to display when this pin is hovered by the user. If none, no tooltip will be displayed."""

    def draw_node_pin(self):
        """Draws this pin. This should be used inside a node drawing context.

        The Node class calls this automatically to draw its input and output pins.
        """
        imgui_node_editor.begin_pin(self.pin_id, self.pin_kind)
        imgui.begin_horizontal(f"{repr(self)}NodePin")
        self.draw_node_pin_contents()
        imgui.end_horizontal()
        if self.pin_tooltip:
            imgui_node_editor.suspend()
            imgui.set_item_tooltip(self.pin_tooltip)
            imgui_node_editor.resume()
        imgui_node_editor.end_pin()

    def draw_node_pin_contents(self):
        """Draws the pin's contents: icon, label, etc.

        The area available for drawing the pin's contents is usually limited, and is horizontally aligned.
        Implementations should override this method to define their drawing logic - default implementation raises an error.
        """
        raise NotImplementedError  # TODO: ter default?

    def get_all_links(self) -> list['NodeLink']:
        """Gets all links connected to this pin."""
        return list(self._links.values())

    def can_link_to(self, pin: 'NodePin') -> tuple[bool, str]:
        """Checks if we can link to the given pin, and gives the reason not in failure cases.

        Performs basic link-validity checks:
        * If Pin kinds (input/output) are different.
        * If Pin's Parent Nodes are different.
        * If we aren't already connected.

        Implementations may override this to add their own linking checks.

        Args:
            pin (NodePin): pin to check if link is possible.

        Returns:
            tuple[bool, str]: the boolean indicates if we can link to the given pin.
            The str return value is the error message indicating why we can't link, if the bool is false.
        """
        if pin.pin_kind == self.pin_kind:
            return False, f"Pins of same kind ({pin.pin_kind})"
        if pin.parent_node == self.parent_node:
            return False, "Pins belong to the same node"
        if self.is_linked_to(pin):
            return False, "Already linked to pin"
        return True, "success"

    def is_link_possible(self, pin: 'NodePin') -> bool:
        """Checks if we can link to the given pin.

        See ``self.can_link_to``. This is just utility method to get the boolean return value from ``self.can_link_to(pin)``.
        """
        return self.can_link_to(pin)[0]

    def is_linked_to(self, pin: 'NodePin') -> bool:
        """Checks if we're linked to the given pin.

        Args:
            pin (NodePin): pin to check against.

        Returns:
            bool: if we have a link to the given pin.
        """
        return pin in self._links

    def is_linked_to_any(self) -> bool:
        """Checks if this Pin has a connection to any other pin."""
        return len(self._links) > 0

    def get_link(self, pin: 'NodePin'):
        """Gets our link to the given pin, if any exists."""
        return self._links.get(pin, None)

    def link_to(self, pin: 'NodePin'):
        """Tries to create a link between this and the given pin.

        This will check if both pins allow linking to each other.
        If linking is possible, the link will be created. Both pins will be updated with the new link,
        and have their ``on_new_link_added`` callbacks executed.

        Args:
            pin (NodePin): The other pin to try to connect to.

        Returns:
            NodeLink: the link object that was just created, or None if linking was not possible.
            Use ``can_link_to`` from this or from the other pin to get the failure reason if required.
        """
        if not self.is_link_possible(pin) or not pin.is_link_possible(self):
            return
        link = self._add_new_link(pin)
        self.on_new_link_added(link)
        pin.on_new_link_added(link)
        return link

    def remove_link_to(self, pin: 'NodePin'):
        """Tries to remove a link between this and the given pin.

        This checks if a link between us exists, and if so, removes the link from us, executes
        the ``on_link_removed`` callbacks (on both pins), and returns the removed link object.

        Args:
            pin (NodePin): the other pin to remove link from.

        Returns:
            NodeLink: the link object that was removed, or None if no link between us existed.
            ``get_link`` or ``is_linked_to`` can be used to check if link exists.
        """
        if not self.is_linked_to(pin):
            return
        link = self._remove_link(pin)
        self.on_link_removed(link)
        pin.on_link_removed(link)
        return link

    def _add_new_link(self, pin: 'NodePin') -> 'NodeLink':
        """Internal method to create a new link between this and the given pin, and add it
        to both pins.

        Use with care! This does no validity checks, nor calls the link added callbacks. See ``link_to`` for
        the proper method to use to link to pins.

        Args:
            pin (NodePin): The pin to link to.

        Returns:
            NodeLink: the new Link object representing the link between these two pins. The output pin will always
            be the link's starting pin. However, since this does not validate that the pins are of different kinds,
            this rule might be broken when this method is used incorrectly.
        """
        if self.pin_kind == imgui_node_editor.PinKind.output:
            link = NodeLink(self, pin)
        else:
            link = NodeLink(pin, self)
        self._links[pin] = link
        pin._links[self] = link
        return link

    def _remove_link(self, pin: 'NodePin'):
        """Internal method to remove the link between this and the given pin, from both pins.

        Use with care! This does no safety checks, nor calls the link-removed callbacks. See ``remove_link_to`` for
        the proper method to use to remove links. As such, this will error out if trying to remove a link that doesn't exist.

        Args:
            pin (NodePin): the pin to remove link to.

        Returns:
            NodeLink: the removed link object.
        """
        pin._links.pop(self)
        return self._links.pop(pin)

    def on_new_link_added(self, link: 'NodeLink'):
        """Internal callback called when a new link is added to this pin.

        Implementations should use this to update their state when a new link is added.
        """
        pass

    def on_link_removed(self, link: 'NodeLink'):
        """Internal callback called when link is removed from this pin.

        Implementations should use this to update their state when a link is removed.
        """
        pass

    def render_edit_details(self):
        """Renders the controls for editing this Pin's details.

        This is used as the contents of the context-menu when this pin is right-clicked, and anywhere else we need to edit the pin.

        Implementations should override this to draw what they want. Default is nothing.
        """
        pass

    def delete(self):
        """Deletes this pin.

        Implementations should override this to have their logic for deleting the pin and removing it from its parent node.
        Default does nothing.
        """
        pass


class NodeLink:
    """The connection between an input and output pins on two different nodes.

    The link is a line connecting pins A and B, where A is a output pin in Node X, and B is a input pin on Node Y.
    It always is a output->input pin connection between different pins/different nodes.

    This class essentially only holds data about the link and a method to render it. Most node-related logic is located in the
    ``Node`` and ``NodePin`` classes. As such, implementations don't need to change/overwrite anything about this class.
    """

    def __init__(self, start_pin: NodePin, end_pin: NodePin, id: imgui_node_editor.LinkId = None, color: Color = None, thickness: float = None):
        self.link_id = imgui_node_editor.LinkId.create() if id is None else id
        self.start_pin: NodePin = start_pin
        """The pin that starts this link. This should be a output pin."""
        self.end_pin: NodePin = end_pin
        """The pin that ends this link. This should be a input pin."""
        self.color = color if color else start_pin.default_link_color
        """Color of this link. Defaults to ``start_pin.default_link_color``."""
        self.thickness: float = thickness if thickness else start_pin.default_link_thickness
        """Thickness of the line of this link."""
        self.is_selected = False
        """If this link is selected by the user in the node-editor."""

    def render_node_link(self):
        """Draws this link between nodes. This should only be called in a node-editor context in imgui."""
        imgui_node_editor.link(self.link_id, self.start_pin.pin_id, self.end_pin.pin_id, self.color, self.thickness)
        self.is_selected = imgui_node_editor.is_link_selected(self.link_id)

    def render_edit_details(self):
        """Renders the controls for editing this Link's details.

        This is used as the contents of the context-menu when this link is right-clicked, and anywhere else we need to edit the link.

        Implementations should override this to draw what they want. Default is nothing.
        """
        pass

    def has_pin(self, pin: NodePin) -> bool:
        """Checks if the given pin is the start or end point of this link."""
        return self.start_pin == pin or self.end_pin == pin

    def __str__(self):
        return f"({self.start_pin})== link to =>({self.end_pin})"


def get_all_links_from_nodes(nodes: list[Node]):
    """Gets a list of all links from all pins of the given nodes.

    Args:
        nodes (list[Node]): list of nodes to get links from

    Returns:
        list[NodeLink]: list of links from all nodes. Each link is unique in the return value, and order of links in the return
        is preserved from the order of nodes.
    """
    links = sum((node.get_all_links() for node in nodes), [])
    return list(dict.fromkeys(links))


# TODO: feature de ordenar o grafo: reposiciona todos nodes pra ficar um grafo decente (tem algo assim na TPLove)
# TODO: copy/paste/cut
# TODO: colocar dados salvos do imgui-node-editor no nosso DataCache
#   - atualmente, ele salva num json default na pasta onde executou o app (ver `Widgets_Test` no ~)
#   - investigar q tem um Widgets_Test.ini lá tb
class NodeEditor:
    """Represents a Node Editor system.

    This wraps imgui-node-editor code (immediate mode) inside a easy to use class that works with our class definitions of
    Node, NodePin and NodeLinks.

    As such, this imgui control has all that is needed to provide a fully featured Node Editor for our nodes system in imgui.
    User only needs to call ``render_system`` each frame with imgui.
    """

    def __init__(self, background_context_menu: Callable[[NodePin | None], Node] = None):
        self.nodes: list[Node] = []
        """List of existing nodes in the system."""
        self._background_context_menu_draw_method = background_context_menu
        self._create_new_node_to_pin: NodePin = None
        self._selected_menu_node: Node = None
        self._selected_menu_pin: NodePin = None
        self._selected_menu_link: NodeLink = None

    def find_node(self, id: imgui_node_editor.NodeId):
        """Finds the node with the given NodeID amongst our nodes."""
        for node in self.nodes:
            if node.node_id == id:
                return node

    def find_pin(self, id: imgui_node_editor.PinId):
        """Finds the pin with the given PinID amongst all pins from our nodes."""
        for node in self.nodes:
            for pin in node.get_input_pins():
                if pin.pin_id == id:
                    return pin
            for pin in node.get_output_pins():
                if pin.pin_id == id:
                    return pin

    def find_link(self, id: imgui_node_editor.LinkId):
        """Finds the link with the given LinkID amongst all links, from all pins, from our nodes."""
        for node in self.nodes:
            for pin in node.get_input_pins():
                for link in pin.get_all_links():
                    if link.link_id == id:
                        return link
            for pin in node.get_output_pins():
                for link in pin.get_all_links():
                    if link.link_id == id:
                        return link

    def render_system(self, nodes: list[Node] = None):
        """Renders this NodeEditor using imgui.

        This takes up all available content area, and splits it into two columns:
        * A side panel/column displaying node selection details and more info.
        * The node editor itself.

        As such, will be good for UX if the window/region this is being rendered to is large or resizable.

        Args:
            nodes (list[Node], optional): If given, this will update our internal list of nodes with this new list.
            Since this method has to be called each frame to properly render this complex control, passing this argument
            can be used as a shortcut to also updating the existing nodes along with rendering this.
        """
        if nodes is not None:
            self.nodes = nodes

        flags = imgui.TableFlags_.borders_inner_v | imgui.TableFlags_.resizable
        if imgui.begin_table("NodeEditorRootTable", 2, flags):
            imgui.table_setup_column("DetailsPanel")
            imgui.table_setup_column("NodesPanel")

            imgui.table_next_column()
            self.render_details_panel()

            imgui.table_next_column()
            self.render_node_editor()

            imgui.end_table()

    def render_details_panel(self):
        """Renders the side panel of this NodeEditor. This panel contains selection details and other info."""
        imgui.begin_child("NodeEditorDetailsPanel")
        has_selection = False

        for node in self.nodes:
            if node.is_selected:
                has_selection = True
                if imgui.collapsing_header(str(node)):
                    node.render_edit_details()
                    imgui.spacing()

        if not has_selection:
            imgui.text_wrapped("Select Nodes to display & edit their details here.")
        imgui.end_child()

    def render_node_editor(self):
        """Renders the Imgui Node Editor part of this NodeEditor."""
        imgui_node_editor.begin("NodeEditor")
        backup_pos = imgui.get_cursor_screen_pos()

        # Step 1: Commit all known node data into editor
        # Step 1-A) Render All Existing Nodes
        for node in self.nodes:
            node.draw_node()

        # Step 1-B) Render All Existing Links
        links = get_all_links_from_nodes(self.nodes)
        for link in links:
            link.render_node_link()

        # Step 2: Handle Node Editor Interactions
        is_new_node_popup_opened = False
        if not is_new_node_popup_opened:
            # Step 2-A) handle creation of links
            self.handle_node_creation_interactions()
            # Step 2-B) Handle deletion action of links
            self.handle_node_deletion_interactions()

        imgui.set_cursor_screen_pos(backup_pos)  # NOTE: Pq? Tinha isso nos exemplos, mas não parece fazer diff.

        self.handle_node_context_menu_interactions()

        # Finished Node Editor
        imgui_node_editor.end()

    def handle_node_creation_interactions(self):
        """Handles new node and new link interactions from the node editor."""
        if imgui_node_editor.begin_create():
            input_pin_id = imgui_node_editor.PinId()
            output_pin_id = imgui_node_editor.PinId()
            if imgui_node_editor.query_new_link(input_pin_id, output_pin_id):
                start_pin = self.find_pin(output_pin_id)
                end_pin = self.find_pin(input_pin_id)

                if start_pin.pin_kind == imgui_node_editor.PinKind.input:
                    start_pin, end_pin = end_pin, start_pin

                if start_pin and end_pin:
                    can_link, msg = start_pin.can_link_to(end_pin)
                    if can_link:
                        self.show_label("link pins")
                        if imgui_node_editor.accept_new_item(Colors.green):
                            start_pin.link_to(end_pin)
                    else:
                        self.show_label(msg)
                        imgui_node_editor.reject_new_item(Colors.red)

            new_pin_id = imgui_node_editor.PinId()
            if imgui_node_editor.query_new_node(new_pin_id):
                new_pin = self.find_pin(new_pin_id)
                if new_pin is not None:
                    self.show_label("Create Node (linked as possible to this pin)")

                if imgui_node_editor.accept_new_item():
                    imgui_node_editor.suspend()
                    self.open_background_context_menu(new_pin)
                    imgui_node_editor.resume()

            imgui_node_editor.end_create()  # Wraps up object creation action handling.

    def handle_node_deletion_interactions(self):
        """Handles node and link deletion interactions from the node editor."""
        if imgui_node_editor.begin_delete():
            deleted_node_id = imgui_node_editor.NodeId()
            while imgui_node_editor.query_deleted_node(deleted_node_id):
                node = self.find_node(deleted_node_id)
                if node and node.can_be_deleted:
                    if imgui_node_editor.accept_deleted_item():
                        # Node implementation should handle removing itself from the list that supplies this editor with nodes.
                        node.delete()
                else:
                    imgui_node_editor.reject_deleted_item()

            # There may be many links marked for deletion, let's loop over them.
            deleted_link_id = imgui_node_editor.LinkId()
            while imgui_node_editor.query_deleted_link(deleted_link_id):
                # If you agree that link can be deleted, accept deletion.
                if imgui_node_editor.accept_deleted_item():
                    # Then remove link from your data.
                    link = self.find_link(deleted_link_id)
                    if link:
                        link.start_pin.remove_link_to(link.end_pin)
            imgui_node_editor.end_delete()

    def handle_node_context_menu_interactions(self):
        """Handles interactions and rendering of all context menus for the node editor."""
        imgui_node_editor.suspend()

        # These empty ids will be filled by their appropriate show_*_context_menu() below.
        # Thus the menu if for the entity with given id.
        node_id = imgui_node_editor.NodeId()
        pin_id = imgui_node_editor.PinId()
        link_id = imgui_node_editor.LinkId()

        if imgui_node_editor.show_node_context_menu(node_id):
            self.open_node_context_menu(node_id)
        elif imgui_node_editor.show_pin_context_menu(pin_id):
            self.open_pin_context_menu(pin_id)
        elif imgui_node_editor.show_link_context_menu(link_id):
            self.open_link_context_menu(link_id)
        elif imgui_node_editor.show_background_context_menu():
            self.open_background_context_menu()

        self.render_node_context_menu()
        self.render_pin_context_menu()
        self.render_link_context_menu()
        self.render_background_context_menu()

        imgui_node_editor.resume()

    def open_node_context_menu(self, node_id: imgui_node_editor.NodeId):
        """Opens the Node Context Menu - the popup when a node is right-clicked, for the given node."""
        imgui.open_popup("NodeContextMenu")
        self._selected_menu_node = self.find_node(node_id)

    def render_node_context_menu(self):
        """Renders the context menu popup for a Node."""
        if imgui.begin_popup("NodeContextMenu"):
            node = self._selected_menu_node
            imgui.text("Node Menu:")
            imgui.separator()
            if node:
                node.render_edit_details()
            else:
                imgui.text_colored(Colors.red, "Invalid Node")
            if node and node.can_be_deleted:
                imgui.separator()
                if menu_item("Delete"):
                    imgui_node_editor.delete_node(node.node_id)
            imgui.end_popup()

    def open_pin_context_menu(self, pin_id: imgui_node_editor.PinId):
        """Opens the Pin Context Menu - the popup when a pin is right-clicked, for the given pin."""
        imgui.open_popup("PinContextMenu")
        self._selected_menu_pin = self.find_pin(pin_id)

    def render_pin_context_menu(self):
        """Renders the context menu popup for a Pin."""
        if imgui.begin_popup("PinContextMenu"):
            pin = self._selected_menu_pin
            imgui.text("Pin Menu:")
            imgui.separator()
            if pin:
                imgui.text(str(pin))
                pin.render_edit_details()
            else:
                imgui.text_colored(Colors.red, "Invalid Pin")
            if pin and pin.can_be_deleted:
                imgui.separator()
                if menu_item("Delete"):
                    pin.delete()
            imgui.end_popup()

    def open_link_context_menu(self, link_id: imgui_node_editor.LinkId):
        """Opens the Link Context Menu - the popup when a link is right-clicked, for the given link."""
        imgui.open_popup("LinkContextMenu")
        self._selected_menu_link = self.find_link(link_id)

    def render_link_context_menu(self):
        """Renders the context menu popup for a Link."""
        if imgui.begin_popup("LinkContextMenu"):
            link = self._selected_menu_link
            imgui.text("link Menu:")
            imgui.separator()
            if link:
                imgui.text(str(link))
                link.render_edit_details()
            else:
                imgui.text_colored(Colors.red, "Invalid link")
            imgui.separator()
            if menu_item("Delete"):
                imgui_node_editor.delete_link(link.link_id)
            imgui.end_popup()

    def open_background_context_menu(self, pin: NodePin = None):
        """Opens the Background Context Menu - the popup when the background of the node-editor canvas is right-clicked.

        This is usually used to allow creating new nodes and other general editor features.

        Args:
            pin (NodePin, optional): pin that is trying to create a node. Defaults to None.
            If given, means the menu was opened from dragging a link from a pin in the editor, so the user wants to create a node
            already linked to this pin.
        """
        imgui.open_popup("BackgroundContextMenu")
        self._create_new_node_to_pin = pin

    def render_background_context_menu(self):
        """Renders the node editor's background context menu."""
        if imgui.begin_popup("BackgroundContextMenu"):
            if self._background_context_menu_draw_method:
                pos = imgui.get_cursor_screen_pos()
                new_node = self._background_context_menu_draw_method(self._create_new_node_to_pin)
                if new_node:
                    if self._create_new_node_to_pin:
                        self.try_to_link_node_to_pin(new_node, self._create_new_node_to_pin)
                    imgui_node_editor.set_node_position(new_node.node_id, imgui_node_editor.screen_to_canvas(pos))
            imgui.end_popup()

    def show_label(self, text: str):
        """Shows a tooltip label at the cursor's current position.

        Args:
            text (str): text to display.
        """
        imgui_node_editor.suspend()
        imgui.set_tooltip(text)
        imgui_node_editor.resume()

    def try_to_link_node_to_pin(self, node: Node, pin: NodePin):
        """Tries to given pin to any acceptable opposite pin in the given node.

        Args:
            node (Node): The node to link to.
            pin (NodePin): The pin to link to.

        Returns:
            NodeLink: the new link, if one was successfully created.
        """
        if pin.pin_kind == imgui_node_editor.PinKind.input:
            other_pins = node.get_output_pins()
        else:
            other_pins = node.get_input_pins()
        for other_pin in other_pins:
            link = pin.link_to(other_pin)
            if link:
                return link