# gen-art

![Atmospheric Aperture](gallery/atmospheric_aperture-seed-42.png)

Reproducible generative stills made from layered mathematical fields in Python.

## Atmospheric Aperture

`atmospheric_aperture`, seed `42`  
PNG, $4000 \times 3000$

Each render derives independent layout, color, and texture streams from one seed. The PNG records its preset, seed, dimensions, and generator version.

## Render

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m gen_art.render --preset atmospheric_aperture --seed 42
```

The final still is written to `gallery/`. Change the detailed art direction in `src/gen_art/presets.py`.

## Explore

```sh
.venv/bin/python -m gen_art.render --preset atmospheric_aperture --seed 42 --contact-sheet --count 6 --columns 3
```

Contact sheets and unselected renders are written to ignored `output/`.

## Animate

Render a fast, 5-second preview loop at $800 \times 600$:

```sh
.venv/bin/python -m gen_art.animate --preset celestial_cascade --seed 42 --preview
```

Render the portfolio loop at $1600 \times 1200$, 24 fps, and 30 seconds:

```sh
.venv/bin/python -m gen_art.animate --preset celestial_cascade --seed 42
```

Each command writes animated WebP and MP4. Animation parameters are periodic, so the artwork returns exactly to its starting state.

Use `--duration 15 --motion-range 0.18 --name celestial_cascade-fast-wide-seed-42` to keep a faster, wider-motion variant beside the default export.