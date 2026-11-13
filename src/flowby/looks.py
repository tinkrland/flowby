"""looks: the direction a kit member actually gives to a generator.

A kit member is a name ("pencil sketch") and a blurb. That is not enough to render anything, and it is
not supposed to be: `kits.py` says a member is `listed` until something real stands behind it. This file
is the something for the members that need no trained weights, only words and settings.

A **look** is not a preset (no nodes), not a style (no corpus, no weights), and not a recipe (no chain).
It is a catalogue row that compiles, deterministically and for free, into the wording a prompt needs for
one model family plus the settings that belong with that wording. Three of them stacked is a brief:
one mark, one surface, one finish.

Where this came from, and what was taken from it (2026-11-13, read not copied: nodetool is AGPL-ish
source and none of it is vendored here):

  - nodetool, `packages/presets`: a preset is `<kind>.<slug>`, it declares the `slot` it occupies, the
    `modes` it runs in, whether it is `stackable`, which ids it `conflicts` with, and one prompt
    fragment per model family with a **required `default`**. The rules that make a catalogue usable are
    all in their `stack.ts` and `compile.ts`: at most three, one per slot, no declared conflict, a
    family fragment falling back to `default` **with a warning**, settings merged per family, and a
    setting two presets disagree about failing the compile rather than silently picking one.
  - their "eject": a preset does not stay a hidden prompt suffix, it opens as an editable graph
    (prompt input -> text template holding the compiled wording -> generator -> output). flowby has the
    same node already: `text.compose` is that template step, which is why `eject()` here returns the
    wording tagged for that op instead of a blob of text.

What is flowby's own: the slot names. nodetool's slots are video-grammar (move, rig, speed, stock,
grade, lighting, era, ramp). A mark on paper is not a camera, so the slots here are `mark` (how the line
was made), `surface` (what it was made on) and `finish` (what happened to it afterwards) — three axes
that are genuinely orthogonal, which is the whole reason a stack of three can say something one cannot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# the most looks one request may carry, for the same reason nodetool picked three: past that the
# directions start arguing and the result is mud.
MAX_STACK = 3

# what a look occupies. one per stack, which is what stops "crayon and charcoal" from being asked for.
SLOTS = ("mark", "surface", "finish", "medium")

# where a look can run. a still is what a look words; motion looks are a later kind, and claiming them
# now would mean inventing settings no preset here declares.
MODES = ("image", "image_edit")

# the model families a look may word, and the model ids that belong to each. a model outside this map
# still compiles: it takes `default` and says so, because a warning beats a refusal when the fallback is
# honest wording rather than broken settings.
FAMILIES = {
    "flux": ("flux-dev", "flux-schnell"),
    "sdxl": ("sdxl-turbo",),
}

# the settings each mode actually forwards, read off the presets' own sweep targets. a look that sets
# anything else is setting something nothing reads, so the catalogue refuses it at load.
MODE_SETTINGS = {
    "image": ("size", "seed", "steps", "guidance"),
    "image_edit": ("strength", "seed", "steps", "guidance"),
}

# the op a look ejects into, and the op it feeds. both exist in presets.py; the test asserts it again so
# this file cannot drift away from the graph.
TEMPLATE_OP = "text.compose"
GENERATE_OP = "image.gen"


class LookRefused(Exception):
    """a look, a catalogue or a stack that does not make sense, with the reason in words a panel can show."""


def family_of(model: str) -> str | None:
    """which family a model id belongs to, or None when nothing here knows it."""
    for family, members in FAMILIES.items():
        if model in members:
            return family
    return None


@dataclass(frozen=True)
class Fragment:
    """one family's wording. `replace` drops the prompt built so far, for a look that owns the frame."""

    prefix: str = ""
    suffix: str = ""
    replace: str = ""

    def apply(self, prompt: str) -> str:
        # joined with commas rather than the space nodetool uses: their fragments are sentences meant to
        # run on after a shot description, and these are directions stacked in front of a subject, where
        # a comma is what stops "paper surface" and "pencil sketch" reading as one phrase
        parts = [self.prefix, self.replace or prompt, self.suffix]
        return ", ".join(part.strip().rstrip(",") for part in parts if part and part.strip()).strip()

    def as_dict(self) -> dict:
        return {key: value for key, value in
                (("prefix", self.prefix), ("suffix", self.suffix), ("replace", self.replace)) if value}


