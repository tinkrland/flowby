"""a style is the one kind that is trained, and everything else here is a way of refusing a bad one.

the other six kinds on the ladder (tool, technique, preset, recipe, workflow, factory) are made of
nodes that run in seconds. a style is a lora, and a lora is a job that takes hours on someone's
free gpu, so it has a lifecycle the others do not:

    corpus -> gated -> training -> validating -> ready          (or refused, or failed)

and it is the only kind with a *weight*. strength is a runtime input, not a property of the file,
so a style that is already trained costs nothing to move.

the rules in `gate` are not invented here. they are the ones tinkrland/illustrace learned the slow
way, mostly by wasting a gpu session: a trigger that is an english word contaminates the claim it
is meant to absorb, a corpus where one subject is half the captions teaches the subject instead of
the look, a corpus that mixes two techniques trains a mush, and a caption that describes the style
credits it to the text instead of the trigger. each is a refusal here so it is found before the
first gpu minute and not after the last.

training runs on the user's own colab through a browser they authorise (routes.py,
`colab-browserbase`). the user supplies the google session and a hugging face token; this module
never holds either, and `training_plan` names them as gates instead of reading them.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field

STATES = ("corpus", "gated", "training", "validating", "ready", "refused", "failed")

# the only moves a style may make. a ready style never goes back to training: a retrain is a new
# style with a new id, so a recipe that pointed at the old one still renders the same pixels.
MOVES = {
    "corpus": {"gated", "refused"},
    "gated": {"training", "refused"},
    "training": {"validating", "failed"},
    "validating": {"ready", "failed"},
    "ready": set(),
    "refused": set(),
    "failed": set(),
}

# a base is chosen for its licence before it is chosen for its quality, because the licence is
# what decides whether a sold style can exist at all. numbers are the ones illustrace measured.
BASES = {
    "flux-dev": {
        "label": "FLUX.1 [dev]",
        "licence": "flux-1-dev-non-commercial",
        "commercial": False,
        "gated_download": True,
        "note": "the better results, and a licence that forbids selling what it makes.",
    },
    "flux-schnell": {
        "label": "FLUX.1 [schnell]",
        "licence": "apache-2.0",
        "commercial": True,
        "gated_download": False,
        "note": "fluxgym's own readme says it gave poor results for lora training. unverified here.",
    },
}

# regions a style can apply to. `whole` is the fallback and the only one that needs no mask.
REGIONS = ("whole", "subject", "background")

# the authority order from illustrace's raster assessment contract. nothing decides silently:
# a mask says where it came from, and the weakest origin lowers confidence instead of hiding.
MASK_ORIGINS = ("user", "model", "heuristic", "whole_frame")

MIN_IMAGES = 10  # illustrace: 10 to 30 is the stated range for a coherent micro style
MAX_SUBJECT_SHARE = 0.40  # illustrace: no single subject family above 40% of captions
MAX_WEIGHT = 0.7  # illustrace: each style lora between 0.3 and 0.7
MIN_WEIGHT = 0.3
MAX_TOTAL_WEIGHT = 1.2  # illustrace: sum of active weights near 1.0 to 1.2
MAX_STACK = 3  # illustrace: interference grows past 2 or 3 simultaneous style loras

# words that describe how a picture was made rather than what it shows. a caption that says them
# is crediting the style to the text, so the trigger never absorbs it and it leaks into every
# generation that mentions the word. not exhaustive, and it says so in the message.
STYLE_WORDS = frozenset(
    """watercolor watercolour oil acrylic gouache impasto brushstroke brushstrokes sketchy
    painterly illustration illustrated cartoon flat vector pastel inked linework lineart
    grainy textured stylized stylised hand-drawn handdrawn""".split()
)

# words about light and time of day. illustrace caught these standing in for the palette: "sunset"
# in a late-period corpus *is* the palette, so keeping it in the caption hands the look to the text.
LIGHT_WORDS = frozenset(
    """sunset sunrise dawn dusk evening morning twilight moonlight moonlit golden-hour
    backlit sunlit midday""".split()
)

# a trigger that is a real word contaminates the look it is meant to absorb. the check is
# structural (letters only, no vowels pattern that spells something), not a dictionary, because
# a dictionary is a dependency and the tree has none. it refuses the obvious and says so.
_COMMON = frozenset(
    """style art paint painting photo image picture drawing sketch comic anime cartoon vintage
    retro modern classic soft clean rough dark light bright warm cold wash ink pop pastel
    watercolor realistic abstract minimal""".split()
)


class StyleRefused(Exception):
    """the corpus or the request is not one a style can be made from, and the message says why."""


@dataclass(frozen=True)
class Item:
    """one training image and its caption. the image itself stays on the user's disk."""

    name: str
    caption: str
    subject: str = ""  # the subject family the caption is about, for the balance check
    technique: str = ""  # an optional tag so a corpus that mixes two hands can be caught

    def as_dict(self) -> dict:
        return {"name": self.name, "caption": self.caption,
                "subject": self.subject, "technique": self.technique}


