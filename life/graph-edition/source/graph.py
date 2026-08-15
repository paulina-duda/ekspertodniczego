import argparse
import math
from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.patches import Circle
from scipy.spatial import cKDTree


@dataclass
class Ring:
    center_idx: int
    radius: float = 0.0
    age: float = 0.0
    strength: float = 1.0


class GraphLife:
    def __init__(self, n=5000, k=14, seed=7):
        self.rng = np.random.default_rng(seed)

        self.n = n
        self.k = k

        # -------------------------------------------------
        # 1. CHMURA PUNKTÓW
        # -------------------------------------------------
        #
        # Sunflower / golden-angle distribution:
        # punkty są równomiernie rozłożone w kole,
        # ale nie wyglądają jak regularna kratka.
        #

        i = np.arange(n, dtype=np.float32)

        golden_angle = np.pi * (3.0 - np.sqrt(5.0))

        r = np.sqrt((i + 0.5) / n) * 0.98
        theta = i * golden_angle

        # subtelna nieregularność
        theta += self.rng.normal(
            0.0,
            0.018,
            size=n
        )

        r *= (
            1.0
            + self.rng.normal(
                0.0,
                0.006,
                size=n
            )
        )

        self.base = np.column_stack(
            (
                r * np.cos(theta),
                r * np.sin(theta)
            )
        ).astype(np.float32)

        # -------------------------------------------------
        # 2. GRAF K-NAJBLIŻSZYCH SĄSIADÓW
        # -------------------------------------------------

        tree = cKDTree(self.base)

        dist, idx = tree.query(
            self.base,
            k=k + 1
        )

        # pierwszy element to punkt sam dla siebie
        self.nbr = idx[:, 1:].astype(np.int32)

        dist = dist[:, 1:].astype(np.float32)

        sigma = (
            np.median(dist[:, -1])
            * 0.75
        )

        weights = np.exp(
            -(
                dist /
                (sigma + 1e-8)
            ) ** 2
        ).astype(np.float32)

        self.w = (
            weights
            /
            (
                weights.sum(
                    axis=1,
                    keepdims=True
                )
                + 1e-8
            )
        )

        # -------------------------------------------------
        # 3. STAN AUTOMATU
        # -------------------------------------------------

        self.state = self.rng.uniform(
            0.0,
            0.025,
            size=n
        ).astype(np.float32)

        # indywidualna faza mikroruchu każdego punktu
        self.phase = self.rng.uniform(
            0.0,
            2 * np.pi,
            size=n
        ).astype(np.float32)

        self.rings = []

        # początkowe skupiska
        self.seed_colonies(6)

    # =====================================================
    # TWORZENIE KOLONII
    # =====================================================

    def seed_colonies(self, count=5):

        centers = self.rng.choice(
            self.n,
            size=count,
            replace=False
        )

        for c in centers:

            d2 = np.sum(
                (
                    self.base
                    - self.base[c]
                ) ** 2,
                axis=1
            )

            bump = np.exp(
                -d2 /
                (
                    2
                    * 0.045 ** 2
                )
            ).astype(np.float32)

            amplitude = self.rng.uniform(
                0.65,
                1.0
            )

            self.state = np.maximum(
                self.state,
                bump * amplitude
            )

            self.rings.append(
                Ring(
                    int(c),
                    radius=0.01,
                    age=0.0,
                    strength=float(amplitude)
                )
            )

    # =====================================================
    # SIGMOID
    # =====================================================

    @staticmethod
    def sigmoid(x):

        x = np.clip(
            x,
            -40.0,
            40.0
        )

        return (
            1.0
            /
            (
                1.0
                + np.exp(-x)
            )
        )

    # =====================================================
    # NOWA FALA
    # =====================================================

    def spawn_ring(self):

        # zwykle fala zaczyna się
        # w już aktywnym regionie

        if (
            self.rng.random() < 0.75
            and np.max(self.state) > 0.25
        ):

            probabilities = np.maximum(
                self.state - 0.20,
                0.0
            ).astype(np.float64)

            total = probabilities.sum()

            if total > 0:

                probabilities /= total

                c = int(
                    self.rng.choice(
                        self.n,
                        p=probabilities
                    )
                )

            else:

                c = int(
                    self.rng.integers(
                        self.n
                    )
                )

        else:

            # czasami powstaje zupełnie nowa kolonia

            c = int(
                self.rng.integers(
                    self.n
                )
            )

            d2 = np.sum(
                (
                    self.base
                    - self.base[c]
                ) ** 2,
                axis=1
            )

            self.state += (
                0.55
                * np.exp(
                    -d2 /
                    (
                        2
                        * 0.025 ** 2
                    )
                )
            ).astype(np.float32)

            np.clip(
                self.state,
                0.0,
                1.0,
                out=self.state
            )

        self.rings.append(
            Ring(
                c,
                radius=0.015,
                age=0.0,
                strength=float(
                    self.rng.uniform(
                        0.6,
                        1.0
                    )
                )
            )
        )

        # żeby nie powstało 3000 pierścieni
        if len(self.rings) > 12:
            self.rings = self.rings[-12:]

    # =====================================================
    # JEDEN KROK AUTOMATU
    # =====================================================

    def step(self, dt, t):

        # -------------------------------------------------
        # średnia aktywność lokalnych sąsiadów
        # -------------------------------------------------

        local = np.sum(
            self.state[self.nbr]
            * self.w,
            axis=1
        )

        # -------------------------------------------------
        # continuous Game of Life
        # -------------------------------------------------
        #
        # aktywność rośnie tylko dla określonego
        # zakresu aktywności sąsiadów
        #

        low = 0.16
        high = 0.50
        edge = 0.035

        window = (
            self.sigmoid(
                (local - low) / edge
            )
            *
            self.sigmoid(
                (high - local) / edge
            )
        )

        growth = (
            1.45
            * window
            * (1.0 - self.state)
        )

        decay = (
            0.52
            * self.state
        )

        diffusion = (
            0.95
            * (
                local
                - self.state
            )
        )

        noise = self.rng.normal(
            0.0,
            0.015,
            size=self.n
        ).astype(np.float32)

        self.state += (
            dt
            * (
                growth
                - decay
                + diffusion
                + noise
            )
        )

        # -------------------------------------------------
        # propagujące się pierścienie
        # -------------------------------------------------

        new_rings = []

        for ring in self.rings:

            ring.radius += (
                dt * 0.18
            )

            ring.age += dt

            center_position = (
                self.base[
                    ring.center_idx
                ]
            )

            d = np.sqrt(
                np.sum(
                    (
                        self.base
                        - center_position
                    ) ** 2,
                    axis=1
                )
            )

            width = (
                0.018
                + 0.005
                * min(
                    ring.age,
                    1.0
                )
            )

            impulse = np.exp(
                -(
                    (
                        d
                        - ring.radius
                    ) ** 2
                )
                /
                (
                    2
                    * width ** 2
                )
            ).astype(np.float32)

            self.state += (
                dt
                * 1.6
                * ring.strength
                * impulse
                * (
                    1.0
                    - self.state
                )
            )

            if (
                ring.age < 4.2
                and ring.radius < 0.85
            ):

                new_rings.append(
                    ring
                )

        self.rings = new_rings

        # -------------------------------------------------
        # sporadyczne spontaniczne zapłony
        # -------------------------------------------------

        if (
            self.rng.random()
            < dt * 0.22
        ):

            c = int(
                self.rng.integers(
                    self.n
                )
            )

            d2 = np.sum(
                (
                    self.base
                    - self.base[c]
                ) ** 2,
                axis=1
            )

            self.state += (
                dt
                * 2.2
                * np.exp(
                    -d2 /
                    (
                        2
                        * 0.020 ** 2
                    )
                )
            ).astype(np.float32)

        np.clip(
            self.state,
            0.0,
            1.0,
            out=self.state
        )

    # =====================================================
    # POZYCJE PUNKTÓW
    # =====================================================

    def positions(
        self,
        t,
        breath_period=8.0
    ):

        # cała struktura kurczy się i rośnie

        breath = (
            0.77
            +
            0.23
            * (
                0.5
                +
                0.5
                * np.cos(
                    2.0
                    * np.pi
                    * t
                    / breath_period
                )
            )
        )

        radial = (
            self.base
            /
            (
                np.linalg.norm(
                    self.base,
                    axis=1,
                    keepdims=True
                )
                + 1e-8
            )
        )

        tangent = np.column_stack(
            (
                -radial[:, 1],
                radial[:, 0]
            )
        )

        # mikroruch organiczny

        wobble_r = (
            0.0060
            * np.sin(
                self.phase
                + 0.75 * t
            )
        )

        wobble_t = (
            0.0040
            * np.sin(
                1.7 * self.phase
                - 0.42 * t
            )
        )

        pos = (
            self.base
            * breath
        )

        pos = (
            pos
            + radial
            * wobble_r[:, None]
            + tangent
            * wobble_t[:, None]
        )

        return (
            pos.astype(np.float32),
            float(breath)
        )


