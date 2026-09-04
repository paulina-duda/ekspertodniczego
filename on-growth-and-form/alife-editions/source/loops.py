"""Langton's loops: the 1984 automaton in which a machine copies itself.

Von Neumann asked whether a machine could build a machine as complicated as
itself, and answered it in 1948 with a universal constructor so large nobody
has ever run the original. Codd cut it down in 1968. Langton cut it down again
in 1984 by giving up on universality -- his loop cannot compute anything, it
can only reproduce -- and what is left is small enough to watch: eight states,
five cells in the neighbourhood, 219 lines of transition table, and one
starting shape ninety cells across.

The loop is a square of **sheath** (state 2) wrapped around a **core** (state
1) that carries a train of signals round and round. Two signals do everything:
7 extends the arm by one cell, 4 turns it left. The train reads `70 70 70 70
40 40` and it is both the machine and its own blueprint -- circulating, it
pushes the arm out; arriving at the arm's tip, the same signals build. Four
extensions and a turn, four times over, and the arm has closed into a second
loop holding a copy of the same train. The daughter's first act is to cut
itself free.

Nothing in the rule mentions copying, a parent, a daughter or a colony.

**What the colony does is the reason this is filmable.** A loop that finds no
free space beside it cannot finish an arm, and a jammed loop retracts into a
still husk -- state 2 with nothing moving in it, permanent. So the colony grows
only on its surface and the inside of it is a graveyard of identical shells.
Measured over a clip: 108 of 399 loops still had a signal in them at the end.

Two things that cost time here and are worth writing down:

- **The seed has to be exact.** A single missing 0 in the signal train --
  `217014142` where the row should read `2170140142` -- leaves a shape that no
  transition matches, and a rule table whose default is "leave the cell alone"
  answers by freezing. It ran for 400 steps and moved 88 cells to 89, which
  looks like a broken renderer and is a wrong initial condition.
- **Unmatched neighbourhoods leave the cell unchanged**, which is Golly's
  `@TABLE` convention, not "set it to zero". Getting that backwards erases the
  colony from the inside out.

Rule table from Golly's `Langtons-Loops.rule`, itself from Bachmutsky's 1999
`loops.java`; 219 transitions in `CNESWC'` order under `rotate4` symmetry.
Verified by running it: the seed doubles its cell count by step 150, which is
the published replication period.
"""

from __future__ import annotations

import numpy as np

# CNESWC' -- centre, north, east, south, west, and the state the centre takes.
# Every line stands for four, one per quarter turn.
TRANSITIONS = """
000000 000012 000020 000030 000050 000063 000071 000112 000122 000132 000212
000220 000230 000262 000272 000320 000525 000622 000722 001022 001120 002020
002030 002050 002125 002220 002322 005222 012321 012421 012525 012621 012721
012751 014221 014321 014421 014721 016251 017221 017255 017521 017621 017721
025271 100011 100061 100077 100111 100121 100211 100244 100277 100511 101011
101111 101244 101277 102026 102121 102211 102244 102263 102277 102327 102424
102626 102644 102677 102710 102727 105427 111121 111221 111244 111251 111261
111277 111522 112121 112221 112244 112251 112277 112321 112424 112621 112727
113221 122244 122277 122434 122547 123244 123277 124255 124267 125275 200012
200022 200042 200071 200122 200152 200212 200222 200232 200242 200250 200262
200272 200326 200423 200517 200522 200575 200722 201022 201122 201222 201422
201722 202022 202032 202052 202073 202122 202152 202212 202222 202272 202321
202422 202452 202520 202552 202622 202722 203122 203216 203226 203422 204222
205122 205212 205222 205521 205725 206222 206722 207122 207222 207422 207722
211222 211261 212222 212242 212262 212272 214222 215222 216222 217222 222272
222442 222462 222762 222772 300013 300022 300041 300076 300123 300421 300622
301021 301220 302511 401120 401220 401250 402120 402221 402326 402520 403221
500022 500215 500225 500232 500272 500520 502022 502122 502152 502220 502244
502722 512122 512220 512422 512722 600011 600021 602120 612125 612131 612225
700077 701120 701220 701250 702120 702221 702251 702321 702525 702720
"""