@dataclass
class Style:
    id: str
    label: str
    trigger: str
    base: str
    items: tuple[Item, ...] = ()
    state: str = "corpus"
    weight: float = 0.6  # the default strength, a runtime input and never baked into the file
    history: list = field(default_factory=list)
    reason: str = ""
    adapter: str = ""  # the user's drive path, set when training finishes
    probe: dict = field(default_factory=dict)  # what validation measured, with its floor

    def as_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "trigger": self.trigger, "base": self.base,
            "state": self.state, "weight": self.weight, "images": len(self.items),
            "adapter": self.adapter, "reason": self.reason, "probe": self.probe,
            "history": list(self.history),
        }


# --- the gate -------------------------------------------------------------------------------


def check_trigger(trigger: str) -> list[str]:
    """why this trigger would contaminate the style, or an empty list."""
    reasons = []
    if not re.fullmatch(r"[a-z]{5,12}", trigger):
        reasons.append(
            f"trigger {trigger!r} should be 5 to 12 lowercase letters with no digits or "
            f"punctuation, so the tokenizer sees a rare word and not a phrase"
        )
        return reasons
    if trigger in _COMMON:
        reasons.append(
            f"trigger {trigger!r} is an ordinary word, so the model already has opinions about it "
            f"and the style would absorb them. use a made-up token (illustrace used 'mzqtlv')"
        )
    # a substring check across every word that names a look, so 'mntwash' is caught for 'wash'
    # even though 'wash' is only in the ordinary-word list. words under 4 letters are skipped
    # because 'ink' and 'oil' would match inside any rare token by accident.
    for word in sorted(STYLE_WORDS | LIGHT_WORDS | _COMMON):
        flat = word.replace("-", "")
        if len(flat) >= 4 and flat in trigger and flat != trigger:
            reasons.append(
                f"trigger {trigger!r} contains {word!r}, a word for the very thing it is meant to "
                f"absorb. illustrace's first draft was 'mntwash' and the critique pass caught it"
            )
            break
    return reasons


def check_captions(trigger: str, items: tuple[Item, ...]) -> list[str]:
    """captions describe the subject and leave the style unspoken, so the trigger carries it.

    one line per kind of problem, not one per image: a corpus with the same mistake in every
    caption should read as one mistake with a count, and name a few examples.
    """
    missing, said_style, said_light = [], {}, {}
    for item in items:
        words = set(re.findall(r"[a-z][a-z-]+", item.caption.lower()))
        if not item.caption.strip().lower().startswith(trigger):
            missing.append(item.name)
        for word in words & STYLE_WORDS:
            said_style.setdefault(word, []).append(item.name)
        for word in words & LIGHT_WORDS:
            said_light.setdefault(word, []).append(item.name)

    def names(found: list[str]) -> str:
        shown = ", ".join(found[:3])
        return shown + (f" and {len(found) - 3} more" if len(found) > 3 else "")

    reasons = []
    if missing:
        one = len(missing) == 1
        reasons.append(
            f"{len(missing)} caption{'' if one else 's'} "
            f"{'does' if one else 'do'} not start with the trigger {trigger!r} ({names(missing)})"
        )
    for word, found in sorted(said_style.items()):
        reasons.append(
            f"{len(found)} caption{'s' if len(found) != 1 else ''} say {word!r} ({names(found)}). "
            f"that credits the style to the text instead of the trigger, so it leaks into every "
            f"prompt that uses the word"
        )
    for word, found in sorted(said_light.items()):
        reasons.append(
            f"{len(found)} caption{'s' if len(found) != 1 else ''} say {word!r} ({names(found)}). "
            f"light and time of day stand in for the palette, so they belong to the trigger and "
            f"not the caption"
        )
    return reasons


