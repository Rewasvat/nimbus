# NOTE: Having to hardcode the imports of widget classes since this was the only way I tried
# that worked having the classes and their documentation work with intellisense when importing
# this module from anywhere.

# Basic Widget types
from nimbus.utils.imgui.widgets.system import UISystem, UIManager
from nimbus.utils.imgui.widgets.base import BaseWidget, LeafWidget, ContainerWidget
from nimbus.utils.imgui.widgets.system_node import UseSystem

# Container Widget Types
from nimbus.utils.imgui.widgets.board import Board
from nimbus.utils.imgui.widgets.axis_list import AxisList
from nimbus.utils.imgui.widgets.panel import Panel
from nimbus.utils.imgui.widgets.canvas import Canvas

# Simple (Leaf) Widget Types
from nimbus.utils.imgui.widgets.rect import Rect
from nimbus.utils.imgui.widgets.label import Label
from nimbus.utils.imgui.widgets.corner import Corner
from nimbus.utils.imgui.widgets.button import Button
from nimbus.utils.imgui.widgets.progressbar import ProgressBar

# LCARS
import nimbus.utils.imgui.widgets.lcars
