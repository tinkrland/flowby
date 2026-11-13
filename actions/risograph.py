# @flowby-name: "Risograph"
# @flowby-description: "Two inks, real misregistration. One or two spot colours printed slightly out of register, the way a duplicator does it."
# @flowby-runtime: python
# @flowby-inputs: [{"name": "source", "type": "image"}]
# @flowby-outputs: [{"name": "printed", "type": "image"}]
# @flowby-params: [
#   {"key": "inks", "label": "Inks", "type": "select", "default": "two", "description": "one ink is a duotone; two is where the misregistration shows",
#    "options": [{"label": "One ink", "value": "one"}, {"label": "Two inks", "value": "two"}]},
#   {"key": "first_ink", "label": "First ink", "type": "select", "default": "blue",
#    "options": [{"label": "Ink blue", "value": "blue"}, {"label": "Ink red", "value": "red"}, {"label": "Ink green", "value": "green"}]},
#   {"key": "second_ink", "label": "Second ink", "type": "select", "default": "red",
#    "visibleIf": [{"key": "inks", "equals": "two"}],
#    "options": [{"label": "Ink red", "value": "red"}, {"label": "Ink orange", "value": "orange"}, {"label": "Ink teal", "value": "teal"}]},
#   {"key": "misregistration", "label": "Misregistration", "type": "number", "default": 2, "min": 0, "max": 12, "step": 1, "unit": "px",
#    "visibleIf": [{"key": "inks", "equals": "two"}],
#    "description": "how far the second plate sits off the first; the whole look lives in this number"},
#   {"key": "threshold", "label": "Ink coverage", "type": "number", "default": 0.55, "min": 0.2, "max": 0.9, "step": 0.05,
#    "description": "how much of the image each plate claims"}
# ]
"""risograph: two spot plates, off register, multiplied onto paper.

misregistration is the point, not a defect to be minimised: a duplicator pulls each drum separately, so
the second plate lands a pixel or two away and the overlap reads darker. the plates are made by
thresholding at different levels of the same grey, which is why one control moves the whole look.
"""

from pathlib import Path

INKS = {"blue": (44, 76, 168), "red": (222, 62, 74), "green": (28, 132, 96),
        "orange": (238, 122, 44), "teal": (26, 130, 140)}
PAPER = (247, 244, 236)


def run(inputs: dict, values: dict, out_dir: str) -> dict:
    from PIL import Image

    grey = Image.open(inputs["source"]).convert("L")
    width, height = grey.size
    paper = Image.new("RGB", (width, height), PAPER)
    threshold = float(values["threshold"])

    # plate one claims the darker half; plate two the lighter half, so the overlap is the midtones and
    # the paper shows through wherever the image is bright
    first = _plate(grey, threshold)
    out = _print(paper, first, INKS[values["first_ink"]])

    if values["inks"] == "two":
        second = _plate(grey, min(0.95, threshold + 0.22))
        shift = int(values["misregistration"])
        out = _print(out, second, INKS[values["second_ink"]], offset=(shift, -shift))

    where = Path(out_dir) / "printed.png"
    where.parent.mkdir(parents=True, exist_ok=True)
    out.save(where)
    return {"printed": str(where)}


def _plate(grey, threshold: float):
    """a mask that is solid where the image is darker than the threshold."""
    cut = int(max(0.0, min(1.0, threshold)) * 255)
    return grey.point(lambda v: 255 if v < cut else 0)


def _print(paper, plate, ink, offset=(0, 0)):
    """multiply one ink through its plate, shifted off register."""
    from PIL import Image, ImageChops

    width, height = paper.size
    solid = Image.new("RGB", (width, height), ink)
    if offset != (0, 0):
        # shifting the plate itself, not the ink, keeps the edges of the image clean
        shifted = Image.new("L", (width, height), 0)
        shifted.paste(plate, offset)
        plate = shifted
    layer = Image.composite(solid, Image.new("RGB", (width, height), (255, 255, 255)), plate)
    return ImageChops.multiply(paper, layer)