def check_corpus(items: tuple[Item, ...]) -> list[str]:
    """the corpus-level refusals: too few, duplicated, mixed in hand, or one subject too big."""
    reasons = []
    if len(items) < MIN_IMAGES:
        reasons.append(
            f"{len(items)} images is below {MIN_IMAGES}. a coherent style wants 10 to 30, and "
            f"20 to 50 at 1024px for a consistent one"
        )
    names = Counter(item.name for item in items)
    for name, count in names.items():
        if count > 1:
            reasons.append(f"{name} appears {count} times. duplicates silently double an image's weight")
    captions = Counter(item.caption for item in items)
    for caption, count in captions.items():
        if count > 1 and len(items) >= MIN_IMAGES:
            reasons.append(
                f"{count} images share the caption {caption[:48]!r}. identical captions mean the "
                f"subject is not being described and the trigger has nothing to separate"
            )
            break
    subjects = Counter(item.subject for item in items if item.subject)
    if subjects:
        top, count = subjects.most_common(1)[0]
        if count / len(items) > MAX_SUBJECT_SHARE:
            reasons.append(
                f"{count} of {len(items)} captions are about {top!r} "
                f"({count / len(items):.0%}, above {MAX_SUBJECT_SHARE:.0%}). the trigger will absorb "
                f"the subject and not the style. rebalance before training"
            )
    techniques = {item.technique for item in items if item.technique}
    if len(techniques) > 1:
        reasons.append(
            f"the corpus mixes {len(techniques)} techniques ({', '.join(sorted(techniques))}). "
            f"two hands in one folder train a mush. split it into two styles"
        )
    return reasons


def gate(style: Style) -> list[str]:
    """every reason this style may not start training. empty means it may."""
    reasons = []
    if style.base not in BASES:
        reasons.append(f"{style.base!r} is not a base. the bases are {', '.join(sorted(BASES))}")
    reasons += check_trigger(style.trigger)
    reasons += check_corpus(style.items)
    reasons += check_captions(style.trigger, style.items)
    if not (MIN_WEIGHT <= style.weight <= MAX_WEIGHT):
        reasons.append(
            f"default weight {style.weight} is outside {MIN_WEIGHT} to {MAX_WEIGHT}. "
            f"outside it a lone style over-saturates or does nothing"
        )
    return reasons


# --- the lifecycle --------------------------------------------------------------------------


def advance(style: Style, state: str, reason: str = "", clock=time.time) -> Style:
    if state not in STATES:
        raise StyleRefused(f"{state!r} is not a state. the states are {', '.join(STATES)}")
    if state not in MOVES[style.state]:
        allowed = ", ".join(sorted(MOVES[style.state])) or "none, it is final"
        raise StyleRefused(f"a style that is {style.state} cannot become {state}. it can become: {allowed}")
    style.history.append({"from": style.state, "to": state, "reason": reason, "at": clock()})
    style.state = state
    style.reason = reason
    return style


def submit(style: Style, clock=time.time) -> Style:
    """run the gate and move the style, so a refusal is a recorded state and not an exception."""
    reasons = gate(style)
    if reasons:
        advance(style, "refused", "; ".join(reasons), clock)
        return style
    return advance(style, "gated", "", clock)


# --- using a trained style ------------------------------------------------------------------


@dataclass(frozen=True)
class Use:
    """one style applied to one image: how hard, and where."""

    style: str
    weight: float
    region: str = "whole"
    priority: int = 0  # lower paints first; the top rank wins where regions overlap


