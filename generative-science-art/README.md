# Generative Science Art

Five projects over the same material — chaotic attractors as 9:16 phone pieces.
Each stands on its own: its own source, its own exports, its own idea about what
the animation is for.

| Project | Idea |
| --- | --- |
| [`equation-editions/`](equation-editions/) | The originals. Line-drawn attractors that build from an empty frame, with a small monospace equation caption. |
| [`luminous-editions/`](luminous-editions/) | The same six pieces rebuilt as seamless loops: opening on the finished sculpture, lit by additive glow and log-density tone mapping. |
| [`emergence-editions/`](emergence-editions/) | Three luminous attractors, but forming — one thread pulled apart by chaos into the whole sculpture. Cut for Instagram, opening on a cover frame. |
| [`palette-editions/`](palette-editions/) | The same three, same cut, but sampled exactly as the luminous editions are — so the last frame matches them pixel for pixel — with alternative palettes for two of them. |
| [`trace-editions/`](trace-editions/) | The same three again, drawn as continuous filaments rather than accumulating density — each step subdivided to about a pixel, so you watch actual lines being laid down. |

Read them in that order and the reasoning is visible: `equation-editions` sets
the subject, `luminous-editions` argues about how it should be lit and framed for
a feed, `emergence-editions` takes the first project's build-up idea back through
the second project's renderer, and `palette-editions` settles what that cost in
colour — the two emergence projects are the two sides of one trade, between a
single-thread growth and an exact colour match.

Requirements are shared and unchanged — `numpy`, `Pillow`, and an FFmpeg with an
H.264 encoder. Each project's README has its own run commands.
