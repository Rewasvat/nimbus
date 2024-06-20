import math
from typing import Callable
from nimbus.utils.imgui.general import menu_item
from nimbus.utils.imgui.colors import Color, Colors
from nimbus.utils.imgui.math import Vector2, Rectangle
from nimbus.utils.idgen import IDManager
from imgui_bundle import imgui, imgui_node_editor  # type: ignore


# TODO: mudar cor de background do node header (mostly pra diferenciar "tipos" de nodes, ver exemplos/cores nas coisas da tapps)
# TODO: mudar cor de background do node content (mostly pra "nodes especiais")
# TODO: permitir um sub-title abaixo do name do nome, no header.
# TODO: linha separando header do content.
# TODO: reciclar node/pin/link-ids caso o tal objeto seja deletado.
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
        self.node_id = imgui_node_editor.NodeId(IDManager().get("GlobalNodeSystem").create())
        self.can_be_deleted = True
        """If this object can be deleted by user-interaction."""
        self.is_selected = False
        """If this node is selected by the user in the node-editor."""
        self.editor: NodeEditor = None
        """NodeEditor system this node is associated with. This is the NodeEditor that is handling/editing this node."""
        self._node_title: str = None

    @property
    def node_title(self) -> str:
        """Title/name of node to display in NodeEditor. If none, defaults to ``str(self)``."""
        return self._node_title if self._node_title else str(self)

    @node_title.setter
    def node_title(self, value: str):
        self._node_title = value

    @property
    def node_area(self) -> Rectangle:
        """Gets the node's area (position and size).
        This is the rectangle that bounds the node."""
        pos = imgui_node_editor.get_node_position(self.node_id)
        size = imgui_node_editor.get_node_size(self.node_id)
        return Rectangle(pos, size)

    def draw_node(self):
        """Draws the node in imgui's Node Editor.

        This should only be called inside a imgui-node-editor rendering context.
        """
        imgui_node_editor.begin_node(self.node_id)
        imgui.push_id(repr(self))
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
        imgui.pop_id()
        imgui_node_editor.end_node()

        self.is_selected = imgui_node_editor.is_node_selected(self.node_id)

    def draw_node_header(self):
        """Used internally to draw the node's header region.

        This is a horizontally aligned region in the top part of the node.
        Displays the node's name (``str(self)``), and a tooltip when the name is hovered, containing
        the docstring of this object's type.
        """
        imgui.begin_horizontal(f"{repr(self)}NodeHeader")
        imgui.spring(1)
        imgui.text_unformatted(self.node_title)
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
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_alignment, Vector2(0, 0.5))
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_size, Vector2(0, 0))
        for i, pin in enumerate(self.get_input_pins()):
            if i > 0:
                imgui.spring(0)
            pin.draw_node_pin()
        num_ins = len(self.get_input_pins())
        num_outs = len(self.get_output_pins())
        if num_outs > num_ins:
            # NOTE: WORKAROUND! This is a fix for a bizarre bug in which the >Parent pin in container widgets (and only it)
            # changes its Y position according to the editor's zoom. The pin itself, as seen by links going out of it and highlight
            # area, is in the correct place. But its contents (the >Parent), regardless of it, moves away.
            size = imgui.get_text_line_height()
            for i in range(num_outs - num_ins):
                imgui.spring(0)
                imgui.dummy((size, size))
        imgui.spring(1, 0)
        imgui_node_editor.pop_style_var(2)
        imgui.end_vertical()

    def draw_node_outputs(self):
        """Used internally to draw the node's output region.

        This is a vertically aligned region, below the header to the right (right/bottom of the node).
        It displays all output pins from the node (see ``self.get_output_pins()``)
        """
        imgui.begin_vertical(f"{repr(self)}NodeOutputs", align=1)
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_alignment, Vector2(1, 0.5))
        imgui_node_editor.push_style_var(imgui_node_editor.StyleVar.pivot_size, Vector2(0, 0))
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

    def walk_in_graph(self, callback: Callable[['Node', int], bool], allowed_outputs: list[type['NodePin']], starting_level=0,
                      walked_nodes: set['Node'] = None):
        """Walks through the graph this node belongs to, starting with it.

        This calls ``callback`` for a node (starting with ``self``) passing the current level. If the callback returns True,
        this will go through all links from all output pins which are instances of types in the ``allowed_outputs`` list.
        For each of these links, this method will be called recursively for the node on the other side of the link.

        Thus, callback will be called for this node and all others that follow the given output pins.
        Callback (and this method) will not be called multiple times for the same node.

        Args:
            callback (Callable[[Node, int], bool]): The callable to be executed for each node we pass by. The callback will receive the node
            instance itself, and the current level. The current level increases by 1 each time we go from one node to the next.
            allowed_outputs (list[type[NodePin]]): List or tuple of NodePin classes for output pins. Pins that are of these classes will be used to
            walk through to the next nodes in the graph via their links.
            starting_level (int, optional): The current level for this ``walk_in_graph`` execution. The ``callback`` will be called with this level.
            This increments internally as the graph is walked through. User may pass this when initially calling this method in the starting node,
            altho its recommended not to. Defaults to 0.
            walked_nodes (set[Node], optional): Set of nodes this walk has already passed through. The walk ignores nodes that are in this set.
            This is used internally to control which nodes we already walked through. Defaults to None.
        """
        if walked_nodes is None:
            walked_nodes = set()
        if self in walked_nodes:
            return
        walked_nodes.add(self)
        ok = callback(self, starting_level)
        if not ok:
            return
        for pin in self.get_output_pins():
            if isinstance(pin, tuple(allowed_outputs)):
                for link in pin.get_all_links():
                    link.end_pin.parent_node.walk_in_graph(callback, allowed_outputs, starting_level + 1, walked_nodes)

    def reposition_nodes(self, allowed_outputs: list[type['NodePin']] = None):
        """Rearranges all nodes following this one, from links of the allowed output pins.

        The nodes will be repositioned after this according to their depth in the graph, and spaced between one another.

        Args:
            allowed_outputs (list[type[NodePin]]): List or tuple of NodePin classes for output pins. Pins that are of these classes will be used to
            walk through to the next nodes in the graph via their links.
        """
        if allowed_outputs is None:
            allowed_outputs = [NodePin]

        # NOTE: marca ponto de save pra undo
        max_width_by_level: dict[int, float] = {}
        total_height_by_level: dict[int, float] = {}

        horizontal_spacing = math.inf
        vertical_spacing = 10

        def check_position(node: Node, level: int):
            nonlocal horizontal_spacing
            node_size = node.node_area.size
            total_height = total_height_by_level.get(level, -vertical_spacing)
            total_height = total_height + node_size.y + vertical_spacing
            total_height_by_level[level] = total_height

            max_width = max_width_by_level.get(level, 0)
            max_width_by_level[level] = max(max_width, node_size.x)
            horizontal_spacing = min(node_size.x, horizontal_spacing)
            return True

        self.walk_in_graph(check_position, allowed_outputs)

        total_graph_width = sum(max_width_by_level.values()) + (len(max_width_by_level)-1)*horizontal_spacing
        current_height_by_level = {}
        offset = Vector2()

        def move_node(node: Node, level: int):
            nonlocal offset
            x = -total_graph_width * 0.5
            for index, width in max_width_by_level.items():
                if index == level:
                    break
                x = x + width + horizontal_spacing

            current_height = current_height_by_level.get(level, total_height_by_level[level] * -0.5)
            y = current_height
            current_height = current_height + node.node_area.size.y + vertical_spacing
            current_height_by_level[level] = current_height

            position = Vector2(x, y) - node.node_area.size * 0.5
            if level > 0:
                imgui_node_editor.set_node_position(node.node_id, position + offset)
            else:
                offset = node.node_area.position - position
            return True

        self.walk_in_graph(move_node, allowed_outputs)
        self.editor.fit_to_window()

    def __getstate__(self):
        """Pickle Protocol: overriding getstate to allow pickling this class.
        This should return a dict of data of this object to reconstruct it in ``__setstate__`` (usually ``self.__dict__``).
        """
        state = vars(self).copy()
        state["node_id"] = self.node_id.id()
        state["editor"] = None  # NodeEditor handles re-setting our editor attribute
        return state

    def __setstate__(self, state: dict[str]):
        """Pickle Protocol: overriding setstate to allow pickling this class.
        This receives the ``state`` data returned from ``self.__getstate__`` that was pickled, and now being unpickled.

        Use the data to rebuild this instance.
        NOTE: the class ``self.__init__`` was probably NOT called according to Pickle protocol.
        """
        self.__dict__.update(state)
        self.node_id = imgui_node_editor.NodeId(state["node_id"])
        for pin in self.get_input_pins() + self.get_output_pins():
            pin._update_state_after_recreation(self)


