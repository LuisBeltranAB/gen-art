"""Render seamlessly looping animated versions of mathematical-field artworks."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from . import __version__
from .presets import PRESETS
from .render import render_image


def animated_preset(preset: dict, seed: int, progress: float, motion_range: float) -> dict:
    """Return the periodic visual state at a normalized point in an artwork loop."""
    rng = np.random.default_rng(np.random.SeedSequence(seed).spawn(1)[0])
    progress %= 1.0
    angle = math.tau * progress
    animated = {**preset, "layers": []}

    for color_key in ("background_top", "background_bottom"):
        color = np.asarray(preset[color_key], dtype=np.float32)
        phase = rng.uniform(0, math.tau, size=3)
        color_motion = np.sin(angle + phase) * 8.0
        animated[color_key] = tuple(np.clip(color + color_motion, 0, 255).round().astype(int))

    for layer in preset["layers"]:
        center = np.asarray(layer["center"], dtype=np.float32)
        orbit_phase = rng.uniform(0, math.tau)
        orbit_ratio = rng.uniform(0.55, 1.0)
        orbit = np.array(
            [math.cos(angle + orbit_phase), math.sin(angle + orbit_phase) * orbit_ratio]
        )
        color_phase = rng.uniform(0, math.tau, size=3)
        color = np.asarray(layer["color"], dtype=np.float32)
        color_motion = np.sin(angle + color_phase) * 10.0
        animated["layers"].append(
            {
                **layer,
                "center": tuple(center + orbit * motion_range),
                "color": tuple(np.clip(color + color_motion, 0, 255).round().astype(int)),
            }
        )
    return animated


def encoder_command(destination: Path, width: int, height: int, fps: int) -> list[str]:
    """Build a raw-video encoder command for a web or fallback animation asset."""
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
    ]
    if destination.suffix == ".webp":
        return command + ["-c:v", "libwebp", "-loop", "0", "-q:v", "82", str(destination)]
    return command + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)]


def render_loop(
    preset_name: str,
    seed: int,
    width: int,
    height: int,
    duration: int,
    fps: int,
    motion_range: float,
    destination_directory: Path,
    name: str | None = None,
) -> tuple[Path, Path]:
    """Stream one deterministic artwork loop to animated WebP and MP4 files."""
    preset = PRESETS[preset_name]
    frame_count = duration * fps
    destination_directory.mkdir(parents=True, exist_ok=True)
    stem = name or f"{preset_name}-seed-{seed}"
    webp_path = destination_directory / f"{stem}.webp"
    mp4_path = destination_directory / f"{stem}.mp4"
    encoders = [
        subprocess.Popen(encoder_command(path, width, height, fps), stdin=subprocess.PIPE)
        for path in (webp_path, mp4_path)
    ]
    try:
        for frame_number in range(frame_count):
            frame_preset = animated_preset(
                preset, seed, frame_number / frame_count, motion_range
            )
            frame = render_image(frame_preset, seed, width, height, supersample=1)
            frame_bytes = frame.tobytes()
            for encoder in encoders:
                assert encoder.stdin is not None
                encoder.stdin.write(frame_bytes)
    finally:
        for encoder in encoders:
            if encoder.stdin is not None:
                encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError("Animation encoder failed.")

    manifest = {
        "generator": "gen-art",
        "generator_version": __version__,
        "preset": preset_name,
        "seed": seed,
        "dimensions": f"{width}x{height}",
        "duration_seconds": duration,
        "fps": fps,
        "frame_count": frame_count,
        "motion_range": motion_range,
    }
    (destination_directory / f"{stem}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return webp_path, mp4_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a seamlessly looping artwork animation.")
    parser.add_argument("--preset", choices=PRESETS, default="celestial_cascade")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--duration", type=int)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--motion-range", type=float, default=0.06)
    parser.add_argument("--name", help="Filename stem for a named animation variation.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    preview = arguments.preview
    width = arguments.width or (800 if preview else 1600)
    height = arguments.height or (600 if preview else 800)
    duration = arguments.duration or (5 if preview else 30)
    destination_directory = Path("output") if preview else Path("gallery")
    webp_path, mp4_path = render_loop(
        arguments.preset,
        arguments.seed,
        width,
        height,
        duration,
        arguments.fps,
        arguments.motion_range,
        destination_directory,
        arguments.name,
    )
    print(webp_path)
    print(mp4_path)


if __name__ == "__main__":
    main()