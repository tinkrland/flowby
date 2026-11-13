# flowby - a computational creative's craftbox

<p align="center">
<img width="20%" height="20%" alt="image" src="https://github.com/user-attachments/assets/448996ed-d9b1-4949-afd8-9fd9f0b2bad5" />
</p>

*one board, two views, and the graph was never hidden*

flowby is a creative studio built on a single claim: the spatial layer and the node layer are the same workspace seen twice. you click a sketch, a sidebar opens with presets written in the language of the thing you are making ("convert sketch to 3d mesh", "apply matte frosted glass"), you drag one slider, and the pixels change. underneath, a subgraph got spawned, wired and left visible. there is a toggle that shows it.

the reason to build this rather than another node editor is the order of the two views. most graph tools make you assemble a pipeline before you can see anything, which is a fine way to think and a terrible way to start. the reason to build it rather than another canvas tool is that a canvas with presets and no graph becomes a slot machine: you cannot see what ran, you cannot fix it, and you cannot take it with you. flowby is the wager that both halves are cheap if you are willing to say out loud that a preset **is** a graph.

nothing here is a clone. the pieces were assembled one at a time, each for a reason that is written down
in [inspiration](#inspiration-and-what-was-taken-from-each) below, and the seam that holds them together is
the part there was nothing to copy from.

## inspiration, and what was taken from each

flowby sits between five products and is none of them. calling it a clone gets the interesting part
backwards: a clone copies what a product looks like, and this tree took a piece from one place, a
refusal from another, and had to invent the joint between them. so each project is listed once, with
what is genuinely wrong with it, and the last column is the honest one.

a library is a dependency and is listed further down. a product is an idea, and these are the ideas.

| project | what it is, and what is wrong with it | what flowby took |
| --- | --- | --- |
| **comfyui** | *too bare.* the graph and nothing else: every job is assembled node by node before anything appears, so the first hour goes on building a pipeline you cannot yet see. | the graph as the real artifact rather than an export format, and ports that carry a declared type, because a value that says what it carries refuses most wrong wires before you finish dragging. left behind: the empty canvas as the front door. |
| **fuser.studio** | a node canvas with recipes: box-select some nodes, collapse them into a form, and a teammate uses the result without ever meeting the graph. | the task-named front door; **focus mode** and its single action; the **selection pill**, including the price of the selection sitting inside it; and the calm chrome (a zoom readout, unlabelled wires, one accent). left behind: the pale palette, since this is dark only. |
| **flora.com** | *entirely freeform, cloud only, models behind a subscription.* the typed sentence is a node, and a refinement is the same box typed into again. | the freeform instinct: typing is a node rather than a settings form, and a refinement is a continuation of the same sentence, not a new job. left behind: the cloud floor and the subscription models. this tree plans for a free colab runtime and a gpu you plug in yourself. |
| **vectary.com/canvas** | *subscription again, and locked in.* presets on a canvas: press a card, get a result, and stay subscribed to keep looking at it. | the preset card as the **fixed** door; one application reaching many frames, which their own page calls design dna matching; and models hidden behind a task name. left behind: the lock-in. a preset here is a subgraph you can open, so pressing it is never a wall. |
| **base44 studio** *(described, not inspected)* | bring a reference, then carry it across more than one frame. | the third door: a style that follows a board rather than a single frame. recorded as a gap because it is one: there is no session there, so `docs/research.md` keeps it as described rather than looked at. |

what is not in that table is the seam, which is the reason to do the assembly at all: **two views of
one graph**, a preset that is a subgraph left visible where a person can find it, and a compiler that
refuses a plan rather than guessing at it. those were not taken from anywhere.

## the one decision everything else follows from

a preset is not a macro that hides nodes. it is a small graph that gets spawned, wired, and left where an advanced user can find it. what the spatial layer shows is a projection of that graph:

| what you see | what it is |
| --- | --- |
| the frame you drag | a node with a position |
| the preset you click | a subgraph, wired from what that frame is currently showing |
| the slider you drag | one parameter on one node inside it, rescaled into human units |
| the wire colour | the only thing that changes what can connect to what |

that projection is the whole architecture. it means there is one truth and no synchronisation problem, it means "break this preset apart" is a bookkeeping operation rather than a rewrite, and it means the compile step is a flattening rather than an interpretation.

## what runs here

`bin/flowby` is the whole surface, and it is a shim over `python3 -m flowby.cli` so the modules are the thing you can read.

```
bin/flowby modes                   the three doors in, and the crossing out of each
bin/flowby presets                 the menu, with each preset's honest state
bin/flowby legend                  the four wires, and the roles that ride them
bin/flowby demo                    build a board, print both views and every wire
bin/flowby graph                   the node layer for the browser, with no geometry in it
bin/flowby sidebar sketch-1        what clicking that element opens
bin/flowby plan                    compile the board into an execution plan
bin/flowby plan --preset animate-composition --set duration=8
bin/flowby routes                  every route, its ceiling, its gates
bin/flowby fit --preset animate-composition
bin/flowby emit --preset sketch-to-mesh --out plan.json
bin/flowby inspector               the contextual panel's payload, one entry per node
bin/flowby runs                    per-node history, and what a run would execute now
bin/flowby run sketch-1 --all      file the whole board, then watch everything become reusable
bin/flowby kohya docs/style-example.json --write out/kohya-run
bin/flowby doctor
```

the modules are the ideas. `dtypes.py` is the four wires and the refusal to add a fifth. `graph.py` is typed ports, cycles and topological order. `presets.py` is the subgraphs a slider stands in for. `scene.py` is elements on a board, which are nodes with a position, plus the chain and the recipe that chain reads back as. `compile.py` is the plan a shell script can run. `routes.py` is where it runs and what each place cannot do. `job.py` is a plan's life and its illegal moves. `hub.py` is the fan-out to the boards that are open.

## in-house vocabulary

seven kinds are named in `theidea/taxonomy.md` and they form a ladder: style, tool, technique,
preset, recipe, workflow, factory, each built only from the rungs below it. of those, a **preset** is
an object (`presets.Preset`) and a **recipe** is the dict `scene.record` returns; a **technique** is
inlined in each preset for now, and **style**, **workflow** and **factory** are not built.

the words below are the ones actually used in the code and in `bin/flowby`. where a common word is
deliberately **not** used, the table says so rather than smoothing it over, because two names for one
thing is how a tool starts lying about what it does.

| word | what it means here | what it is *not* |
| --- | --- | --- |
| **preset** | a task card: one input, one job, sliders, sometimes a sweep. pressing it spawns a subgraph and leaves it on the board. | not a macro that hides nodes, and not a saved file. it is generated from what the frame is showing when you press it, which is why it chains instead of overwriting. |
| **kit** | a shelf that collects the members of one craft: `analog` (cyanotype, linocut stamps, wax seals, block printing, screen print, risograph, lithograph, woodblock, etching), `handdrawn` (pencil sketch, doodle, scribbled, ballpoint, ink pen, charcoal, crayon, marker) and `textile` (the thread itself, with cross stitch and woven as subtypes under it). it builds nothing and trains nothing. | not a rung on the ladder. a listed member is a name and nothing else, and the menu prints `listed, not built yet` rather than looking pressable. |
| **style** | trained weights, a trigger and a default strength: a look a preset takes as an input. | not a preset. it has no job of its own, and it is the only kind whose work is training rather than a node. |
| **technique** | tools in a known order, plus the reason for that order. | not a preset: no input slot, so there is nothing to point it at. |
| **recipe** | the chain read back. `scene.record` returns a chain with its values and its measured cost, and `scene.replay` applies it to another frame in one call. | not a second thing to store. the chain was always the recipe, which is why nothing new is written when one is recorded. |
| **template** | a word this tree does **not** use. what other tools call a template is a **preset** here (one input, one job) or a **recipe** (its own inputs and outputs). | not a synonym for either. one word spanning two rungs is exactly the blur this list exists to prevent. |
| **sweep** | one click that comes back with several variants. the work before the swept node runs once and only the tail is copied, so six relights of one plate is one read and six renders. | not a loop, and not six runs of everything. the compiler treats it as a branch, and the cost line shows the difference. |
| **slot** | an empty input a preset refuses to compile without: `style-transfer` needs the look it copies, `place-graphic` needs the graphic. | not an error state. it is a preset admitting it cannot fill its own inputs, and the refusal names the slot. |
| **board preset** | a preset whose tail lands on every frame it is pointed at while its head runs once (`studio-light`), so three frames cost one light read and three grades: 0.6 + 3 x 0.9 minutes. | not a separate mechanism. same preset, wider scope, and it breaks apart like any other. |
| **control** | a slider on a preset. `roughness intensity`, `metalness intensity`, `opacity control` and `emission maps` are four sliders on one node, not four jobs. | not a preset. the brief's 29 bullets became 16 presets and 16 controls, because a menu of twenty-nine model calls is a worse sidebar. |
| **plug** | a gpu you rent, added with an endpoint and a token. the token goes in and never comes back out. | not connected because it was typed in. it reads `connected` only after a health check answers, and private or metadata addresses are refused. |
| **route** | where a plan runs, and what that place honestly cannot do: `local`, `colab-browserbase`, `runpod-serverless`, `replicate`. | not a preference. `routes.fit` refuses a plan that will not survive the place it was going, before a browser is opened. |
| **door** | freeform, fixed, style: the three first moves. | not three products. every door reaches every other, and `tests/selftest.py` performs each crossing. |
| **factory** | a workflow plus a trigger, a queue, a budget and a reviewer. | not built, and deliberately last: no human in the loop is a cost decision before it is a feature. |

## the four wires, and the fifth thing that does not get a colour

| wire | colour | carried |
| --- | --- | --- |
| `text` | amber | a prompt, a caption, a parameter said out loud |
| `image` | green | a still: pixels, a render, a mask, a depth map |
| `video` | blue | ordered stills with time attached |
| `mesh` | red | vertices, faces, materials, a scene graph |

control channels (depth, mask, pose, palette, style) are **roles on green**, not a fifth and sixth colour. a depth map and a portrait are both images, and an eye that has to learn six colours stops using colour at all.

the other half of the palette is the refusal: **nothing coerces**. an image does not become a mesh by being plugged into a mesh port. it becomes a mesh by passing through a node that says so, which is why `animate-composition` contains a `render.frames` node with a red input and a blue output. a conversion you can see is a conversion you can undo.

## three doors into one graph

the three instincts in the table above each open on a different first move, and none of them is a separate product here:

* **freeform** (fuser's instinct): you type, and the typing is a node. `bin/flowby demo` starts this way, an amber text element wired into a model.
* **fixed** (vectary's instinct): you press a card, and the card is a subgraph you can open.
* **style** (base44 studio's instinct): you bring a reference, and then carry it across more than one frame.

`bin/flowby modes` prints all three, and the claim it exists to defend is the last line: **every door reaches every other**. freeform stops being freeform the moment you apply a preset, and the words you typed are still a node you can rewire rather than a setting you have lost. a fixed preset is left for the graph underneath the first time you point a frame at an intermediate node. a carried style is still a node, so it can be narrowed to one frame or taken apart.

those crossings are not promises in prose. `tests/selftest.py` performs each one on a real board, because a mode you cannot leave is a product and not a mode.

one honest gap: the style door is modelled from a description of base44's studio, not from the product. my browser has no session there, so `docs/research.md` records it as described rather than inspected.

## the presets

every preset below is task-named, because the unit a person thinks in is the task and not the model. every one is in state `designed`: the graphs wire and refuse correctly, and **no asset has come back from a worker yet**.

| preset | model | reads | writes | stage | nodes | controls |
| --- | --- | --- | --- | --- | --- | --- |
| `text-to-image` | sdxl-turbo | amber | green | explore | 2 | 3 |
| `sketch-to-mesh` | triposr | green | red | explore | 3 | 3 |
| `frosted-glass` | none: shading maths on a material | red | red | refine | 2 | 3 |
| `animate-composition` | none: a camera move and a render | red | blue | output | 3 | 3 |
| `style-transfer` | ip-adapter | green | green | explore | 2 | 2 |
| `code-container` | none: your own code | green | green | refine | 1 | 0 |
| `relight` | ic-light | green | green | explore | 2 | 2 |
| `studio-light` | ic-light | green | green | refine | 2 | 5 |
| `surface-detail` | flux-depth-lora | red | red | refine | 3 | 2 |
| `extract-material` | material-estimator, sam-segment | green | green | explore | 2 | 2 |
| `apply-material` | pbr-painter | red | red | refine | 2 | 2 |
| `texture-maps` | pbr-gen | red | green | output | 3 | 6 |
| `environment` | ic-light | red | red | refine | 2 | 4 |
| `layers-to-3d` | depth-anything, layer-lift | green | red | explore | 2 | 2 |
| `sketch-to-render` | controlnet-scribble, sdxl-turbo | green | green | refine | 2 | 3 |
| `3d-text` | none: extrusion and bevelling is geometry maths | amber | red | explore | 2 | 3 |
| `handwriting-to-font` | none: image maths in the browser; delivers a font bundle, not a wire | green | amber | refine | 2 | 5 |
| `swatch-swap` | none: counting colours and blending pixels, in the browser | green | green | refine | 1 | 2 |
| `palette-9` | none: the same quantiser, answering with nine colours | green | amber | explore | 1 | 1 |
| `view-ortho` | none: trimesh, a camera and a projection | red | green | output | 1 | 1 |
| `replace-object` | flux-fill, sam-segment | green | green | refine | 2 | 3 |
| `place-graphic` | pbr-painter | red | red | refine | 2 | 3 |
| `clear-interior` | flux-fill, sam-segment | green | green | refine | 2 | 3 |
| `cut-out` | birefnet | green | green | output | 1 | 2 |
| `swap-background` | birefnet, ic-light | green | green | refine | 2 | 2 |
| `extract-pose` | dwpose | green | green | explore | 1 | 1 |
| `inpaint` | flux-fill | green | green | refine | 1 | 2 |

three things about that table are load bearing.

**presets chain, and the chain starts where the frame is now.** applying `sketch-to-mesh` to a sketch points the frame at the mesh node. applying `frosted-glass` next reads the mesh, not the sketch, so the material lands on the geometry and the original drawing is still a node behind it. nothing is destructive and nothing has to be re-imported.

**the sidebar only offers what can be applied now.** on a raw sketch, `frosted-glass` is not in the list, because it reads a red wire and the sketch is green. after the mesh exists, it is. this is the difference between a menu of everything and a next step.

**one click can come back with several results.** `relight` is a **sweep**: one photograph, six lighting setups, side by side, because that is what both reference products actually ship and it is the most useful thing on either page. the compiler treats it as a branch rather than a loop. the work before the swept node runs **once** and only the tail is copied, so six relights of one plate is one read and six renders, not six of everything. the cost says so: 0.3 minutes of shared work and 6.6 of gpu, and the plan carries eight steps, not twelve.

`scene.show_variant` picks one to keep looking at, and picking is a pointer rather than a re-run. every variant was produced, the artifact names carry the number (`sketch-1#1.png` through `#6`), and the frame that receives them gets one group instead of one image.

**some presets are not about one frame.** `studio-light` is a **board** preset: one lighting reference, graded onto every frame you point it at, so a board reads as one shoot instead of four unrelated renders. the head of its subgraph runs **once** and the tail lands per frame, which is why three frames cost one light read and three grades (0.6 + 3 × 0.9 minutes) and the pipeline view shows one wire fanning into three. their own benefits table calls this design dna matching; the mechanism is a shared node, not a copy of one.

that is the only place the two scopes differ. everything else about a board preset behaves like the rest of this tree: it chains off what each frame is showing, it refuses a frame on the wrong wire, and it can be broken apart into the same nodes.

**the catalogue is named after surfaces and runs models.** this was wrong here for a round, and the correction is the interesting part: crease, stitch, emboss and deboss are **diffusion passes**, not a carved edge. `surface-detail` is therefore a model painting a depth map from a sentence (`flux-depth-lora`) and then a geometry node applying it, and the choice arrives at the model as a prompt fragment rather than as a mode name.

that is the whole trick two of the projects above sell: *crease* is a word a designer already has, and behind it sits a model nobody had to choose between. the words are the interface, the models are the product. `presets.PROCEDURAL` is the written list of the five presets that genuinely need no model (shading maths, a camera move, your own code, extruding a font, and tracing a scan into a font), so an absence of models is always a claim somebody made rather than something discovered later, and `bin/flowby presets` prints the model next to the name.

**one preset cannot fill its own inputs, and says so.** `style-transfer` needs a second asset, the look it copies. it spawns with an empty slot, refuses to compile while the slot is empty, and the refusal names the slot. filling it is `scene.link`, which is one drag in the node view.

## the brief, and what it became

the owner's tool list is in the tree as data, not as prose: `catalogue.py`. it is four levels deep and flowby is three, and the difference is the product decision worth stating.

**29 bullets became 16 presets and 16 controls.** a *group* is a sidebar section, a *tool* is a preset, and a *control* inside a tool is a slider on that preset rather than a preset of its own. so `roughness intensity`, `metalness intensity`, `opacity control` and `emission maps` are four bullets and four sliders on one node of `texture-maps`, and `crease`, `stitch`, `emboss` and `deboss` are four bullets and four values of one choice on `surface-detail`. a menu of twenty-nine things that each cost a model call would be vectary with a worse sidebar.

`bin/flowby catalogue` prints the whole mapping, and it exits non-zero if a bullet resolves to nothing:

```
29 bullets -> 16 presets and 16 controls
presets the brief never names, and why: 7
every bullet resolves
```

those seven are declared in `catalogue.PRIMITIVES` with a reason each, because the brief assumes them without naming them: somewhere to put words, a red wire to dress, a material with no model, the motion its framing section stops short of, the escape hatch for your own code, one cheap relight, and style transfer before it reaches across a board. an absence is a claim somebody made, which is the same rule `presets.PROCEDURAL` applies to models.

two of the collapses are worth pulling out because they are where a catalogue usually lies:

* **explore material variations** is a **sweep**, so six finishes cost one unwrap and six paints. strip the subject and it would cost six of everything, which is what a menu does. the plan for a chair in six finishes is nine steps and seven artifacts, and the suite asserts the unwrap appears once.
* **geometric pattern mapping** is a control on `place-graphic`, not a preset, because a pattern is what a graphic does when it meets a surface rather than a separate job. `place-graphic` also carries a **slot** for the graphic, which makes it a two-asset preset like style transfer.

## the recipe, which is the chain read back

a preset is one click. a chain of presets is a workflow, and a workflow worth running twice is worth naming. `scene.record(element)` returns the chain in the order it was built, with its values and its measured cost, and `scene.replay(element, recipe)` applies it to another frame in one call. nothing new is stored, because the chain was always the recipe: it can be read back instead of saved.

## the two libraries it does not write itself

**@xyflow/react** (React Flow, MIT) draws the node layer and **@dagrejs/dagre** (MIT) decides where
nodes sit. this is deliberate: the interesting problem here is the seam between the two views, not
bezier maths and hit-testing. python stopped emitting pixel positions the day dagre arrived, because
two layout systems disagree by default and a node a person dragged was lost on the next render. the
graph now reports `rank` and `row`, and geometry has exactly one owner.

**motion** (Framer Motion, MIT) makes it move: nodes enter staggered by their depth in the graph,
wires draw themselves from source to target, and anything a pointer touches settles on a spring. the
numbers live in `web/src/anim.mjs` so they can be tested without a DOM, and `prefers-reduced-motion`
turns every one of them off rather than shortening them.

the seam is testable from node with no DOM, which is the point of `web/src/graph.mjs`: the browser's
palette is compared against `bin/flowby --json legend`, a wire into a port that does not exist
refuses by name, the layout is deterministic across runs, and no two nodes overlap.

the spatial canvas is the honest exception. **tldraw is source-available, not open source**: 2.x and
3.x are licensed for non-commercial use, and 4.x forbids production deployment without a licence key
and enforces it. so `tldraw@2.4.6` is on loan while this is a development project, and decision 11
in `theidea/decisions.md` lists the three ways out, including the contained swap to an MIT canvas,
because the coordinate contract lives in `align.mjs` behind a pure function with its own test.

## where it runs, and what each place honestly cannot do

the brief asks for a compute loop with no permanent gpu and no cloud floor: a browser drives a free colab runtime, `kernel/kernel.sh` builds the environment inside it, the gpu does the work, and the artifacts post home. that loop is here, and so are the four facts that decide whether it survives a job.

| route | gpu | ceiling | dies after | disk outlives it | cost |
| --- | --- | --- | --- | --- | --- |
| `local` | no | 24h | never | yes | free |
| `colab-browserbase` | yes | 12h | 90s of silence | no, drive only | free, in someone else's queue |
| `runpod-serverless` | yes | 4h | 30s of silence | with a paid volume | pennies per second |
| `replicate` | yes | 1h | never | no | per prediction |

those numbers are fields on the route, not prose, which is the point: `routes.fit` refuses a plan that will not survive the place it was going to run, and `compile` refuses before a browser is opened rather than at hour nine. `colab-browserbase` also carries `policy: contested`, and its note is the honest sentence: a session cookie is the credential, cookies expire on google's schedule, and the terms do not invite automation of the runtime. it is a prototype rail with a known ceiling. that is a reason to keep the seam clean, not a reason to pretend the seam is not there.

## what is verified, and what is only designed

| part | state | evidence |
| --- | --- | --- |
| wires, graph, presets, chaining, slots | verified | `tests/selftest.py` |
| the compiled plan, its cost, its refusals | verified | `tests/selftest.py` |
| the sweep: shared head, copied tail, one artifact per variant | verified | `tests/selftest.py` |
| board scope: one head reaching several frames | verified | `tests/selftest.py` |
| the route table and its refusals | verified | `tests/selftest.py` |
| job lifecycle, artifact checking, watchdog | verified | `tests/selftest.py` |
| `kernel.sh` parsing and dry run | verified | run as a subprocess |
| the worker's plumbing, with simulated bytes | verified | manifest digests are real |
| the worker's model calls | **not written** | `kernel/worker.py` names each op and refuses |
| the tldraw + r3f camera alignment | verified | `node --test web/tests/align.test.mjs` |
| the node canvas: palette, wires, layout, refusals | verified | `node --test web/tests/graph.test.mjs` |
| the node canvas actually drawing | verified | headless chrome: 7 nodes, 5 wires, 12 handles |
| the motion spec, including reduced motion | verified | `node --test web/tests/anim.test.mjs` |
| dark mode only, with no light theme to drift into | verified | `node --test web/tests/dark.test.mjs` |
| the spatial canvas being shippable | **licence** | tldraw is source-available, not open source; decision 11 |
| the web binding: canvas, command bar, kits menu, gpu plug | verified | `npm run build`, 276 tests in `web/tests`, and loaded in chrome against the real graph |
| the selection pill and its focus view | verified | `web/tests/selection.test.mjs`; pill measured at 313px on desktop and 303px inside a 390px phone, 50px clear of the toolbox |
| the kits menu showing each style's true state | verified | `web/tests/kitsmenu.test.mjs`, and opened in chrome at both widths |
| the gpu plug refusing private and metadata addresses | verified | `tests/plug_test.py`, plus the health check that is the only way it becomes connected |
| fastapi, celery, browserbase | designed | imports guarded, `python3 -m app.main` says so |

the distinction matters more than the count. a tree that says "designed" is one you can debug; a tree that says "done" is one you have to trust.

## what this tree does not do

it does not watch a video and figure out the choreography. it does not implement a single model call, so every preset is `designed` and no asset has come back from a worker. it does not persist a board to a database, so the cli works on a demo board it builds in memory. two things the page shows are drawn from board state that python does not hear about yet: duplicate and delete in the selection pill, and a placed node from the command bar (picking a row reports that placing it is the bridge, and the bridge is not built). there is no store for a preset made from a selection, which is why that row in the pill's `...` menu is listed and off.

the next three things, in the order they unblock the most: a frame that draws a mesh from a url, so the loop can be closed on someone else's gpu; a `text-to-image` worker that calls a real model, because that is the cheapest one to prove; and a second board, because every board so far has been a fixture.