AllIDTypes = imgui_node_editor.NodeId | imgui_node_editor.PinId | imgui_node_editor.LinkId
"""Alias for all ID types in imgui-node-editor (NodeId, PinId and LinkId)"""
PinKind = imgui_node_editor.PinKind
"""Alias for ``imgui_node_editor.PinKind``: enumeration of possible pin kinds."""


# TODO: ter default pin content?
class NodePin:
    """An Input or Output Pin in a Node.

    A pin is the point in a node used to make connections (links - see ``NodeLink``) to other node (to pins in other nodes).

    Implementations should override the method ``draw_node_pin_contents()`` to draw the pin's contents.
    """

    def __init__(self, parent: Node, kind: PinKind, name: str):
        self.parent_node: Node = parent
        # TODO: talvez tenhamos que atualizar a associacao do pin_name->id se pin name trocar
        self.pin_name = name
        self.pin_id = imgui_node_editor.PinId(IDManager().get("GlobalNodeSystem").create(f"node{parent.node_id.id()}_pin_{name}"))
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
        if self.pin_kind == PinKind.output:
            imgui.text_unformatted(self.pin_name)
        self.draw_node_pin_contents()
        if self.pin_kind == PinKind.input:
            imgui.text_unformatted(self.pin_name)
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
        raise NotImplementedError

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

    def remove_all_links(self):
        """Removes all links from this pin."""
        for pin in list(self._links.keys()):
            self.remove_link_to(pin)

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
        if self.pin_kind == PinKind.output:
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

    def __getstate__(self):
        """Pickle Protocol: overriding getstate to allow pickling this class.
        This should return a dict of data of this object to reconstruct it in ``__setstate__`` (usually ``self.__dict__``).
        """
        state = vars(self).copy()
        state["pin_id"] = self.pin_id.id()
        state["parent_node"] = None  # Node re-creating us should handle setting parent_node.
        state["_links"] = {}  # NodeEditor handles re-creating all links, since each link needs at least 2 nodes/pins to be already recreated.
        return state

    def __setstate__(self, state: dict[str]):
        """Pickle Protocol: overriding setstate to allow pickling this class.
        This receives the ``state`` data returned from ``self.__getstate__`` that was pickled, and now being unpickled.

        Use the data to rebuild this instance.
        NOTE: the class ``self.__init__`` was probably NOT called according to Pickle protocol.
        """
        self.__dict__.update(state)
        self.pin_id = imgui_node_editor.PinId(state["pin_id"])

    def _update_state_after_recreation(self, parent: Node):
        """Internal method to update state of this Pin instance after recreation (unpickling).
        This is called by the parent node to update its pins' state after it (the node) is ready.

        NOTE: not to be called outside ``Node.__setstate__`` chains.

        Args:
            parent (Node): parent node that is recreating this pin.
        """
        self.parent_node = parent


