"""three doors into one graph.

the three products this tree is built between each open on a different first move:

* **freeform**, which is closer to fuser: the first thing you do is type, and the typing goes
  straight into a model.
* **fixed**, which is closer to vectary canvas: the first thing you do is press a card, and the
  card hides a graph.
* **style**, which is where base44's studio sits: the first thing you do is bring a reference, and
  then the interesting part is carrying it across more than one frame.

the claim worth making is not that flowby has all three. it is that the three are **entry points
into the same graph**, and that claim is only worth anything if you can cross from any one of them
into the others without exporting, re-importing, or starting again. so each mode below carries the
crossing it promises, and `tests/selftest.py` performs every crossing on a real board rather than
trusting this docstring.

one honest gap: the style mode is modelled from the description of base44's studio rather than from
the product. the appraisal of it is in `docs/research.md` and it says the same thing.
"""

from dataclasses import dataclass

from . import presets


@dataclass(frozen=True)
class Mode:
    name: str
    label: str
    first_move: str
    opens: str
    crosses_to: tuple[str, ...]
    crossing: str
    cost_before_press: str


MODES = {
    "freeform": Mode(
        name="freeform",
        label="type, and the typing is the first node",
        first_move="a text element on the board, which is an amber node the moment it exists",
        opens=("an amber wire into whatever you point it at; the prompt is a parameter of a node, "
               "not a setting of the application"),
        crosses_to=("fixed", "style"),
        crossing=("apply a preset to it and it becomes a subgraph with sliders; the words you "
                  "typed are still a node you can rewire, which is the difference between a "
                  "prompt box and a prompt node"),
        cost_before_press="the preset's estimate, before anything is spent, including the fan",
    ),
    "fixed": Mode(
        name="fixed",
        label="press a card, and the card is a graph",
        first_move="a preset card in the sidebar, chosen by what it does rather than by model",
        opens="a spawned subgraph, wired and left visible underneath the frame it landed on",
        crosses_to=("freeform", "style"),
        crossing=("open the pipeline view and every node of the preset is addressable: rewire an "
                  "input, fill a slot from another frame, or point the frame at an intermediate "
                  "node instead of the sink"),
        cost_before_press="the same estimate, plus the read/write wires it will need",
    ),
    "style": Mode(
        name="style",
        label="bring a reference, then carry it",
        first_move="a reference frame, because a style is something you have rather than describe",
        opens=("a preset that refuses to compile until the reference exists (its Slot), or one "
               "head read shared across every frame (its shared_seam)"),
        crosses_to=("fixed", "freeform"),
        crossing=("a carried style is still a node: swap the reference, drop the board reach to a "
                  "single frame, or take the head apart and wire the palette somewhere else"),
        cost_before_press=("one read and N applications for a board, and the panel says N before "
                           "you press it"),
    ),
}


def legend() -> dict:
    """the three doors, as data, for the CLI and for a test that reads the readme."""
    crossing_matrix = {name: list(mode.crosses_to) for name, mode in MODES.items()}
    return {
        "modes": [
            {
                "name": mode.name,
                "label": mode.label,
                "first_move": mode.first_move,
                "opens": mode.opens,
                "crosses_to": list(mode.crosses_to),
                "crossing": mode.crossing,
                "cost_before_press": mode.cost_before_press,
            }
            for mode in MODES.values()
        ],
        "crossings": crossing_matrix,
        "reachable": _every_mode_reaches_every_other(),
        "presets_by_door": _by_door(),
    }


def _every_mode_reaches_every_other() -> bool:
    """a door you cannot leave is a product, not a mode."""
    for name, mode in MODES.items():
        for other in MODES:
            if other == name or other in mode.crosses_to:
                continue
            return False
    return True


def _by_door() -> dict:
    """which presets open on which move, so the sidebar can lead with the right ones."""
    doors: dict[str, list[str]] = {name: [] for name in MODES}
    for preset in presets.PRESETS.values():
        if preset.shared_seam or preset.slots:
            doors["style"].append(preset.name)
        elif preset.input_dtype == "text":
            doors["freeform"].append(preset.name)
        else:
            doors["fixed"].append(preset.name)
    return doors
