# looks: making a kit member actually render something

A kit member is a name, a blurb and a state. That was deliberate (`docs/kits.md`): `listed` means
"named and nothing else", and the menu dims it rather than offering a card that fails. But it left the
handdrawn kit with eight names and no way to use any of them, and a style needs a corpus and a GPU
before it can help anyone.

A **look** is the answer for the members that need neither. It is a catalogue row that compiles, with no
model call and no cost, into the wording a prompt needs for one model family plus the settings that
belong with that wording. Eight of the ten shipped looks word the handdrawn kit; two more (`paper tooth`,
`photocopy`, `flat scan`) give the other two axes something real to hold, which is what makes a stack of
three possible at all.

```
looks/look.pencil-sketch.json      the row: slot, modes, fragments per family, settings
src/flowby/looks.py                the loader, the refusals, the compiler, the ejection
bin/flowby look <ids> --model ...  compile a brief
bin/flowby look <id> --eject       the two steps a board would hold
```

## where the rules came from

Read on 2026-11-13 in `nodetool-ai/nodetool`, `packages/presets` (`schema.ts`, `stack.ts`,
`compile.ts`, `eject.ts`) and its docs page. It is the most complete published answer to how a style
actually reaches a model, and their answers were worth checking against rather than inventing. Nothing
is vendored: the rules are re-expressed in python over flowby's own wire types.

What was taken:

- **`<kind>.<slug>` ids**, a declared `slot`, `modes`, `stackable`, an explicit `conflicts` list, and one
  prompt fragment **per model family with a required `default`**. The required default is the important
  one: without it, a model whose family nobody anticipated compiles to nothing and bills for it.
- **At most three, one per slot**, refused by the picker and by the compiler with the same sentence, so
  a card never looks available and then fails.
- **A family fragment falling back to `default` with a warning**, because "we used the generic words" is
  something a person should see before blaming the look for a render.
- **Settings merged per family**, keys the mode does not forward dropped with a warning, and two looks
  that disagree about one setting failing the compile by name rather than the later one silently winning.
- **Ejection**: a look does not stay a hidden suffix. It opens as steps a person can edit. nodetool ejects
  prompt input → text template → generator → output; flowby already has that template node
  (`text.compose`), so `eject()` returns the direction tagged for it and the generator's settings beside
  it. That is the difference between a style you can tune and a style you can only pick.

What was flowby's own:

- **The slots.** nodetool's slots are video grammar: move, rig, speed, stock, grade, lighting, era, ramp.
  A mark on paper is not a camera. The three here are `mark` (how the line was made), `surface` (what it
  was made on) and `finish` (what happened to it after), plus an unused `medium` for the analog kit. The
  axes are orthogonal on purpose: a stack of three says something none of the three says alone, and two
  marks cannot stack because "crayon and charcoal" is a request to shade one picture two ways.
- **Commas, not spaces.** Their fragments are sentences meant to run on after a shot description. These
  are directions stacked in front of a subject and joined with commas, which is what stops "paper tooth"
  and "pencil sketch" reading as one phrase.
- **A conflict check across slots**, because the slot rule cannot express it: `photocopy` is a finish and
  `pencil sketch` is a mark, so only the explicit list can say that photocopying a light graphite drawing
  loses it.
- **The catalogue validates as a set**, not row by row. A conflict naming a look that does not exist is a
  lie the picker would then have to explain, and only the whole folder can see it.

## what a compile is

```
$ bin/flowby look look.pencil-sketch look.paper-tooth --model sdxl-turbo --prompt "a fox in a coat"
cold press watercolour paper texture, coarse grain, deckled edge, paper surface, pencil sketch,
graphite on paper, hatching for shadow, paper tooth, sketchy contour lines, monochrome, high detail,
a fox in a coat

applied: look.pencil-sketch, look.paper-tooth
settings: nothing the look itself sets
```

The subject comes last because the directions are prefixes: the first look named ends up closest to the
subject, the last wraps furthest out. The alternative worth knowing about is `replace`, a fragment that
drops the prompt built so far, for a look that has to own the whole instruction; no shipped look uses it.

A compile returns the wording, the settings, the ids that made it and everything it had to leave unsaid.
The warnings are the interesting part:

- `a-model-from-next-year is not a model with a family here, so every look used its default wording`
- `look.photocopy sets strength, which image does not forward`
- `look.bare has no flux fragment, so its default wording was used`

## the refusals

Every one of these is a sentence a panel can print, and every one is tested with the message asserted, so
a refusal cannot quietly become a different refusal:

| asked for | refused because |
| --- | --- |
| `pencil-sketch` + `charcoal` | both set the mark, so one has to go |
| `pencil-sketch` + `photocopy` | listed as conflicting directions |
| four looks | a brief holds at most 3 |
| `marker` twice | marker is already in the brief |
| `marker --mode video` | marker does not run in video; it runs in image, image_edit |
| two looks setting `guidance` differently | guidance is set to 3.0 by look.a and to 8.0 by look.b |

## a look on the board

`looks.place(scene, ident, preset=, mode=)` puts a look where it can be used: it compiles the look for
the model the preset actually names, then adds a **text node holding the direction** and applies the
preset that reads text. The direction goes into the text node rather than a hidden prompt field because
that node is the thing a person edits afterwards, and adding their subject to it is the same gesture as
typing.

Three answers worth knowing:

- **the settings become sliders.** A compiled look speaks in node params (`steps`, `guidance`); a panel
  speaks in slider names (`detail`, `fidelity`). `settings_as_sliders` reads the mapping off the preset's
  own sliders, so it cannot invent a control the panel does not draw. A setting with no slider is dropped
  **out loud**, named in `warnings`, rather than silently.
- **an unknown model is not a failure.** `model_for` returns `""` when no step names a model this tree
  knows; the look then compiles with its required default fragment and says so in `warnings`. Guessing a
  family would tune words for a model nothing runs.
- **placing is not running.** Nothing is generated. The board gets a text node and a preset's nodes, and
  `docs/looks.md` says that in the same breath as the button's label, which is `place`, not `run`.

Reachable three ways: `bin/flowby place look.crayon --preset text-to-image`, `POST /api/looks/place`
`{look, preset?, mode?}` returning the whole board, and the kits menu, where only a `worded` member has a
button at all.

## what is not built

- **No picker.** `looks.shelf()` groups the catalogue by slot with each look's families, settings and
  conflicts, which is exactly what a picker draws, and `GET /api/looks` serves it, but the board has no
  slot-by-slot panel for it yet: placing is reached from the kits menu, not from a look's own page.
- **No pin.** A placed look records its preset and values, but a board placement does not hold a recipe
  version, so improving a look can still change a board that used it.
- **`medium` is empty.** No analog look exists; the analog kit's nine members are still `listed`.
- **Two families.** `flux` (dev, schnell) and `sdxl` (turbo) are the families flowby's presets actually
  run on. A third model means a third fragment per look, which is the cost of the design and the reason
  `default` is mandatory.
- **Motion looks.** A look words a still. A moving picture's direction is a different grammar and no
  preset here declares the settings one would need, so `modes` stops at image and image_edit.