class NodeLink:
    """The connection between an input and output pins on two different nodes.

    The link is a line connecting pins A and B, where A is a output pin in Node X, and B is a input pin on Node Y.
    It always is a output->input pin connection between different pins/different nodes.

    This class essentially only holds data about the link and a method to render it. Most node-related logic is located in the
    ``Node`` and ``NodePin`` classes. As such, implementations don't need to change/overwrite anything about this class.
    """

    def __init__(self, start_pin: NodePin, end_pin: NodePin, id: imgui_node_editor.LinkId = None, color: Color = None, thickness: float = None):
        self.link_id = imgui_node_editor.LinkId(IDManager().get("GlobalNodeSystem").create()) if id is None else id
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

    def animate_flow(self, reversed=False):
        """Triggers a temporary animation of "flowing" in this link, from the start to the end pin.

        This animation quite visually indicates a flow of one pin to the other.
        Flow animation parameters can be changed in Imgui Node Editor's Style.

        Args:
            reversed (bool, optional): True if animation should be reversed (from end pin to start pin). Defaults to False.
        """
        direction = imgui_node_editor.FlowDirection.backward if reversed else imgui_node_editor.FlowDirection.forward
        imgui_node_editor.flow(self.link_id, direction)

    def __str__(self):
        return f"({self.start_pin})== link to =>({self.end_pin})"

    def __getstate__(self):
        """Pickle Protocol: overriding getstate to allow pickling this class.
        This should return a dict of data of this object to reconstruct it in ``__setstate__`` (usually ``self.__dict__``).
        """
        state = vars(self).copy()
        state["link_id"] = self.link_id.id()
        state["start_pin"] = self.start_pin.pin_id.id()
        state["end_pin"] = self.end_pin.pin_id.id()
        return state

    def __setstate__(self, state: dict[str]):
        """Pickle Protocol: overriding setstate to allow pickling this class.
        This receives the ``state`` data returned from ``self.__getstate__`` that was pickled, and now being unpickled.

        Use the data to rebuild this instance.
        NOTE: the class ``self.__init__`` was probably NOT called according to Pickle protocol.
        """
        self.__dict__.update(state)
        # NodeEditor handles recreating all links, after all nodes/pins are recreated.
        self.link_id = imgui_node_editor.LinkId(state["link_id"])


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


# TODO: copy/paste/cut
# TODO: esquema de salvar estado pra ter CTRL+Z (UNDO)
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
            if pin:
                imgui.separator()
                if menu_item("Remove All Links"):
                    pin.remove_all_links()
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
