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
            # a choice is (what you see, what the node receives). for a prompt fragment the second
            # is the longer phrase; for a mode name it is the name itself.
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
    # the artifact kind this step's output leaves the graph as, when that is not just its wire.
    # a font is the case: the wire it travels on is text (the family name), and what the user
    # receives is an .otf/.ttf/.woff bundle. artifacts.KINDS says which kinds exist.
    deliverable: str | None = None

    def node_params(self) -> dict:
        """the params a board node starts with: the step's own, plus what it delivers when set.

        the deliverable rides in params because the spawner already copies them and the compiler
        already reads them, so no graph node needed a new field and no existing node changed.
        """
        out = dict(self.params)
        if self.deliverable:
            out["deliverable"] = self.deliverable
        return out


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
    shared_seam: str = ""
    tail_port: str = ""
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
        if self.shared_seam:
            head = self.steps[self.entry]
            if self.shared_seam not in head.outputs:
                raise PresetRefused(
                    f"{self.name} shares {self.shared_seam!r} but its entry step does not "
                    f"produce it"
                )
            if self.tail_port not in self.steps[self.sink].inputs:
                raise PresetRefused(
                    f"{self.name} takes its frame on {self.tail_port!r}, which "
                    f"{self.sink} does not read"
                )
            if self.sweep is not None:
                raise PresetRefused(
                    f"{self.name} both shares a head and sweeps a slider; one of those is a "
                    f"shape this tree has not had to think about yet"
                )
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

    @property
    def scope(self) -> str:
        """board presets run one head and reach many frames; element presets reach one."""
        return "board" if self.shared_seam else "element"

    def head_roles(self) -> set[str]:
        return {self.entry} if self.shared_seam else set()

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

    def estimate(self, values: dict | None = None, frames: int = 1) -> dict:
        """what this costs if you press it. both products above show this before the run, not
        after, and it is the single cheapest thing that stops a board from being a slot machine."""
        tail = self.tail()
        copies = len(self.sweep.values) if self.sweep else 1
        head = self.head_roles()
        frames = max(1, frames) if self.shared_seam else 1

        def multiplier(role: str) -> int:
            # a swept tail repeats per value; a board tail repeats per frame; a head repeats never
            if role in head:
                return 1
            return (copies if role in tail else 1) * frames

        gpu = sum(step.requires.get("minutes", 0) * multiplier(role)
                  for role, step in self.steps.items() if step.requires.get("gpu"))
        total = sum(step.requires.get("minutes", 0) * multiplier(role)
                    for role, step in self.steps.items())
        return {"minutes": round(total, 1),
                "gpu_minutes": round(gpu, 1),
                "cpu_minutes": round(total - gpu, 1),
                "models": sorted({m for step in self.steps.values()
                                  for m in (step.requires.get("models") or [])})}

    def sidebar(self, values: dict | None = None, frames: int = 1) -> dict:
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
            "estimate": self.estimate(values, frames=frames),
            "slots": [{"name": s.name, "node": s.node, "port": s.port,
                       "dtype": s.dtype, "means": s.means} for s in self.slots],
            "scope": self.scope,
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


