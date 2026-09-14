import tempfile
import unittest
from pathlib import Path

from PIL import Image

from gen_art.presets import PRESETS
from gen_art.animate import animated_preset
from gen_art.render import render_image, save_image


class RenderTests(unittest.TestCase):
    def test_same_seed_produces_same_pixels(self) -> None:
        first = render_image(PRESETS["atmospheric_aperture"], 42, 60, 80)
        second = render_image(PRESETS["atmospheric_aperture"], 42, 60, 80)

        self.assertEqual(first.tobytes(), second.tobytes())

    def test_png_contains_reproduction_metadata(self) -> None:
        image = render_image(PRESETS["atmospheric_aperture"], 42, 60, 80)
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "artwork.png"
            save_image(image, destination, "atmospheric_aperture", 42)
            with Image.open(destination) as saved:
                self.assertEqual(saved.info["preset"], "atmospheric_aperture")
                self.assertEqual(saved.info["seed"], "42")
                self.assertEqual(saved.info["dimensions"], "60x80")

    def test_artwork_loop_returns_to_its_starting_state(self) -> None:
        start = animated_preset(PRESETS["celestial_cascade"], 42, 0.0, 0.06)
        end = animated_preset(PRESETS["celestial_cascade"], 42, 1.0, 0.06)

        self.assertEqual(start, end)