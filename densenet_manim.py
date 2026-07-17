from manim import *
import numpy as np


config.pixel_width = 1000
config.pixel_height = 1000
config.frame_width = 8
config.frame_height = 8
config.background_color = "#090B10"


class DenseNetDiagram(Scene):
    def create_column(
        self,
        count: int,
        x_pos: float,
        top: float,
        bottom: float,
        radius: float,
        color: str,
    ) -> VGroup:
        y_positions = np.linspace(top, bottom, count)
        return VGroup(
            *[
                Dot(
                    point=np.array([x_pos, y, 0]),
                    radius=radius,
                    fill_color=color,
                    fill_opacity=0.95,
                    stroke_width=0,
                )
                for y in y_positions
            ]
        )

    def layered_glow(self, mob: Mobject, color: str, radius: float) -> VGroup:
        return VGroup(
            Circle(radius=radius * 2.6, fill_color=color, fill_opacity=0.05, stroke_opacity=0).move_to(mob),
            Circle(radius=radius * 1.7, fill_color=color, fill_opacity=0.08, stroke_opacity=0).move_to(mob),
        )

    def dense_bundle(
        self,
        left_layer: VGroup,
        right_layer: VGroup,
        fanout: int,
        stroke_width: float,
        color: str,
        opacity: float,
        jitter: float,
    ) -> VGroup:
        lines = VGroup()
        right_count = len(right_layer)
        spread = fanout // 2

        for index, left_node in enumerate(left_layer):
            mapped = int(index * (right_count - 1) / max(len(left_layer) - 1, 1))
            start = max(0, mapped - spread)
            stop = min(right_count, mapped + spread + 1)

            for target_index in range(start, stop):
                start_point = left_node.get_center()
                end_point = right_layer[target_index].get_center()
                curve_lift = (target_index - mapped) * 0.002
                path = CubicBezier(
                    start_point,
                    start_point + np.array([jitter, curve_lift + 0.14, 0]),
                    end_point + np.array([-jitter, curve_lift - 0.14, 0]),
                    end_point,
                    stroke_color=color,
                    stroke_width=stroke_width,
                    stroke_opacity=opacity,
                )
                lines.add(path)

        return lines

    def cross_threads(
        self,
        left_layer: VGroup,
        right_layer: VGroup,
        step_left: int,
        step_right: int,
        color: str,
        opacity: float,
        stroke_width: float,
        lift: float,
    ) -> VGroup:
        threads = VGroup()
        left_indices = range(0, len(left_layer), step_left)
        right_indices = range(len(right_layer) - 1, -1, -step_right)

        for left_index, right_index in zip(left_indices, right_indices):
            start = left_layer[left_index].get_center()
            end = right_layer[right_index].get_center()
            curve = CubicBezier(
                start,
                start + np.array([1.2, lift, 0]),
                end + np.array([-1.2, -lift, 0]),
                end,
                stroke_color=color,
                stroke_width=stroke_width,
                stroke_opacity=opacity,
            )
            threads.add(curve)

        return threads

    def construct(self):
        haze_a = Circle(radius=2.7, fill_color="#11304A", fill_opacity=0.14, stroke_opacity=0).shift(LEFT * 2.7 + UP * 2.5)
        haze_b = Circle(radius=2.4, fill_color="#10281D", fill_opacity=0.13, stroke_opacity=0).shift(RIGHT * 2.4 + DOWN * 1.9)
        haze_c = Circle(radius=2.0, fill_color="#3A2216", fill_opacity=0.08, stroke_opacity=0).shift(RIGHT * 2.9 + UP * 2.2)

        input_layer = self.create_column(100, -2.9, 2.75, -2.75, 0.016, "#92D6FF")
        hidden_layer = self.create_column(500, 0.0, 2.95, -2.95, 0.008, "#B8FFD2")
        output_layer = self.create_column(50, 2.9, 2.25, -2.25, 0.022, "#FFD39A")

        left_glow = self.layered_glow(input_layer, "#2F9BFF", 0.7)
        mid_glow = self.layered_glow(hidden_layer, "#64F0A8", 0.95)
        right_glow = self.layered_glow(output_layer, "#FFB264", 0.62)

        left_to_hidden = self.dense_bundle(
            input_layer,
            hidden_layer,
            fanout=41,
            stroke_width=0.45,
            color="#4CA6D9",
            opacity=0.14,
            jitter=0.95,
        )
        hidden_to_right = self.dense_bundle(
            hidden_layer,
            output_layer,
            fanout=13,
            stroke_width=0.38,
            color="#77E1A6",
            opacity=0.12,
            jitter=0.95,
        )

        diagonal_a = self.cross_threads(
            input_layer,
            output_layer,
            step_left=3,
            step_right=1,
            color="#D8F3FF",
            opacity=0.09,
            stroke_width=0.5,
            lift=1.35,
        )
        diagonal_b = self.cross_threads(
            input_layer[::-1],
            output_layer,
            step_left=3,
            step_right=1,
            color="#C2FFD8",
            opacity=0.07,
            stroke_width=0.45,
            lift=-1.25,
        )

        shell = RoundedRectangle(
            corner_radius=0.34,
            width=7.35,
            height=6.9,
            stroke_color="#1B2130",
            stroke_width=1.2,
            fill_opacity=0,
        )

        self.add(
            haze_a,
            haze_b,
            haze_c,
            shell,
            left_glow,
            mid_glow,
            right_glow,
            left_to_hidden,
            hidden_to_right,
            diagonal_a,
            diagonal_b,
            input_layer,
            hidden_layer,
            output_layer,
        )
        self.wait(1)
