import nimbus.utils.imgui.type_editor as types
from nimbus.utils.imgui.widgets.base import LeafWidget, WidgetColors
from nimbus.utils.imgui.widgets.label import TextObject, Fonts
from nimbus.utils.imgui.widgets.lcars.alerts import XAMLPath
from nimbus.utils.imgui.colors import Color, Colors
from nimbus.utils.imgui.math import Vector2
from imgui_bundle import imgui


class SFCM(LeafWidget):
    """Purely visual STARFLEET COMMAND badge widget.

    The badge graphics itself has a fixed aspect-ratio to preserve its proportions, and will try to fit to the slot's area.
    So depending on slot size, some empty space may be left on the left/right or top/bottom sides.
    """

    def __init__(self):
        super().__init__()
        self.node_header_color = WidgetColors.Assets  # TODO: que cor pra isso? das basicas é Assets ou Primitives. Ou fazer outra cor pra LCARS?
        self._out_margin = 10
        self._text = TextObject("STARFLEET COMMAND")
        self._text.scale = 2.0
        self._text.font = Fonts.LCARS_BOLD
        self._xaml_scale = Vector2(1/192.760, 1/192.760)
        self._white = Colors.white
        self._blue = Color.from_hex("FF0E5FD8", use_argb=True)
        self._black = Color.from_hex("ff221e1f", use_argb=True)
        self._build()

    @types.float_property()
    def out_margin(self) -> float:
        """The margin of the borders/corners to the edges of our slot's available area."""
        return self._out_margin

    @out_margin.setter
    def out_margin(self, value: float):
        self._out_margin = value

    def _build(self):
        """Builds the internal XAMLPaths and other data we need to draw this badge.
        Usually this should only be called once, when this object is constructed (this is done automatically)."""
        left_laurel_path = [
            # LEFT SIDE
            "M 39.457,33.017 C 40.086,28.766 43.954,21.153 47.767,19.403 C 47.890,20.838 47.261,22.082 47.084,23.340 C 50.200,21.536 54.082,17.654 \
                58.510,16.847 C 55.886,22.028 51.772,26.770 47.275,30.393 C 43.776,32.333 43.147,32.771 39.470,33.017 L 39.457,33.017 Z",
            "M 30.969,46.945 C 30.531,39.509 32.404,31.896 37.270,27.153 C 36.833,30.652 36.149,33.960 36.395,37.582 C 38.514,37.391 41.138,36.830 \
                43.134,35.901 C 42.382,38.648 34.454,46.644 30.955,46.958 L 30.955,46.958 L 30.969,46.945 Z",
            "M 27.784,36.885 C 27.784,36.885 27.593,48.626 28.727,51.688 C 32.158,51.496 33.279,51.182 36.286,49.815 C 35.220,53.751 28.850,59.683 \
                26.609,59.998 C 22.987,52.439 23.738,44.006 27.798,36.899 L 27.798,36.899 L 27.784,36.885 Z",
            "M 25.351,73.229 C 18.299,66.545 16.918,57.934 19.419,49.063 C 21.292,54.120 22.536,59.861 25.857,64.180 C 28.358,63.428 30.723,62.062 \
                33.033,60.996 C 32.349,65.684 29.042,70.181 25.351,73.228 C 25.351,73.228 25.351,73.228 25.351,73.229 Z",
            "M 13.802,62.308 C 16.617,67.925 20.485,75.853 25.912,79.598 C 28.030,78.914 30.532,75.730 31.967,73.980 C 31.844,78.914 29.219,83.780 \
                26.281,87.348 C 17.164,85.407 12.421,72.422 13.788,62.308 L 13.788,62.308 L 13.802,62.308 Z",
            "M 11.683,76.796 C 14.116,81.047 22.358,91.968 28.235,93.403 C 30.039,93.280 32.855,86.965 33.538,85.475 C 33.292,90.027 33.169,97.148 \
                30.285,100.961 C 18.668,100.838 11.054,88.291 11.683,76.796 L 11.683,76.796 Z",
            "M 14.362,96.273 C 18.545,100.264 26.417,106.579 32.718,106.579 C 34.345,104.460 35.903,100.578 37.147,97.148 C 38.527,102.765 \
                38.527,108.014 37.461,113.755 C 26.404,115.750 16.986,106.633 14.362,96.273 C 14.362,96.273 14.362,96.273 14.362,96.273 Z",
            "M 46.332,124.566 C 38.842,125.318 28.905,123.760 25.980,117.076 C 31.283,118.456 35.343,118.880 40.960,118.825 C 42.204,115.709 \
                43.079,112.524 43.899,109.394 C 46.141,113.891 46.332,119.577 46.332,124.566 C 46.332,124.566 46.332,124.566 46.332,124.566 Z",
            "M 36.340,128.311 C 41.329,128.872 46.141,128.749 50.009,128.120 C 50.514,123.869 50.569,119.564 50.637,118.251 C 53.385,122.311 \
                57.690,127.737 56.761,133.232 C 49.025,134.476 42.081,133.983 36.340,128.297 L 36.340,128.297 L 36.340,128.311 Z",
            "M 77.987,146.039 C 76.675,145.041 75.172,143.797 73.928,142.786 C 76.798,142.594 83.113,143.100 85.600,141.351 C 83.919,137.605 \
                60.998,137.482 57.184,136.362 C 61.490,133.806 61.175,134.927 60.123,130.238 C 71.044,135.665 84.097,133.355 91.163,142.225 \
                C 86.981,146.162 83.236,145.847 77.987,146.039 L 77.987,146.039 L 77.987,146.039 Z",
        ]
        right_laurel_path = [
            # RIGHT SIDE
            "M 153.477,33.017 C 152.793,28.766 148.925,21.153 145.112,19.403 C 144.989,20.838 145.672,22.082 145.795,23.340 C 142.679,21.536 \
                138.797,17.654 134.368,16.847 C 137.047,22.028 141.107,26.770 145.604,30.393 C 149.103,32.333 149.731,32.771 153.477,33.017 Z",
            "M 161.910,46.945 C 162.347,39.509 160.475,31.896 155.609,27.153 C 156.114,30.652 156.730,33.960 156.483,37.582 C 154.420,37.391 \
                151.795,36.830 149.745,35.901 C 150.497,38.648 158.424,46.644 161.923,46.958 L 161.923,46.958 L 161.910,46.945 Z",
            "M 165.163,36.885 C 165.163,36.885 165.286,48.626 164.165,51.688 C 160.734,51.496 159.668,51.182 156.607,49.815 C 157.673,53.751 \
                164.042,59.683 166.352,59.998 C 169.906,52.439 169.168,44.006 165.163,36.899 L 165.163,36.899 L 165.163,36.885 Z",
            "M 167.596,73.229 C 174.594,66.545 175.961,57.934 173.459,49.063 C 171.587,54.120 170.343,59.861 167.090,64.180 C 164.534,63.428 \
                162.224,62.062 159.846,60.996 C 160.529,65.684 163.837,70.181 167.582,73.228 L 167.582,73.228 L 167.596,73.229 Z",
            "M 179.145,62.308 C 176.275,67.925 172.407,75.853 166.967,79.598 C 164.848,78.914 162.347,75.730 160.912,73.980 C 161.035,78.914 \
                163.659,83.780 166.598,87.348 C 175.715,85.407 180.457,72.422 179.145,62.308 L 179.145,62.308 L 179.145,62.308 Z",
            "M 181.209,76.796 C 178.776,81.047 170.534,91.968 164.657,93.403 C 162.908,93.280 160.106,86.965 159.354,85.475 C 159.600,90.027 \
                159.723,97.148 162.607,100.961 C 174.225,100.838 181.838,88.291 181.209,76.796 L 181.209,76.796 Z",
            "M 178.530,96.273 C 174.348,100.264 166.475,106.579 160.174,106.579 C 158.547,104.460 156.989,100.578 155.745,97.148 C 154.365,102.765 \
                154.365,108.014 155.431,113.755 C 166.543,115.750 175.906,106.633 178.530,96.273 L 178.530,96.273 L 178.530,96.273 Z",
            "M 146.629,124.566 C 154.064,125.318 163.987,123.760 166.926,117.076 C 161.623,118.456 157.618,118.880 151.946,118.825 C 150.702,115.709 \
                149.827,112.524 149.075,109.394 C 146.765,113.891 146.642,119.577 146.642,124.566 L 146.642,124.566 L 146.629,124.566 Z",
            "M 156.620,128.311 C 151.631,128.872 146.752,128.749 142.884,128.120 C 142.378,123.869 142.323,119.564 142.323,118.251 C 139.508,122.311 \
                135.270,127.737 136.200,133.232 C 143.950,134.476 150.880,133.983 156.620,128.297 L 156.620,128.297 L 156.620,128.311 Z",
            "M 114.973,146.039 C 116.285,145.041 117.721,143.797 119.033,142.786 C 116.094,142.594 109.793,143.100 107.292,141.351 C 108.973,137.605 \
                131.894,137.482 135.763,136.362 C 131.389,133.806 131.703,134.927 132.769,130.238 C 121.903,135.665 108.795,133.355 101.729,142.225 \
                C 105.980,146.162 109.656,145.847 114.973,146.039 Z",
        ]
        self.laurels = [
            XAMLPath(" ".join(left_laurel_path), self._xaml_scale),
            XAMLPath(" ".join(right_laurel_path), self._xaml_scale)
        ]
        self.laurels[1].reverse()  # Right XAML path should be reversed to render properly.

        self.star_circles = [
            (51.485, 57.578, 60.066),
            (54.984, 64.194, 67.939),
            (51.293, 78.245, 81.921),
            (52.414, 83.493, 87.238),
            (54.164, 95.234, 97.722),
            (62.775, 102.916, 105.403),
            (68.146, 110.160, 112.647),
            (66.397, 102.916, 105.403),
            (77.509, 100.674, 103.982),
            (78.630, 106.169, 109.476),
            (75.513, 104.296, 106.784),
            (103.055, 118.101, 120.589),
            (100.745, 107.481, 109.969),
            (98.189, 104.925, 107.413),
            (106.554, 104.050, 107.413),
            (62.351, 70.891, 73.324),
            (66.602, 81.880, 84.368),
            (70.661, 75.142, 77.630),
            (65.098, 92.255, 96.806),
            (70.278, 96.382, 98.870),
            (72.028, 91.954, 95.699),
            (75.650, 93.826, 96.314),
            (73.340, 86.459, 88.947),
            (77.400, 86.651, 89.138),
            (81.896, 92.268, 94.756),
            (84.206, 95.453, 100.565),
            (103.246, 98.884, 101.371),
            (101.688, 95.070, 98.378),
            (131.717, 99.936, 102.752),
            (125.224, 79.393, 82.195),
            (83.332, 66.217, 68.704),
            (91.382, 80.637, 83.452),
            (91.013, 87.443, 89.931),
            (82.894, 82.578, 85.065),
            (89.140, 76.577, 79.065),
            (96.822, 75.948, 78.436),
            (96.016, 82.072, 84.559),
            (105.939, 96.929, 99.417),
            (102.631, 86.623, 89.111),
            (106.813, 80.008, 82.496),
            (114.372, 76.755, 79.243),
            (99.569, 78.559, 82.796),
            (95.824, 90.983, 95.221),
            (139.098, 86.118, 90.355),
            (113.689, 69.688, 73.926),
            (106.950, 71.998, 74.814),
            (136.610, 74.814, 77.616),
            (119.620, 72.504, 75.320),
            (117.242, 68.076, 70.891),
            (104.435, 69.511, 72.313),
            (96.125, 58.590, 61.392),
            (112.048, 59.656, 62.458),
            (117.229, 58.590, 61.392),
            (122.791, 62.772, 65.588),
            (126.482, 63.893, 66.695),
            (136.542, 57.086, 59.834),
            (130.295, 54.585, 57.387),
            (126.168, 56.020, 58.836),
            (121.179, 53.082, 55.897),
            (115.247, 52.576, 55.392),
            (96.016, 71.055, 74.800),
            (95.893, 64.372, 68.117),
            (118.746, 62.130, 65.875),
            (134.478, 60.257, 64.003),
            (140.724, 63.811, 67.488),
            (140.095, 51.756, 55.501),
            (126.728, 46.576, 50.321),
            (129.161, 50.703, 53.519),
            (131.402, 44.266, 47.081),
            (123.092, 41.395, 44.143),
            (126.783, 34.520, 37.322),
            (112.732, 25.089, 27.905),
            (103.178, 26.962, 29.709),
            (92.940, 37.076, 39.892),
            (77.577, 44.443, 47.245),
            (69.021, 42.503, 46.248),
            (85.628, 43.446, 47.191),
            (77.632, 26.333, 30.010),
        ]
        self.star_crosses = [
            "M 112.240,74.623 C 114.044,84.983 112.240,83.425 122.737,85.120 C 111.994,86.801 113.935,85.311 112.240,95.617 \
                C 110.804,85.557 112.117,86.692 101.688,85.120 C 111.871,83.493 110.367,84.928 112.240,74.623 L 112.240,74.623 Z",
            "M 106.554,46.152 C 108.549,57.209 106.622,55.583 117.789,57.332 C 106.294,59.205 108.358,57.524 106.608,68.513 \
                C 104.982,57.838 106.485,59.027 95.305,57.332 C 106.171,55.583 104.613,57.141 106.540,46.152 L 106.540,46.152 L 106.554,46.152 Z",
            "M 79.955,60.394 C 82.265,73.256 80.024,71.383 93.009,73.379 C 79.641,75.566 82.019,73.625 80.024,86.432 \
                C 78.151,73.939 79.832,75.320 66.916,73.379 C 79.532,71.383 77.714,73.188 79.969,60.394 L 79.969,60.394 L 79.955,60.394 Z",
        ]
        self.star_crosses = [XAMLPath(p, self._xaml_scale) for p in self.star_crosses]

    def _draw_badge(self):
        """Draws this badge using imgui."""
        base_pos = self._pos + self.out_margin
        base_size = self._area - self.out_margin * 2
        ratio = 1.0 / self._xaml_scale.aspect_ratio()
        if base_size.y * ratio > base_size.x:
            size = Vector2(base_size.x, base_size.x / ratio)
            pos = base_pos + (0, (base_size.y - size.y) * 0.5)
        else:
            size = Vector2(base_size.y * ratio, base_size.y)
            pos = base_pos + ((base_size.x - size.x) * 0.5, 0)

        draw = imgui.get_window_draw_list()

        radius = (130.744 - 13.717) * 0.5 * self._xaml_scale.x * size.x
        center = pos + Vector2(96.494, 13.717) * self._xaml_scale * size + (0, radius)

        black_radius = (126.808 - 17.654) * 0.5 * self._xaml_scale.x * size.x
        inner_radius = (125.687 - 18.775) * 0.5 * self._xaml_scale.x * size.x
        black_ring_thickness = black_radius - inner_radius
        black_radius -= black_ring_thickness * 0.5

        blue_radius = (124.552 - 19.909) * 0.5 * self._xaml_scale.x * size.x

        # Draw circles (holders)
        draw.add_circle_filled(center, radius, self._white.u32)
        draw.add_circle(center, black_radius, self._black.u32, thickness=black_ring_thickness)
        draw.add_circle_filled(center, blue_radius, self._blue.u32)

        # Draw stars
        for x, top_y, bot_y in self.star_circles:
            radius = (bot_y - top_y) * 0.5 * self._xaml_scale.x * size.x
            center = pos + self._xaml_scale * (x, top_y) * size + (0, radius)
            draw.add_circle_filled(center, radius, self._white.u32)
        for star_path in self.star_crosses:
            star_path.render(pos, size, self._white)

        # Draw details (laurels)
        for det_path in self.laurels:
            det_path.render(pos, size, self._white)

        # Draw text
        x_min = 4.384
        x_max = 188.057
        y_min = 154.827
        y_max = 175.972
        # text_pos/text_area defines the actual rect to render the text.
        text_pos = pos + self._xaml_scale * (x_min, y_min) * size
        text_area = (pos + self._xaml_scale * (x_max, y_max) * size) - text_pos
        # draw.add_rect(text_pos, text_pos + text_area, self._blue.u32)
        self._text.area.position = text_pos
        self._text.area.size = text_area
        self._text.draw()

    def render(self):
        self._draw_badge()
        self._handle_interaction()