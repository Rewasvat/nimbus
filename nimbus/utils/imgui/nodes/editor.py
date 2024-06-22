from typing import Callable
from nimbus.utils.imgui.colors import Colors
from nimbus.utils.imgui.general import menu_item
from nimbus.utils.imgui.nodes.nodes import Node, NodePin, NodeLink, PinKind
from imgui_bundle import imgui, imgui_node_editor  # type: ignore


AllIDTypes = imgui_node_editor.NodeId | imgui_node_editor.PinId | imgui_node_editor.LinkId
"""Alias for all ID types in imgui-node-editor (NodeId, PinId and LinkId)"""


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


# TODO: copy/paste/cut (com suporte aos atalhos de teclado)
#   - testar o role de shortcuts do imgui-node-editor
# TODO: esquema de salvar estado pra ter CTRL+Z (UNDO)
# TODO: atalho de teclado pro Fit To Window
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
        """Callable used in the Editor's Background Context Menu to create a new node.

        The callable should draw the controls its needs to display all options of nodes to create. If user selects a node to create,
        the callable should return the new Node's instance. The new node doesn't need to be added to this editor, the editor does that automatically.

        Callable only receives a single argument: a NodePin argument. This is the pin the user pulled a link from and selected to create a new node.
        This might be None if the user simply clicked the background of the editor to create a new node anywhere. The callable thus can use this to
        filter possible Nodes to allow creation.
        """
        self._create_new_node_to_pin: NodePin = None
        """Pin from which a user pulled a new link to create a new link.

        This is used by the Background Context Menu. If this is not-None, then the menu was opened by pulling
        a link to create a new node."""
        self._selected_menu_node: Node = None
        self._selected_menu_pin: NodePin = None
        self._selected_menu_link: NodeLink = None

    def add_node(self, node: Node):
        """Adds a node to this NodeEditor. This will show the node in the editor, and allow it to be edited/updated.

        If this node has links to any other nodes, those nodes have to be in this editor as well for the links to be shown.
        This methods only adds the given node.

        Args:
            node (Node): Node to add to this editor. If node is already on the editor, does nothing.
        """
        if node not in self.nodes:
            self.nodes.append(node)

    def remove_node(self, node: Node):
        """Removes the given node from this NodeEditor. The node will no longer be shown in the editor, and no longer updateable
        through the node editor.

        Args:
            node (Node): Node to remove from this editor. If node isn't in this editor, does nothing.
        """
        if node in self.nodes:
            self.nodes.remove(node)

    def _compare_ids(self, a_id: AllIDTypes, b_id: AllIDTypes | int):
        """Compares a imgui-node-editor ID object to another to check if they match.

        Args:
            a_id (NodeId | PinId | LinkId): a ID object to check.
            b_id (NodeId | PinId | LinkId | int): a ID object or INT value to check against.

        Returns:
            bool: if the IDs are the same.
        """
        if isinstance(b_id, int):
            return a_id.id() == b_id
        return a_id == b_id

    def find_node(self, id: imgui_node_editor.NodeId | int):
        """Finds the node with the given NodeID amongst our nodes."""
        for node in self.nodes:
            if self._compare_ids(node.node_id, id):
                return node

    def find_pin(self, id: imgui_node_editor.PinId | int):
        """Finds the pin with the given PinID amongst all pins from our nodes."""
        for node in self.nodes:
            for pin in node.get_input_pins():
                if self._compare_ids(pin.pin_id, id):
                    return pin
            for pin in node.get_output_pins():
                if self._compare_ids(pin.pin_id, id):
                    return pin

    def find_link(self, id: imgui_node_editor.LinkId | int):
        """Finds the link with the given LinkID amongst all links, from all pins, from our nodes."""
        for node in self.nodes:
            for pin in node.get_input_pins():
                for link in pin.get_all_links():
                    if self._compare_ids(link.link_id, id):
                        return link
            for pin in node.get_output_pins():
                for link in pin.get_all_links():
                    if self._compare_ids(link.link_id, id):
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
                imgui.push_id(repr(node))
                if imgui.collapsing_header(node.node_title):
                    node.render_edit_details()
                    imgui.spacing()
                imgui.pop_id()

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
            node.editor = self
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

                if start_pin.pin_kind == PinKind.input:
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
                        link.delete()
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
            if pin:
                imgui.separator()
                if menu_item("Remove All Links"):
                    pin.delete_all_links()
                if pin.can_be_deleted:
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
                    self.add_node(new_node)
                    if self._create_new_node_to_pin:
                        self.try_to_link_node_to_pin(new_node, self._create_new_node_to_pin)
                    imgui_node_editor.set_node_position(new_node.node_id, imgui_node_editor.screen_to_canvas(pos))
            if self._create_new_node_to_pin is None:
                imgui.separator()
                if menu_item("Fit to Window"):
                    self.fit_to_window()
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
        if pin.pin_kind == PinKind.input:
            other_pins = node.get_output_pins()
        else:
            other_pins = node.get_input_pins()
        for other_pin in other_pins:
            link = pin.link_to(other_pin)
            if link:
                return link

    def get_graph_area(self, margin: float = 10):
        """Gets the graph's total area.

        This is the bounding box that contains all nodes in the editor, as they are positioned at the moment.

        Args:
            margin (float, optional): Optional margin to add to the returned area. The area will be expanded by this amount
            to each direction (top/bottom/left/right). Defaults to 10.

        Returns:
            Rectangle: the bounding box of all nodes together. This might be None if no nodes exist in the editor.
        """
        area = None
        for node in self.nodes:
            if area is None:
                area = node.node_area
            else:
                area += node.node_area
        if area is not None:
            area.expand(margin)
        return area

    def fit_to_window(self):
        """Changes the editor's viewport position and zoom in order to make all content in the editor
        fit in the window (the editor's area)."""
        imgui_node_editor.navigate_to_content()

    def __getstate__(self):
        """Pickle Protocol: overriding getstate to allow pickling this class.
        This should return a dict of data of this object to reconstruct it in ``__setstate__`` (usually ``self.__dict__``).
        """
        state = vars(self).copy()
        state["_create_new_node_to_pin"] = None
        state["_selected_menu_node"] = None
        state["_selected_menu_pin"] = None
        state["_selected_menu_link"] = None
        state["__picklestate_all_links"] = get_all_links_from_nodes(self.nodes)
        return state

    def __setstate__(self, state: dict[str]):
        """Pickle Protocol: overriding setstate to allow pickling this class.
        This receives the ``state`` data returned from ``self.__getstate__`` that was pickled, and now being unpickled.

        Use the data to rebuild this instance.
        NOTE: the class ``self.__init__`` was probably NOT called according to Pickle protocol.
        """
        links: list[NodeLink] = state.pop("__picklestate_all_links")
        self.__dict__.update(state)
        for node in self.nodes:
            node.editor = self
        for link in links:
            # Update link with its pins
            link.start_pin = self.find_pin(link.start_pin)
            link.end_pin = self.find_pin(link.end_pin)
            # Update pins with the link
            link.start_pin._links[link.end_pin] = link
            link.end_pin._links[link.start_pin] = link
