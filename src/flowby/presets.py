"""presets: a slider you can drag, and the subgraph it actually is.

a preset is not a macro that hides nodes. it is a small graph that gets spawned, wired and left
visible, plus a list of parameters it exposes to the spatial layer as sliders. the abstraction
lives in the presentation only: the graph is the truth, the slider is a view of one port's
default, and the sidebar is a projection of the preset's `exposed` list.

that single decision is why "break apart a preset" is a one line operation later instead of a
rewrite: there is nothing to unwrap, the subgraph was always there.
"""

from dataclasses import dataclass, field

from . import dtypes
from .graph import Port


class PresetRefused(Exception):
    """the preset cannot do what was asked, and says why in words a slider can display."""


@dataclass(frozen=True)
class Target:
    """one node parameter a slider moves. `low`/`high` rescale human range onto machine range."""

    node: str
    param: str
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True)
class Slider:
    name: str
    label: str
    low: float
    high: float
    default: float
    means: str
    targets: tuple[Target, ...]
    unit: str = ""
    kind: str = "number"
    choices: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if self.kind not in ("number", "choice"):
            raise PresetRefused(f"{self.name}: {self.kind!r} is not a control kind")
        if self.kind == "choice":
            if not self.choices:
                raise PresetRefused(f"{self.name} is a choice with nothing to choose")
            labels = [c[0] for c in self.choices]
            if len(set(labels)) != len(labels):
                raise PresetRefused(f"{self.name} offers {', '.join(labels)} twice")
            if self.default not in labels:
                raise PresetRefused(
                    f"{self.name} defaults to {self.default!r}, which is not one of "
                    f"{', '.join(labels)}"
                )
        elif not (self.low <= self.default <= self.high):
            raise PresetRefused(
                f"{self.name} defaults to {self.default:g}, outside its own {self.low:g}..{self.high:g}"
            )

    def where(self, value) -> float:
        """the slider's own position for a stored value, which is 0..1 for the frontend."""
        if self.kind == "choice":
            labels = [c[0] for c in self.choices]
            return labels.index(value) / max(1, len(labels) - 1)
        span = self.high - self.low
        return 0.0 if span == 0 else (float(value) - self.low) / span

    def check(self, value):
        if self.kind == "choice":
            if value not in [c[0] for c in self.choices]:
                raise PresetRefused(
                    f"{self.name} is {value!r}; the choices are "
                    f"{', '.join(c[0] for c in self.choices)}"
                )
            return value
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise PresetRefused(f"{self.name} takes a number, not {value!r}") from None
        if not (self.low <= number <= self.high):
            raise PresetRefused(
                f"{self.name} runs {self.low:g} to {self.high:g}{self.unit}; {number:g} is outside it"
            )
        return number

    def project(self, value) -> list[tuple[str, str, object]]:
        """(node role, param, machine value) for every node this slider moves."""
        self.check(value)
        if self.kind == "choice":
            mapped = dict(self.choices)[value]
        else:
            mapped = float(value)
        out = []
        for target in self.targets:
            if target.low is None or target.high is None or self.kind == "choice":
                machine = mapped
            else:
                span = self.high - self.low
                step = 0.0 if span == 0 else (mapped - self.low) / span
                machine = target.low + step * (target.high - target.low)
                if isinstance(target.low, int) and isinstance(target.high, int):
                    machine = int(round(machine))
            out.append((target.node, target.param, machine))
        return out


@dataclass(frozen=True)
class Sweep:
    """one parameter, several values, several results side by side.

    this is the shape both reference products sell and neither of them explains, because it reads as
    a feature and is actually a compiler question: the work before the swept node happens once, and
    only the branch after it is duplicated per value. six lighting versions is one read and six
    renders, not six of everything.
    """

    slider: str
    label: str
    values: tuple

    def __post_init__(self):
        if not self.values:
            raise PresetRefused(f"{self.label} sweeps nothing")
        if len(set(self.values)) != len(self.values):
            raise PresetRefused(f"{self.label} sweeps {self.values} and repeats itself")

    def __len__(self) -> int:
        return len(self.values)


