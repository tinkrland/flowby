# @flowby-name: "Hatching"
# @flowby-description: "Scribble lines that follow the shape. Strips at one angle, each nudged off register, ending round at the object's edge rather than cut square."
# @flowby-runtime: python
# @flowby-inputs: [{"name": "source", "type": "image"}]
# @flowby-outputs: [{"name": "hatched", "type": "image"}]
# @flowby-params: [
#   {"key": "angle", "label": "Angle", "type": "number", "default": 45, "min": 0, "max": 180, "step": 5,
#    "unit": "°", "description": "the whole screen turns together; hand hatching is usually 30-60°"},
#   {"key": "spacing", "label": "Spacing", "type": "number", "default": 3, "min": 2, "max": 20, "step": 1,
#    "unit": "px", "description": "distance between strips before they wobble"},
#   {"key": "width", "label": "Line width", "type": "number", "default": 2, "min": 1, "max": 10, "step": 1,
#    "unit": "px", "description": "thickness of the pen, drawn round-capped"},
#   {"key": "angleJitter", "label": "Angle jitter", "type": "number", "default": 4, "min": 0, "max": 20, "step": 1,
#    "unit": "°", "description": "how far each strip tilts off the screen angle"},
#   {"key": "spacingJitter", "label": "Spacing jitter", "type": "number", "default": 1, "min": 0, "max": 6, "step": 1,
#    "unit": "px", "description": "spacing wobble across the strips"},
#   {"key": "offsetJitter", "label": "Overhang", "type": "number", "default": 3, "min": 0, "max": 12, "step": 1,
#    "unit": "px", "description": "how far each stroke's ends wander along the strip"},
#   {"key": "tone", "label": "Follows tone", "type": "number", "default": 0.6, "min": 0, "max": 1, "step": 0.05,
#    "description": "0 hatches the whole picture evenly; 1 only marks the dark parts"},
#   {"key": "ink", "label": "Ink", "type": "select", "default": "black",
#    "options": [{"label": "Black", "value": "black"}, {"label": "Ink blue", "value": "blue"},
#                {"label": "Ink red", "value": "red"},
#                {"label": "From the picture", "value": "source"}]},
#   {"key": "seed", "label": "Seed", "type": "number", "default": 7, "min": 0, "max": 999, "step": 1,
#    "description": "same seed, same scribble, every time"}
# ]
"""hatching: the scratchy, hand-drawn line fill, ported from a shader rather than invented.

the technique is Amagi's "Hatching Effect with VFX-JS" pen (`codepen.io/fand/pen/RNovGmR`, read
2026-11-13) reduced from GLSL to PIL. the shader's idea, which is the whole reason it looks drawn rather
than printed:

  - the screen is strips indexed by their distance along one normal, exactly like a halftone screen, but
  - every strip gets its own angle (`angleJitter`), its own spacing (`spacingJitter`) and its own pivot
    point pushed along its own direction, so the strips are not parallel and do not line up at the edge,
  - the stroke is not a strip clipped by the region, it is a **capsule**: the part of the centreline that
    lies inside the region, shifted along itself by `offsetJitter`, thickened by `width`, with round caps.
    that is why a stroke ends in a circle at the silhouette instead of a square cut,
  - overlapping strokes take the **maximum** ink, not the sum, so crossings do not go darker than a line,
  - and the stroke may take its colour from the picture underneath instead of one flat ink.

the shader measures the capsule analytically (a distance field with a search along the line for the
nearest covered point). this does the same shape by rasterising: clip the centreline to the region,
dilate it into a disc, and paste. same geometry, no per-pixel loop, no numpy.

one thing is flowby's and not the pen's: `tone`. the pen draws over a DOM element whose alpha is the
region, and a portrait has no alpha, so without a density signal every line is equally black and the
result is wallpaper. `tone` multiplies the ink by darkness, so the strokes gather where the picture is
dark, which is what a person means by "hatch this".
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

INKS = {"black": (18, 18, 20), "blue": (32, 58, 150), "red": (176, 42, 40)}


def _hash(n: float) -> float:
    """the shader's `fract(sin(n * 127.1) * 43758.5453123)`, kept so a seed means the same thing here."""
    return (math.sin(n * 127.1) * 43758.5453123) % 1.0


def _region(image: Image.Image) -> Image.Image:
    """where a stroke may exist: the alpha channel, or everywhere if the picture has none."""
    if image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info):
        return image.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 8 else 0)
    return Image.new("L", image.size, 255)


def _disc(radius: int) -> list[tuple[int, int]]:
    """the offsets that dilate a one-pixel line into a stroke of `2 * radius + 1` with round caps."""
    if radius <= 0:
        return [(0, 0)]
    offsets = [(0, 0)]
    steps = max(8, radius * 6)
    for step in range(steps):
        turn = 2 * math.pi * step / steps
        for reach in range(1, radius + 1):
            dx, dy = round(math.cos(turn) * reach), round(math.sin(turn) * reach)
            if (dx, dy) not in offsets:
                offsets.append((dx, dy))
    return offsets


