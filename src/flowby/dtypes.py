"""the four colours, and the rule that keeps the palette from growing.

a wire is a promise about what can travel on it: amber is text, green is image, blue is video,
red is mesh. four types is already the largest palette an eye can hold at a glance, and the
glance is the entire reason the pipeline layer exists. so a fifth thing that wants a colour does
not get one, it gets a `role` and rides the wire it already fits.

the other half of this file is the refusal. nothing coerces. an image does not become a mesh by
being plugged into a mesh port, it becomes a mesh by passing through a node that says so, which
means the conversion is visible on the board instead of hidden in a rule.
"""

from dataclasses import dataclass


class UnknownDtype(Exception):
    """a wire that is not one of the four, refused rather than given a default colour."""


@dataclass(frozen=True)
class Wire:
    dtype: str
    colour: str
    hex: str
    means: str


WIRES = {
    "text": Wire("text", "amber", "#f59e0b", "words: a prompt, a caption, a parameter said out loud"),
    "image": Wire("image", "green", "#22c55e", "a still: pixels, a render, a mask, a depth map"),
    "video": Wire("video", "blue", "#3b82f6", "ordered stills with time attached"),
    "mesh": Wire("mesh", "red", "#ef4444", "geometry: vertices, faces, materials, a scene graph"),
}

# the control channels are not dtypes. they are hints about what a green wire is carrying,
# because a depth map and a portrait are the same four numbers and the wrong kind of green.
ROLES = {
    "depth": "a controlnet channel read out of geometry the board already has",
    "mask": "what to leave alone, drawn on the canvas",
    "pose": "skeleton hints, for a composition that has to move like something",
    "palette": "colours lifted from one image and handed to another",
    "style": "the look of a reference, without its content",
}


def wire(dtype: str) -> Wire:
    try:
        return WIRES[dtype]
    except KeyError:
        raise UnknownDtype(
            f"{dtype!r} is not a wire. the palette is {', '.join(sorted(WIRES))}."
        ) from None


def colour(dtype: str) -> str:
    return wire(dtype).colour


def hex_of(dtype: str) -> str:
    return wire(dtype).hex


def role(name: str) -> str:
    """a role is checked against the list so a typo is a refusal, not a silent extra channel."""
    if name not in ROLES:
        raise UnknownDtype(f"{name!r} is not a role. the roles are {', '.join(sorted(ROLES))}.")
    return name


def of_role(name: str) -> str:
    """every role rides green, which is the whole point of having roles instead of colours."""
    role(name)
    return "image"


def accepts(src: str, dst: str) -> bool:
    """an edge carries one dtype, unchanged. equality, not convertibility."""
    return wire(src).dtype == wire(dst).dtype


def mismatch(src: str, dst: str) -> str:
    s, d = wire(src), wire(dst)
    return (
        f"a {s.colour} wire ({s.dtype}) cannot feed a {d.colour} port ({d.dtype}). "
        f"put a node between them that does the conversion, so it is visible."
    )


def palette() -> list[dict]:
    """the legend, as data, for the inspector and for a test that reads the readme."""
    return [
        {"dtype": w.dtype, "colour": w.colour, "hex": w.hex, "means": w.means}
        for w in WIRES.values()
    ]
