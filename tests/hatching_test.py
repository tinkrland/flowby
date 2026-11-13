"""hatching_test: the ported shader has to look like lines, and every control has to do its job.

the reference is Amagi's "Hatching Effect with VFX-JS" pen, read 2026-11-13. the parts worth testing are
the ones that make hatching read as *drawn* rather than as a printed screen: strokes clipped to the
region with round caps, per-strip jitter, maximum-not-sum overlap, and (flowby's own addition) ink that
gathers in the dark. most of these are measurable on a synthetic picture, so none of them are judged by
eye.
"""

import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from flowby import actions


def gradient(width=200, height=90) -> Image.Image:
    """left dark, right light, fully opaque: every stroke visible and no clipping to confuse a count."""
    picture = Image.new("L", (width, height))
    pen = picture.load()
    for y in range(height):
        for x in range(width):
            pen[x, y] = int(30 + 225 * x / (width - 1))
    return picture.convert("RGB")


def blob(size=120) -> Image.Image:
    """an opaque disc on a transparent field: the region has a shape, so a stroke must end on it."""
    picture = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pen = picture.load()
    for y in range(size):
        for x in range(size):
            if (x - size / 2) ** 2 + (y - size / 2) ** 2 < (size / 2 - 6) ** 2:
                pen[x, y] = (40, 40, 44, 255)
    return picture


class Base(unittest.TestCase):
    def setUp(self):
        self.room = Path(tempfile.mkdtemp())
        self.action = actions.from_file("actions/hatching.py")

    def run_on(self, picture: Image.Image, **values) -> Image.Image:
        source = self.room / f"source-{abs(hash(tuple(sorted(values.items()))))}.png"
        picture.save(source)
        out = self.action.run({"source": str(source)}, str(self.room / "out"), values)["hatched"]
        made = Image.open(out)
        made.load()
        return made

    @staticmethod
    def ink(picture: Image.Image, box=None) -> int:
        """how many pixels are stroked. count only on the light end of the gradient, because a dark
        source pixel is already below the threshold and would be counted as ink it never received."""
        grey = picture.convert("L")
        if box:
            grey = grey.crop(box)
        return sum(1 for value in grey.tobytes() if value < 60)


class TheContract(Base):
    def test_it_declares_itself_like_every_other_action(self):
        self.assertEqual(self.action.name, "Hatching")
        self.assertEqual([(p.name, p.dtype) for p in self.action.inputs], [("source", "image")])
        self.assertEqual([(p.name, p.dtype) for p in self.action.outputs], [("hatched", "image")])

    def test_every_control_the_shader_had_survives_the_port(self):
        keys = {param.key for param in self.action.params}
        for key in ("angle", "spacing", "width", "angleJitter", "spacingJitter", "offsetJitter", "seed"):
            self.assertIn(key, keys, f"{key} came from the pen and should not have been dropped")

    def test_a_value_outside_the_controls_own_range_is_refused(self):
        for bad in ({"spacing": 1}, {"width": 0}, {"angleJitter": 40}, {"angle": 200}):
            with self.assertRaises(actions.ActionRefused, msg=str(bad)):
                self.action.values(bad)


class ItIsDeterministic(Base):
    def test_the_same_seed_draws_the_same_scribble(self):
        one = self.run_on(gradient(), seed=4)
        two = self.run_on(gradient(), seed=4)
        self.assertEqual(one.tobytes(), two.tobytes())

    def test_another_seed_is_another_scribble(self):
        one = self.run_on(gradient(), seed=4)
        two = self.run_on(gradient(), seed=5)
        self.assertNotEqual(one.tobytes(), two.tobytes())

    def test_the_angle_jitter_changes_how_parallel_the_strips_are(self):
        square = {"spacingJitter": 0, "offsetJitter": 0}
        straight = self.run_on(gradient(), angleJitter=0, **square)
        loose = self.run_on(gradient(), angleJitter=18, **square)
        self.assertNotEqual(straight.tobytes(), loose.tobytes())