@dataclass(frozen=True)
class Slot:
    """an input a preset needs and cannot invent.

    style transfer is the honest example: the thing being repainted comes from the frame you
    clicked, and the look it is repainted *in* comes from somewhere else. a preset with a slot
    spawns incomplete and refuses to compile until a second asset is wired in, and the sentence it
    refuses with is the instruction for doing that.
    """

    name: str
    node: str
    port: str
    dtype: str
    means: str


@dataclass(frozen=True)
class Step:
    op: str
    label: str
    inputs: dict[str, Port] = field(default_factory=dict)
    outputs: dict[str, Port] = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    requires: dict = field(default_factory=dict)


def image(role: str | None = None, **kw) -> Port:
    return Port("image", role=role, **kw)


@dataclass(frozen=True)
class Preset:
    name: str
    label: str
    blurb: str
    applies_to: tuple[str, ...]
    input_dtype: str
    entry: str
    entry_port: str
    sink: str
    steps: dict[str, Step]
    edges: tuple[tuple[str, str, str, str], ...]
    sliders: dict[str, Slider]
    slots: tuple[Slot, ...] = ()
    sweep: Sweep | None = None
    stage: str = "explore"
    flips_plane: str | None = None
    state: str = "designed"
    evidence: str = "no asset has come back from a worker yet"

    def __post_init__(self):
        dtypes.wire(self.input_dtype)
        if self.sink not in self.steps:
            raise PresetRefused(f"{self.name}: sink {self.sink!r} is not one of its steps")
        if self.entry not in self.steps:
            raise PresetRefused(f"{self.name}: entry {self.entry!r} is not one of its steps")
        for a, ap, b, bp in self.edges:
            for role_name, port in ((a, ap), (b, bp)):
                if role_name not in self.steps:
                    raise PresetRefused(f"{self.name}: edge names {role_name!r}, which it does not have")
        if self.stage not in STAGES:
            raise PresetRefused(f"{self.name}: {self.stage!r} is not a stage")
        for slot in self.slots:
            if slot.node not in self.steps:
                raise PresetRefused(f"{self.name}: slot {slot.name!r} names a step it lacks")
            if slot.port not in self.steps[slot.node].inputs:
                raise PresetRefused(
                    f"{self.name}: slot {slot.name!r} names {slot.port!r}, "
                    f"which {slot.node} does not take"
                )
            dtypes.wire(slot.dtype)
        if self.sweep is not None and self.sweep.slider not in self.sliders:
            raise PresetRefused(
                f"{self.name} sweeps {self.sweep.slider!r}, which is not one of its sliders"
            )
        if self.sweep is not None:
            slider = self.sliders[self.sweep.slider]
            for value in self.sweep.values:
                slider.check(value)
        for slider in self.sliders.values():
            slider.project(slider.default)
            for target in slider.targets:
                if target.node not in self.steps:
                    raise PresetRefused(
                        f"{self.name}.{slider.name} moves {target.node}, which is not a step"
                    )
                if target.param not in self.steps[target.node].params:
                    raise PresetRefused(
                        f"{self.name}.{slider.name} moves {target.node}.{target.param}, "
                        f"which is not a parameter of it"
                    )

    def out_dtype(self) -> str:
        outputs = self.steps[self.sink].outputs
        return next(iter(outputs.values())).dtype

    def minutes(self) -> float:
        return sum(step.requires.get("minutes", 0) for step in self.steps.values())

    def branch_point(self) -> str:
        """the node the sweep starts at: the first target of the swept slider."""
        if self.sweep is None:
            return ""
        return self.sliders[self.sweep.slider].targets[0].node

    def tail(self) -> set[str]:
        """every step at or after the branch point, which is the part the sweep duplicates."""
        start = self.branch_point()
        if not start:
            return set()
        reached = {start}
        growing = True
        while growing:
            growing = False
            for a, _, b, _ in self.edges:
                if a in reached and b not in reached:
                    reached.add(b)
                    growing = True
        return reached

    def estimate(self, values: dict | None = None) -> dict:
        """what this costs if you press it. both products above show this before the run, not
        after, and it is the single cheapest thing that stops a board from being a slot machine."""
        tail = self.tail()
        copies = len(self.sweep.values) if self.sweep else 1
        gpu = sum(step.requires.get("minutes", 0) * (copies if role in tail else 1)
                  for role, step in self.steps.items() if step.requires.get("gpu"))
        total = sum(step.requires.get("minutes", 0) * (copies if role in tail else 1)
                    for role, step in self.steps.items())
        return {"minutes": round(total, 1),
                "gpu_minutes": round(gpu, 1),
                "cpu_minutes": round(total - gpu, 1),
                "models": sorted({m for step in self.steps.values()
                                  for m in (step.requires.get("models") or [])})}

    def sidebar(self, values: dict | None = None) -> dict:
        """the contextual panel's payload: what this preset does, and the controls it exposes."""
        values = {s.name: s.default for s in self.sliders.values()} | (values or {})
        return {
            "preset": self.name,
            "label": self.label,
            "blurb": self.blurb,
            "state": self.state,
            "evidence": self.evidence,
            "changes": {"from": self.input_dtype, "to": self.out_dtype(),
                        "plane": self.flips_plane},
            "controls": [
                {
                    "name": s.name,
                    "label": s.label,
                    "kind": s.kind,
                    "low": s.low,
                    "high": s.high,
                    "unit": s.unit,
                    "means": s.means,
                    "value": values[s.name],
                    "where": s.where(values[s.name]),
                    "choices": [c[0] for c in s.choices],
                }
                for s in self.sliders.values()
            ],
            "nodes": len(self.steps),
            "stage": self.stage,
            "minutes": self.minutes(),
            "estimate": self.estimate(values),
            "slots": [{"name": s.name, "node": s.node, "port": s.port,
                       "dtype": s.dtype, "means": s.means} for s in self.slots],
            "sweep": ({"slider": self.sweep.slider, "label": self.sweep.label,
                       "values": list(self.sweep.values),
                       "variants": len(self.sweep.values)} if self.sweep else None),
        }