# =========================================================
# RENDEROWANIE MP4
# =========================================================

def render(
    output,
    seconds=12,
    fps=30,
    n=5000,
    k=14,
    dpi=100,
    width=720,
    height=1280,
    seed=7
):

    sim = GraphLife(
        n=n,
        k=k,
        seed=seed
    )

    dt = 1.0 / fps

    frames = int(
        seconds * fps
    )

    fig_width = width / dpi
    fig_height = height / dpi

    fig, ax = plt.subplots(
        figsize=(
            fig_width,
            fig_height
        ),
        dpi=dpi
    )

    fig.subplots_adjust(
        0,
        0,
        1,
        1
    )

    background = "#05070d"

    fig.patch.set_facecolor(
        background
    )

    ax.set_facecolor(
        background
    )

    ax.set_xlim(
        -1.06,
        1.06
    )

    ax.set_ylim(
        -1.06,
        1.06
    )

    ax.set_aspect(
        "equal"
    )

    ax.axis("off")

    pos, _ = sim.positions(
        0.0
    )

    # -------------------------------------------------
    # KOLORY
    # -------------------------------------------------

    base_color = np.array(
        [
            0.44,
            0.47,
            0.52,
            0.55
        ],
        dtype=np.float32
    )

    hot_color = np.array(
        [
            1.00,
            0.48,
            0.08,
            1.00
        ],
        dtype=np.float32
    )

    gold_color = np.array(
        [
            1.00,
            0.72,
            0.18,
            1.00
        ],
        dtype=np.float32
    )

    colors = np.repeat(
        base_color[None, :],
        n,
        axis=0
    )

    sizes = np.full(
        n,
        2.2
    )

    # -------------------------------------------------
    # GLOW
    # -------------------------------------------------

    glow = ax.scatter(
        pos[:, 0],
        pos[:, 1],
        s=np.full(
            n,
            8.0
        ),
        c=colors,
        linewidths=0,
        zorder=1
    )

    # -------------------------------------------------
    # GŁÓWNE PUNKTY
    # -------------------------------------------------

    dots = ax.scatter(
        pos[:, 0],
        pos[:, 1],
        s=sizes,
        c=colors,
        linewidths=0,
        zorder=3
    )

    # -------------------------------------------------
    # PIERŚCIENIE
    # -------------------------------------------------

    max_rings = 12

    ring_patches = []

    for _ in range(
        max_rings
    ):

        circle = Circle(
            (0, 0),
            radius=0.01,
            fill=False,
            lw=1.0,
            edgecolor=(
                1.0,
                0.5,
                0.1,
                0.0
            ),
            zorder=2
        )

        ax.add_patch(
            circle
        )

        ring_patches.append(
            circle
        )

    # -------------------------------------------------
    # DUŻE HALO
    # -------------------------------------------------

    core_glow = ax.scatter(
        [],
        [],
        s=[],
        c=[],
        linewidths=0,
        zorder=2
    )

    # =================================================
    # AKTUALIZACJA KLATKI
    # =================================================

    def update(frame):

        t = (
            frame
            * dt
        )

        # nowa fala co około 1.3 sekundy

        if (
            frame > 0
            and
            frame
            % max(
                1,
                int(
                    1.3
                    * fps
                )
            )
            == 0
        ):

            sim.spawn_ring()

        # fizyka

        sim.step(
            dt,
            t
        )

        # nowe pozycje

        pos, breath = (
            sim.positions(t)
        )

        state = np.clip(
            sim.state,
            0.0,
            1.0
        )

        # -------------------------------------------------
        # KOLOR
        # -------------------------------------------------

        mix = np.clip(
            state ** 0.72,
            0.0,
            1.0
        )[:, None]

        rgba = (
            base_color[None, :]
            * (
                1.0
                - mix
            )
            +
            hot_color[None, :]
            * mix
        )

        rgba[:, 3] = (
            0.32
            +
            0.68
            * np.clip(
                0.18
                + state,
                0.0,
                1.0
            )
        )

        # -------------------------------------------------
        # ROZMIAR PUNKTÓW
        # -------------------------------------------------

        dot_sizes = (
            1.8
            +
            8.0
            * (
                state ** 1.7
            )
        )

        # -------------------------------------------------
        # GLOW
        # -------------------------------------------------

        glow_rgba = (
            rgba.copy()
        )

        glow_rgba[:, :3] = (
            gold_color[:3]
        )

        glow_rgba[:, 3] = (
            0.02
            +
            0.20
            * (
                state ** 2.0
            )
        )

        glow_sizes = (
            5.0
            +
            70.0
            * (
                state ** 2.3
            )
        )

        dots.set_offsets(
            pos
        )

        dots.set_sizes(
            dot_sizes
        )

        dots.set_facecolors(
            rgba
        )

        glow.set_offsets(
            pos
        )

        glow.set_sizes(
            glow_sizes
        )

        glow.set_facecolors(
            glow_rgba
        )

        # -------------------------------------------------
        # NAJJAŚNIEJSZE CENTRA
        # -------------------------------------------------

        local = np.sum(
            state[sim.nbr]
            * sim.w,
            axis=1
        )

        score = (
            state
            - local
        )

        candidates = np.where(
            (
                state > 0.58
            )
            &
            (
                score > -0.02
            )
        )[0]

        if len(
            candidates
        ) > 0:

            top = candidates[
                np.argsort(
                    state[
                        candidates
                    ]
                )[-18:]
            ]

            halo_positions = (
                pos[top]
            )

            halo_sizes = (
                180.0
                +
                700.0
                * (
                    state[top]
                    ** 2
                )
            )

            halo_colors = np.tile(
                np.array(
                    [
                        1.0,
                        0.40,
                        0.05,
                        0.07
                    ]
                ),
                (
                    len(top),
                    1
                )
            )

            core_glow.set_offsets(
                halo_positions
            )

            core_glow.set_sizes(
                halo_sizes
            )

            core_glow.set_facecolors(
                halo_colors
            )

        else:

            core_glow.set_offsets(
                np.empty(
                    (0, 2)
                )
            )

            core_glow.set_sizes(
                np.empty(
                    (0,)
                )
            )

        # -------------------------------------------------
        # WIDOCZNE PIERŚCIENIE
        # -------------------------------------------------

        for j, patch in enumerate(
            ring_patches
        ):

            if j < len(
                sim.rings
            ):

                ring = (
                    sim.rings[j]
                )

                center = (
                    sim.base[
                        ring.center_idx
                    ]
                    * breath
                )

                alpha = max(
                    0.0,
                    1.0
                    - ring.age
                    / 4.2
                )

                patch.center = (
                    float(
                        center[0]
                    ),
                    float(
                        center[1]
                    )
                )

                patch.set_radius(
                    float(
                        ring.radius
                        * breath
                    )
                )

                patch.set_edgecolor(
                    (
                        1.0,
                        0.48,
                        0.08,
                        0.28
                        * alpha
                    )
                )

                patch.set_linewidth(
                    0.7
                    +
                    1.2
                    * alpha
                )

                patch.set_visible(
                    True
                )

            else:

                patch.set_visible(
                    False
                )

        return [
            glow,
            dots,
            core_glow,
            *ring_patches
        ]

    # =================================================
    # ANIMACJA
    # =================================================

    animation = FuncAnimation(
        fig,
        update,
        frames=frames,
        interval=1000 / fps,
        blit=False
    )

    writer = FFMpegWriter(
        fps=fps,
        codec="libx264",
        bitrate=9000,
        extra_args=[
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart"
        ]
    )

    animation.save(
        output,
        writer=writer,
        dpi=dpi
    )

    plt.close(fig)


# =========================================================
# CLI
# =========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Graph-based continuous "
            "Game-of-Life animation"
        )
    )

    parser.add_argument(
        "--output",
        default="graph_life.mp4"
    )

    parser.add_argument(
        "--seconds",
        type=float,
        default=12.0
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30
    )

    parser.add_argument(
        "--points",
        type=int,
        default=5000
    )

    parser.add_argument(
        "--neighbors",
        type=int,
        default=14
    )

    parser.add_argument(
        "--width",
        type=int,
        default=720
    )

    parser.add_argument(
        "--height",
        type=int,
        default=1280
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=100
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=7
    )

    args = parser.parse_args()

    render(
        output=args.output,
        seconds=args.seconds,
        fps=args.fps,
        n=args.points,
        k=args.neighbors,
        dpi=args.dpi,
        width=args.width,
        height=args.height,
        seed=args.seed
    )


if __name__ == "__main__":
    main()