# The 1984 starting configuration: a loop holding `70 70 70 70 40 40`, with the
# stub of a construction arm already pointing right.
SEED = (
    "02222222200000",
    "21701401420000",
    "20222222020000",
    "27200002120000",
    "21200002120000",
    "20200002120000",
    "27200002120000",
    "21222222122222",
    "20710710711111",
    "02222222222222",
)

SHEATH = 2
CORE = 1


def transition_table() -> np.ndarray:
    """The 219 rules expanded to all 32,768 neighbourhoods, flat.

    Indexed `centre * 4096 + north * 512 + east * 64 + south * 8 + west`. The
    default is the centre's own state: a neighbourhood the table does not
    mention is one the automaton leaves alone.
    """
    table = np.zeros((8, 8, 8, 8, 8), dtype=np.uint8)
    for centre in range(8):
        table[centre] = centre
    for line in TRANSITIONS.split():
        centre, north, east, south, west, result = (int(digit) for digit in line)
        ring = [north, east, south, west]
        for turn in range(4):
            a, b, c, d = ring[turn:] + ring[:turn]
            table[centre, a, b, c, d] = result
    return table.reshape(-1)


class Loops:
    """A world of Langton's loops, and how long each cell has been dead.

    `age` is the piece's only measured quantity: steps since this cell last
    changed state. It is zero everywhere the machine is working and climbs
    without limit through the husks, which is the difference between the live
    rim of the colony and the crystal behind it. It is what the palette reads.
    """

    def __init__(self, height: int, width: int, row: int, column: int) -> None:
        self.height, self.width = height, width
        self.table = transition_table()
        self.grid = np.zeros((height, width), dtype=np.uint8)
        self.age = np.zeros((height, width), dtype=np.int32)
        self.step_index = 0

        patch = np.array([[int(ch) for ch in line] for line in SEED], dtype=np.uint8)
        top = row - patch.shape[0] // 2
        left = column - patch.shape[1] // 2
        self.grid[top:top + patch.shape[0], left:left + patch.shape[1]] = patch

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            grid = self.grid
            wide = grid.astype(np.int32)
            north = np.roll(wide, 1, axis=0)
            south = np.roll(wide, -1, axis=0)
            east = np.roll(wide, -1, axis=1)
            west = np.roll(wide, 1, axis=1)
            index = wide * 4096 + north * 512 + east * 64 + south * 8 + west
            following = self.table[index]
            self.age += 1
            self.age[following != grid] = 0
            self.grid = following
            self.step_index += 1

    # ------------------------------------------------------------------
    # Measurement
    # ------------------------------------------------------------------

    def census(self) -> tuple[int, int]:
        """How many loops there are, and how many still have a signal in them.

        A loop is counted as the pocket of background it encloses, which is the
        one feature every loop has and no husk loses. Alive means a signal
        state (4 to 7) sits in the ring around that pocket.
        """
        from scipy import ndimage

        labels, count = ndimage.label(self.grid == 0)
        if count == 0:
            return 0, 0
        edge = (
            set(labels[0].tolist()) | set(labels[-1].tolist())
            | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
        )
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
        pockets = [
            i for i in range(1, count + 1)
            if i not in edge and sizes[i - 1] >= 4
        ]
        signal = (self.grid >= 4) & (self.grid <= 7)
        alive = sum(
            1 for i in pockets
            if signal[ndimage.binary_dilation(labels == i, iterations=2)].any()
        )
        return len(pockets), alive

    def extent(self) -> tuple[int, int, int, int]:
        """Bounding box of everything drawn, as (top, bottom, left, right)."""
        rows = np.flatnonzero(np.any(self.grid > 0, axis=1))
        columns = np.flatnonzero(np.any(self.grid > 0, axis=0))
        if rows.size == 0:
            return 0, 0, 0, 0
        return int(rows[0]), int(rows[-1]), int(columns[0]), int(columns[-1])
