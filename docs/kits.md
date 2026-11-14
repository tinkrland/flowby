# kits

A kit collects; it builds nothing. The rules are in `src/flowby/kits.py`.

## handdrawn, and why it is not the same shelf as analog

The owner asked for a kit beside `analog` on 2026-11-13: "pencil sketch, doodle, scribbled, etc."

The split between the two kits is the mark, not the hand. `analog` is what a press or a hot tool leaves:
carved, screened, pressed, bitten. `handdrawn` is what a tool leaves when a hand drags it across the
surface: graphite that lightens where the hand lifted, a pencil that never lifted and so crossed its own
marks, ink that pooled where the nib stopped. A linocut was cut by hand and still belongs to `analog`,
because the look comes from the block and the press, not from the wobble of the line.

Eight members, all `listed`: pencil sketch, doodle, scribbled, ballpoint, ink pen, charcoal, crayon,
marker. `scribbled` is the owner's word and stays the label; the id is `scribble` so it can be written in
a url.

## paint: the kit the `medium` slot was holding a place for

The owner's point on 2026-11-14, with vectary's own preset picker in hand: the styles worth having are
already out there, watercolour among them, so take them rather than invent them.

`paint` is the fourth kit and the one that finally uses the `medium` slot. The line that separates it
from the other three is **the solvent, not the brush**: `analog` is what a press or a hot tool leaves,
`handdrawn` is what a tool leaves when a hand drags it, and `paint` is what a wet medium does to itself
after the hand has gone: pooled washes, a bloom where the water pushed the pigment, a hard dried rim where
a wash stopped, chalky bloom on opaque pigment, bristle ridges left standing.

Four members, all worded (`looks/look.watercolour.json` and its siblings):

| member | what it is |
| --- | --- |
| `watercolour` | transparent washes on damp paper, hard dried rims, granulation in the tooth |
| `gouache` | opaque matte flats, chalky bloom, one shape laid over another because the paint covers |
| `ink-wash` | one pigment diluted into greys, pooled darker where the brush rested, wet bleeds |
| `oil-paint` | impasto ridges catching the light, wet-in-wet mixing, canvas weave in the thin passages |

All four occupy `medium`, so two of them in one brief is refused by the slot rule, and the words say it
(`watercolour` and `gouache` cannot both be the medium of one picture). A paint composes with a `surface`
and a `finish`, which is why `watercolour + paper-tooth + flat-scan` is a legal stack of three and is the
example in the tests.