# vectary canvas walks a piece of work through four stages, and the vocabulary is the useful part:
# collect what inspires it, explore directions, refine one, validate in context. a preset knows which
# stage it belongs to, so the sidebar can group by intent instead of by model.
STAGES = {
    "explore": "find a direction",
    "refine": "push one direction further",
    "output": "turn it into something deliverable",
}

PRESETS: dict[str, Preset] = {}


def register(preset: Preset) -> Preset:
    if preset.name in PRESETS:
        raise PresetRefused(f"{preset.name} is already registered")
    PRESETS[preset.name] = preset
    return preset


def get(name: str) -> Preset:
    try:
        return PRESETS[name]
    except KeyError:
        raise PresetRefused(
            f"there is no preset {name!r}. the presets are {', '.join(sorted(PRESETS))}."
        ) from None


def names() -> list[str]:
    return list(PRESETS)


# ---------------------------------------------------------------------------
# the presets themselves. every one of these is `designed`: the graph is wired
# and refused correctly, and nothing here has produced a pixel on real hardware.


register(Preset(
    name="text-to-image",
    label="write it into a frame",
    blurb="a sentence becomes a still, and the sentence stays editable on the board.",
    applies_to=("text",),
    input_dtype="text",
    entry="write",
    entry_port="draft",
    sink="paint",
    steps={
        "write": Step(
            op="text.compose",
            label="the sentence",
            inputs={"draft": Port("text", optional=True)},
            outputs={"out": Port("text")},
            params={"prefix": "", "mood": "clean"},
            requires={"minutes": 0.2},
        ),
        "paint": Step(
            op="image.gen",
            label="generate",
            inputs={"prompt": Port("text"),
                    "look": image("style", optional=True)},
            outputs={"out": Port("image")},
            params={"steps": 28, "guidance": 6.0, "size": 1024},
            requires={"pip": ["diffusers", "torch"], "models": ["sdxl-turbo"],
                      "gpu": True, "minutes": 1.6, "needs": {"image": "a reference, or none"}},
        ),
    },
    edges=(("write", "out", "paint", "prompt"),),
    stage="explore",
    sliders={
        "detail": Slider(
            name="detail", label="detail", low=8, high=48, default=28,
            means="how many passes the generator takes. more detail, more waiting.",
            targets=(Target("paint", "steps"),),
            unit=" steps",
        ),
        "fidelity": Slider(
            name="fidelity", label="fidelity", low=1.0, high=14.0, default=6.0,
            means="how strictly it follows the words, at the cost of invention.",
            targets=(Target("paint", "guidance"),),
        ),
        "mood": Slider(
            name="mood", label="mood", low=0, high=1, default="clean",
            means="a house style, appended to whatever you wrote.",
            kind="choice",
            choices=(("clean", "clean"), ("film", "35mm film, grain"),
                     ("neon", "neon, wet streets"), ("paper", "paper, ink")),
            targets=(Target("write", "mood"),),
        ),
    },
))


