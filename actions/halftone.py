# @flowby-name: "Halftone"
# @flowby-description: "Dots, angles and colour modes. A brightness screen: dark areas grow the dot until it swallows the cell."
# @flowby-runtime: python
# @flowby-inputs: [{"name": "source", "type": "image"}]
# @flowby-outputs: [{"name": "dotted", "type": "image"}]
# @flowby-params: [
#   {"key": "cell", "label": "Dot size", "type": "number", "default": 8, "min": 3, "max": 24, "step": 1,
#    "unit": "px", "description": "how many pixels make one dot's cell; smaller is a finer screen"},
#   {"key": "angle", "label": "Screen angle", "type": "select", "default": "45",
#    "description": "turning the screen is what stops dots reading as a grid",
#    "options": [{"label": "0°", "value": "0"}, {"label": "15°", "value": "15"},
#                {"label": "45°", "value": "45"}, {"label": "75°", "value": "75"}]},
#   {"key": "colour", "label": "Ink", "type": "select", "default": "black",
#    "options": [{"label": "Black", "value": "black"}, {"label": "Ink blue", "value": "blue"},
#                {"label": "Ink red", "value": "red"}]}
# ]
"""halftone: a brightness screen, written as an action so its controls come out of the header.

the work is the same one a print shop does: rotate the screen off the pixel grid, measure each cell,
grow a dot in proportion to how dark that cell is, and rotate back. it is deterministic, costs nothing,
and needs no model, which is exactly why it belongs here rather than on the paid side of the board.
"""

from pathlib import Path

INKS = {"black": (16, 16, 18), "blue": (28, 48, 150), "red": (208, 48, 66)}


def run(inputs: dict, values: dict, out_dir: str) -> dict:
    """inputs: {source}; values: the header's params; returns {dotted: path}."""
    from PIL import Image, ImageDraw

    cell = int(values["cell"])
    angle = float(values["angle"])
    ink = INKS[values["colour"]]

    source = Image.open(inputs["source"]).convert("L")
    width, height = source.size
    if width < cell or height < cell:
        raise ValueError(f"a {width}x{height} image is smaller than one {cell}px dot")

    # measure on a rotated copy so the dots sit on a diagonal, then rotate the dots back
    screen = source.rotate(angle, resample=Image.BILINEAR, fillcolor=255)
    dots = Image.new("L", (width, height), 255)
    pen = ImageDraw.Draw(dots)
    grey = screen.load()
    for top in range(0, height, cell):
        for left in range(0, width, cell):
            # the mean of the cell, not its corner: a corner sample makes stripes alias into dots
            total = 0
            count = 0
            for y in range(top, min(top + cell, height)):
                for x in range(left, min(left + cell, width)):
                    total += grey[x, y]
                    count += 1
            dark = (255 - total / count) / 255
            radius = dark * cell * 0.62
            if radius < 0.5:
                continue
            cx, cy = left + cell / 2, top + cell / 2
            pen.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)

    mask = dots.rotate(-angle, resample=Image.BILINEAR, fillcolor=255)
    out = Image.new("RGB", (width, height), (246, 244, 238))
    out.paste(ink, mask=mask.point(lambda v: 255 - v))
    where = Path(out_dir) / "dotted.png"
    where.parent.mkdir(parents=True, exist_ok=True)
    out.save(where)
    return {"dotted": str(where)}