def check_stack(uses: list[Use], styles: dict[str, Style], mask_origin: str | None = None) -> list[str]:
    """why this combination of styles would bleed, or an empty list.

    illustrace's numbers, not ours: each weight 0.3 to 0.7, the sum near 1.0 to 1.2, and no more
    than three at once, with masks preferred to stacking when there are two.
    """
    reasons = []
    if not uses:
        return ["no style is being applied"]
    for use in uses:
        style = styles.get(use.style)
        if style is None:
            reasons.append(f"{use.style!r} is not a style this board knows")
            continue
        if style.state != "ready":
            reasons.append(f"{style.label} is {style.state}, and only a ready style can be applied")
        if use.region not in REGIONS:
            reasons.append(f"{use.region!r} is not a region. the regions are {', '.join(REGIONS)}")
        if not (MIN_WEIGHT <= use.weight <= MAX_WEIGHT):
            reasons.append(
                f"{style.label} at {use.weight} is outside {MIN_WEIGHT} to {MAX_WEIGHT}"
            )
    bases = {styles[u.style].base for u in uses if u.style in styles}
    if len(bases) > 1:
        reasons.append(
            f"these styles were trained against different bases ({', '.join(sorted(bases))}). "
            f"a lora only works on the model it was trained for"
        )
    if len(uses) > MAX_STACK:
        reasons.append(
            f"{len(uses)} styles at once is past {MAX_STACK}. adapters interfere beyond two or "
            f"three, so use masks to give each its own region"
        )
    # the sum only matters for styles that share pixels. two styles on different regions do not.
    by_region: dict[str, float] = {}
    for use in uses:
        reach = ("subject", "background") if use.region == "whole" else (use.region,)
        for region in reach:
            by_region[region] = by_region.get(region, 0.0) + use.weight
    for region, total in by_region.items():
        if total > MAX_TOTAL_WEIGHT + 1e-9:
            reasons.append(
                f"the styles reaching the {region} sum to {total:.2f}, above {MAX_TOTAL_WEIGHT}. "
                f"over-saturation starts there"
            )
    regional = [u for u in uses if u.region != "whole"]
    if regional and mask_origin is None:
        reasons.append("a style placed on the subject or background needs a mask, and none was given")
    if mask_origin is not None and mask_origin not in MASK_ORIGINS:
        reasons.append(f"{mask_origin!r} is not a mask origin. they are {', '.join(MASK_ORIGINS)}")
    return reasons


def confidence(mask_origin: str | None) -> str:
    """a mask that was guessed lowers confidence out loud instead of passing for a drawn one."""
    return {"user": "high", "model": "medium", "heuristic": "low",
            "whole_frame": "low", None: "high"}[mask_origin]


def resolve_order(uses: list[Use]) -> list[Use]:
    """lowest priority number paints first, so the last painter wins a contested pixel."""
    return sorted(uses, key=lambda use: (use.priority, use.style))


def rank_weights(uses: list[Use], decay: float = 0.65) -> dict[str, float]:
    """illustrace's gravity: the top rank keeps its weight and each lower rank decays by 0.65.

    strength is how much you take; gravity is who wins a conflict. the two are separate axes, so a
    lower-ranked style at a high strength still blends under a top-ranked one at a lower strength.
    """
    ranked = sorted(uses, key=lambda use: (-use.priority, use.style))
    return {use.style: round(use.weight * (decay ** index), 4) for index, use in enumerate(ranked)}


# --- the training plan ----------------------------------------------------------------------

# measured by illustrace on a free t4: 450 steps at 10 to 20 seconds each. the estimate scales with
# the corpus because the step count does, and says "about" because the range is a factor of two.
SECONDS_PER_STEP = (10, 20)
REPEATS = 3
EPOCHS = 10
SAVE_EVERY = 2


def steps_for(images: int, repeats: int = REPEATS, epochs: int = EPOCHS) -> int:
    return images * repeats * epochs


def estimate_minutes(images: int) -> tuple[float, float]:
    """low and high wall-clock minutes for the training step alone, on a free t4."""
    steps = steps_for(images)
    return steps * SECONDS_PER_STEP[0] / 60, steps * SECONDS_PER_STEP[1] / 60