register(Preset(
    name="sketch-to-mesh",
    label="convert sketch to 3d mesh",
    blurb="the drawing you made becomes geometry, in the same place on the board.",
    applies_to=("sketch", "image"),
    input_dtype="image",
    entry="read",
    entry_port="image",
    sink="bake",
    flips_plane="3d",
    steps={
        "read": Step(
            op="control.depth",
            label="read the volume",
            inputs={"image": Port("image")},
            outputs={"out": image("depth")},
            params={"weight": 0.7, "blur": 2},
            requires={"pip": ["opencv-python-headless", "torch"], "minutes": 0.4},
        ),
        "mould": Step(
            op="mesh.triposr",
            label="build the mesh",
            inputs={"control": image("depth")},
            outputs={"out": Port("mesh")},
            params={"target_faces": 60000, "guidance": 4.5, "smooth": 2},
            requires={"pip": ["trimesh", "torch"], "models": ["triposr"],
                      "gpu": True, "minutes": 3.2},
        ),
        "bake": Step(
            op="mesh.bake",
            label="seams and normals",
            inputs={"geometry": Port("mesh")},
            outputs={"out": Port("mesh")},
            params={"uv_tile": 2, "weld": 0.0005, "normals": "smooth"},
            requires={"pip": ["trimesh"], "minutes": 0.9},
        ),
    },
    edges=(("read", "out", "mould", "control"), ("mould", "out", "bake", "geometry")),
    stage="explore",
    sliders={
        "detail": Slider(
            name="detail", label="surface detail", low=4000, high=150000, default=60000,
            means="the polygon budget. detail you can see, at the price of load time.",
            targets=(Target("mould", "target_faces"),),
            unit=" faces",
        ),
        "fidelity": Slider(
            name="fidelity", label="fidelity to the drawing", low=0.3, high=1.0, default=0.7,
            means="how much the depth channel is trusted over the model's own guess.",
            targets=(Target("read", "weight"),),
        ),
        "smooth": Slider(
            name="smooth", label="smoothness", low=0, high=5, default=2,
            means="how many times the surface is relaxed. high smooths away thin strokes.",
            targets=(Target("mould", "smooth"),),
        ),
    },
))


