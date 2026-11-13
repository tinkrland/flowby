"""actions: a node whose body is one file, and whose controls are declared in that file's header.

this is flowby's answer to what FLORA's action catalog actually is, read from their own API on
2026-11-13 (`flora_search_actions`, `flora_get_action`). every one of their 42 prebuilt actions is a
single file of code with a header of `# @flora-…` annotations: name, description, inputs, outputs, and
params with types, ranges and `visibleIf` conditions. there is no plugin registry, no schema in a
database, and no drift between the code and the panel, because the panel is read out of the file. all 42
are `charged_cost: 0`, and they pick one of two runtimes by what the work needs: `python` for files
(ffmpeg) and `javascript` for pixels already in a browser (canvas, shaders). the model nodes are where
the money is; the utility layer is free and instant.

flowby keeps that contract and reads both spellings of it, so a FLORA action file's header parses here
unchanged and can be reimplemented behind it. what flowby does not take is running arbitrary pasted code
on the same process as the board: an action runs in the disposable kernel container, and this module
only ever reads a header, validates it, and calls a function it was pointed at.

an action file, in full:

    # @flowby-name: "Halftone"
    # @flowby-description: "Dots, angles and colour modes."
    # @flowby-runtime: python
    # @flowby-inputs: [{"name": "source", "type": "image"}]
    # @flowby-outputs: [{"name": "dotted", "type": "image"}]
    # @flowby-params: [
    #   {"key": "cell", "label": "Dot size", "type": "number", "default": 8, "min": 3, "max": 24, "step": 1},
    #   {"key": "angle", "label": "Screen angle", "type": "select", "default": "45",
    #    "options": [{"label": "0°", "value": "0"}, {"label": "45°", "value": "45"}]}
    # ]
    def run(inputs, values, out_dir):
        ...
        return {"dotted": "out/dotted.png"}
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path

# the header prefixes this module reads. flora's own files carry `@flora-`, and a file that parses as
# one of theirs should not need editing to be understood here.
PREFIXES = ("flowby", "flora")

# the wires flowby has, and the spellings an action may use for each. an action declaring `audio` is
# refused by name rather than silently dropped: flowby has four wires and pretending otherwise would
# lose a file at run time instead of at parse time.
WIRES = {"text": "text", "image": "image", "video": "video", "mesh": "mesh", "model3d": "mesh"}
NOT_YET = {"audio": "audio"}

# declared param types that carry a number, and the kinds they land on. `nonScaledSlider` is flora's
# spell for a slider whose value is a raw number rather than a 0..1 fraction, and it means nothing to a
# panel, so both arrive as a number.
NUMBERS = ("number", "nonScaledSlider", "slider", "integer")
KINDS = {"choice": "choice", "select": "choice", "text": "text", "string": "text",
         "toggle": "choice", "boolean": "choice"}

# what a header need not say: how long a run takes. a code action is seconds, so the defaults are
# small and deliberately unexciting; a header may override with @flowby-minutes.
MINUTES = {"python": 0.4, "javascript": 0.2}

HEADER_KEYS = ("name", "description", "runtime", "inputs", "outputs", "params", "minutes")


class ActionRefused(Exception):
    """an action that cannot be described is refused, and the sentence says what to fix."""


@dataclass(frozen=True)
class Port:
    name: str
    dtype: str


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    kind: str
    default: object
    means: str = ""
    low: float | None = None
    high: float | None = None
    step: float | None = None
    unit: str = ""
    choices: tuple[tuple[str, str], ...] = ()      # (label, value)
    when: tuple[tuple[str, str], ...] = ()         # ((other key, required value), …)

    def shown(self, values: dict) -> bool:
        """whether a panel should draw this control for these values."""
        return all(str(values.get(key)) == str(want) for key, want in self.when)

    def where(self, value) -> float:
        """the 0..1 position the frontend wants, the same shape presets already use."""
        if self.kind == "choice":
            labels = [v for _, v in self.choices]
            try:
                return labels.index(str(value)) / max(1, len(labels) - 1)
            except ValueError:
                return 0.0
        if self.kind == "text" or self.low is None or self.high is None:
            return 0.0
        span = self.high - self.low
        return 0.0 if span == 0 else (float(value) - self.low) / span

    def check(self, value):
        """the value, or a refusal. this is the only place a value from a page is believed."""
        if self.kind == "choice":
            allowed = [v for _, v in self.choices]
            if str(value) not in allowed:
                raise ActionRefused(
                    f"{self.key} does not offer {value!r}: choose one of {', '.join(allowed)}"
                )
            return str(value)
        if self.kind == "text":
            if not isinstance(value, str):
                raise ActionRefused(f"{self.key} is text, and {value!r} is not")
            return value
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ActionRefused(f"{self.key} is a number, and {value!r} is not") from None
        if self.low is not None and number < self.low:
            raise ActionRefused(f"{self.key} is {number:g}, below its own {self.low:g}")
        if self.high is not None and number > self.high:
            raise ActionRefused(f"{self.key} is {number:g}, above its own {self.high:g}")
        return number


@dataclass
class Action:
    name: str
    means: str                      # the description, in the action's own words
    runtime: str
    inputs: tuple[Port, ...]
    outputs: tuple[Port, ...]
    params: tuple[Param, ...] = ()
    minutes: float = 0.4
    source: str = ""
    path: str = ""

    # -- what the panel asks for -------------------------------------------------------------

    def values(self, overrides: dict | None = None) -> dict:
        """every param's value, defaults with the caller's overrides checked on top."""
        out = {p.key: p.default for p in self.params}
        for key, value in (overrides or {}).items():
            known = next((p for p in self.params if p.key == key), None)
            if known is None:
                raise ActionRefused(f"{self.name} has no parameter {key!r}")
            out[key] = known.check(value)
        return out

    def controls(self, overrides: dict | None = None) -> list[dict]:
        """the controls, in the header's order, each saying whether it applies to these values.

        a control that does not apply is still returned rather than dropped: a panel that forgets a
        control cannot show it again when the choice changes, and a page that only ever receives the
        visible ones would have to learn the rule itself.
        """
        values = self.values(overrides)
        out = []
        for param in self.params:
            out.append({
                "name": param.key,
                "label": param.label,
                "kind": param.kind,
                "low": param.low,
                "high": param.high,
                "step": param.step,
                "unit": param.unit,
                "means": param.means,
                "value": values[param.key],
                "where": param.where(values[param.key]),
                "choices": [value for _, value in param.choices],
                "choice_labels": [label for label, _ in param.choices],
                "shown": param.shown(values),
                "because": dict(param.when),
            })
        return out

    def estimate(self, overrides: dict | None = None) -> dict:
        """what a run of this costs. code is not a model, so the answer is nothing, and fast."""
        self.values(overrides)
        return {"minutes": self.minutes, "gpu_minutes": 0.0, "cost_usd": 0.0,
                "free_because": f"{self.runtime} code, not a model"}

    def panel(self, overrides: dict | None = None) -> dict:
        """the whole sidebar payload for one action, in the shape presets already use."""
        return {
            "action": self.name,
            "label": self.name,
            "blurb": self.means,
            "runtime": self.runtime,
            "changes": {"from": self.inputs[0].dtype if self.inputs else None,
                        "to": self.outputs[0].dtype if self.outputs else None},
            "inputs": [{"name": p.name, "dtype": p.dtype} for p in self.inputs],
            "outputs": [{"name": p.name, "dtype": p.dtype} for p in self.outputs],
            "controls": self.controls(overrides),
            "estimate": self.estimate(overrides),
        }

    # -- running -----------------------------------------------------------------------------

    def run(self, inputs: dict[str, str], out_dir: str, overrides: dict | None = None) -> dict[str, str]:
        """call the file's own `run`, after checking its inputs and values.

        this is the seam the kernel worker uses. it refuses before it calls anything: a missing input,
        a value out of range, a module with no `run`. it never re-declares what the action said it
        returns; it checks the answer against the declared outputs and refuses a mismatch.
        """
        from . import dtypes  # noqa: F401  (imported for the side effect of the wire registry being checked)

        for port in self.inputs:
            if not inputs.get(port.name):
                raise ActionRefused(f"{self.name} needs {port.name!r} ({port.dtype}) and was given nothing")
        values = self.values(overrides)
        module = load(self.path)
        if not hasattr(module, "run"):
            raise ActionRefused(f"{self.path} has a header but no run(inputs, values, out_dir)")
        got = module.run(dict(inputs), values, out_dir)
        if not isinstance(got, dict):
            raise ActionRefused(f"{self.name}.run returned {type(got).__name__}, not a dict of outputs")
        missing = [p.name for p in self.outputs if not got.get(p.name)]
        if missing:
            raise ActionRefused(f"{self.name} declared {', '.join(missing)} and returned no path for it")
        extra = [k for k in got if k not in {p.name for p in self.outputs}]
        if extra:
            raise ActionRefused(f"{self.name} returned {', '.join(extra)}, which it never declared")
        for name, path in got.items():
            if not Path(path).exists():
                raise ActionRefused(f"{self.name} said {name} is at {path}, and nothing is there")
        return got


# -- reading a header ------------------------------------------------------------------------


def parse(source: str, path: str = "") -> Action:
    """an action from its file's text, or a refusal naming the line that is wrong."""
    header, unknown = _header(source)
    if unknown:
        raise ActionRefused(
            f"{path or 'this action'} has @…-{unknown[0]}, which is not a header key: "
            f"the keys are {', '.join(HEADER_KEYS)}"
        )
    name = _text(header, "name", path)
    if not name:
        raise ActionRefused(f"{path or 'this action'} has no @flowby-name, so it cannot be listed")
    means = _text(header, "description", path)
    runtime = (_text(header, "runtime", path) or "python").strip()
    if runtime not in MINUTES:
        raise ActionRefused(f"{name} says runtime {runtime!r}: flowby runs python or javascript")

    inputs = _ports(name, _json(header, "inputs", path), "input")
    outputs = _ports(name, _json(header, "outputs", path), "output")
    if not inputs:
        raise ActionRefused(f"{name} takes no inputs, so there is nothing to wire it to")
    if not outputs:
        raise ActionRefused(f"{name} returns nothing, so nothing can be wired after it")

    params = _params(name, _json(header, "params", path) or [], path)
    minutes = _scalar(header, "minutes")
    if minutes is None:
        minutes = MINUTES[runtime]
    try:
        minutes = float(minutes)
    except (TypeError, ValueError):
        raise ActionRefused(f"{name} says {minutes!r} minutes") from None
    if minutes < 0:
        raise ActionRefused(f"{name} says {minutes:g} minutes, which is not a duration")
    return Action(name=name, means=means, runtime=runtime, inputs=inputs, outputs=outputs,
                  params=params, minutes=minutes, source=source, path=path)


