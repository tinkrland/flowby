# actions: a node that is one file with its contract in the header

Read on 2026-11-13 from FLORA's own API (`flora_search_actions`, `flora_get_action` across 14 queries,
42 actions) and from Fuser's public pages. This page is what flowby takes from that, and what it
deliberately does not.

## what their catalog actually is

Every one of FLORA's 42 prebuilt actions is **a single file of code with a header of annotations**. No
plugin registry, no schema table, no separate panel definition. `flora_get_action` returns the file
itself, and the file declares its own node:

```python
# @flora-name: "Video Effect"
# @flora-description: "Apply a stylistic video effect: vignette, film grain, pixelate, …"
# @flora-inputs: [{ "name": "source", "type": "video" }]
# @flora-outputs: [{ "name": "effected", "type": "video" }]
# @flora-params: [
#   {"key": "effect", "label": "Effect", "type": "select", "default": "vignette",
#    "options": [{"label": "Film Grain", "value": "grain"}, …]},
#   {"key": "grainStrength", "label": "Grain Strength", "type": "number", "default": 18,
#    "min": 0, "max": 80, "step": 1,
#    "visibleIf": [{"key": "effect", "equals": "grain"}]}
# ]
input_info = get_input(0)
if input_info["type"] != "video":
    raise FloraUserError("Expected a video input")
strength = get_param("grainStrength", 18)
```

Four things that follow, and they are the whole design:

1. **The panel is derived, not described twice.** A slider exists because a param is declared. A slider
   appears only sometimes because of `visibleIf`. There is no way for the panel and the code to disagree,
   because there is one artefact.
2. **Params are typed with ranges and conditions**: `number` (with `min`, `max`, `step`), `select` (with
   labelled options), `nonScaledSlider` (flora's spell for "the value is a raw number, not a 0..1
   fraction"), plus a `visibleIf` that points at another param and one of its option values.
3. **The runtime is chosen by the work, not by the author's taste.** 19 actions are `python` and shell out
   to `ffmpeg` for files; 23 are `javascript` and carry a `-browser` suffix because they draw on a canvas
   or in a shader. Same contract, two places to run it.
4. **All 42 are `charged_cost: 0`.** Not cheap: free. The money in that product sits entirely in the model
   nodes. The utility layer (crop, resize, blur, colour grade, halftone-ish screens, frame grids, video
   geometry) is code, so it is instant and costs the user nothing, which is what makes a canvas feel
   responsive to rearrange rather than expensive to experiment on.

Their run contract, from the same files: `get_input(i)` hands back `{type, path}`, `get_param(key, default)`
reads a value, `FloraUserError` is how a bad input is reported to the user, and an action writes
`/tmp/output/<declared-output-name>.<ext>`. Outputs are declared by name, so a downstream node wires to a
name rather than a position.

## what Fuser does differently, and why it matters here

Fuser's Recipes are the same *idea* one level up: a selection of connected nodes becomes one node with
exposed Inputs and Outputs, and every instance is **pinned to a workflow version**, so improving a recipe
does not silently change work already placed. Running a recipe shows a credit estimate first, previous
runs are browsable with arrows, and `Reset inputs` restores saved starting values while *wired* inputs
keep taking their value from the canvas. Their Tools list (Risograph, Halftone, Datamosh, Y2K VHS look,
Line hatching) is Fuser's own creative-code family, verified on `fuser.studio/features/recipes`; FLORA's
catalog search returns no match for those five names, so the "Effects & looks" menu is most likely
Fuser's. Worth saying plainly, because it means the five effects are *code tools with one-line promises*,
not techniques FLORA built.

## what flowby has now

`src/flowby/actions.py` reads a header and nothing else. It accepts `@flowby-` and `@flora-` prefixes, so
a FLORA action file parses here unchanged, and it refuses rather than warns when the description lies:

| the description lies by | the refusal |
| --- | --- |
| no `@flowby-name` | an action with no name cannot be listed |
| an unknown header key (`@flowby-descriptio`) | names the typo, because a silent skip means a blank blurb forever |
| an unknown runtime | flowby runs `python` or `javascript` |
| a wire it does not have (`audio`) | names the four wires it does have |
| the same port or param twice | names it |
| a default outside its own range | the action's own bug, caught at parse |
| a select with no options, or a default not offered | names the options |
| `visibleIf` pointing at a param that does not exist, at a value that never occurs, or at a continuous number | refused: a page would have to reimplement the comparison to draw it |

`controls()` returns **every** param in header order with a `shown` flag rather than only the visible
ones. Dropping hidden controls would leave a panel unable to draw them when the choice changes, and would
move the visibility rule into the page. `values()` is the only place a value from a page is believed:
ranges, choices and unknown keys are all refused there. `estimate()` answers `0.0` and says why:
`python code, not a model`.

`run()` is the seam the kernel worker will use: it checks every declared input is present, calls the
file's own `run(inputs, values, out_dir)`, then checks the answer against the declared outputs. A module
with no `run`, a returned dict missing a declared output, a returned output that was never declared, and
a path that does not exist are each refused with the name in the sentence.

`bin/flowby actions` lists the shelf; `bin/flowby action Risograph --values '{"inks":"one"}'` prints the
panel a page would draw, with `Second ink` and `Misregistration` marked hidden.

## the shelf, so far

Two real actions, both runnable today, both written here rather than copied (`actions/`):

- **Halftone** (`image → image`): cell size 3..24 px, screen angle 0/15/45/75, ink black/blue/red. Rotate
  the screen off the pixel grid, take each cell's *mean* (a corner sample aliases stripes into dots), grow
  a dot by darkness, rotate back, print the ink through the mask.
- **Risograph** (`image → image`): one or two inks, misregistration 0..12 px, ink coverage 0.2..0.9. The
  second plate and its shift are only offered when `inks` is `two`, which is the `visibleIf` rule doing
  real work in a real file.

Both are deterministic, need no model, and cost nothing. `docs/../out/actions-demo/` holds a source /
halftone / risograph strip made by running them.

## what is not built

- **A runner that writes into the board.** `Action.run` works, but no board action calls it yet, and the
  kernel worker still walks flowby's own plan steps rather than action files.
- **JavaScript actions.** The contract accepts `runtime: javascript` and refuses any other, but nothing
  executes one; the browser side would be a canvas or WebGL runner in `web/`.
- **`text` params in the panel.** The parser produces them; the panel draws numbers and choices only.
- **Version pinning.** Fuser's best idea, and the one flowby has no equivalent for: a placed action or
  preset should pin the version it was placed at, so improving it does not silently change old boards.
  That belongs with `runs.py`, which already files a run under the inputs it came from.
