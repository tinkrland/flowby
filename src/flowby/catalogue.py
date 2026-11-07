"""the owner's tool list, kept as data so the registry has to answer to it.

the brief arrives as a tree four levels deep:

    materials and physical properties
      extract and apply
        explore material variations

flowby is three levels deep, and the difference is the whole reason this file exists:

* a **group** is a section of the sidebar. it costs nothing and is not worth a module.
* a **tool** is a preset. it spawns nodes, costs a model call, and can be broken apart.
* a **control** inside a tool is a slider on that preset, not a preset of its own.

so `roughness intensity`, `metalness intensity`, `opacity control` and `emission maps` are four
bullets in the brief and four sliders on one node of one preset, and `crease`, `stitch`, `emboss`
and `deboss` are four more bullets and four values of a single choice. that collapse is not a
shortcut, it is the claim: a menu of twenty-nine things that each cost a model call would be
vectary with a worse sidebar. a menu of fourteen jobs with the arithmetic exposed is the product.

what this file buys is a test. `catalogue.coverage()` refuses a bullet that resolves to nothing, and
`tests/selftest.py` refuses a preset that no bullet names unless it is declared here as a
`primitive` with a reason. the same discipline `presets.PROCEDURAL` applies to models, applied to
the brief: an absence has to be a claim somebody made.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tool:
    """one bullet of the brief, and what it actually is."""

    label: str
    preset: str
    control: str = ""
    note: str = ""

    @property
    def kind(self) -> str:
        return "control" if self.control else "preset"


@dataclass(frozen=True)
class Section:
    name: str
    tools: tuple[Tool, ...]


@dataclass(frozen=True)
class Group:
    name: str
    sections: tuple[Section, ...] = ()
    tools: tuple[Tool, ...] = ()

    def all_tools(self) -> list[Tool]:
        out = list(self.tools)
        for section in self.sections:
            out.extend(section.tools)
        return out


GROUPS: tuple[Group, ...] = (
    Group(
        name="materials and physical properties",
        sections=(
            Section("extract and apply", (
                Tool("extract materials", "extract-material",
                     note="a set of surfaces with albedo, roughness and metalness per one"),
                Tool("apply materials", "apply-material",
                     note="one unwrap, then a paint per finish"),
                Tool("explore material variations", "apply-material", control="finish",
                     note="six finishes off one unwrap, because the sweep is the feature"),
            )),
            Section("texture maps", (
                Tool("pbr textures", "texture-maps",
                     note="the map set as a whole: albedo plus the five below"),
                Tool("normal maps", "texture-maps", control="normal_strength",
                     note="derived from the height, not painted; a sobel pass, not a model"),
                Tool("roughness intensity", "texture-maps", control="roughness"),
                Tool("metalness intensity", "texture-maps", control="metalness"),
                Tool("opacity control", "texture-maps", control="opacity"),
                Tool("emission maps", "texture-maps", control="emission"),
            )),
        ),
    ),
    Group(
        name="surface details and textile embellishments",
        sections=(
            Section("structural lines", (
                Tool("crease", "surface-detail", control="detail",
                     note="a diffusion pass that paints a wrinkle map, not a carved edge"),
                Tool("stitches", "surface-detail", control="detail",
                     note="the same pass with a different sentence"),
            )),
            Section("dimensional tooling", (
                Tool("emboss", "surface-detail", control="detail",
                     note="raises the paint into the geometry on the relief step"),
                Tool("deboss", "surface-detail", control="detail",
                     note="the same, inverted, which is one word to the model and one sign here"),
            )),
        ),
    ),
    Group(
        name="lighting and environment setups",
        sections=(
            Section("studio controls", (
                Tool("adapt studio lighting styles", "studio-light", control="style"),
                Tool("test color palettes", "studio-light", control="palette"),
                Tool("lighting intensity", "studio-light", control="intensity"),
            )),
            Section("outdoor environments", (
                Tool("skate park", "environment", control="where",
                     note="reflections come from the place, which is why it is a scene and not "
                          "a prompt"),
                Tool("outdoor option presets", "environment", control="where",
                     note="the same slider: a place is a choice, not a preset each"),
            )),
        ),
    ),
    Group(
        name="2d to 3d design and geometric generation",
        sections=(
            Section("dimensional synthesis", (
                Tool("generate 3d from 2d layers", "layers-to-3d"),
                Tool("sketch to photorealistic render", "sketch-to-render"),
                Tool("3d text presets", "3d-text",
                     note="extrusion and bevel, so no model and a reason in PROCEDURAL"),
            )),
            Section("object variations", (
                Tool("replace selected objects", "replace-object"),
                Tool("graphic placement", "place-graphic",
                     note="a slot, because a graphic is a second asset"),
                Tool("geometric pattern mapping", "place-graphic", control="pattern"),
            )),
        ),
    ),
    Group(
        name="scene curation and framing",
        sections=(
            Section("spatial isolation", (
                Tool("clear an interior", "clear-interior"),
                Tool("background removal", "cut-out"),
                Tool("background replacement", "swap-background",
                     note="cut out plus a slot for the new ground"),
            )),
            Section("pose and composition", (
                Tool("extract a pose", "extract-pose",
                     note="the pose becomes its own green frame, and can drive a different subject"),
                Tool("inpaint adjustments", "inpaint",
                     note="mask is the second asset, which is the honest shape of an inpaint"),
            )),
        ),
    ),
)


PRIMITIVES = {
    "text-to-image": "the brief assumes somewhere to put words; this is that door",
    "sketch-to-mesh": "the red wire has to exist before any material can dress it",
    "frosted-glass": "a material with no model, kept as the example of shading maths",
    "animate-composition": "the brief's framing section stops at stills; motion is what comes next",
    "code-container": "the escape hatch the brief implies with 'advanced developers'",
    "relight": "one light, one frame: the cheap primitive the studio and environment presets scale",
    "style-transfer": "the third door in its simplest form, before it reaches across a board",
}


def all_tools() -> list[tuple[str, str, Tool]]:
    """(group, section, tool) for every bullet, flattened, in the order the brief lists them."""
    out = []
    for group in GROUPS:
        for tool in group.tools:
            out.append((group.name, "", tool))
        for section in group.sections:
            for tool in section.tools:
                out.append((group.name, section.name, tool))
    return out


def coverage() -> dict:
    """what resolves, what does not, and which presets the brief never names."""
    from . import presets

    gaps, misfiled = [], []
    for group, section, tool in all_tools():
        if tool.preset not in presets.PRESETS:
            gaps.append(f"{tool.label} -> {tool.preset}, which is not a preset")
            continue
        if tool.control:
            preset = presets.PRESETS[tool.preset]
            if tool.control not in preset.sliders:
                misfiled.append(
                    f"{tool.label} -> {tool.preset}.{tool.control}, which is not one of its "
                    f"controls")

    named = {tool.preset for _, _, tool in all_tools()}
    unclaimed = sorted(set(presets.PRESETS) - named - set(PRIMITIVES))
    stale = sorted(set(PRIMITIVES) - (set(presets.PRESETS) - named))

    return {
        "tools": len(all_tools()),
        "presets_named": len(named),
        "controls": sum(1 for _, _, t in all_tools() if t.control),
        "gaps": gaps,
        "misfiled": misfiled,
        "unclaimed": unclaimed,
        "stale_primitives": stale,
        "ok": not (gaps or misfiled or unclaimed or stale),
    }


def tree() -> list[str]:
    """the brief, printed as what it became."""
    lines = []
    for group in GROUPS:
        lines.append(group.name)
        for tool in group.tools:
            lines.append(f"  {_line(tool)}")
        for section in group.sections:
            lines.append(f"  {section.name}")
            for tool in section.tools:
                lines.append(f"    {_line(tool)}")
    return lines


def _line(tool: Tool) -> str:
    if tool.control:
        return f"{tool.label:34} = {tool.preset}.{tool.control}"
    return f"{tool.label:34} = {tool.preset}"