register(Preset(
    name="frosted-glass",
    label="apply matte frosted glass",
    blurb="a material, applied to whatever mesh is selected, without a shading language.",
    applies_to=("model",),
    input_dtype="mesh",
    entry="shell",
    entry_port="geometry",
    sink="light",
    steps={
        "shell": Step(
            op="shade.pbr",
            label="the material",
            inputs={"geometry": Port("mesh")},
            outputs={"out": Port("mesh")},
            params={"roughness": 0.35, "transmission": 0.6, "ior": 1.5, "tint": "#ffffff"},
            requires={"pip": ["trimesh"], "minutes": 0.4},
        ),
        "light": Step(
            op="shade.light",
            label="light it",
            inputs={"scene": Port("mesh")},
            outputs={"out": Port("mesh")},
            params={"key": 3.0, "fill": 1.2, "temp": 5600},
            requires={"pip": ["trimesh"], "minutes": 0.5},
        ),
    },
    edges=(("shell", "out", "light", "scene"),),
    stage="refine",
    sliders={
        "frost": Slider(
            name="frost", label="frost", low=0.05, high=0.7, default=0.35,
            means="how much the surface scatters instead of reflecting. glass to stone.",
            targets=(Target("shell", "roughness"),),
        ),
        "clarity": Slider(
            name="clarity", label="clarity", low=0.0, high=0.95, default=0.6,
            means="how much light passes through. high clarity needs more samples to be quiet.",
            targets=(Target("shell", "transmission"),),
        ),
        "warmth": Slider(
            name="warmth", label="warmth", low=2700, high=8000, default=5600,
            means="the colour temperature of the key light, in kelvin.",
            targets=(Target("light", "temp"),),
            unit="K",
        ),
    },
))


register(Preset(
    name="animate-composition",
    label="animate scene composition",
    blurb="the composition becomes a shot: a camera move, and frames to prove it.",
    applies_to=("model",),
    input_dtype="mesh",
    entry="stage",
    entry_port="geometry",
    sink="film",
    steps={
        "stage": Step(
            op="scene.stage",
            label="stage the board",
            inputs={"geometry": Port("mesh")},
            outputs={"out": Port("mesh")},
            params={"floor": True, "spacing": 1.0},
            requires={"pip": ["trimesh"], "minutes": 0.4},
        ),
        "rig": Step(
            op="anim.orbit",
            label="move the camera",
            inputs={"scene": Port("mesh")},
            outputs={"out": Port("mesh")},
            params={"frames": 120, "degrees": 180, "ease": "ease-in-out"},
            requires={"pip": ["numpy"], "minutes": 0.7},
        ),
        # the one place a dtype changes hands: red goes in, blue comes out, and it is a node
        # you can see rather than a rule hidden in the wire.
        "film": Step(
            op="render.frames",
            label="render the shot",
            inputs={"scene": Port("mesh")},
            outputs={"out": Port("video")},
            params={"fps": 24, "codec": "h264", "samples": 64},
            requires={"pip": ["bpy", "imageio-ffmpeg"], "gpu": True, "minutes": 7.5},
        ),
    },
    edges=(("stage", "out", "rig", "scene"), ("rig", "out", "film", "scene")),
    stage="output",
    sliders={
        "duration": Slider(
            name="duration", label="duration", low=2, high=15, default=5,
            means="seconds of finished shot. frames are 24 a second and cost the same each.",
            targets=(Target("rig", "frames", 48, 360),),
            unit="s",
        ),
        "orbit": Slider(
            name="orbit", label="orbit", low=0, high=360, default=180,
            means="how far the camera travels around the composition.",
            targets=(Target("rig", "degrees"),),
            unit="°",
        ),
        "motion": Slider(
            name="motion", label="motion", low=0, high=1, default="ease-in-out",
            means="the shape of the move: constant, eased at both ends, or springy.",
            kind="choice",
            choices=(("still", "still"), ("linear", "linear"),
                     ("ease-in-out", "ease-in-out"), ("spring", "spring")),
            targets=(Target("rig", "ease"),),
        ),
    },
))