@dataclass(frozen=True)
class Look:
    id: str
    name: str
    description: str
    slot: str
    modes: tuple[str, ...]
    prompt: dict[str, object]
    inputs: tuple[str, ...] = ("text",)
    stackable: bool = True
    conflicts: tuple[str, ...] = ()
    params: dict[str, object] = field(default_factory=dict)
    family_params: dict[str, dict[str, object]] = field(default_factory=dict)
    kit: str = ""

    def which(self, family: str | None) -> tuple[str, bool]:
        """which fragment this family reads, and whether it had to fall back. the fallback is the
        caller's warning to make, not this method's quietly deciding it is fine."""
        if family and family in self.prompt:
            return family, False
        return "default", family is not None

    def settings(self, mode: str, family: str | None) -> tuple[dict, list[str]]:
        """the settings this look sets for this mode and family, and what it had to leave out."""
        merged = dict(self.params)
        scoped = self.family_params.get(family or "", {})
        merged.update(scoped)
        allowed = MODE_SETTINGS.get(mode, ())
        kept, dropped = {}, []
        for key, value in merged.items():
            if key in allowed:
                kept[key] = value
            else:
                dropped.append(f"{self.id} sets {key}, which {mode} does not forward")
        # a family-scoped setting for a family other than the one running is not a loss, it is a
        # different branch; but a scoped key that vanished from the merge is worth naming.
        for other, values in self.family_params.items():
            if other == (family or ""):
                continue
            for key in values:
                if key not in merged:
                    dropped.append(f"{self.id} has a {other} setting for {key} that this model does not use")
        return kept, dropped


def _fragment_of(raw: object) -> Fragment:
    """a fragment is a string or an object; both end up one shape so there is one join rule."""
    if isinstance(raw, Fragment):
        return raw
    if isinstance(raw, str):
        return Fragment(prefix=raw)
    return Fragment(**raw)


def _load_prompt(raw: object, where: str) -> dict[str, object]:
    if not isinstance(raw, dict) or not raw:
        raise LookRefused(f"{where}: a look needs a prompt fragment, and at least one called default")
    if "default" not in raw:
        raise LookRefused(f"{where}: a look needs a default fragment, because an unknown model has to "
                          f"fall back to something rather than to nothing")
    out: dict[str, object] = {}
    for family, fragment in raw.items():
        if family != "default" and family not in FAMILIES:
            raise LookRefused(f"{where}: {family!r} is not a model family here. the families are "
                              f"{', '.join(FAMILIES)}")
        if isinstance(fragment, str):
            if not fragment.strip():
                raise LookRefused(f"{where}: the {family} fragment is empty")
            out[family] = fragment.strip()
            continue
        if not isinstance(fragment, dict):
            raise LookRefused(f"{where}: the {family} fragment must be a string or an object")
        unknown = set(fragment) - {"prefix", "suffix", "replace"}
        if unknown:
            raise LookRefused(f"{where}: the {family} fragment has {', '.join(sorted(unknown))}, which is "
                              f"not prefix, suffix or replace")
        if not any(str(value).strip() for value in fragment.values()):
            raise LookRefused(f"{where}: the {family} fragment says nothing")
        out[family] = {key: str(value).strip() for key, value in fragment.items()}
    return out


