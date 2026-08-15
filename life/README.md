# Life

Cellular automata: rules with no arithmetic in them that build clocks, memory,
machines, and things that copy themselves. The oldest argument that biology and
computation are one subject.

## Wetware editions

[`wetware-editions/`](wetware-editions/) reads Conway's Life three ways — as
tissue, as a machine, and as what noise settles into when left alone — in the
same house style as [`../attractors/`](../attractors/) and
[`../libra/solvent-editions/`](../libra/solvent-editions/).

```bash
python3 life/wetware-editions/source/render_life.py
```

Two of the three keep Conway's rule unmodified and record the entire run as a
solid in (x, y, t), so a history becomes an object you can turn around. See its
README for the method, and for what the third one changes and why.
