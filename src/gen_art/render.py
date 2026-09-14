"""Render deterministic, layered mathematical fields as PNG artwork."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin

from . import __version__
from .presets import PRESETS


def adjusted_color(color: tuple[int, int, int], variation: np.ndarray) -> np.ndarray:
    """Apply a small, deterministic channel variation to a palette color."""
    return np.clip(np.asarray(color, dtype=np.float32) + variation, 0, 255) / 255.0


def render_image(
    preset: dict,
    seed: int,
    width: int,
    height: int,
    supersample: int = 2,
) -> Image.Image:
    """Render one preset with independently derived layout, color, and texture streams."""
    internal_width = width * supersample
    internal_height = height * supersample
    seed_sequence = np.random.SeedSequence(seed)
    layout_rng, color_rng, texture_rng = (
        np.random.default_rng(child_seed) for child_seed in seed_sequence.spawn(3)
    )

    background_top = np.asarray(preset["background_top"], dtype=np.float32) / 255.0
    background_bottom = np.asarray(preset["background_bottom"], dtype=np.float32) / 255.0
    color_jitter = preset["color_jitter"]
    layers = []
    for layer in preset["layers"]:
        layout_offset = layout_rng.normal(0, preset["layout_jitter"], size=2)
        color_offset = color_rng.normal(0, color_jitter, size=3)
        layers.append(
            {
                "center": np.asarray(layer["center"]) + layout_offset,
                "radius": np.asarray(layer["radius"]),
                "color": adjusted_color(layer["color"], color_offset),
                "opacity": layer["opacity"],
            }
        )

    pixels = np.empty((internal_height, internal_width, 3), dtype=np.uint8)
    horizontal_positions = (np.arange(internal_width, dtype=np.float32) + 0.5) / internal_width
    chunk_height = 128
    for start_row in range(0, internal_height, chunk_height):
        end_row = min(start_row + chunk_height, internal_height)
        vertical_positions = (
            np.arange(start_row, end_row, dtype=np.float32) + 0.5
        ) / internal_height
        progress = vertical_positions[:, np.newaxis, np.newaxis]
        canvas = background_top * (1.0 - progress) + background_bottom * progress
        canvas = np.broadcast_to(canvas, (end_row - start_row, internal_width, 3)).copy()

        for layer in layers:
            horizontal_distance = (
                (horizontal_positions[np.newaxis, :] - layer["center"][0]) / layer["radius"][0]
            )
            vertical_distance = (
                (vertical_positions[:, np.newaxis] - layer["center"][1]) / layer["radius"][1]
            )
            field = np.exp(-2.4 * (horizontal_distance**2 + vertical_distance**2))
            alpha = (field * layer["opacity"])[..., np.newaxis]
            canvas = canvas * (1.0 - alpha) + layer["color"] * alpha

        texture_strength = preset["texture_strength"]
        if texture_strength:
            texture = texture_rng.normal(0, texture_strength / 255.0, size=canvas.shape)
            canvas = np.clip(canvas + texture, 0.0, 1.0)
        pixels[start_row:end_row] = np.rint(canvas * 255).astype(np.uint8)

    image = Image.fromarray(pixels, mode="RGB")
    if supersample > 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image


def save_image(image: Image.Image, destination: Path, preset_name: str, seed: int) -> None:
    """Save a traceable PNG with the complete reproduction key."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("generator", "gen-art")
    metadata.add_text("generator_version", __version__)
    metadata.add_text("preset", preset_name)
    metadata.add_text("seed", str(seed))
    metadata.add_text("dimensions", f"{image.width}x{image.height}")
    image.save(destination, pnginfo=metadata)


def render_contact_sheet(arguments: argparse.Namespace, preset: dict) -> Path:
    """Render compact variations for curation, separate from committed gallery images."""
    longest_side = 400
    scale = longest_side / max(arguments.width, arguments.height)
    thumbnail_width = round(arguments.width * scale)
    thumbnail_height = round(arguments.height * scale)
    rows = (arguments.count + arguments.columns - 1) // arguments.columns
    sheet = Image.new("RGB", (thumbnail_width * arguments.columns, thumbnail_height * rows))
    for index in range(arguments.count):
        variation = render_image(
            preset, arguments.seed + index, thumbnail_width, thumbnail_height, supersample=1
        )
        position = ((index % arguments.columns) * thumbnail_width, (index // arguments.columns) * thumbnail_height)
        sheet.paste(variation, position)
    destination = Path("output") / f"{arguments.preset}-seeds-{arguments.seed}-{arguments.seed + arguments.count - 1}.png"
    save_image(sheet, destination, arguments.preset, arguments.seed)
    return destination


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render reproducible mathematical-field artwork.")
    parser.add_argument("--preset", choices=PRESETS, default="atmospheric_aperture")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--width", type=int, default=4000)
    parser.add_argument("--height", type=int, default=3000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--contact-sheet", action="store_true")
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--columns", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    preset = PRESETS[arguments.preset]
    if arguments.contact_sheet:
        destination = render_contact_sheet(arguments, preset)
    else:
        destination = arguments.output or Path("gallery") / f"{arguments.preset}-seed-{arguments.seed}.png"
        image = render_image(preset, arguments.seed, arguments.width, arguments.height)
        save_image(image, destination, arguments.preset, arguments.seed)
    print(destination)


if __name__ == "__main__":
    main()