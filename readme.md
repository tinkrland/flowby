# flowby

*one board, two views, and the graph was never hidden*

flowby is a creative studio built on a single claim: the spatial layer and the node layer are the same workspace seen twice. you click a sketch, a sidebar opens with presets written in the language of the thing you are making ("convert sketch to 3d mesh", "apply matte frosted glass"), you drag one slider, and the pixels change. underneath, a subgraph got spawned, wired and left visible. there is a toggle that shows it.

the reason to build this rather than another node editor is the order of the two views. most graph tools make you assemble a pipeline before you can see anything, which is a fine way to think and a terrible way to start. the reason to build it rather than another canvas tool is that a canvas with presets and no graph becomes a slot machine: you cannot see what ran, you cannot fix it, and you cannot take it with you. flowby is the wager that both halves are cheap if you are willing to say out loud that a preset **is** a graph.

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
bin/flowby sidebar sketch-1        what clicking that element opens
bin/flowby plan                    compile the board into an execution plan
bin/flowby plan --preset animate-composition --set duration=8
bin/flowby routes                  every route, its ceiling, its gates
bin/flowby fit --preset animate-composition
bin/flowby emit --preset sketch-to-mesh --out plan.json
bin/flowby doctor
```

the modules are the ideas. `dtypes.py` is the four wires and the refusal to add a fifth. `graph.py` is typed ports, cycles and topological order. `presets.py` is the subgraphs a slider stands in for. `scene.py` is elements on a board, which are nodes with a position, plus the chain and the recipe that chain reads back as. `compile.py` is the plan a shell script can run. `routes.py` is where it runs and what each place cannot do. `job.py` is a plan's life and its illegal moves. `hub.py` is the fan-out to the boards that are open.

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

the three products this sits between each open on a different first move, and that is not three products to flowby:

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
| `frosted-glass` | none: shading maths | red | red | refine | 2 | 3 |
| `animate-composition` | none: a camera and a render | red | blue | output | 3 | 3 |
| `style-transfer` | ip-adapter | green | green | explore | 2 | 2 |
| `relight` | ic-light | green | green | explore | 2 | 2 |
| `studio-light` | ic-light | green | green | refine | 2 | 2 |
| `surface-detail` | flux-depth-lora | red | red | refine | 3 | 2 |
| `code-container` | none: your own code | green | green | refine | 1 | 0 |

three things about that table are load bearing.

**presets chain, and the chain starts where the frame is now.** applying `sketch-to-mesh` to a sketch points the frame at the mesh node. applying `frosted-glass` next reads the mesh, not the sketch, so the material lands on the geometry and the original drawing is still a node behind it. nothing is destructive and nothing has to be re-imported.

**the sidebar only offers what can be applied now.** on a raw sketch, `frosted-glass` is not in the list, because it reads a red wire and the sketch is green. after the mesh exists, it is. this is the difference between a menu of everything and a next step.

**one click can come back with several results.** `relight` is a **sweep**: one photograph, six lighting setups, side by side, because that is what both reference products actually ship and it is the most useful thing on either page. the compiler treats it as a branch rather than a loop. the work before the swept node runs **once** and only the tail is copied, so six relights of one plate is one read and six renders, not six of everything. the cost says so: 0.3 minutes of shared work and 6.6 of gpu, and the plan carries eight steps, not twelve.

`scene.show_variant` picks one to keep looking at, and picking is a pointer rather than a re-run. every variant was produced, the artifact names carry the number (`sketch-1#1.png` through `#6`), and the frame that receives them gets one group instead of one image.

**some presets are not about one frame.** `studio-light` is a **board** preset: one lighting reference, graded onto every frame you point it at, so a board reads as one shoot instead of four unrelated renders. the head of its subgraph runs **once** and the tail lands per frame, which is why three frames cost one light read and three grades (0.6 + 3 × 0.9 minutes) and the pipeline view shows one wire fanning into three. their own benefits table calls this design dna matching; the mechanism is a shared node, not a copy of one.

that is the only place the two scopes differ. everything else about a board preset behaves like the rest of this tree: it chains off what each frame is showing, it refuses a frame on the wrong wire, and it can be broken apart into the same nodes.

**the catalogue is named after surfaces and runs models.** this was wrong here for a round, and the correction is the interesting part: crease, stitch, emboss and deboss are **diffusion passes**, not a carved edge. `surface-detail` is therefore a model painting a depth map from a sentence (`flux-depth-lora`) and then a geometry node applying it, and the choice arrives at the model as a prompt fragment rather than as a mode name.

that is the whole trick both products sell: *crease* is a word a designer already has, and behind it sits a model nobody had to choose between. the words are the interface, the models are the product. `presets.PROCEDURAL` is the written list of the three presets that genuinely need no model (shading maths, a camera move, your own code), so an absence of models is always a claim somebody made rather than something discovered later, and `bin/flowby presets` prints the model next to the name.

**one preset cannot fill its own inputs, and says so.** `style-transfer` needs a second asset, the look it copies. it spawns with an empty slot, refuses to compile while the slot is empty, and the refusal names the slot. filling it is `scene.link`, which is one drag in the node view.

## the recipe, which is the chain read back

a preset is one click. a chain of presets is a workflow, and a workflow worth running twice is worth naming. `scene.record(element)` returns the chain in the order it was built, with its values and its measured cost, and `scene.replay(element, recipe)` applies it to another frame in one call. nothing new is stored, because the chain was always the recipe: it can be read back instead of saved.

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
| the react binding | designed | no `node_modules` in this checkout |
| fastapi, celery, browserbase | designed | imports guarded, `python3 -m app.main` says so |

the distinction matters more than the count. a tree that says "designed" is one you can debug; a tree that says "done" is one you have to trust.

## what this tree does not do

it does not watch a video and figure out the choreography. it does not implement a single model call. it does not have a frontend you can load: `web/` holds the alignment maths (tested) and the react binding (not built). it does not persist a board to a database, so the cli works on a demo board it builds in memory.

the next three things, in the order they unblock the most: a frame that draws a mesh from a url, so the loop can be closed on someone else's gpu; a `text-to-image` worker that calls a real model, because that is the cheapest one to prove; and a second board, because every board so far has been a fixture.