def from_file(path: str) -> Action:
    """an action, read from a file. the path is kept, because running it needs the module back."""
    where = Path(path)
    try:
        source = where.read_text()
    except OSError as problem:
        raise ActionRefused(f"cannot read {path}: {problem.strerror}") from None
    action = parse(source, path)
    action.path = str(where)
    return action


def load(path: str):
    """the file as a module, named after its path so two actions cannot collide."""
    if not path:
        raise ActionRefused("this action was parsed from text, not a file, so it cannot be run")
    spec = importlib.util.spec_from_file_location(f"flowby_action_{Path(path).stem}", path)
    if spec is None or spec.loader is None:
        raise ActionRefused(f"{path} is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shelf(directory: str) -> dict[str, Action]:
    """every action in a directory, by name, refused as a set if any two claim the same name."""
    where = Path(directory)
    if not where.is_dir():
        # an empty shelf and a missing directory look identical to a caller, and one of them is a typo
        raise ActionRefused(f"{directory} is not a directory of actions")
    found: dict[str, Action] = {}
    for path in sorted(where.glob("*.py")):
        if path.name.startswith("_"):
            continue
        action = from_file(str(path))
        if action.name in found:
            raise ActionRefused(f"{action.name} is declared twice: {found[action.name].path} and {path}")
        found[action.name] = action
    return found


# -- the header itself -----------------------------------------------------------------------


def _header(source: str) -> tuple[dict, list[str]]:
    """every `@prefix-key:` block in the comment lines, parsed as json, with its value as text.

    a value may run over several comment lines, which is how flora writes a params list, so a block is
    collected until it parses.
    """
    blocks: dict[str, str] = {}
    unknown: list[str] = []
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#"):
            i += 1
            continue
        body = line.lstrip("#").strip()
        found = None
        for prefix in PREFIXES:
            marker = f"@{prefix}-"
            if body.startswith(marker):
                found = body[len(marker):]
                break
        if found is None:
            i += 1
            continue
        key, _, value = found.partition(":")
        key = key.strip()
        value = value.strip()
        i += 1
        # keep taking comment lines while a bracketed value is still incomplete. a bare word is
        # already complete: `@flowby-runtime: python` must not swallow the line after it, which is
        # exactly what an unconditional "collect until it parses" did.
        while not _complete(value) and i < len(lines):
            more = lines[i].strip()
            if not more.startswith("#"):
                break
            value += " " + more.lstrip("#").strip()
            i += 1
        if key in HEADER_KEYS:
            blocks[key] = value
        else:
            unknown.append(key)
    return blocks, unknown


def _complete(value: str) -> bool:
    """whether a header value has been collected in full: a bracketed one must parse, a bare one is whole."""
    text = value.strip()
    if text[:1] in "[{":
        try:
            json.loads(text)
            return True
        except ValueError:
            return False
    return bool(text)


def _scalar(header: dict, key: str):
    """a header value as written: json when it is json, the bare word when it is a bare word."""
    raw = header.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw.strip()


def _json(header: dict, key: str, path: str):
    raw = header.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        raise ActionRefused(f"{path or 'this action'} has @…-{key} that is not json: {raw[:60]}") from None


def _text(header: dict, key: str, path: str) -> str:
    raw = header.get(key)
    if raw is None:
        return ""
    value = _scalar(header, key)
    if not isinstance(value, str):
        raise ActionRefused(f"{path or 'this action'} has @…-{key} that is not a quoted string")
    return value.strip()


def _ports(name: str, declared, which: str) -> tuple[Port, ...]:
    if not declared:
        return ()
    if not isinstance(declared, list):
        raise ActionRefused(f"{name} declares {which} as {type(declared).__name__}, not a list")
    ports, seen = [], set()
    for entry in declared:
        if not isinstance(entry, dict) or not entry.get("name"):
            raise ActionRefused(f"{name} has {which} {entry!r} with no name")
        wire = str(entry.get("type") or "").strip()
        if wire in NOT_YET:
            raise ActionRefused(
                f"{name} {which} {entry['name']!r} is {wire}, and flowby's wires are "
                f"{', '.join(sorted(set(WIRES.values())))}: {wire} has none"
            )
        dtype = WIRES.get(wire)
        if dtype is None:
            raise ActionRefused(
                f"{name} {which} {entry['name']!r} is {wire!r}, which is not a wire flowby has: "
                f"{', '.join(sorted(set(WIRES.values())))}"
            )
        if entry["name"] in seen:
            raise ActionRefused(f"{name} declares the {which} {entry['name']!r} twice")
        seen.add(entry["name"])
        ports.append(Port(entry["name"], dtype))
    return tuple(ports)


def _params(name: str, declared, path: str) -> tuple[Param, ...]:
    if not isinstance(declared, list):
        raise ActionRefused(f"{name} declares params as {type(declared).__name__}, not a list")
    params, seen = [], set()
    for entry in declared:
        if not isinstance(entry, dict):
            raise ActionRefused(f"{name} has a param {entry!r} that is not an object")
        key = str(entry.get("key") or "").strip()
        if not key:
            raise ActionRefused(f"{name} has a param with no key")
        if key in seen:
            raise ActionRefused(f"{name} declares the param {key!r} twice")
        seen.add(key)
        params.append(_param(name, key, entry))
    # visibility can only point at something that exists, and only at a choice, because "show this when
    # that equals that" is meaningless against a free number
    by_key = {p.key: p for p in params}
    for param in params:
        for other, want in param.when:
            if other not in by_key:
                raise ActionRefused(
                    f"{name} shows {param.key!r} when {other!r} is {want!r}, and {other!r} is not a param"
                )
            if by_key[other].kind != "choice":
                raise ActionRefused(
                    f"{name} shows {param.key!r} based on {other!r}, which is {by_key[other].kind} "
                    f"and not a choice"
                )
            if want not in [v for _, v in by_key[other].choices]:
                raise ActionRefused(
                    f"{name} shows {param.key!r} when {other!r} is {want!r}, and {other!r} never is"
                )
    return tuple(params)


def _param(name: str, key: str, entry: dict) -> Param:
    label = str(entry.get("label") or key)
    means = str(entry.get("description") or entry.get("means") or "")
    declared = str(entry.get("type") or "number").strip()
    step = entry.get("step")
    when = _when(entry.get("visibleIf", entry.get("visible_if")))
    if declared in NUMBERS:
        low, high = entry.get("min"), entry.get("max")
        default = entry.get("default")
        if default is None:
            default = low if low is not None else 0
        param = Param(key=key, label=label, kind="number", default=float(default), means=means,
                      low=None if low is None else float(low), high=None if high is None else float(high),
                      step=None if step is None else float(step),
                      unit=str(entry.get("unit") or ""), when=when)
        param.check(param.default)   # a default outside its own range is the action's own bug
        return param
    kind = KINDS.get(declared)
    if kind is None:
        raise ActionRefused(f"{name} param {key!r} is {declared!r}, which is not a param type flowby draws")
    if declared in ("toggle", "boolean"):
        param = Param(key=key, label=label, kind="choice", default="On" if entry.get("default") else "Off",
                      means=means, choices=(("On", "On"), ("Off", "Off")), when=when)
        return param
    if declared in ("text", "string"):
        return Param(key=key, label=label, kind="text", default=str(entry.get("default") or ""),
                     means=means, when=when)
    options = entry.get("options") or []
    if not options:
        raise ActionRefused(f"{name} param {key!r} is a select with nothing to choose")
    choices, labels = [], []
    for option in options:
        value = str(option.get("value")) if isinstance(option, dict) else str(option)
        label_of = str(option.get("label") or value) if isinstance(option, dict) else value
        if value in labels:
            raise ActionRefused(f"{name} param {key!r} offers {value!r} twice")
        choices.append((label_of, value))
        labels.append(value)
    default = str(entry.get("default", labels[0]))
    param = Param(key=key, label=label, kind="choice", default=default, means=means,
                  choices=tuple(choices), when=when)
    param.check(default)
    return param


def _when(declared) -> tuple[tuple[str, str], ...]:
    """`[{"key": "effect", "equals": "grain"}]` or `{"effect": "grain"}` into pairs."""
    if not declared:
        return ()
    if isinstance(declared, dict):
        return tuple((str(k), str(v)) for k, v in declared.items())
    out = []
    for entry in declared:
        if not isinstance(entry, dict) or "key" not in entry:
            raise ActionRefused(f"visibleIf entry {entry!r} has no key")
        out.append((str(entry["key"]), str(entry.get("equals"))))
    return tuple(out)
