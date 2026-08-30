#!/usr/bin/env python3
"""A cellular automaton whose rule is a small network, fitted rather than written.

Every other rule in this project was written down by somebody. Gray-Scott is two
diffusion constants and a feed rate; Lenia is a kernel and a growth curve; the
sandpile is one sentence about integers. Somebody chose them, and what they do
is a consequence of a choice a person can read.

This one is not written. It is 8,320 numbers found by gradient descent, and it is
exactly as local as the others: a cell sees itself and its immediate neighbours,
and updates itself. Same shape of rule, same simultaneous update across the whole
grid, same nobody in charge. The only difference is where the numbers came from
(Mordvintsev, Randazzo, Niklasson and Levin, *Growing Neural Cellular Automata*,
Distill 2020).

What the training asks for is one thing only: **after some number of steps, the
grid should look like this picture**. There is no term in the loss for holding
still, none for stopping at the right size, and — the point of the piece — none
whatsoever for repair. The loss has never seen a damaged organism.

Three parts, in the order they matter:

- `planarian` draws the target. A flatworm, because it is the animal the
  regeneration literature is *about*: cut one in half and the head end grows a
  tail while the tail end grows a head, eyes included.
- `Rule` is the automaton. Sixteen channels per cell, of which one is visible;
  perception is a fixed 3x3 stencil (the cell, and the two Sobel derivatives);
  the update is two 1x1 convolutions, which is to say a small dense network
  applied identically at every cell.
- `train` fits it, and `regeneration_report` is the experiment the piece rests
  on: grow one, cut its head off, and count what comes back.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


WEIGHTS_DIR = Path(__file__).resolve().parents[1] / "weights"


def device_for(preference: str | None = None) -> torch.device:
    if preference:
        return torch.device(preference)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ----------------------------------------------------------------------
# The target
# ----------------------------------------------------------------------

# Half-width down the body, as a fraction of the widest half-width, from the tip
# of the head (0) to the tip of the tail (1). A planarian is not a tube: the head
# flares into two auricles, pinches at the neck, swells through the pharyngeal
# third and then tapers to a point. Those four events are the whole silhouette,
# and the automaton has to rebuild every one of them from a single cell.
PROFILE = (
    (0.000, 0.00),
    (0.018, 0.30),  # the head is truncated, not pointed
    (0.045, 0.42),
    (0.075, 0.56),
    (0.100, 0.78),  # auricles
    (0.118, 0.80),
    (0.140, 0.58),  # and the pinch immediately behind them
    (0.180, 0.54),  # neck
    (0.270, 0.76),
    (0.430, 1.00),
    (0.600, 0.98),
    (0.760, 0.84),
    (0.880, 0.57),
    (0.960, 0.27),
    (1.000, 0.00),
)


def planarian(
    width: int = 124,
    height: int = 168,
    length: float = 140.0,
    waist: float = 23.0,
    eye_row: float = 0.155,
    eye_offset: float = 0.50,
    eye_radius: float = 3.4,
) -> np.ndarray:
    """The silhouette to be grown, as one soft mask in 0..1.

    Antialiased rather than binary, and deliberately so: a hard-edged target
    gives the network a step function to chase and it answers with a ring of
    permanently twitching cells along the outline. One cell of ramp is enough to
    make the boundary something a gradient can sit on.

    The eyespots are holes. A spot of a *different colour* would need a second
    visible channel and would make colour in the finished piece mean two things
    at once; a hole is the same channel, and it is the harder thing to rebuild —
    the automaton has to stop growing in two places it has never been told about
    except through the picture.
    """
    rows, columns = np.mgrid[0:height, 0:width].astype(np.float64)
    centre_x = (width - 1) / 2.0
    top = (height - length) / 2.0
    along = (rows - top) / length

    half_width = np.interp(along, [t for t, _ in PROFILE], [w for _, w in PROFILE]) * waist
    mask = np.clip(half_width - np.abs(columns - centre_x) + 0.5, 0.0, 1.0)
    mask[(along < 0.0) | (along > 1.0)] = 0.0

    # The eyespots are placed against the *local* half-width rather than the
    # widest one, so moving the profile around cannot slide them off the head.
    eye_half_width = float(
        np.interp(eye_row, [t for t, _ in PROFILE], [w for _, w in PROFILE]) * waist
    )
    for side in (-1.0, 1.0):
        centre_row = top + eye_row * length
        centre_column = centre_x + side * eye_offset * eye_half_width
        hole = np.clip(
            np.hypot(rows - centre_row, columns - centre_column) - eye_radius + 0.5, 0.0, 1.0
        )
        mask *= hole
    return mask.astype(np.float32)


def seed_cell(target: np.ndarray) -> tuple[int, int]:
    """Where the single starting cell goes: the target's own centre of mass.

    Not the middle of the grid. The organism is not symmetric about its middle —
    it has a head — and starting off-centre means the finished body sits somewhere
    other than where it was framed.
    """
    total = max(float(target.sum()), 1e-9)
    rows, columns = np.mgrid[0 : target.shape[0], 0 : target.shape[1]]
    return int(round(float((rows * target).sum() / total))), int(
        round(float((columns * target).sum() / total))
    )


# ----------------------------------------------------------------------
# The automaton
# ----------------------------------------------------------------------


class Rule(torch.nn.Module):
    """One update rule, applied identically and simultaneously at every cell.

    A cell holds `channels` numbers. The first is visible — call it alpha, how
    much of the organism is here — and the rest are hidden, with no assigned
    meaning at all: whatever the fitting decides to keep there. Chemical
    gradients, a coordinate system, a clock; nobody knows, and nothing in the
    training says.

    A step is three things:

    1. **Perceive.** Each channel is convolved with three fixed 3x3 stencils —
       itself, and the Sobel derivatives across and down. That is the entire
       neighbourhood: a cell knows its own state and which way each of its
       channels is sloping. The stencils are *not* learned; making them fixed is
       what keeps the rule comparable to Gray-Scott, which also only ever sees a
       Laplacian.
    2. **Update.** 1x1 convolutions are dense layers applied per cell, so this is
       a two-layer network with the same weights at every position. It outputs a
       *change*, and the second layer starts at zero, so the automaton begins as
       the do-nothing rule and every behaviour in it was added by fitting.
    3. **Fire, sometimes.** Each cell updates with probability `fire_rate`. Cells
       have no shared clock, and a synchronous automaton can exploit one — the
       parity of the step number is free information, and a network will happily
       build a rule that depends on it. Dropping half the updates at random
       removes that, at the cost of nothing.

    Then the alive mask: a cell may only hold state if it or a neighbour has
    alpha above 0.1. This is what makes the empty grid stay empty rather than
    filling with faint arithmetic, and it is also the only reason the black
    around the organism is black.
    """

    def __init__(self, channels: int = 16, hidden: int = 128, fire_rate: float = 0.5) -> None:
        super().__init__()
        self.channels = channels
        self.fire_rate = fire_rate

        identity = torch.tensor([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]])
        sobel = torch.tensor([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]) / 8.0
        stencils = torch.stack([identity, sobel, sobel.T])
        self.register_buffer(
            "stencils", stencils.repeat(channels, 1, 1).unsqueeze(1), persistent=False
        )

        self.hidden_layer = torch.nn.Conv2d(channels * 3, hidden, 1)
        self.output_layer = torch.nn.Conv2d(hidden, channels, 1, bias=False)
        torch.nn.init.zeros_(self.output_layer.weight)

    def alive(self, state: torch.Tensor) -> torch.Tensor:
        return F.max_pool2d(state[:, :1], 3, stride=1, padding=1) > 0.1

    def perceive(self, state: torch.Tensor) -> torch.Tensor:
        # Zero padding, which means the grid genuinely has an edge and the rule
        # can feel it. That is honest -- a dish has walls -- and it also means the
        # organism must be framed with a margin, or it learns the wall as scenery.
        return F.conv2d(state, self.stencils, padding=1, groups=self.channels)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        before = self.alive(state)
        change = self.output_layer(F.relu(self.hidden_layer(self.perceive(state))))
        fire = (
            torch.rand(state.shape[0], 1, *state.shape[2:], device=state.device) <= self.fire_rate
        ).float()
        state = state + change * fire
        return state * (before & self.alive(state)).float()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            channels=self.channels,
            fire_rate=self.fire_rate,
            **{name: tensor.detach().cpu().numpy() for name, tensor in self.state_dict().items()},
        )

    @staticmethod
    def load(path: Path, device: torch.device | None = None) -> "Rule":
        stored = np.load(path)
        rule = Rule(
            channels=int(stored["channels"]),
            hidden=int(stored["hidden_layer.weight"].shape[0]),
            fire_rate=float(stored["fire_rate"]),
        )
        rule.load_state_dict(
            {
                name: torch.tensor(stored[name])
                for name in stored.files
                if name not in ("channels", "fire_rate")
            }
        )
        return rule.to(device_for(None) if device is None else device).eval()


def blank(batch: int, channels: int, height: int, width: int, device) -> torch.Tensor:
    return torch.zeros(batch, channels, height, width, device=device)


def seeded(
    batch: int, channels: int, height: int, width: int, row: int, column: int, device
) -> torch.Tensor:
    """One cell, all channels at 1, everything else empty.

    The whole organism has to come out of this. Nothing distinguishes the seed
    from any other cell except that it is the only one switched on, which is what
    makes the piece's first second worth watching: there is no plan in there, no
    coordinates, no map of where the head goes.
    """
    state = blank(batch, channels, height, width, device)
    state[:, :, row, column] = 1.0
    return state


def amputate(state: torch.Tensor, row: int, keep: str = "below") -> torch.Tensor:
    """A transverse cut: everything on one side of a row is removed outright.

    Removed, not damaged -- all sixteen channels zeroed, hidden ones included, so
    nothing is left behind that could be a memory of what used to be there. The
    fragment carries no information about the missing half except its own cut
    face.
    """
    cut = state.clone()
    if keep == "below":
        cut[:, :, :row] = 0.0
    else:
        cut[:, :, row:] = 0.0
    return cut


# ----------------------------------------------------------------------
# Fitting
# ----------------------------------------------------------------------


def _loss(state: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return ((state[:, :1] - target) ** 2).mean(dim=(1, 2, 3))


def train(
    target: np.ndarray,
    channels: int = 16,
    hidden: int = 128,
    iterations: int = 8000,
    batch: int = 8,
    pool_size: int = 1024,
    steps: tuple[int, int] = (64, 96),
    damage: int = 0,
    learning_rate: float = 2e-3,
    runaway: float = 1.0,
    seed: int = 0,
    device: torch.device | None = None,
    report=None,
) -> tuple[Rule, dict]:
    """Fit the rule, with a sample pool so it has to persist rather than peak.

    **Why a pool.** Training only ever on runs that start from the seed teaches
    the automaton to look right at step 80 and says nothing about step 300; what
    that produces is an organism that assembles beautifully and then boils. The
    pool keeps the states a batch ended on and starts later batches from them, so
    the rule is repeatedly asked to still be right after a number of steps it was
    never trained for. The worst sample in each batch is thrown out and replaced
    by a fresh seed, or the pool drifts away from ever having to grow at all.

    **`damage` is the experiment.** At zero, no organism in the entire fitting is
    ever cut, and whether the finished rule can regenerate is a question about
    what fell out of learning to grow. Above zero, that many of the best samples
    in each batch are cut before the run, and regeneration becomes something the
    training pressed for -- though even then nothing tells it *how*; the loss
    still only ever says what the finished picture should be.

    **A pool is a memory, and that is what makes it fragile.** A state that runs
    away does not simply score badly and get replaced; it sits in the pool and
    takes out every batch it is drawn into, and one non-finite gradient poisons
    every weight in the rule permanently. The first damage run died this way at
    iteration 7,200 and then ran another 12,800 without saying so. Hence three
    guards, none of them optional: a step with a non-finite gradient is skipped,
    any sample scoring worse than `runaway` goes back into the pool as a fresh
    seed, and the weights that are kept are the best two-hundred-iteration mean
    rather than whatever the last iteration happened to leave behind.

    Returns the rule and a record of what happened, which is what the piece's
    copy has to be true to.
    """
    device = device_for(None) if device is None else device
    torch.manual_seed(seed)
    generator = np.random.default_rng(seed)

    height, width = target.shape
    goal = torch.tensor(target, device=device)[None, None]
    row, column = seed_cell(target)

    rule = Rule(channels=channels, hidden=hidden).to(device)
    optimiser = torch.optim.Adam(rule.parameters(), lr=learning_rate)
    schedule = torch.optim.lr_scheduler.MultiStepLR(
        optimiser, milestones=[iterations // 2], gamma=0.3
    )

    pool = seeded(pool_size, channels, height, width, row, column, device)
    seed_state = seeded(1, channels, height, width, row, column, device)[0]
    history: list[float] = []
    best_loss, best_weights = float("inf"), None
    replaced = rejected = 0

    for iteration in range(iterations):
        picks = torch.tensor(
            generator.choice(pool_size, batch, replace=False), device=device, dtype=torch.long
        )
        state = pool[picks].clone()

        # Highest loss out, fresh seed in. Ranking the batch is also how the
        # damaged samples get chosen: cutting the *best* ones is what makes the
        # cut a hard case rather than a coup de grace on something already broken.
        order = torch.argsort(_loss(state, goal), descending=True)
        state = state[order]
        state[0] = seed_state
        if damage > 0:
            for index in range(batch - damage, batch):
                if generator.random() < 0.5:
                    keep = "below" if generator.random() < 0.5 else "above"
                    line = int(generator.integers(int(height * 0.2), int(height * 0.8)))
                    state[index : index + 1] = amputate(state[index : index + 1], line, keep)
                else:
                    radius = float(generator.uniform(height * 0.08, height * 0.22))
                    centre_row = float(generator.uniform(0, height))
                    centre_column = float(generator.uniform(0, width))
                    rows, columns = torch.meshgrid(
                        torch.arange(height, device=device, dtype=torch.float32),
                        torch.arange(width, device=device, dtype=torch.float32),
                        indexing="ij",
                    )
                    state[index] *= (
                        torch.hypot(rows - centre_row, columns - centre_column) > radius
                    ).float()

        for _ in range(int(generator.integers(steps[0], steps[1] + 1))):
            state = rule(state)

        losses = _loss(state, goal)
        loss = losses.mean()
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        # Gradients through eighty applications of the same weights span orders of
        # magnitude between one iteration and the next. Normalising each one to
        # unit length throws away that scale and keeps only the direction, which
        # is the difference between this converging and diverging on iteration 40.
        finite = True
        for parameter in rule.parameters():
            if parameter.grad is not None:
                if not torch.isfinite(parameter.grad).all():
                    finite = False
                    break
                parameter.grad /= parameter.grad.norm() + 1e-8
        if finite:
            optimiser.step()
        else:
            # One infinite gradient poisons every weight in the rule, and from
            # there every future loss is a nan and the run is over -- it just
            # keeps going for another twelve thousand iterations without saying
            # so. Skipping the step costs one iteration.
            rejected += 1
        schedule.step()

        with torch.no_grad():
            # A pool is a memory, which is exactly what makes it dangerous: a
            # single state that has run away stays in it for the rest of the run
            # and takes out every batch it is drawn into. A blank grid scores
            # about 0.21 against this target, so anything past `runaway` is not a
            # bad attempt at the animal, it is a diverging one -- put a fresh
            # seed back in its place and let the rule try again.
            spoiled = ~torch.isfinite(losses) | (losses > runaway)
            state = torch.where(
                spoiled[:, None, None, None], seed_state[None], state.detach()
            )
            pool[picks] = state
            replaced += int(spoiled.sum())
        history.append(float(loss.detach()))

        # Keep the best rule seen, not the last one. Divergence is recoverable
        # for the pool and not for the weights, and the cheapest insurance is a
        # copy of whatever was working two hundred iterations ago.
        if iteration % 200 == 199:
            recent = float(np.mean(history[-200:]))
            if np.isfinite(recent) and recent < best_loss:
                best_loss = recent
                best_weights = {
                    name: tensor.detach().clone() for name, tensor in rule.state_dict().items()
                }
        if report is not None and (iteration % 200 == 0 or iteration == iterations - 1):
            recent = float(np.mean(history[-200:]))
            report(
                f"  iteration {iteration:5d}  loss {history[-1]:.5f}  mean200 {recent:.5f}"
                f"  best {best_loss:.5f}  reseeded {replaced}  skipped {rejected}"
            )

    if best_weights is not None:
        rule.load_state_dict(best_weights)
    return rule.eval(), {
        "iterations": iterations,
        "damage": damage,
        "final_loss": best_loss,
        "reseeded": replaced,
        "skipped": rejected,
        "history": history,
    }


# ----------------------------------------------------------------------
# The experiment the piece rests on
# ----------------------------------------------------------------------


@torch.no_grad()
def grow(
    rule: Rule, target: np.ndarray, steps: int, device: torch.device | None = None
) -> torch.Tensor:
    device = device_for(None) if device is None else device
    row, column = seed_cell(target)
    state = seeded(1, rule.channels, *target.shape, row, column, device)
    for _ in range(steps):
        state = rule(state)
    return state


@torch.no_grad()
def regeneration_report(
    rule: Rule,
    target: np.ndarray,
    grow_steps: int = 140,
    cut_at: float = 0.22,
    regrow_steps: int = 200,
    persist_steps: int = 600,
    device: torch.device | None = None,
) -> dict:
    """Grow one, check it persists, cut its head off, and see what comes back.

    Four numbers, and the piece's copy is only allowed to say what they support:

    - `grown` — error against the target once it has finished growing.
    - `persisted` — error after another few hundred steps with nothing done to
      it. A rule that scores well here has learned to *stop*, which is not the
      same thing as having learned to grow.
    - `regrown` — error after the cut and the regrowth. Compared against `grown`,
      this is the whole question.
    - `eyes` — the two holes are the sharpest test in the picture, because they
      are the only feature the automaton has to build by *not* growing. Measured
      as how deep the pair of them are, against how deep they are in a body that
      was never cut.
    """
    device = device_for(None) if device is None else device
    goal = torch.tensor(target, device=device)[None, None]
    height = target.shape[0]

    state = grow(rule, target, grow_steps, device)
    grown = float(_loss(state, goal))
    grown_eyes = _eye_depth(state, target)

    settled = state.clone()
    for _ in range(persist_steps):
        settled = rule(settled)
    persisted = float(_loss(settled, goal))

    cut_row = int(round(body_top(target) + cut_at * body_length(target)))
    fragment = amputate(state, cut_row, keep="below")
    remaining = float(fragment[:, :1].clamp(0, 1).sum() / max(state[:, :1].clamp(0, 1).sum(), 1e-9))
    for _ in range(regrow_steps):
        fragment = rule(fragment)
    regrown = float(_loss(fragment, goal))

    return {
        "grown": grown,
        "persisted": persisted,
        "regrown": regrown,
        "kept": remaining,
        "cut_row": cut_row,
        "eyes_grown": grown_eyes,
        "eyes_regrown": _eye_depth(fragment, target),
    }


def body_top(target: np.ndarray) -> float:
    rows = np.flatnonzero(target.max(axis=1) > 0.5)
    return float(rows[0])


def body_length(target: np.ndarray) -> float:
    rows = np.flatnonzero(target.max(axis=1) > 0.5)
    return float(rows[-1] - rows[0])


def _eye_depth(state: torch.Tensor, target: np.ndarray) -> float:
    """How dark the eyespots are, relative to the head around them.

    1.0 means the two holes are as empty as the target asks; 0.0 means the head
    is a solid paddle with no eyes in it at all.
    """
    solid = planarian_without_eyes(target)
    holes = solid - target
    if holes.sum() < 1.0:
        return float("nan")
    alpha = state[0, 0].clamp(0.0, 1.0).cpu().numpy()
    inside = holes > 0.5
    rim = (solid > 0.5) & (holes < 0.1)
    head = rim & (np.arange(target.shape[0])[:, None] < body_top(target) + 0.25 * body_length(target))
    if head.sum() < 1.0:
        return float("nan")
    return float(1.0 - alpha[inside].mean() / max(alpha[head].mean(), 1e-6))


def planarian_without_eyes(target: np.ndarray) -> np.ndarray:
    """The same silhouette with the holes filled, used only for measurement."""
    height, width = target.shape
    filled = np.zeros_like(target)
    for row in range(height):
        columns = np.flatnonzero(target[row] > 0.5)
        if len(columns):
            filled[row, columns[0] : columns[-1] + 1] = 1.0
    return filled


# ----------------------------------------------------------------------
# Fitting from the command line
# ----------------------------------------------------------------------


def main() -> None:
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Fit a growing neural CA to the planarian.")
    parser.add_argument("--name", default="regrowth-planarian", help="weight file stem")
    parser.add_argument("--iterations", type=int, default=8000)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--pool", type=int, default=1024)
    parser.add_argument("--channels", type=int, default=16)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--steps", type=int, nargs=2, default=(72, 112))
    parser.add_argument(
        "--damage", type=int, default=0,
        help="samples per batch cut before the run; 0 means the rule never sees an injury",
    )
    parser.add_argument("--learning-rate", type=float, default=2e-3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--grid", type=int, nargs=2, default=(124, 168), help="width height")
    parser.add_argument("--regrow-steps", type=int, default=240)
    arguments = parser.parse_args()

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True

    target = planarian(*arguments.grid)
    print(
        f"target {target.shape[1]}x{target.shape[0]}, "
        f"{int((target > 0.5).sum()):,} cells of body, seed at {seed_cell(target)}",
        flush=True,
    )

    started = time.time()
    rule, record = train(
        target,
        channels=arguments.channels,
        hidden=arguments.hidden,
        iterations=arguments.iterations,
        batch=arguments.batch,
        pool_size=arguments.pool,
        steps=tuple(arguments.steps),
        damage=arguments.damage,
        learning_rate=arguments.learning_rate,
        seed=arguments.seed,
        report=print,
    )
    parameters = sum(p.numel() for p in rule.parameters())
    print(
        f"fitted {parameters:,} numbers in {time.time() - started:.0f}s, "
        f"final loss {record['final_loss']:.5f}",
        flush=True,
    )

    result = regeneration_report(rule, target, regrow_steps=arguments.regrow_steps)
    print(
        "  grown     {grown:.5f}\n"
        "  persisted {persisted:.5f}  (600 further steps, untouched)\n"
        "  regrown   {regrown:.5f}  (cut at row {cut_row}, {kept:.0%} of the body kept)\n"
        "  eyes      {eyes_grown:.2f} grown -> {eyes_regrown:.2f} regrown".format(**result),
        flush=True,
    )

    path = WEIGHTS_DIR / f"{arguments.name}.npz"
    rule.save(path)
    print(f"saved {path}", flush=True)


if __name__ == "__main__":
    main()
