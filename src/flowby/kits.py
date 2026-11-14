"""preset kits: a shelf of styles and subtypes around one craft.

a kit is not a new rung on the ladder in theidea/taxonomy.md. it builds nothing and trains nothing;
it COLLECTS, so a person who wants "something analog" finds cyanotype, linocut and wax seal together
and not scattered across a menu sorted by model. the ladder's rule (a thing is built only from rungs
below it) is not touched, because a kit only points down the ladder.

what a kit member can be, and the one thing this file will not do:

    - a STYLE: a look that has to be trained (see styles.py: corpus, gate, training, ready)
    - a SUBTYPE: a variant inside a style or a craft (cross stitch inside textile)
    - a PRESET: an existing task card from presets.py, named here so the kit can offer it

the owner listed the first members on 2026-11-09 and said the styles are built later and more will
be given. so a member is marked `listed` until it has been built, and `listed` means exactly "named
and nothing else": no corpus, no trained weights, no preset behind it. the menu shows it, dimmed and
labelled, and never offers to run it. a member does not become `ready` by being edited here; it
becomes ready when styles.py says its style is. `state_of()` reads that, so this file cannot lie.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# what a member is. the same words the taxonomy uses.
KINDS = ("style", "subtype", "preset")

# where a member stands. `listed` is the only state anything here is in today.
STATES = ("listed", "corpus", "training", "ready")


class KitRefused(Exception):
    """a kit that does not make sense is refused when it is built, not when someone opens the menu."""


@dataclass(frozen=True)
class Member:
    id: str
    label: str
    kind: str = "style"
    blurb: str = ""
    # a subtype names its parent member, so cross stitch can sit under textile without being a style
    parent: str | None = None
    # the name in presets.PRESETS when kind == "preset"; None otherwise
    preset: str | None = None
    # the name in styles.py when a style has actually been built; None while it is only listed
    style: str | None = None
    # the id in looks.py when the member has real wording behind it. not a style and not a preset: a
    # look compiles to a sentence and settings, so a member with one can render before anything is
    # trained. it stays `listed` regardless, because `listed` is about what the menu may offer to run.
    look: str | None = None

    def __post_init__(self):
        if self.kind not in KINDS:
            raise KitRefused(f"{self.id}: {self.kind!r} is not a kind of member ({', '.join(KINDS)})")
        if not self.id or self.id != self.id.lower() or " " in self.id:
            raise KitRefused(f"{self.id!r}: an id is lowercase with no spaces, so it can be written in a url and a file")
        if self.kind == "preset" and not self.preset:
            raise KitRefused(f"{self.id}: a preset member has to name the preset it offers")
        if self.kind != "preset" and self.preset:
            raise KitRefused(f"{self.id}: only a preset member names a preset")


@dataclass(frozen=True)
class Kit:
    id: str
    label: str
    blurb: str
    members: tuple[Member, ...] = field(default_factory=tuple)

    def __post_init__(self):
        seen: set[str] = set()
        for m in self.members:
            if m.id in seen:
                raise KitRefused(f"{self.id}: two members are called {m.id!r}")
            seen.add(m.id)
        for m in self.members:
            if m.parent is not None and m.parent not in seen:
                raise KitRefused(f"{self.id}: {m.id} sits under {m.parent!r}, which is not in this kit")
            if m.parent == m.id:
                raise KitRefused(f"{self.id}: {m.id} cannot be its own parent")

    def member(self, member_id: str) -> Member:
        for m in self.members:
            if m.id == member_id:
                return m
        raise KeyError(member_id)

    def children(self, member_id: str) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.parent == member_id)

    def roots(self) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.parent is None)


# --- the kits the owner has named ------------------------------------------------------------------
#
# analog: the looks of things made by hand, on a surface, with a medium. the owner named three and
# said more are coming; they go here as one line each.
#
# textile: made by thread. "subtypes" is the owner's word: cross stitch and woven are kinds of
# textile, not looks laid over one, so they are subtype members under a textile style.
#
# handdrawn: the owner asked (2026-11-13) for a kit beside analog, "pencil sketch, doodle, scribbled,
# etc." the line between the two is the mark, not the hand: analog is what a press or a hot tool leaves
# (carved, screened, burnt), handdrawn is what a tool leaves when a hand drags it across the surface.
# so pencil and ballpoint belong here and linocut does not, even though a hand cut the lino.

ANALOG = Kit(
    id="analog",
    label="analog",
    blurb="the look of something made by hand, on a surface, with a medium",
    members=(
        Member("cyanotype", "cyanotype", blurb="prussian blue sun prints, the white of the object left where light was blocked"),
        Member("linocut-stamp", "linocut stamps", blurb="carved block, flat ink, the rough edge a gouge leaves"),
        Member("wax-seal", "wax seals", blurb="pressed wax with a raised emblem and a ragged pool around it"),
        Member("blockprint", "block printing", blurb="carved block pressed in ink, repeat motifs with slight misregistration and uneven coverage"),
        Member("screenprint", "screen print", blurb="flat layered ink pushed through a mesh, hard colour edges and overprint where layers cross"),
        Member("risograph", "risograph", blurb="spot-colour duplicator ink, grainy fills, soft misregistration, and colours that mix where they overlap"),
        Member("lithograph", "lithograph", blurb="drawn on stone with greasy crayon, soft tonal grain and a printed-from-a-plate depth"),
        Member("woodblock", "woodblock", blurb="cut along the grain, flat colour areas with wood texture showing through the ink"),
        Member("etching", "etching", blurb="lines bitten into metal, fine cross-hatching and a plate mark pressed into the paper"),
    ),
)

HANDDRAWN = Kit(
    id="handdrawn",
    label="handdrawn",
    blurb="the look of a line a hand dragged across a surface, wobbly and human",
    members=(
        Member("pencil-sketch", "pencil sketch", blurb="graphite on tooth, grey line that lightens where the hand lifted, and a smudge where it rested", look="look.pencil-sketch"),
        Member("doodle", "doodle", blurb="line with no plan: shapes that fill a margin, looping, going over their own edges", look="look.doodle"),
        Member("scribble", "scribbled", blurb="the pencil never lifted, so the marks cross and darken where they pile up", look="look.scribble"),
        Member("ballpoint", "ballpoint", blurb="a thin blue-black line with the skip and blob of a cheap pen running dry", look="look.ballpoint"),
        Member("ink-pen", "ink pen", blurb="confident ink line that swells on the downstroke and pools where the nib stopped", look="look.ink-pen"),
        Member("charcoal", "charcoal", blurb="soft black dust, broad strokes, white of the paper coming through the grain", look="look.charcoal"),
        Member("crayon", "crayon", blurb="waxy pigment that skips the tooth and leaves a broken edge on every stroke", look="look.crayon"),
        Member("marker", "marker", blurb="flat felt-tip colour that overlaps into a darker band and bleeds past the line", look="look.marker"),
    ),
)

TEXTILE = Kit(
    id="textile",
    label="textile",
    blurb="images made of thread: counted, woven, or stitched",
    members=(
        Member("textile", "textile", blurb="the thread itself: fibre, weave, the grain of cloth"),
        Member("cross-stitch", "cross stitch", kind="subtype", parent="textile",
               blurb="counted x stitches on a grid, every pixel a stitch"),
        Member("woven", "woven", kind="subtype", parent="textile",
               blurb="warp and weft, a pattern that exists only where threads cross"),
    ),
)

#
# paint: the owner's point (2026-11-14), from vectary's own picker: the styles worth taking are already
# there, watercolour among them. this is the kit the empty `medium` slot was holding a place for: analog
# is what a press or a hot tool leaves, handdrawn is what a tool leaves when a hand drags it, and paint is
# what a wet medium does to itself after the hand has gone (pooling, blooming, the dried rim of a wash).
# so the line is the solvent, not the brush.

PAINT = Kit(
    id="paint",
    label="paint",
    blurb="the look of a wet medium left to do what it does: pool, bloom, and dry at the edge",
    members=(
        Member("watercolour", "watercolour", blurb="transparent washes on damp paper, a hard dried rim where each one stopped, granulation in the hollows of the tooth", look="look.watercolour"),
        Member("gouache", "gouache", blurb="opaque matte colour in flat shapes, chalky bloom, one shape laid over another because the paint covers", look="look.gouache"),
        Member("ink-wash", "ink wash", blurb="one pigment diluted into greys, pooled darker where the brush rested, wet bleeds carrying the edges soft", look="look.ink-wash"),
        Member("oil-paint", "oil paint", blurb="loaded bristle ridges catching the light, colour mixed wet into itself, canvas weave through the thin passages", look="look.oil-paint"),
    ),
)

KITS: dict[str, Kit] = {k.id: k for k in (ANALOG, HANDDRAWN, PAINT, TEXTILE)}


def get(kit_id: str) -> Kit:
    try:
        return KITS[kit_id]
    except KeyError:
        raise KitRefused(f"{kit_id!r} is not a kit. the kits are {', '.join(KITS)}") from None


# --- where a member really stands ----------------------------------------------------------------------

def state_of(member: Member, styles: dict | None = None, presets: dict | None = None) -> str:
    """`listed` unless something real stands behind the member.

    a style member is as far along as the style it names: styles.py owns that lifecycle, and this
    reads it and decides nothing. a preset member is `ready` only if the preset exists. a member that
    names nothing is `listed`, and so is one whose style or preset is missing, because a name with
    nothing behind it must not be offered as something that runs.
    """
    if member.kind == "preset":
        return "ready" if presets is not None and member.preset in presets else "listed"
    if member.style is None:
        return "listed"
    style = (styles or {}).get(member.style)
    if style is None:
        return "listed"
    # styles.py has seven states; a kit shows four. everything before training is a corpus, and a
    # style that was refused or failed is not offered, so it reads as listed again
    return {"corpus": "corpus", "gated": "corpus", "training": "training", "validating": "training",
            "ready": "ready"}.get(style.state, "listed")


def runnable(member: Member, styles: dict | None = None, presets: dict | None = None) -> bool:
    return state_of(member, styles, presets) == "ready"


def menu(styles: dict | None = None, presets: dict | None = None, looks: dict | None = None) -> dict:
    """the kits as the page draws them. nothing here is invented: every state comes from state_of."""
    out = []
    for kit in KITS.values():
        def row(m: Member) -> dict:
            state = state_of(m, styles, presets)
            return {"id": m.id, "label": m.label, "kind": m.kind, "blurb": m.blurb, "parent": m.parent,
                    "preset": m.preset, "state": state, "runnable": state == "ready",
                    # a look is wording, so say which and whether it is actually in the catalogue; a
                    # member naming a look that is not there is the same lie as a preset that is not
                    "look": m.look, "worded": bool(m.look and looks and m.look in looks)}
        rows = [row(m) for m in kit.members]
        out.append({"id": kit.id, "label": kit.label, "blurb": kit.blurb, "members": rows,
                    "ready": sum(1 for r in rows if r["runnable"]), "total": len(rows)})
    return {"kits": out}