register(Preset(
    name="style-transfer",
    label="style transfer",
    blurb="one image lends its look to another, and the look is a wire you can re-aim.",
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="paint",
    entry_port="content",
    sink="paint",
    slots=(
        Slot(name="the look", node="read", port="reference", dtype="image",
             means="a second image whose style gets copied. drop one onto this preset's slot."),
    ),
    steps={
        "read": Step(
            op="style.read",
            label="read the look",
            inputs={"reference": Port("image")},
            outputs={"out": image("style")},
            params={"patch": 224},
            requires={"pip": ["torch", "pillow"], "minutes": 0.3},
        ),
        "paint": Step(
            op="image.stylize",
            label="repaint",
            inputs={"content": Port("image"), "reference": image("style")},
            outputs={"out": Port("image")},
            params={"strength": 0.6, "preserve": 0.4},
            requires={"pip": ["diffusers", "torch"], "models": ["ip-adapter"],
                      "gpu": True, "minutes": 1.4},
        ),
    },
    edges=(("read", "out", "paint", "reference"),),
    stage="explore",
    sliders={
        "strength": Slider(
            name="strength", label="strength", low=0.0, high=1.0, default=0.6,
            means="how far the image is allowed to drift toward the reference.",
            targets=(Target("paint", "strength"),),
        ),
        "keep": Slider(
            name="keep", label="keep the shapes", low=0.0, high=0.8, default=0.4,
            means="how much of the original composition survives the repaint.",
            targets=(Target("paint", "preserve"),),
        ),
    },
))


register(Preset(
    name="code-container",
    label="wire a code container",
    blurb=("your own python, in the chain, with the same wires as everything else. the escape "
           "hatch, not the front door."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="run",
    entry_port="content",
    sink="run",
    stage="refine",
    steps={
        "run": Step(
            op="code.python",
            label="your code",
            inputs={"content": Port("image")},
            outputs={"out": Port("image")},
            params={"source": "def process(image):\n    return image", "timeout": 120},
            requires={"minutes": 0.5},
        ),
    },
    edges=(),
    sliders={},
))


register(Preset(
    name="relight",
    label="relight the shot",
    blurb=("one photo, six lighting setups, side by side. pick the one that reads and keep going."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="meter",
    entry_port="photo",
    sink="relight",
    stage="explore",
    steps={
        "meter": Step(
            op="light.meter",
            label="read the plate",
            inputs={"photo": Port("image")},
            outputs={"out": image("palette")},
            params={"white_balance": "auto"},
            requires={"pip": ["pillow"], "minutes": 0.3},
        ),
        "relight": Step(
            op="light.relight",
            label="relight",
            inputs={"plate": image("palette")},
            outputs={"out": Port("image")},
            params={"kelvin": 5600, "exposure": 0.0, "softness": 0.4},
            requires={"pip": ["torch"], "models": ["ic-light"], "gpu": True, "minutes": 1.1},
        ),
    },
    edges=(("meter", "out", "relight", "plate"),),
    sweep=Sweep(slider="warmth", label="six lighting versions",
                values=(4500, 5200, 5600, 6500, 7500, 8500)),
    sliders={
        "warmth": Slider(
            name="warmth", label="warmth", low=2000, high=9000, default=5600,
            means="the colour of the light, in kelvin. studio daylight sits near the middle.",
            targets=(Target("relight", "kelvin"),),
            unit="K",
        ),
        "softness": Slider(
            name="softness", label="softness", low=0.0, high=1.0, default=0.4,
            means="hard key light through to a big diffused source.",
            targets=(Target("relight", "softness"),),
        ),
    },
))


def legend() -> dict:
    """what the frontend needs to draw a preset menu without knowing any of the above."""
    return {
        "presets": [
            {"name": p.name, "label": p.label, "blurb": p.blurb,
             "applies_to": list(p.applies_to),
             "from": p.input_dtype, "to": p.out_dtype(),
             "state": p.state, "nodes": len(p.steps),
             "controls": len(p.sliders), "stage": p.stage,
             "variants": len(p.sweep.values) if p.sweep else 1,
             "estimate": p.estimate()["minutes"]}
            for p in PRESETS.values()
        ],
        "wires": dtypes.palette(),
        "roles": dict(dtypes.ROLES),
    }
