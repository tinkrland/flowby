"""recipes: the chain on an element, given a name, a version, and the inputs somebody else can change.

read off Fuser's recipe pages on 2026-11-13 (`fuser.studio/recipes`, 198 recipes shown, and the
individual pages for PS1-Style Graphics and Adding Micrographics). what a recipe is *there*, in their
own markup:

    PS1-Style Subject Image                      ← a name for the result, not for the process
    Transform a text subject … into a PS1-style image …
    Inputs: Subject   Outputs: PS1-Style Image   ← the two blocks that make it usable by someone else
    @maggie · v2                                 ← an author and a version
    Models in this recipe: GPT Image (OpenAI)

and, from their features page, the behaviour that version number implies: a placed recipe is **pinned**
to the version it was placed at, so improving a recipe cannot silently change work already on somebody's
board. you adopt an update when you decide to.

flowby already had the chain (`Scene.record` reads it back, `replay` applies it) and had none of the
rest: no version, no exposed inputs, no name for the result, no pin. this module is that rest, and it is
deliberately small, because a recipe is still just a chain and inventing a second storage format for one
would be how the two drift apart.

the three refusals matter more than the fields:

  - an exposed input has to feed something in the chain. a control that changes nothing is a lie, and it
    is the kind of lie that only shows up when a stranger tries to use the recipe.
  - two exposed inputs cannot feed the same value, or the second one silently wins.
  - a placement whose pin does not match the recipe is not quietly updated; it says which version it
    holds and which one it was offered.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from . import presets


class RecipeRefused(Exception):
    """a recipe that cannot be used by somebody else is refused, and the sentence says why."""


@dataclass(frozen=True)
class Exposed:
    """one control a stranger may change, and exactly where its value goes."""
    label: str
    preset: str          # which step in the chain
    param: str           # which slider on that step
    start: object        # the value the recipe was saved with
    means: str = ""

    def target(self) -> tuple[str, str]:
        return (self.preset, self.param)


@dataclass
class Recipe:
    name: str
    brief: str                        # what you bring and what you get, in one line
    steps: tuple[dict, ...]
    inputs: tuple[Exposed, ...] = ()
    output: str = ""
    dtype: str = ""
    category: str = ""
    author: str = ""
    models: tuple[str, ...] = field(default_factory=tuple)

    # -- identity ---------------------------------------------------------------------------

    @property
    def version(self) -> str:
        """a short hash of what the recipe *does*, so a rename is not a new version.

        the steps, their values, their slot wiring and the exposed targets are in; the name, the brief,
        the author, the category and the output's own name are out, because none of them change a single
        pixel. this is the number a placement pins, so it has to move when a param does and stay still
        when prose does. Fuser draw the same line: names and labels are shared across versions, the
        wiring is not. the output's *type* is derived from the last step, so it cannot change without
        the steps changing.
        """
        material = {
            "steps": [{"preset": s["preset"],
                       "values": _ordered(s.get("values") or {}),
                       "slots": _ordered(s.get("slots") or {})} for s in self.steps],
            "inputs": [{"target": list(e.target()), "start": e.start} for e in self.inputs],
        }
        blob = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:6]

    # -- the panel --------------------------------------------------------------------------

    def estimate(self) -> dict:
        minutes = round(sum(presets.get(s["preset"]).minutes() for s in self.steps), 1)
        gpu = round(sum(presets.get(s["preset"]).estimate()["gpu_minutes"] for s in self.steps), 1)
        return {"minutes": minutes, "gpu_minutes": gpu}

    def panel(self) -> dict:
        """the payload a page draws: what it is, what it takes, what it gives, what it costs."""
        return {
            "recipe": self.name,
            "brief": self.brief,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "inputs": [{"label": e.label, "start": e.start, "means": e.means,
                        "preset": e.preset, "param": e.param} for e in self.inputs],
            "outputs": [{"name": self.output, "dtype": self.dtype}] if self.output else [],
            "models": list(self.models),
            "chain": [{"preset": s["preset"], "values": dict(s.get("values") or {})} for s in self.steps],
            "estimate": self.estimate(),
        }

    # -- using it ---------------------------------------------------------------------------

    def values_for(self, given: dict | None = None) -> dict:
        """each step's values with the exposed inputs applied, given values checked first."""
        by_label = {e.label: e for e in self.inputs}
        overrides = dict(given or {})
        unknown = [label for label in overrides if label not in by_label]
        if unknown:
            raise RecipeRefused(
                f"{self.name} exposes {', '.join(by_label) or 'nothing'}, and was given "
                f"{', '.join(unknown)}"
            )
        per_step = {i: dict(s.get("values") or {}) for i, s in enumerate(self.steps)}
        for exposed in self.inputs:
            value = overrides.get(exposed.label, exposed.start)
            step = presets.get(exposed.preset)
            slider = step.sliders.get(exposed.param)
            if slider is None:
                raise RecipeRefused(f"{self.name} feeds {exposed.preset}.{exposed.param}, which is not a "
                                    f"control on it")
            per_step[self._index(exposed.preset)][exposed.param] = slider.check(value)
        return {"steps": [{"preset": s["preset"], "values": per_step[i]}
                          for i, s in enumerate(self.steps)]}

    def placed(self, pin: str) -> "Placement":
        """this recipe, held at a version. the point of the argument is that it is required."""
        if not pin:
            raise RecipeRefused(f"a placement of {self.name} has to say which version it holds")
        return Placement(recipe=self, pin=pin)

    def _index(self, preset: str) -> int:
        for i, step in enumerate(self.steps):
            if step["preset"] == preset:
                return i
        raise RecipeRefused(f"{self.name} has no step called {preset}")