def look_from_dict(raw: dict, where: str = "<look>") -> Look:
    """read one catalogue row, refusing anything a panel would have to apologise for."""
    ident = str(raw.get("id") or "")
    if not ident.startswith("look.") or not ident[5:].replace("-", "").isalnum():
        raise LookRefused(f"{where}: id {ident!r} should look like look.pencil-sketch")
    for key in ("name", "description"):
        if not str(raw.get(key) or "").strip():
            raise LookRefused(f"{where}: {ident} needs a {key}")
    slot = str(raw.get("slot") or "")
    if slot not in SLOTS:
        raise LookRefused(f"{where}: {ident} occupies {slot!r}, and the slots are {', '.join(SLOTS)}")
    modes = tuple(raw.get("modes") or ())
    if not modes:
        raise LookRefused(f"{where}: {ident} has to say where it runs")
    for mode in modes:
        if mode not in MODES:
            raise LookRefused(f"{where}: {ident} runs in {mode!r}, and the modes are {', '.join(MODES)}")

    params = dict(raw.get("params") or {})
    family_params = {family: dict(values) for family, values in (raw.get("family_params") or {}).items()}
    for family in family_params:
        if family not in FAMILIES:
            raise LookRefused(f"{where}: {ident} has settings for {family!r}, which is not a family here")
    allowed = {key for mode in modes for key in MODE_SETTINGS[mode]}
    every = dict(params)
    for values in family_params.values():
        every.update(values)
    for key in every:
        if key not in allowed:
            raise LookRefused(f"{where}: {ident} sets {key!r}, which no mode it runs in forwards. "
                              f"the settings are {', '.join(sorted(allowed))}")

    inputs = tuple(raw.get("inputs") or ("text",))
    for dtype in inputs:
        if dtype not in ("text", "image"):
            raise LookRefused(f"{where}: {ident} takes {dtype!r}, and a look takes text or an image")

    return Look(
        id=ident,
        name=str(raw["name"]).strip(),
        description=str(raw["description"]).strip(),
        slot=slot,
        modes=modes,
        prompt=_load_prompt(raw.get("prompt"), where),
        inputs=inputs,
        stackable=bool(raw.get("stackable", True)),
        conflicts=tuple(raw.get("conflicts") or ()),
        params=params,
        family_params=family_params,
        kit=str(raw.get("kit") or ""),
    )


def catalogue(path: str | Path = "looks") -> dict[str, Look]:
    """every look in a folder, refused as a set: a conflict naming a look that does not exist is a lie
    a picker would then have to explain."""
    folder = Path(path)
    if not folder.is_dir():
        raise LookRefused(f"{folder} is not a folder of looks")
    found: dict[str, Look] = {}
    for file in sorted(folder.glob("*.json")):
        raw = json.loads(file.read_text())
        look = look_from_dict(raw, where=file.name)
        if look.id in found:
            raise LookRefused(f"{file.name} repeats {look.id}; a catalogue cannot hold two of one look")
        found[look.id] = look
    if not found:
        raise LookRefused(f"{folder} holds no looks")
    for look in found.values():
        for other in look.conflicts:
            if other == look.id:
                raise LookRefused(f"{look.id} conflicts with itself")
            if other not in found:
                raise LookRefused(f"{look.id} conflicts with {other}, which is not a look here")
    return found


# --- the rules a picker and the compiler both apply ---------------------------------------------------

def pair_block(a: Look, b: Look) -> str | None:
    """why these two cannot share a brief, or None. one sentence, naming the reason."""
    if a.id == b.id:
        return f"{a.name} is already in the brief"
    if not a.stackable:
        return f"{a.name} cannot be stacked with anything"
    if not b.stackable:
        return f"{b.name} cannot be stacked with anything"
    if a.slot == b.slot:
        return f"{a.name} and {b.name} both set the {a.slot}, so one has to go"
    if b.id in a.conflicts or a.id in b.conflicts:
        return f"{a.name} and {b.name} are listed as conflicting directions"
    return None


def can_add(selected: tuple[str, ...], candidate: str, looks: dict[str, Look], mode: str = "image") -> str | None:
    """None when the candidate can join, or the sentence to show on its card. the picker disables with
    this and the compiler refuses with it, so the two cannot disagree."""
    look = looks.get(candidate)
    if look is None:
        return f"{candidate} is not a look here"
    if mode not in look.modes:
        return f"{look.name} does not run in {mode}"
    if len(selected) >= MAX_STACK:
        return f"a brief holds at most {MAX_STACK} looks"
    for other in selected:
        held = looks.get(other)
        if held is None:
            continue
        reason = pair_block(held, look)
        if reason:
            return reason
    return None


@dataclass(frozen=True)
class Compiled:
    """what a brief becomes: wording, settings, the looks that made it, and what was left unsaid."""

    prompt: str
    params: dict[str, object]
    applied: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict:
        return {"prompt": self.prompt, "params": self.params,
                "applied": list(self.applied), "warnings": list(self.warnings)}


