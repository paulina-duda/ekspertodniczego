"""Scientific-art Manim scene for the Lorenz attractor.

Render:
    manim -qh --format=webm atraktory/lorenz_gif.py LorenzAttractorScientificArt

Optional GIF conversion after rendering:
    ffmpeg -i media/videos/lorenz_gif/1080p30/LorenzAttractorScientificArt.webm \
        -vf "fps=20,scale=800:-1:flags=lanczos" atraktory/lorenz_attractor.gif
"""

from __future__ import annotations

from manim import *
import numpy as np


config.pixel_width = 1080
config.pixel_height = 1080
config.frame_width = 8
config.frame_height = 8
config.frame_rate = 30
config.background_color = "#03050A"
config.output_file = "LorenzAttractorScientificArt"


SIGMA = 10.0
RHO = 28.0
BETA = 8.0 / 3.0
DT = 0.006
WARMUP_STEPS = 1800
DRAW_STEPS = 12500
DISPLAY_POINTS = 1800
DRAW_TIME = 10.0


def lorenz_derivative(point: np.ndarray) -> np.ndarray:
    x, y, z = point
    return np.array(
        [
            SIGMA * (y - x),
            x * (RHO - z) - y,
            x * y - BETA * z,
        ],
        dtype=np.float64,
    )


def integrate_lorenz(total_steps: int) -> np.ndarray:
    points = np.empty((total_steps, 3), dtype=np.float64)
    points[0] = np.array([0.1, 0.0, 0.0], dtype=np.float64)

    for index in range(1, total_steps):
        point = points[index - 1]
        k1 = lorenz_derivative(point)
        k2 = lorenz_derivative(point + 0.5 * DT * k1)
        k3 = lorenz_derivative(point + 0.5 * DT * k2)
        k4 = lorenz_derivative(point + DT * k3)
        points[index] = point + (DT / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    return points


def prepared_lorenz_points() -> np.ndarray:
    raw = integrate_lorenz(WARMUP_STEPS + DRAW_STEPS)[WARMUP_STEPS:]
    sampled_indices = np.linspace(0, len(raw) - 1, DISPLAY_POINTS).astype(int)
    sampled = raw[sampled_indices]

    center = sampled.mean(axis=0)
    centered = sampled - center
    scale = 5.9 / np.max(np.ptp(centered, axis=0))

    # Manim's z-axis gets a slightly smaller scale so the butterfly keeps a
    # sculptural profile while remaining legible in a square frame.
    points = centered * scale
    points[:, 2] *= 0.78
    return points


def smooth_path(points: np.ndarray, stroke_width: float, opacity: float) -> VMobject:
    path = VMobject()
    path.set_points_smoothly(points)
    path.set_stroke(width=stroke_width, opacity=opacity)
    path.set_color_by_gradient("#2FD7FF", "#B7F36B", "#FFE66D", "#FF6B8A", "#F7FAFF")
    path.set_shade_in_3d(True)
    return path


def spectral_halo(path: VMobject) -> VGroup:
    halo = VGroup()
    for width, opacity in [(14, 0.045), (8, 0.075), (4, 0.12)]:
        layer = path.copy()
        layer.set_stroke(width=width, opacity=opacity)
        halo.add(layer)
    return halo


def scientific_scaffold() -> VGroup:
    axes = ThreeDAxes(
        x_range=(-3.2, 3.2, 1),
        y_range=(-3.2, 3.2, 1),
        z_range=(-2.4, 2.4, 1),
        x_length=6.2,
        y_length=6.2,
        z_length=4.7,
        tips=False,
        axis_config={
            "color": "#6F7D95",
            "stroke_width": 0.7,
            "stroke_opacity": 0.28,
        },
    )

    xy_plane = NumberPlane(
        x_range=(-4, 4, 1),
        y_range=(-4, 4, 1),
        x_length=7.0,
        y_length=7.0,
        background_line_style={
            "stroke_color": "#1A2434",
            "stroke_width": 0.55,
            "stroke_opacity": 0.26,
        },
        axis_config={"stroke_opacity": 0},
    )
    xy_plane.set_z_index(-10)
    xy_plane.set_opacity(0.58)

    return VGroup(xy_plane, axes)


class LorenzAttractorScientificArt(ThreeDScene):
    def construct(self):
        points = prepared_lorenz_points()
        trace = smooth_path(points, stroke_width=1.05, opacity=0.98)
        ghost_trace = trace.copy().set_stroke("#7DA7C8", width=0.42, opacity=0.075)
        halo = spectral_halo(trace)

        head = Dot3D(point=points[0], radius=0.045, color="#F7FAFF")
        head_glow = Dot3D(point=points[0], radius=0.12, color="#2FD7FF")
        head_glow.set_opacity(0.22)

        scaffold = scientific_scaffold()

        title = Text("Lorenz attractor", font_size=25, color="#EAF2FF")
        subtitle = Text("sigma=10   rho=28   beta=8/3", font_size=16, color="#8EA3BC")
        signature = Text("phase-space emergence", font_size=15, color="#53657D")

        title.to_corner(UL, buff=0.28)
        subtitle.next_to(title, DOWN, aligned_edge=LEFT, buff=0.08)
        signature.to_corner(DR, buff=0.28)

        self.set_camera_orientation(phi=66 * DEGREES, theta=-58 * DEGREES, zoom=0.78)
        self.add(scaffold, ghost_trace)
        self.add_fixed_in_frame_mobjects(title, subtitle, signature)
        self.play(
            FadeIn(title, shift=0.12 * DOWN),
            FadeIn(subtitle, shift=0.12 * DOWN),
            FadeIn(signature, shift=0.12 * UP),
            FadeIn(scaffold, run_time=1.2),
            FadeIn(ghost_trace, run_time=1.2),
        )

        self.add(head_glow, head)
        self.begin_ambient_camera_rotation(rate=PI / DRAW_TIME, about="theta")
        self.play(
            Create(halo, lag_ratio=0.0),
            Create(trace),
            MoveAlongPath(head, trace),
            MoveAlongPath(head_glow, trace),
            run_time=DRAW_TIME,
            rate_func=linear,
        )
        self.stop_ambient_camera_rotation()

        self.play(
            head.animate.set_opacity(0),
            head_glow.animate.set_opacity(0),
            trace.animate.set_stroke(width=0.95, opacity=1.0),
            halo.animate.set_opacity(0.58),
            run_time=1.2,
        )
        self.wait(0.8)