def training_plan(style: Style, route: str = "colab-browserbase") -> dict:
    """the style's training job in the same shape every other job has.

    it is a flat plan with one training step and the seams routes.fit already checks: a gpu, a
    duration against the route's ceiling, and the credentials named as gates and never read. the
    resume path is part of the plan, not an afterthought, because a 2 hour job on a free runtime
    will be cut at least once.
    """
    if style.state != "gated":
        raise StyleRefused(
            f"{style.label} is {style.state}. only a gated style gets a training plan"
            + (f": {style.reason}" if style.reason else "")
        )
    base = BASES[style.base]
    low, high = estimate_minutes(len(style.items))
    steps = steps_for(len(style.items))
    env_gates = ["GOOGLE_SESSION_COOKIES", "COLAB_NOTEBOOK_ID"]
    if base["gated_download"]:
        env_gates.append("HF_TOKEN")  # the user's own, from an account that accepted the licence
    return {
        "contract": "flowby/1",
        "kind": "style.train",
        "job_id": f"style:{style.id}",
        "route": route,
        "style": style.id,
        "trigger": style.trigger,
        "base": style.base,
        "licence": base["licence"],
        "commercial": base["commercial"],
        "env": {"gpu": True, "pip": ["accelerate"], "models": [base["label"]], "gates": env_gates},
        "estimate_minutes": round(high, 1),
        "estimate_range_minutes": [round(low, 1), round(high, 1)],
        "steps": [{
            "id": "train",
            "op": "style.train",
            "inputs": {},
            "params": {
                "network": "lora_flux", "dim": 16, "alpha": 16, "lr": 1e-4,
                "epochs": EPOCHS, "repeats": REPEATS, "images": len(style.items),
                "total_steps": steps,
                # the flags a free t4 needs, from illustrace's first live run. without them the
                # host is killed for memory with no traceback, which is why they are written down.
                "flags": ["--fp8_base", "--mixed_precision fp16", "--save_precision fp16",
                          "--lowram", "--blocks_to_swap 8", "--cache_latents_to_disk",
                          "--cache_text_encoder_outputs_to_disk"],
                "caption_dropout_rate": 0.1,
                "bucket": [768, 1024],
            },
        }],
        "resume": {
            "save_every_epochs": SAVE_EVERY,
            "state_on": "the user's drive",
            "on_cut": "rerun the same plan; training resumes from the last saved epoch",
            "weights_cached_on_drive": True,
        },
        "artifacts": [{"id": "adapter", "step": "train", "port": "out", "dtype": "mesh",
                       "name": f"{style.trigger}.safetensors", "kind": "lora"}],
        "caveats": [
            "the runtime is the user's own colab, driven through a browser they authorise",
            f"about {low / 60:.1f} to {high / 60:.1f} hours on a free t4, so expect it to be cut at least once",
        ] + ([] if base["commercial"] else [
            f"{base['label']} is {base['licence']}: a style trained on it cannot be sold",
        ]),
    }


def validate_probe(measured: dict, floor: dict, fidelity_max: float = 10.0) -> dict:
    """illustrace's adapter probe, as a verdict a style cannot skip.

    `measured` is the palette distance of holdout generations to the training profile (cie76 delta
    e) and `floor` is the same distance for the untrained base. fidelity needs the first under 10.
    leakage is any component that moved on a negative prompt by more than the floor plus one
    standard deviation. a probe with no floor is refused, because 'passes' is uncalibrated without
    the untrained model to compare against.
    """
    if "palette_de" not in measured:
        raise StyleRefused("the probe has no palette distance, so there is nothing to judge fidelity by")
    if not floor:
        raise StyleRefused("the probe has no floor from the untrained base, so a pass would mean nothing")
    leaked = []
    for component, value in measured.get("unclaimed", {}).items():
        base = floor.get(component, {"mean": 0.0, "sd": 0.0})
        if value > base["mean"] + base["sd"]:
            leaked.append(component)
    fidelity = measured["palette_de"] < fidelity_max
    return {
        "fidelity": fidelity,
        "palette_de": measured["palette_de"],
        "leaked": sorted(leaked),
        "ready": fidelity and not leaked,
        "caveat": "illustrace measured several dE of noise in this metric, so 10 is not a hard line",
    }