def compile_looks(ids: tuple[str, ...], *, model: str, mode: str, prompt: str,
                  looks: dict[str, Look], ) -> Compiled:
    """compile a brief deterministically: no model call, no cost, same words every time."""
    if len(ids) > MAX_STACK:
        raise LookRefused(f"a brief holds at most {MAX_STACK} looks, and this one asks for {len(ids)}")
    chosen: list[Look] = []
    for ident in ids:
        look = looks.get(ident)
        if look is None:
            raise LookRefused(f"{ident!r} is not a look here")
        if mode not in look.modes:
            raise LookRefused(f"{look.name} does not run in {mode}; it runs in {', '.join(look.modes)}")
        chosen.append(look)
    for i, a in enumerate(chosen):
        for b in chosen[i + 1:]:
            reason = pair_block(a, b)
            if reason:
                raise LookRefused(reason)

    family = family_of(model)
    words = prompt
    applied: list[str] = []
    warnings: list[str] = []
    if family is None:
        # a model nothing here knows still compiles: the default wording is honest prose, not broken
        # settings. it says so, because "we used the generic words" is something a person should see.
        warnings.append(f"{model} is not a model with a family here, so every look used its default wording")
    settings: dict[str, object] = {}
    owners: dict[str, str] = {}
    for look in chosen:
        used, fell_back = look.which(family)
        if fell_back:
            warnings.append(f"{look.id} has no {family} fragment, so its default wording was used")
        fragment = _fragment_of(look.prompt[used])
        words = fragment.apply(words)
        applied.append(look.id)
        kept, dropped = look.settings(mode, family)
        warnings.extend(dropped)
        for key, value in kept.items():
            owner = owners.get(key)
            if owner and settings[key] != value:
                raise LookRefused(f"{key} is set to {settings[key]!r} by {owner} and to {value!r} by "
                                  f"{look.id}; two looks cannot both be right about it")
            settings[key] = value
            owners[key] = look.id
    return Compiled(prompt=words, params=settings, applied=tuple(applied), warnings=tuple(warnings))


def eject(ident: str, *, model: str, mode: str = "image",
          looks: dict[str, Look] | None = None) -> dict:
    """a look as two steps a board can hold and a person can edit: the direction, then the generator.

    this is the part worth taking from nodetool's eject: the style is not a hidden suffix, it is a node
    holding text, so changing the wording is editing the graph rather than fighting a setting. the
    direction compiles against an empty draft, because the sentence someone brings arrives on the
    compose step's own input rather than being baked in here.
    """
    shelf = looks if looks is not None else catalogue()
    compiled = compile_looks((ident,), model=model, mode=mode, prompt="", looks=shelf)
    look = shelf[ident]
    return {
        "look": look.id,
        "name": look.name,
        "steps": [
            {"op": TEMPLATE_OP, "label": "the direction", "params": {"prefix": compiled.prompt}},
            {"op": GENERATE_OP, "label": "generate", "params": dict(compiled.params)},
        ],
        "warnings": list(compiled.warnings),
    }


def shelf(looks: dict[str, Look]) -> dict:
    """the catalogue as a panel draws it: one group per slot, each look with what it does and where."""
    groups = []
    for slot in SLOTS:
        members = [look for look in looks.values() if look.slot == slot]
        if not members:
            continue
        groups.append({
            "slot": slot,
            "looks": [{
                "id": look.id, "name": look.name, "description": look.description,
                "kit": look.kit, "modes": list(look.modes), "stackable": look.stackable,
                "conflicts": list(look.conflicts), "families": sorted(look.prompt),
                "settings": sorted({key for key in (set(look.params)
                                                    | {k for v in look.family_params.values() for k in v})
                                    if any(key in MODE_SETTINGS[mode] for mode in look.modes)}),
            } for look in sorted(members, key=lambda held: held.name)],
        })
    return {"max_stack": MAX_STACK, "slots": [slot for slot in SLOTS],
            "families": {family: list(models) for family, models in FAMILIES.items()},
            "groups": groups, "total": len(looks)}
