# Final3 glycolytic Selkov flux-3D MP4

Ten folder zawiera komplet MP4 wygenerowanych skryptem:

```bash
python3 atraktory/skrypty/final3_glycolytic_flux3d_9x16_mp4.py --all-presets
```

To wersja Selkova z transientem zachowanym od początku animacji i z osia `z` jako metaboliczny flux:

```text
x = reduced substrate S
y = reduced product P
z = metabolic flux v(S, P)
```

Opcjonalny zapis trajektorii biologicznej do CSV:

```bash
python3 atraktory/skrypty/final3_glycolytic_flux3d_9x16_mp4.py --all-presets --save-trajectory
```