@dataclass
class Placement:
    """a recipe as a board holds it: pinned, and only updated when somebody says so."""
    recipe: Recipe
    pin: str

    @property
    def current(self) -> bool:
        return self.pin == self.recipe.version

    def holds(self) -> Recipe:
        """the recipe as placed. refuses once the recipe has moved on, rather than running new code.

        this is the whole reason the pin exists: work already on a board should not change because
        somebody improved the thing it came from.
        """
        if not self.current:
            raise RecipeRefused(
                f"this board holds {self.recipe.name} v{self.pin}, and the recipe is now "
                f"v{self.recipe.version}: adopt the update to run the new one"
            )
        return self.recipe

    def adopt(self) -> "Placement":
        """take the update. explicit, because it is the one path that changes finished work."""
        return Placement(recipe=self.recipe, pin=self.recipe.version)

    def view(self) -> dict:
        return {"recipe": self.recipe.name, "pinned": self.pin, "available": self.recipe.version,
                "current": self.current,
                "offer": None if self.current else "adopt the update to run the new one"}


# -- making one ----------------------------------------------------------------------------


def of(record: dict, *, inputs=(), output: str = "", category: str = "",
       author: str = "", brief: str | None = None) -> Recipe:
    """a recipe from a chain `Scene.record` read back, with the inputs somebody else may change.

    `record` is flowby's own chain, unchanged: this adds identity to it rather than a second format.
    """
    steps = tuple(record.get("steps") or ())
    if not steps:
        raise RecipeRefused("a recipe with no steps is not a recipe: there is nothing to run")
    name = str(record.get("name") or "").strip()
    if not name:
        raise RecipeRefused("a recipe needs a name: it is the thing somebody searches for")
    for step in steps:
        if step["preset"] not in presets.PRESETS:
            raise RecipeRefused(f"{name} names the preset {step['preset']!r}, which does not exist")

    for exposed in inputs:
        if not exposed.label.strip():
            raise RecipeRefused(f"{name} has an exposed input with no label")
        if exposed.preset not in {s["preset"] for s in steps}:
            raise RecipeRefused(
                f"{name} exposes {exposed.label!r} into {exposed.preset}, which is not one of its steps"
            )
        preset = presets.get(exposed.preset)
        slider = preset.sliders.get(exposed.param)
        if slider is None:
            raise RecipeRefused(
                f"{name} exposes {exposed.label!r} onto {exposed.preset}.{exposed.param}, and that "
                f"preset's controls are {', '.join(preset.sliders) or 'none'}"
            )
        slider.check(exposed.start)   # a starting value out of its own range is the recipe's bug
    seen: dict[tuple[str, str], str] = {}
    for exposed in inputs:
        if exposed.target() in seen:
            raise RecipeRefused(
                f"{name} exposes {seen[exposed.target()]!r} and {exposed.label!r} onto the same "
                f"{exposed.preset}.{exposed.param}: one value cannot come from two places"
            )
        seen[exposed.target()] = exposed.label

    last = presets.get(steps[-1]["preset"])
    dtype = last.out_dtype()
    if not output:
        output = str(last.out_dtype())
    text = brief if brief is not None else f"{name}: {len(steps)} steps"
    if not text.strip():
        raise RecipeRefused(f"{name} needs a brief: one line saying what you bring and what you get")
    if len(text) > 200:
        raise RecipeRefused(f"{name}'s brief is {len(text)} characters: it is one line, not a page")

    models = tuple(sorted({m for step in steps
                           for m in presets.get(step["preset"]).estimate().get("models", [])}))
    return Recipe(name=name, brief=text.strip(), steps=steps, inputs=tuple(inputs), output=output,
                  dtype=dtype, category=category, author=author, models=models)


def default_inputs(record: dict) -> tuple[Exposed, ...]:
    """the control worth handing to a stranger: the first step's sweep slider, else its first control.

    a preset names a sweep when it has one control that is the whole point of it, so that is the honest
    default. this is a default, not a policy: `of()` takes whatever inputs a caller exposes.
    """
    steps = record.get("steps") or ()
    if not steps:
        return ()
    preset = presets.get(steps[0]["preset"])
    slider = preset.sweep.slider if preset.sweep is not None else next(iter(preset.sliders), None)
    if slider is None:
        return ()
    control = preset.sliders[slider]
    # the starting value is what the chain was actually saved with, not the control's default: a recipe
    # that opens on the default would quietly change the very board it was read from
    start = (steps[0].get("values") or {}).get(control.name, control.default)
    return (Exposed(label=control.label, preset=steps[0]["preset"], param=control.name,
                    start=start, means=control.means),)


def shelf(recipes: list[Recipe], *, output: str | None = None, category: str | None = None) -> list[Recipe]:
    """the two facets Fuser's index filters by: what comes out, and what kind of job it is for."""
    out = list(recipes)
    if output:
        out = [r for r in out if r.dtype == output]
    if category:
        out = [r for r in out if r.category == category]
    return out


def facets(recipes: list[Recipe]) -> dict:
    """what the filter menus would contain, counted, so a page need not guess."""
    outputs: dict[str, int] = {}
    categories: dict[str, int] = {}
    for recipe in recipes:
        outputs[recipe.dtype] = outputs.get(recipe.dtype, 0) + 1
        key = recipe.category or "uncategorised"
        categories[key] = categories.get(key, 0) + 1
    return {"outputs": outputs, "categories": categories}


def _ordered(mapping: dict) -> dict:
    return {key: mapping[key] for key in sorted(mapping)}