register(Preset(
    name="studio-light",
    label="match the light across the board",
    blurb=("one lighting reference, graded onto every frame you pick. a board that reads as one "
           "shoot instead of four unrelated renders."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="study",
    entry_port="reference",
    sink="grade",
    tail_port="plate",
    shared_seam="palette",
    stage="refine",
    steps={
        "study": Step(
            op="light.study",
            label="read the reference light",
            inputs={"reference": Port("image")},
            outputs={"palette": image("palette")},
            params={"look": "studio"},
            requires={"models": ["ic-light"], "gpu": True, "minutes": 0.6},
        ),
        "grade": Step(
            op="light.grade",
            label="grade onto this frame",
            inputs={"plate": Port("image"), "palette": image("palette")},
            outputs={"out": Port("image")},
            params={"temperature": 0.5, "contrast": 0.5, "palette": "neutral",
                    "intensity": 1.0},
            requires={"models": ["ic-light"], "gpu": True, "minutes": 0.9},
        ),
    },
    edges=(("study", "palette", "grade", "palette"),),
    sliders={
        "temperature": Slider(
            name="temperature", label="warmth", low=0.0, high=1.0, default=0.5,
            means="cool blue on one side, tungsten on the other.",
            targets=(Target("grade", "temperature"),),
        ),
        "contrast": Slider(
            name="contrast", label="contrast", low=0.0, high=1.0, default=0.5,
            means="flat and soft through to a hard ratio.",
            targets=(Target("grade", "contrast"),),
        ),
        "style": Slider(
            name="style", label="adapt the lighting style", low=0, high=1, default="studio",
            kind="choice",
            choices=(("studio", "studio"), ("three point", "three point"),
                     ("softbox", "softbox"), ("rim", "rim light"), ("window", "window light")),
            means="which standing setup the reference is read as. the palette is still read from "
                  "your frame; this decides how to read it.",
            targets=(Target("study", "look"),),
        ),
        "palette": Slider(
            name="palette", label="colour palette", low=0, high=1, default="neutral",
            kind="choice",
            choices=(("neutral", "neutral"), ("warm amber", "warm amber"),
                     ("cool teal", "cool teal"), ("high key", "high key"),
                     ("low key", "low key")),
            means="test a grade across every frame at once, which is the whole reason this preset "
                  "runs once and reaches many.",
            targets=(Target("grade", "palette"),),
        ),
        "intensity": Slider(
            name="intensity", label="lighting intensity", low=0.2, high=2.0, default=1.0,
            means="how much of the new light replaces the old, from a hint to a room change.",
            targets=(Target("grade", "intensity"),),
        ),
    },
))

register(Preset(
    name="surface-detail",
    label="add surface detail",
    blurb="creases, stitches, raised edges or cut-in seams. the difference between a shape and a made object.",
    applies_to=("model",),
    input_dtype="mesh",
    entry="read",
    entry_port="geometry",
    sink="relief",
    stage="refine",
    steps={
        "read": Step(
            op="mesh.read",
            label="read the surface",
            inputs={"geometry": Port("mesh")},
            outputs={"out": Port("mesh"), "guide": image("depth")},
            params={"resolution": 1024},
            requires={"pip": ["trimesh", "pillow"], "minutes": 0.3},
        ),
        "paint": Step(
            op="detail.paint",
            label="paint the detail map",
            inputs={"guide": image("depth")},
            outputs={"map": image("depth")},
            params={"prompt": "soft folds, as in cloth that has been worn", "strength": 0.7},
            requires={"models": ["flux-depth-lora"], "gpu": True, "minutes": 1.4},
        ),
        "relief": Step(
            op="mesh.relief",
            label="apply the relief",
            inputs={"geometry": Port("mesh"), "map": image("depth")},
            outputs={"out": Port("mesh")},
            params={"depth": 0.6, "width": 0.4},
            requires={"pip": ["trimesh"], "minutes": 0.6},
        ),
    },
    edges=(("read", "out", "relief", "geometry"), ("read", "guide", "paint", "guide"),
           ("paint", "map", "relief", "map")),
    sliders={
        "detail": Slider(
            name="detail", label="detail", low=0.0, high=3.0, default="crease",
            kind="choice",
            means=("crease cuts soft folds into it, as in worn cloth. stitch lays a tailored line "
                   "along a seam. emboss raises a patch. deboss cuts the same shape in."),
            choices=(
                ("crease", "soft folds, as in cloth that has been worn"),
                ("stitch", "tailored stitch lines running along a seam"),
                ("emboss", "a raised patch, as in moulded leather"),
                ("deboss", "a recess cut into the surface, as in a stamped logo"),
            ),
            targets=(Target("paint", "prompt"),),
        ),
        "depth": Slider(
            name="depth", label="depth", low=0.0, high=1.0, default=0.6,
            means="how far the detail sits off or into the surface.",
            targets=(Target("relief", "depth"),),
        ),
    },
))


register(Preset(
    name="extract-material",
    label="extract materials",
    blurb=("take the material off something you already like and keep it as a set: albedo, "
           "roughness, metalness, per surface."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="read",
    entry_port="image",
    sink="estimate",
    stage="explore",
    steps={
        "read": Step(
            op="material.segment",
            label="find the surfaces",
            inputs={"image": Port("image")},
            outputs={"out": image("segmentation")},
            params={"min_area": 0.02},
            requires={"pip": ["torch"], "models": ["sam-segment"], "gpu": True, "minutes": 0.7},
        ),
        "estimate": Step(
            op="material.estimate",
            label="read albedo, roughness and metalness",
            inputs={"surfaces": image("segmentation")},
            outputs={"out": image("material")},
            params={"layers": 5},
            requires={"models": ["material-estimator"], "gpu": True, "minutes": 1.1},
        ),
    },
    edges=(("read", "out", "estimate", "surfaces"),),
    sliders={
        "layers": Slider(
            name="layers", label="how many materials", low=1, high=8, default=5,
            means="one clean material or a set of eight; each one is another surface it has to find.",
            targets=(Target("estimate", "layers"),),
        ),
        "barely": Slider(
            name="barely", label="ignore small surfaces", low=0.005, high=0.10, default=0.02,
            means="anything under this fraction of the frame is skipped, which keeps buckles and "
                  "buttons out of the set.",
            targets=(Target("read", "min_area"),),
        ),
    },
))


register(Preset(
    name="apply-material",
    label="apply materials",
    blurb=("dress a mesh in a material set and see six finishes at once. one unwrap, six paints, "
           "which is what 'explore material variations' actually costs."),
    applies_to=("mesh",),
    input_dtype="mesh",
    entry="unwrap",
    entry_port="geometry",
    sink="paint",
    stage="refine",
    steps={
        "unwrap": Step(
            op="mesh.uv",
            label="lay the surface flat",
            inputs={"geometry": Port("mesh")},
            outputs={"out": image("layout")},
            params={"margin": 0.01},
            requires={"pip": ["trimesh"], "minutes": 0.3},
        ),
        "paint": Step(
            op="material.apply",
            label="paint it on",
            inputs={"layout": image("layout"), "material": image("material")},
            outputs={"out": Port("mesh")},
            params={"finish": "matte", "tiling": 1.0},
            requires={"pip": ["trimesh"], "models": ["pbr-painter"], "gpu": True,
                      "minutes": 1.4,
                      "needs": {"image": "a material set, or any image to wear"}},
        ),
    },
    edges=(("unwrap", "out", "paint", "layout"),),
    slots=(
        Slot(name="the material", node="paint", port="material", dtype="image",
             means="the set from extract material, or any image you want the surface to wear"),
    ),
    sweep=Sweep(slider="finish", label="six finishes", values=(
        "matte", "satin", "polished", "brushed", "hammered", "raw")),
    sliders={
        "finish": Slider(
            name="finish", label="finish", low=0, high=1, default="matte", kind="choice",
            choices=(("matte", "matte"), ("satin", "satin"), ("polished", "polished"),
                     ("brushed", "brushed"), ("hammered", "hammered"), ("raw", "raw")),
            means="what the surface does to light. the sweep runs all six off one unwrap.",
            targets=(Target("paint", "finish"),),
        ),
        "tiling": Slider(
            name="tiling", label="tiling", low=0.25, high=4.0, default=1.0,
            means="how many times the material repeats across the surface.",
            targets=(Target("paint", "tiling"),),
        ),
    },
))


register(Preset(
    name="texture-maps",
    label="pbr texture maps",
    blurb=("one pass produces the whole map set: albedo, normals, roughness, metalness, opacity, "
           "emission. five of the six are sliders on the same node, not five more nodes."),
    applies_to=("mesh",),
    input_dtype="mesh",
    entry="layout",
    entry_port="geometry",
    sink="normals",
    stage="output",
    steps={
        "layout": Step(
            op="mesh.uv",
            label="lay the surface flat",
            inputs={"geometry": Port("mesh")},
            outputs={"out": image("layout")},
            params={"margin": 0.01},
            requires={"pip": ["trimesh"], "minutes": 0.3},
        ),
        "paint": Step(
            op="texture.pbr",
            label="paint the map set",
            inputs={"layout": image("layout")},
            outputs={"out": image("maps")},
            params={"roughness": 0.5, "metalness": 0.0, "opacity": 1.0, "emission": 0.0,
                    "resolution": 2048},
            requires={"pip": ["torch"], "models": ["pbr-gen"], "gpu": True, "minutes": 1.8},
        ),
        "normals": Step(
            op="texture.normal",
            label="derive normals and the rest",
            inputs={"maps": image("maps")},
            outputs={"out": image("maps")},
            params={"strength": 0.5, "from": "height"},
            requires={"pip": ["numpy", "pillow"], "minutes": 0.2},
        ),
    },
    edges=(("layout", "out", "paint", "layout"), ("paint", "out", "normals", "maps")),
    sliders={
        "roughness": Slider(
            name="roughness", label="roughness", low=0.0, high=1.0, default=0.5,
            means="mirror smooth at zero, chalk at one.",
            targets=(Target("paint", "roughness"),),
        ),
        "metalness": Slider(
            name="metalness", label="metalness", low=0.0, high=1.0, default=0.0,
            means="dielectric through to metal, which changes what the lighting is allowed "
                  "to reflect.",
            targets=(Target("paint", "metalness"),),
        ),
        "opacity": Slider(
            name="opacity", label="opacity", low=0.0, high=1.0, default=1.0,
            means="below one the material writes an alpha channel and the frame gets something "
                  "behind it.",
            targets=(Target("paint", "opacity"),),
        ),
        "emission": Slider(
            name="emission", label="emission", low=0.0, high=1.0, default=0.0,
            means="how much the surface is a light source rather than a lit thing.",
            targets=(Target("paint", "emission"),),
        ),
        "normal_strength": Slider(
            name="normal_strength", label="normal depth", low=0.0, high=2.0, default=0.5,
            means="how hard the normals turn at an edge. past one they start to lie.",
            targets=(Target("normals", "strength"),),
        ),
        "resolution": Slider(
            name="resolution", label="map size", low=1024, high=4096, default=2048,
            means="texels per side. the only control here that costs memory rather than time.",
            targets=(Target("paint", "resolution"),),
            unit=" px",
        ),
    },
))


register(Preset(
    name="environment",
    label="put it outside",
    blurb=("a scene that lights the thing rather than sitting behind it: skate park, courtyard, "
           "overcast street. reflections come from the place, not from a gradient."),
    applies_to=("mesh", "image"),
    input_dtype="mesh",
    entry="place",
    entry_port="subject",
    sink="light",
    stage="refine",
    steps={
        "place": Step(
            op="scene.environment",
            label="build the place",
            inputs={"subject": Port("mesh")},
            outputs={"out": image("environment"), "subject": Port("mesh")},
            params={"variant": "skate park", "sun": 0.6, "floor": True},
            requires={"pip": ["trimesh"], "minutes": 0.3},
        ),
        "light": Step(
            op="mesh.relight",
            label="light it from there",
            inputs={"geometry": Port("mesh"), "environment": image("environment")},
            outputs={"out": Port("mesh")},
            params={"bounce": 0.5, "reflections": 0.7},
            requires={"models": ["ic-light"], "gpu": True, "minutes": 1.2},
        ),
    },
    edges=(("place", "out", "light", "environment"),
           ("place", "subject", "light", "geometry")),
    sliders={
        "where": Slider(
            name="where", label="where", low=0, high=1, default="skate park", kind="choice",
            choices=(("skate park", "skate park"), ("courtyard", "courtyard"),
                     ("overcast street", "overcast street"), ("rooftop", "rooftop"),
                     ("studio void", "studio void")),
            means="the place decides the reflections, so this is the biggest single lever here.",
            targets=(Target("place", "variant"),),
        ),
        "sun": Slider(
            name="sun", label="sun", low=0.0, high=1.0, default=0.6,
            means="overhead flat light through to a low raking sun.",
            targets=(Target("place", "sun"),),
        ),
        "bounce": Slider(
            name="bounce", label="bounce", low=0.0, high=1.0, default=0.5,
            means="how much light comes back off the ground into the underside.",
            targets=(Target("light", "bounce"),),
        ),
        "reflections": Slider(
            name="reflections", label="reflections", low=0.0, high=1.0, default=0.7,
            means="the part that makes it read as outdoors at all.",
            targets=(Target("light", "reflections"),),
        ),
    },
))


register(Preset(
    name="layers-to-3d",
    label="generate 3d from 2d layers",
    blurb=("a flat artwork is split into layers by depth and lifted into a relief, so each plane "
           "sits behind the one in front of it."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="split",
    entry_port="stack",
    sink="lift",
    stage="explore",
    flips_plane="3d",
    steps={
        "split": Step(
            op="layers.split",
            label="split by depth",
            inputs={"stack": Port("image")},
            outputs={"out": image("layers")},
            params={"max_layers": 6, "feather": 2},
            requires={"pip": ["torch"], "models": ["depth-anything"], "gpu": True,
                      "minutes": 0.8},
        ),
        "lift": Step(
            op="mesh.lift",
            label="lift the layers apart",
            inputs={"layers": image("layers")},
            outputs={"out": Port("mesh")},
            params={"gap": 0.12, "bevel": 0.01},
            requires={"pip": ["trimesh"], "models": ["layer-lift"], "gpu": True,
                      "minutes": 1.5},
        ),
    },
    edges=(("split", "out", "lift", "layers"),),
    sliders={
        "max_layers": Slider(
            name="max_layers", label="layers", low=2, high=12, default=6,
            means="how many planes it separates. more layers is more relief and more cleanup.",
            targets=(Target("split", "max_layers"),),
        ),
        "gap": Slider(
            name="gap", label="depth", low=0.0, high=0.5, default=0.12,
            means="the space between layers, which is the difference between a cutout and a stack.",
            targets=(Target("lift", "gap"),),
        ),
    },
))


register(Preset(
    name="sketch-to-render",
    label="sketch to photorealistic render",
    blurb="the line stays yours; what changes is what the line is made of.",
    applies_to=("sketch", "image"),
    input_dtype="image",
    entry="read",
    entry_port="image",
    sink="render",
    stage="refine",
    steps={
        "read": Step(
            op="control.lines",
            label="hold the line",
            inputs={"image": Port("image")},
            outputs={"out": image("lines")},
            params={"threshold": 0.5},
            requires={"pip": ["opencv-python-headless"], "minutes": 0.2},
        ),
        "render": Step(
            op="image.gen",
            label="render it as a thing",
            inputs={"lines": image("lines"), "look": image("style", optional=True)},
            outputs={"out": Port("image")},
            params={"steps": 24, "guidance": 6.0, "material": "ceramic"},
            requires={"pip": ["diffusers", "torch"],
                      "models": ["sdxl-turbo", "controlnet-scribble"], "gpu": True,
                      "minutes": 1.9},
        ),
    },
    edges=(("read", "out", "render", "lines"),),
    sliders={
        "fidelity": Slider(
            name="fidelity", label="fidelity", low=1.0, high=12.0, default=6.0,
            means="obey the drawing, or drift into something plausible.",
            targets=(Target("render", "guidance"),),
        ),
        "keep": Slider(
            name="keep", label="how much line", low=0.1, high=0.9, default=0.5,
            means="where the line-extraction threshold sits, so faint pencil is kept or lost.",
            targets=(Target("read", "threshold"),),
        ),
        "material": Slider(
            name="material", label="made of", low=0, high=1, default="ceramic",
            kind="choice",
            choices=(("ceramic", "ceramic"), ("clay", "clay"), ("resin", "resin"),
                     ("paper", "paper")),
            means="the substance the drawing gets rendered in.",
            targets=(Target("render", "material"),),
        ),
    },
))


register(Preset(
    name="3d-text",
    label="3d text",
    blurb=("words become geometry on the board, bevelled and lit by whatever material you put on "
           "them next."),
    applies_to=("text",),
    input_dtype="text",
    entry="write",
    entry_port="draft",
    sink="extrude",
    stage="explore",
    flips_plane="3d",
    steps={
        "write": Step(
            op="text.compose",
            label="the words",
            inputs={"draft": Port("text", optional=True)},
            outputs={"out": Port("text")},
            params={"prefix": "", "case": "as typed"},
            requires={"minutes": 0.2},
        ),
        "extrude": Step(
            op="mesh.extrude",
            label="extrude and bevel",
            inputs={"words": Port("text")},
            outputs={"out": Port("mesh")},
            params={"depth": 0.25, "bevel": 0.02, "font": "Inter", "tracking": 0.0},
            requires={"pip": ["trimesh", "fonttools"], "minutes": 0.4},
        ),
    },
    edges=(("write", "out", "extrude", "words"),),
    sliders={
        "depth": Slider(
            name="depth", label="depth", low=0.02, high=1.0, default=0.25,
            means="how far the letters come off the wall.",
            targets=(Target("extrude", "depth"),),
        ),
        "bevel": Slider(
            name="bevel", label="bevel", low=0.0, high=0.1, default=0.02,
            means="the edge that catches the light. at zero the letters look cut from paper.",
            targets=(Target("extrude", "bevel"),),
        ),
        "font": Slider(
            name="font", label="font", low=0, high=1, default="Inter", kind="choice",
            choices=(("Inter", "Inter"), ("serif", "serif"), ("mono", "mono"),
                     ("rounded", "rounded")),
            means="the only control here that changes the shape rather than the light.",
            targets=(Target("extrude", "font"),),
        ),
    },
))


register(Preset(
    name="replace-object",
    label="replace selected objects",
    blurb=("paint over one thing and have the shot believe it: the mask is found, the hole is "
           "filled, the shadow on the floor is redrawn."),
    applies_to=("image",),
    input_dtype="image",
    entry="mask",
    entry_port="image",
    sink="fill",
    stage="refine",
    steps={
        "mask": Step(
            op="image.segment",
            label="find the object",
            inputs={"image": Port("image")},
            outputs={"mask": image("mask"), "subject": Port("image")},
            params={"hint": "the main object", "expand": 0.02},
            requires={"models": ["sam-segment"], "gpu": True, "minutes": 0.6},
        ),
        "fill": Step(
            op="image.inpaint",
            label="put something else there",
            inputs={"image": Port("image"), "mask": image("mask")},
            outputs={"out": Port("image")},
            params={"prompt": "a ceramic vase", "strength": 0.9},
            requires={"models": ["flux-fill"], "gpu": True, "minutes": 1.3},
        ),
    },
    edges=(("mask", "subject", "fill", "image"), ("mask", "mask", "fill", "mask")),
    sliders={
        "select": Slider(
            name="select", label="select", low=0, high=1, default="the main object",
            kind="choice",
            choices=(("the main object", "the main object"), ("furniture", "furniture"),
                     ("a person", "a person"), ("the background", "the background")),
            means="what gets masked. the mask is a wire, so you can also see it and drag its edge "
                  "in the pipeline view.",
            targets=(Target("mask", "hint"),),
        ),
        "becomes": Slider(
            name="becomes", label="becomes", low=0, high=1, default="a ceramic vase",
            kind="choice",
            choices=(("a ceramic vase", "a ceramic vase"), ("a wooden bowl", "a wooden bowl"),
                     ("a plant", "a tall plant"), ("nothing", "an empty floor")),
            means="what fills the hole, in words, because that is how the model takes it.",
            targets=(Target("fill", "prompt"),),
        ),
        "strength": Slider(
            name="strength", label="strength", low=0.3, high=1.0, default=0.9,
            means="how far the fill is allowed to move away from the pixels underneath it.",
            targets=(Target("fill", "strength"),),
        ),
    },
))


register(Preset(
    name="place-graphic",
    label="graphic placement",
    blurb=("a graphic is laid onto a surface and follows it, so a repeat reads as print rather "
           "than as a sticker."),
    applies_to=("mesh",),
    input_dtype="mesh",
    entry="unwrap",
    entry_port="geometry",
    sink="decal",
    stage="refine",
    steps={
        "unwrap": Step(
            op="mesh.uv",
            label="lay the surface flat",
            inputs={"geometry": Port("mesh")},
            outputs={"out": image("layout")},
            params={"margin": 0.01, "pattern": "as drawn"},
            requires={"pip": ["trimesh"], "minutes": 0.3},
        ),
        "decal": Step(
            op="material.decal",
            label="set the graphic into it",
            inputs={"layout": image("layout"), "graphic": image("graphic")},
            outputs={"out": Port("mesh")},
            params={"mode": "print", "bleed": 0.0},
            requires={"pip": ["trimesh"], "models": ["pbr-painter"], "gpu": True,
                      "minutes": 1.0,
                      "needs": {"image": "the graphic itself"}},
        ),
    },
    edges=(("unwrap", "out", "decal", "layout"),),
    slots=(
        Slot(name="the graphic", node="decal", port="graphic", dtype="image",
             means="the artwork to place, as an image on the board"),
    ),
    sliders={
        "pattern": Slider(
            name="pattern", label="pattern", low=0, high=1, default="as drawn", kind="choice",
            choices=(("as drawn", "as drawn"), ("repeat", "repeat"),
                     ("kaleidoscope", "kaleidoscope"), ("grid", "grid")),
            means="how the graphic tiles across the surface, which is the geometric half of this "
                  "preset.",
            targets=(Target("unwrap", "pattern"),),
        ),
        "mode": Slider(
            name="mode", label="printed as", low=0, high=1, default="print", kind="choice",
            choices=(("print", "print"), ("emboss", "emboss"), ("embroidery", "embroidery")),
            means="whether the graphic is ink, raised, or stitched.",
            targets=(Target("decal", "mode"),),
        ),
        "bleed": Slider(
            name="bleed", label="bleed", low=0.0, high=0.2, default=0.0,
            means="how far past the seam the graphic is allowed to run, so it does not stop dead "
                  "at an edge.",
            targets=(Target("decal", "bleed"),),
        ),
    },
))


register(Preset(
    name="clear-interior",
    label="clear an interior",
    blurb="empty the room but keep the room: walls, floor and light stay, the furniture goes.",
    applies_to=("image",),
    input_dtype="image",
    entry="mask",
    entry_port="image",
    sink="fill",
    stage="refine",
    steps={
        "mask": Step(
            op="image.segment",
            label="find what is in it",
            inputs={"image": Port("image")},
            outputs={"mask": image("mask"), "subject": Port("image")},
            params={"target": "furniture", "keep": "walls, floor, windows", "expand": 0.04},
            requires={"models": ["sam-segment"], "gpu": True, "minutes": 0.8},
        ),
        "fill": Step(
            op="image.inpaint",
            label="empty it",
            inputs={"image": Port("image"), "mask": image("mask")},
            outputs={"out": Port("image")},
            params={"prompt": "an empty room, same light", "strength": 0.8},
            requires={"models": ["flux-fill"], "gpu": True, "minutes": 1.6},
        ),
    },
    edges=(("mask", "subject", "fill", "image"), ("mask", "mask", "fill", "mask")),
    sliders={
        "target": Slider(
            name="target", label="clear", low=0, high=1, default="furniture", kind="choice",
            choices=(("furniture", "furniture"), ("everything", "everything loose"),
                     ("clutter", "clutter only")),
            means="what counts as the thing to remove.",
            targets=(Target("mask", "target"),),
        ),
        "keep": Slider(
            name="keep", label="keep", low=0, high=1, default="walls, floor, windows",
            kind="choice",
            choices=(("walls, floor, windows", "walls, floor, windows"),
                     ("the light", "the light"), ("the view", "the view out the window")),
            means="what the fill is not allowed to invent over.",
            targets=(Target("mask", "keep"),),
        ),
        "strength": Slider(
            name="strength", label="strength", low=0.3, high=1.0, default=0.8,
            means="how completely the new surface replaces the old one.",
            targets=(Target("fill", "strength"),),
        ),
    },
))


register(Preset(
    name="cut-out",
    label="remove the background",
    blurb="a subject with an honest edge, including hair, which is where matting usually gives up.",
    applies_to=("image",),
    input_dtype="image",
    entry="matte",
    entry_port="image",
    sink="matte",
    stage="output",
    steps={
        "matte": Step(
            op="image.matte",
            label="separate subject from ground",
            inputs={"image": Port("image")},
            outputs={"out": image("cutout")},
            params={"feather": 2, "threshold": 0.5},
            requires={"models": ["birefnet"], "gpu": True, "minutes": 0.7},
        ),
    },
    edges=(),
    sliders={
        "feather": Slider(
            name="feather", label="edge", low=0.0, high=8.0, default=2.0,
            means="soft pixels at the boundary. too little and a cutout reads as a sticker.",
            targets=(Target("matte", "feather"),),
        ),
        "threshold": Slider(
            name="threshold", label="confidence", low=0.2, high=0.8, default=0.5,
            means="how sure the matte has to be before a pixel counts as subject.",
            targets=(Target("matte", "threshold"),),
        ),
    },
))


register(Preset(
    name="swap-background",
    label="replace the background",
    blurb="keep the subject, lose the room, and put a chosen frame behind it.",
    applies_to=("image",),
    input_dtype="image",
    entry="matte",
    entry_port="image",
    sink="compose",
    stage="refine",
    steps={
        "matte": Step(
            op="image.matte",
            label="cut the subject out",
            inputs={"image": Port("image")},
            outputs={"cutout": image("cutout")},
            params={"feather": 2},
            requires={"models": ["birefnet"], "gpu": True, "minutes": 0.7},
        ),
        "compose": Step(
            op="image.composite",
            label="put the new ground behind",
            inputs={"subject": image("cutout"), "background": image("background")},
            outputs={"out": Port("image")},
            params={"match_light": 0.6, "contact_shadow": 0.4},
            requires={"models": ["ic-light"], "gpu": True, "minutes": 1.0,
                      "needs": {"image": "a background frame"}},
        ),
    },
    edges=(("matte", "cutout", "compose", "subject"),),
    slots=(
        Slot(name="the background", node="compose", port="background", dtype="image",
             means="the frame to put behind it, which is any image already on the board"),
    ),
    sliders={
        "match_light": Slider(
            name="match_light", label="match the light", low=0.0, high=1.0, default=0.6,
            means="warm the subject towards the new ground, or leave it as shot.",
            targets=(Target("compose", "match_light"),),
        ),
        "contact_shadow": Slider(
            name="contact_shadow", label="contact shadow", low=0.0, high=1.0, default=0.4,
            means="the shadow that stops the subject floating a centimetre above the floor.",
            targets=(Target("compose", "contact_shadow"),),
        ),
    },
))


register(Preset(
    name="extract-pose",
    label="extract a pose",
    blurb=("the pose comes out as its own frame, which means it can drive a different subject "
           "without re-describing anything."),
    applies_to=("image",),
    input_dtype="image",
    entry="pose",
    entry_port="image",
    sink="pose",
    stage="explore",
    steps={
        "pose": Step(
            op="pose.estimate",
            label="read the pose",
            inputs={"image": Port("image")},
            outputs={"out": image("pose")},
            params={"detail": "full body", "smooth": 1},
            requires={"models": ["dwpose"], "gpu": True, "minutes": 0.5},
        ),
    },
    edges=(),
    sliders={
        "detail": Slider(
            name="detail", label="detail", low=0, high=1, default="full body", kind="choice",
            choices=(("full body", "full body"), ("hands", "hands"), ("face", "face")),
            means="how much of the body it maps. hands and face are slower and pickier.",
            targets=(Target("pose", "detail"),),
        ),
    },
))


register(Preset(
    name="inpaint",
    label="inpaint adjustments",
    blurb=("change one region and leave the rest of the frame untouched. the mask is the second "
           "asset, which is the honest shape of every inpaint job."),
    applies_to=("image",),
    input_dtype="image",
    entry="fill",
    entry_port="image",
    sink="fill",
    stage="refine",
    steps={
        "fill": Step(
            op="image.inpaint",
            label="fill the region",
            inputs={"image": Port("image"), "mask": image("mask")},
            outputs={"out": Port("image")},
            params={"prompt": "a seam that belongs there", "strength": 0.85},
            requires={"models": ["flux-fill"], "gpu": True, "minutes": 1.2,
                      "needs": {"image": "a mask"}},
        ),
    },
    edges=(),
    slots=(
        Slot(name="the area", node="fill", port="mask", dtype="image",
             means="a mask, or any image whose bright areas mark the region"),
    ),
    sliders={
        "fills": Slider(
            name="fills", label="fills with", low=0, high=1, default="a seam that belongs there",
            kind="choice",
            choices=(("a seam that belongs there", "a seam that belongs there"),
                     ("the same material", "the same material"),
                     ("a repair, no trace", "a repair with no trace")),
            means="words, because the model takes words.",
            targets=(Target("fill", "prompt"),),
        ),
        "strength": Slider(
            name="strength", label="strength", low=0.3, high=1.0, default=0.85,
            means="how free the fill is inside the masked region only.",
            targets=(Target("fill", "strength"),),
        ),
    },
))


register(Preset(
    name="handwriting-to-font",
    label="handwriting to font",
    blurb=("scan a practice sheet and get a font back: the letters are found, traced, and packed, "
           "and a row that cannot be named is refused instead of silently dropped."),
    applies_to=("image", "sketch"),
    input_dtype="image",
    entry="detect",
    entry_port="sheet",
    sink="pack",
    stage="refine",
    steps={
        "detect": Step(
            op="font.detect",
            label="find the letters",
            inputs={"sheet": Port("image")},
            outputs={"out": Port("image", role="mask")},
            params={"blur": 1, "threshold": None, "invert": False, "dilate": 1,
                    "min_size": 0.0002, "max_size": 0.2},
            requires={"runtime": "browser", "minutes": 0.1},
        ),
        "pack": Step(
            op="font.pack",
            label="trace and pack the font",
            inputs={"letters": Port("image", role="mask")},
            outputs={"out": Port("text")},
            params={"family": "Handwriting", "formats": ["otf", "ttf", "woff"],
                    "epsilon": 1.5, "allow_partial": False},
            requires={"runtime": "browser", "minutes": 0.1},
            deliverable="font",
        ),
    },
    edges=(("detect", "out", "pack", "letters"),),
    sliders={
        "threshold": Slider(
            name="threshold", label="ink threshold", low=0, high=255, default="auto",
            kind="choice", choices=(("auto", None), ("light", 180), ("medium", 140), ("heavy", 100)),
            means="where paper ends and ink begins. auto finds it from the page, the others force it.",
            targets=(Target("detect", "threshold"),),
        ),
        "invert": Slider(
            name="invert", label="light ink on dark paper", low=0, high=1, default="no",
            kind="choice", choices=(("no", False), ("yes", True)),
            means="turn on for chalk, or a scan where the ink reads lighter than the page.",
            targets=(Target("detect", "invert"),),
        ),
        "blur": Slider(
            name="blur", label="smooth the scan", low=0.0, high=3.0, default=1.0,
            means="softens paper grain before the ink is found. too high and thin strokes break.",
            targets=(Target("detect", "blur"),),
        ),
        "join": Slider(
            name="join", label="join broken strokes", low=0, high=3, default=1,
            means="closes small gaps inside a letter. too high and neighbours fuse into one.",
            targets=(Target("detect", "dilate"),),
        ),
        "smoothness": Slider(
            name="smoothness", label="outline smoothness", low=0.5, high=4.0, default=1.5,
            means="how much the traced outline is simplified. low keeps every wobble.",
            targets=(Target("pack", "epsilon"),),
        ),
    },
))


PROCEDURAL = {
    "frosted-glass": "shading maths on a material, which is arithmetic rather than inference",
    "animate-composition": "a camera move and a render, which is exactly what they say they are",
    "code-container": "your own code, which is the one thing a model should not be guessing at",
    "3d-text": ("extrusion and bevelling is geometry maths, and the material is a second preset "
                "rather than a guess"),
    "handwriting-to-font": ("thresholding, connected components and outline tracing on a scan: "
                            "image maths that runs in the browser, and a model would only guess at "
                            "letters it can measure"),
}


def model_census() -> dict[str, list[str]]:
    """which preset calls which model, and which ones honestly do not.

    the correction that produced this: both reference products name their presets after surfaces
    and *run models*. crease and stitch are diffusion passes, not a carved edge. so a preset that
    names no model is making a claim, and it has to say which claim in PROCEDURAL rather than
    leaving the absence to be discovered later.
    """
    census = {}
    for name, preset in PRESETS.items():
        models = sorted({m for step in preset.steps.values()
                         for m in (step.requires.get("models") or [])})
        census[name] = models
    return census


def legend() -> dict:
    """what the frontend needs to draw a preset menu without knowing any of the above."""
    return {
        "presets": [
            {"name": p.name, "label": p.label, "blurb": p.blurb,
             "applies_to": list(p.applies_to),
             "from": p.input_dtype, "to": p.out_dtype(),
             "state": p.state, "nodes": len(p.steps),
             "controls": len(p.sliders), "stage": p.stage,
             "models": sorted({m for s in p.steps.values()
                               for m in (s.requires.get("models") or [])}),
             "variants": len(p.sweep.values) if p.sweep else 1,
             "estimate": p.estimate()["minutes"]}
            for p in PRESETS.values()
        ],
        "wires": dtypes.palette(),
        "roles": dict(dtypes.ROLES),
    }