class EveryControlDoesSomething(Base):
    def test_wider_spacing_leaves_more_paper(self):
        light = (150, 0, 200, 90)
        tight = self.ink(self.run_on(gradient(), spacing=3, tone=0), box=light)
        loose = self.ink(self.run_on(gradient(), spacing=12, tone=0), box=light)
        self.assertGreater(tight, loose * 2, f"{tight} vs {loose}")

    def test_a_wider_pen_puts_down_more_ink(self):
        light = (150, 0, 200, 90)
        thin = self.ink(self.run_on(gradient(), width=1, tone=0), box=light)
        thick = self.ink(self.run_on(gradient(), width=6, tone=0), box=light)
        self.assertGreater(thick, thin * 2, f"{thick} vs {thin}")

    def test_the_angle_turns_the_whole_screen(self):
        one = self.run_on(gradient(), angle=20, tone=1)
        two = self.run_on(gradient(), angle=70, tone=1)
        self.assertNotEqual(one.tobytes(), two.tobytes())

    def test_spacing_jitter_wobbles_the_gaps_on_its_own(self):
        # one control at a time: with both jitters turned up together, either could be doing the work
        # and removing one of them goes unnoticed (this test was caught doing exactly that)
        square = {"angleJitter": 0, "offsetJitter": 0}
        still = self.run_on(gradient(), spacingJitter=0, **square)
        wobbling = self.run_on(gradient(), spacingJitter=5, **square)
        self.assertNotEqual(still.tobytes(), wobbling.tobytes())

    def test_overhang_walks_the_stroke_ends_on_its_own(self):
        # measured on a shape, not on a full-frame picture: overhang is where the ink stops, so a
        # picture with no silhouette for the strokes to stop on cannot show it at all
        square = {"angleJitter": 0, "spacingJitter": 0, "tone": 0}
        flush = self.run_on(blob(), offsetJitter=0, **square).convert("L").tobytes()
        overhanging = self.run_on(blob(), offsetJitter=12, **square).convert("L").tobytes()
        self.assertNotEqual(flush, overhanging)


class ItFollowsTone(Base):
    def test_at_zero_the_whole_picture_is_hatched(self):
        out = self.run_on(gradient(), tone=0)
        light_side = self.ink(out, box=(160, 0, 200, 90))
        self.assertGreater(light_side, 0, "tone 0 should hatch the light end too")

    def test_at_one_the_light_end_is_left_alone(self):
        # without this, every stroke is equally black on a photo that has no alpha, and the result is
        # wallpaper rather than hatching
        out = self.run_on(gradient(), tone=1)
        self.assertEqual(self.ink(out, box=(175, 0, 200, 90)), 0)


class ItStaysInsideTheShape(Base):
    def test_no_stroke_lands_outside_the_region(self):
        out = self.run_on(blob(), tone=0, spacing=4)
        alpha = out.getchannel("A")
        stroked = out.convert("L")
        for y in range(0, 120, 3):
            for x in range(0, 120, 3):
                if alpha.getpixel((x, y)) == 0:
                    self.assertNotEqual(stroked.getpixel((x, y)), 18,
                                        f"a black stroke at {(x, y)} is outside the shape")

    def test_a_stroke_never_extends_the_shape(self):
        # the capsule: a stroke is clipped to the region and then rounded at the end, so it cannot add
        # an opaque pixel where the picture had none. counting ink colour outside was measuring the
        # transparent black that is already there.
        source = blob()
        if Path("/tmp/hatch-blob.png").exists():
            Path("/tmp/hatch-blob.png").unlink()
        source.save("/tmp/hatch-blob.png")
        out = Image.open(self.action.run({"source": "/tmp/hatch-blob.png"}, str(self.room / "b"),
                                         {"tone": 0, "spacing": 5, "width": 4, "offsetJitter": 12}
                                         )["hatched"]).convert("RGBA")
        was = source.getchannel("A").tobytes()
        is_now = out.getchannel("A").tobytes()
        extra = sum(1 for before, after in zip(was, is_now) if before == 0 and after > 0)
        self.assertEqual(extra, 0)


class TheInk(Base):
    def test_a_flat_ink_paints_one_colour(self):
        out = self.run_on(gradient(), ink="blue", tone=0)
        colours = {colour for _, colour in out.convert("RGB").getcolors(4096) or []}
        self.assertIn((32, 58, 150), colours)

    def test_the_picture_can_be_its_own_ink(self):
        picture = Image.new("RGB", (80, 80), (200, 40, 40))
        out = self.run_on(picture, ink="source", tone=0)
        colours = {colour for _, colour in out.convert("RGB").getcolors(4096) or []}
        # the stroke is the colour underneath it, so a red picture hatches red, not black
        self.assertNotIn((18, 18, 20), colours)
        self.assertTrue(any(r > 150 and g < 80 for r, g, _ in colours))


class ItIsQuick(Base):
    def test_a_board_sized_picture_hatches_in_seconds_not_minutes(self):
        # it is code, so the promise is that a run is instant; a regression here is felt as a lag
        started = time.monotonic()
        self.run_on(gradient(960, 540), spacing=3, width=2)
        self.assertLess(time.monotonic() - started, 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
