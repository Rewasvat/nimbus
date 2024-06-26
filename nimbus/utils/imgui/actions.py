import click
import traceback
from imgui_bundle import imgui, imgui_node_editor  # type: ignore
from nimbus.utils.imgui.nodes import Node, NodePin, PinKind
from nimbus.utils.imgui.nodes_common import CommonNode, input_property, output_property
from nimbus.utils.imgui.colors import Colors
from nimbus.utils.imgui.math import Vector2
from nimbus.utils.imgui.general import menu_item, not_user_creatable


class ActionFlow(NodePin):
    """A Flow pin for Action nodes.

    Flow pins control execution flow of actions.

    When a action executes, it triggers some of its output flow pins. These will then
    trigger the input-flow pins they're connected to, thus triggering those pin's actions.

    Input Flow pins are expected to be in Action nodes, for triggering them.
    Output Flow pins however may be present in any kind of nodes, as other sources of flow execution.
    """

    def __init__(self, parent: Node, kind: PinKind, name="FLOW"):
        super().__init__(parent, kind, name)
        self.parent_node: Action = parent  # to update type-hint.

    def draw_node_pin_contents(self):
        draw = imgui.get_window_draw_list()
        size = imgui.get_text_line_height()
        p1 = Vector2.from_cursor_screen_pos()
        draw.path_line_to(p1)
        draw.path_line_to(p1 + (size * 0.6, 0))
        draw.path_line_to(p1 + (size, size * 0.5))
        draw.path_line_to(p1 + (size * 0.6, size))
        draw.path_line_to(p1 + (0, size))
        draw.path_line_to(p1)
        color = imgui.get_color_u32(Colors.white)
        if self.is_linked_to_any():
            draw.path_fill_convex(color)
        else:
            thickness = 2
            draw.path_stroke(color, thickness=thickness)
        imgui.dummy((size, size))

    def can_link_to(self, pin: NodePin) -> tuple[bool, str]:
        ok, msg = super().can_link_to(pin)
        if not ok:
            return ok, msg
        if not isinstance(pin, ActionFlow):
            return False, "Can only link to a Action's Flow pin."
        return True, "success"

    def trigger(self):
        """Triggers this Flow pin, which'll:
        * If this is a input flow pin, will ``execute()`` our parent Action. This happens inside a TRY/EXCEPT block, printing to
        terminal any Exceptions.
        * If this is a output flow pin, will call this same ``trigger()`` in all input flow-pins linked to us.

        So this executes one or more Actions, which in turn will execute other actions, thus starting a cascate of action processing.
        """
        if self.pin_kind == PinKind.input:
            # If we are a input flow pin, we just execute our node.
            try:
                self.parent_node.execute()
            except Exception:
                # TODO: melhorar msg pra ser mais fácil identificar qual action node que falhou.
                click.secho(f"Error while executing action {self.parent_node}:\n{traceback.format_exc()}", fg="red")
        else:
            # If we are a output flow pin, we trigger all input pins we're connected to.
            # Since flow pins only connect to flow pins, they'll have this trigger() method.
            for in_pin in self._links.keys():
                in_pin.trigger()

    def render_edit_details(self):
        self._draw_test_trigger_menu_item()

    def _draw_test_trigger_menu_item(self):
        """Triggers this flow pin, which will trigger linked input actions.

        Those actions in turn will trigger their output flows, possibly starting a cascate of action executions.

        This button is intended for testing purposes only since it only allows to trigger from a Node Editor.
        """
        # This is implemented as a method just to be easy to have the docstring together.
        if menu_item("Test Trigger"):
            self.trigger()
        imgui.set_item_tooltip(self._draw_test_trigger_menu_item.__doc__)

    def __str__(self):
        return f"{self.pin_kind.name.capitalize()} ActionFlow {self.pin_name}"


@not_user_creatable
class Action(CommonNode):
    """Generic code/logic execution node. A Action is a node that:
    * Is triggered by a ActionFlow pin.
    * May receive input data, from linked data pins or from its defined default values.
    * Executes some logic
    * May send output data, to be used by other nodes.
    * May have ActionFlow output pins, which can be used to trigger other actions.

    As such, actions define a system of generic logic execution akin to a node-based visual language.
    """

    def __init__(self):
        super().__init__()
        self._inputs.append(ActionFlow(self, PinKind.input, "Execute"))
        self._outputs.append(ActionFlow(self, PinKind.output, "Trigger"))
        self.create_data_pins_from_properties()

    def execute(self):
        """Executes the logic of this action.

        Subclasses should overwrite this method to implement their logic. Default behavior in ``Action`` base class is to
        raise an error.

        To receive dynamic data from the node system as input, the Action should define ``@input_property()`` properties.
        The action can then use this properties to get its input value. Input data can come from the input data pin's default value,
        or from the output data pin it is connected to.

        To send dynamic data from the action's logic as output, the Action should define ``@output_property()`` properties.
        The action can then use the property's setter to set its output value.

        When implementing its logic in this method, the Action subclass should then:
        * Use its input property's getters to get its input data.
        * Process its data, do its work, etc.
        * Set its output data using its output property's setters.
        * Use ``trigger_flow(name)`` to trigger the next node, connected to our ActionFlow output pin with the given name.
        """
        raise NotImplementedError

    def trigger_flow(self, name: str = "Trigger"):
        """Triggers our ActionFlow output pin of the given name.

        The ``execute`` implementation of Action subclasses should call this to trigger the next actions in the hierarchy
        (after setting any output data!).

        Args:
            name (str, optional): Name of the output flow pin to trigger. Defaults to "Trigger", which is Action's
            default output pin.
        """
        for flow in [pin for pin in self._outputs if isinstance(pin, ActionFlow)]:
            if flow.pin_name == name:
                flow.trigger()


class Print(Action):
    """Prints a value to the terminal."""

    @input_property()
    def text(self) -> str:
        """Text to print."""

    def execute(self):
        click.secho(self.text)
        self.trigger_flow()


# TODO: criar as várias actions que já precisaremos de inicio
# TODO: mudar design básico dos nodes, pra diferenciar entre Widgets, Actions, e provavelmente Sensors tb se ele for um node em si.
# TODO: ver se dá pra fazer um decorator que ao ser posto numa function, cria uma action que:
#   - recebe os mesmos params da func como inputs da action
#      - principalmente, ver se isso funcionaria com métodos de classes, onde o `self` seria um input a receber tb.
#   - tem os mesmos outputs como os return values da func
#       - se for output tuple[a,b], separa em outputs diferentes
#   - no execute, a action pega os inputs e passa e executa a func, seta os returns como outputs e vai embora.
#   - isso daria problema com save/load. Pro pickle funcionar, a classe precisa existir na raiz de algum módulo.
#       - ai essas coisas que criam classes dinamicamente (dentro de uma função por exemplo) caga o pickle
#       - pesquisar, talvez dê pra adaptar o save/load do pickle pra funcionar com classes dinamicas assim.
# TODO: criar action que só tem um unico DataPin de output do tipo T. Nenhum flow. seria action de criar um valor estatico.
#   - teria que criar uma derivada pra cada tipo (cada tipo no TypeDatabase que não seja Noop) parece bom
#   - seria melhor se der pra gerar essas classes automaticamente num FOR or something.
