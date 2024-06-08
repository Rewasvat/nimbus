# NOTE: Having to hardcode the imports of widget classes since this was the only way I tried
# that worked having the classes and their documentation work with intellisense when importing
# this module from anywhere.

# Basic Widget types
from nimbus.utils.imgui_widgets.base import BaseWidget, LeafWidget, ContainerWidget, WidgetSystem

# Container Widget Types
from nimbus.utils.imgui_widgets.board import Board
from nimbus.utils.imgui_widgets.axis_list import AxisList
from nimbus.utils.imgui_widgets.panel import Panel
from nimbus.utils.imgui_widgets.canvas import Canvas

# Simple (Leaf) Widget Types
from nimbus.utils.imgui_widgets.rect import Rect
from nimbus.utils.imgui_widgets.label import Label
from nimbus.utils.imgui_widgets.corner import Corner
from nimbus.utils.imgui_widgets.button import Button
from nimbus.utils.imgui_widgets.progressbar import ProgressBar