def _move(mask: Image.Image, dx: float, dy: float) -> Image.Image:
    """a translate that does not wrap: the canvas is padded by more than the largest shift."""
    if not dx and not dy:
        return mask
    return ImageChops.offset(mask, int(round(dx)), int(round(dy)))


def run(inputs: dict, values: dict, out_dir: str) -> dict:
    source = Image.open(inputs["source"]).convert("RGBA")
    width, height = source.size
    angle_deg = float(values["angle"])
    spacing = max(2, int(values["spacing"]))
    pen = max(1, int(values["width"]))
    angle_jitter = math.radians(float(values["angleJitter"]))
    spacing_jitter = float(values["spacingJitter"])
    overhang = float(values["offsetJitter"])
    tone = float(values["tone"])
    seed = float(values["seed"])
    ink = str(values["ink"])

    # work on a padded canvas so a shifted mask never wraps a stroke round to the far edge
    pad = int(math.ceil(pen + overhang + spacing + 2))
    size = (width + 2 * pad, height + 2 * pad)
    region = Image.new("L", size, 0)
    region.paste(_region(source), (pad, pad))

    base = math.radians(angle_deg)
    normal = (-math.sin(base), math.cos(base))
    along = (math.cos(base), math.sin(base))
    centre = (size[0] * 0.5, size[1] * 0.5)
    diagonal = math.hypot(*size)

    # every strip whose line can cross the canvas, plus a margin for the ones whose pivot drifted in
    reach = int(diagonal / spacing) + 4
    middle = int(round((centre[0] * normal[0] + centre[1] * normal[1]) / spacing))

    spans = Image.new("L", size, 0)
    for index in range(middle - reach, middle + reach + 1):
        tilt = base + (_hash(index * 1.37 + seed) - 0.5) * angle_jitter
        direction = (math.cos(tilt), math.sin(tilt))
        strip_normal = (-math.sin(tilt), math.cos(tilt))
        offset = (index + 0.5) * spacing + (_hash(index * 3.91 + seed) - 0.5) * 2.0 * spacing_jitter

        # the pivot walks along the strip by up to half the canvas at full jitter: that is what makes a
        # tilted strip drift away from the place its spacing put it
        drift = ((_hash(index * 7.13 + seed) * 2.0 - 1.0)
                 * min(1.0, angle_jitter / math.radians(10)) * 0.5)
        pivot = (centre[0] + strip_normal[0] * offset + direction[0] * drift * diagonal,
                 centre[1] + strip_normal[1] * offset + direction[1] * drift * diagonal)

        span = Image.new("L", size, 0)
        ImageDraw.Draw(span).line(
            [(pivot[0] - direction[0] * diagonal, pivot[1] - direction[1] * diagonal),
             (pivot[0] + direction[0] * diagonal, pivot[1] + direction[1] * diagonal)],
            fill=255, width=1)
        # the stroke's ink is the part of the line the picture covers, shifted along the line itself
        shift = (_hash(index * 5.23 + seed) - 0.5) * 2.0 * overhang
        covered = ImageChops.multiply(span, _move(region, -shift * direction[0], -shift * direction[1]))
        if covered.getbbox() is None:
            continue
        spans = ImageChops.lighter(spans, covered)

    # one dilation for the whole file rather than one per stroke: the union of a one-pixel line and its
    # disc is a round-capped stroke, and taking the lightest keeps crossings no darker than a line
    stroke = Image.new("L", size, 0)
    for dx, dy in _disc(max(0, (pen - 1) // 2)):
        stroke = ImageChops.lighter(stroke, _move(spans, dx, dy))

    # and then clipped to the shape again after thickening. the reference thickens a centreline that is
    # already clipped, which lets ink spill half a pen past the silhouette; painting into a picture
    # instead of over a DOM element, that spill is a dark fringe on transparent pixels, so the dilate
    # happens first and the clip after: the ends still land in an arc on the edge, inside the shape.
    stroke = ImageChops.multiply(stroke, region)

    if tone > 0:
        # a portrait has no alpha, so without a density signal every stroke is equally black and the
        # result is wallpaper: fade the ink by darkness, at 0 leaving it untouched
        darkness = Image.new("L", size, 0)
        darkness.paste(source.convert("L").point(lambda v: 255 - v), (pad, pad))
        stroke = ImageChops.multiply(stroke, darkness.point(lambda v: int(255 - tone * (255 - v))))

    paper = Image.new("RGBA", size, (0, 0, 0, 0))
    paper.paste(source, (pad, pad))
    if ink == "source":
        # the stroke takes the colour underneath, which is how a hatch sits in a picture, not on it
        painted = Image.composite(paper.copy(), paper, stroke)
    else:
        flat = Image.new("RGBA", size, (*INKS.get(ink, INKS["black"]), 255))
        painted = Image.composite(flat, paper, stroke)

    where = Path(out_dir)
    where.mkdir(parents=True, exist_ok=True)
    target = where / "hatched.png"
    painted.crop((pad, pad, pad + width, pad + height)).save(target)
    return {"hatched": str(target)}
