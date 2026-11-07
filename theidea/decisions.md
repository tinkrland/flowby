# decisions

*what this tree concluded from the brief, including the two places it pushed back*

## 1. a preset is a subgraph, not a macro

the brief says clicking a preset "implicitly spawns and links the necessary underlying nodes behind the scenes". the word that decides the whole architecture is *spawns*. a macro would run and hide; a spawn leaves the nodes there.

so `presets.py` holds templates, `scene.apply` instantiates them into the real graph with namespaced ids, and the sidebar is a projection of their exposed parameters. the consequences are all good and all free:

* there is no second source of truth, so the two views cannot disagree;
* "break apart a preset" is `scene.detach`, which clears one field and keeps every wire;
* a wire in the node view is the same object a slider moves, so an advanced user editing a parameter by hand and a designer dragging a slider are doing the same thing.

the cost is that a preset has to be honest about its own shape. it cannot be a black box with a prompt, because there is nowhere to hide one.

## 2. four colours, and control channels ride green

the brief names four wire colours: amber text, green image, blue video, red mesh. controlnet channels are not on that list, and the tempting fix is a fifth and sixth colour for depth and mask.

they ride **green** as a `role` instead. a depth map and a portrait are the same four numbers on the same kind of wire; what differs is what the receiving node expects to be true about them, and that belongs on the port, not in the palette. six colours is a legend nobody reads, and an unread legend means the node view stops being legible at a glance, which was the entire point of having one.

## 3. nothing coerces, so conversion is a node

the brief does not say what happens when a red wire meets a green port. the answer that keeps the graph trustworthy: **it is refused**, and the conversion is a node you can see.

`animate-composition` is the example the tree ships. it takes a mesh and produces a video, and it does that through `render.frames`, a node with a red input and a blue output. nothing about that node is special plumbing; it is just where the change of type is written down. the alternative, a rule that quietly casts a mesh to an image whenever a green port asks, is how node tools end up with a graph that no longer explains its own output.

## 4. presets chain off what a frame is currently showing

the brief says every visual asset behaves as an active node. the question that follows is which node a second preset reads.

the answer is the element's *current display*, not its original media. so a sketch becomes a mesh, and the material applied next lands on the mesh, and the drawing stays behind both of them as a node nobody deleted. this is the "dimensionally fluid" half of the brief made mechanical: applying `sketch-to-mesh` flips the element's plane from 2d to 3d, and the flip is recorded in the element's history because it is a decision a person made.

the corollary is the sidebar's rule: **only the presets that can be applied to the current state are offered.** a menu of everything is a menu that mostly refuses.

## 5. a preset can have a slot it cannot fill

`style-transfer` needs two images: the content, which is the frame you clicked, and the look, which is not on the board yet.

the brief does not cover this, and the lazy models are both wrong: making the second input optional produces a preset that silently does nothing useful, and refusing the preset entirely loses the flow. so a preset may declare a **slot**, spawn incomplete, and refuse to compile with a sentence that names it. filling the slot is one wire in the node view, or `scene.link`.

this is also what makes the two views equal rather than one being a beginner mode: the spatial layer cannot express "this needs a second asset" and the pipeline layer expresses it in a drag.

## 6. the chain is the recipe, so recipes are read rather than saved

fuser's recipes are a workflow packaged and re-run in one click, and they are the best idea in that product. the useful observation is that flowby already has the workflow: it is the ordered chain of preset instances on an element.

so `record` walks the chain and returns it, `replay` applies it somewhere else, and there is no recipe file format to version. the estimate comes along because each preset already declares what it costs. if recipes ever need to be shared, they are a json object the chain already produces.

## 7. where it runs is data, not prose

the brief's compute loop is a browser driving a colab runtime, and the honest problem with that loop is not that it is wrong, it is that it has four constraints that a job can violate silently: a twelve hour ceiling, a runtime reclaimed after ninety seconds of quiet, a disk that lives in someone else's drive, and terms that do not invite automation.

the tree puts all four on the route as fields. `routes.fit` refuses a plan that will not survive there, and `compile` refuses before a browser opens instead of at hour nine. colab stays the default for anything that needs a gpu, because it is the cheap one and the brief is explicitly about low-cost prototyping; it just cannot be the *only* rail, and the seam that moves a job elsewhere is a table entry rather than a refactor.

the two places this pushed back on the brief, stated plainly: cookies are a worse credential than an api key and will expire on someone else's schedule, so the colab driver is the only code that touches them; and the plan is flattened before it leaves the backend, so the worker never interprets a graph. the brief implies both. making them explicit is what lets the second rail be added without touching the first.

## 8. the plan is flat

the brief says the backend handles "mapping frontend geometric states into structured execution json scripts". the shape this tree chose is a **topologically ordered list of steps whose inputs already name other steps**, not a graph the worker walks.

the reason is the far end: `kernel.sh` is a shell script, and a shell script cannot resolve a wire. flattening once, in python, where the graph is typed and testable, means the container's job is to install, run, and post, and that every type error is found on the wrong side of the network.

## 9. a tool list is a mapping, not a menu

the owner's brief is four levels deep: group, section, tool, control. flowby is three: group, tool
(preset), control (slider). the mapping is data in `catalogue.py` so it can be tested, and the
numbers are the decision: **29 bullets, 16 presets, 16 controls.**

two bullets are worth calling out because they are where a catalogue usually cheats. `explore
material variations` is a sweep, not six presets, so the work before the swept node runs once. and
`geometric pattern mapping` is a control on `place-graphic` rather than a preset, because a pattern
is what a graphic does when it meets a surface.

the rule for a new bullet: **it is a preset if it changes what the graph produces, and a control if
it changes a number or a word the same graph already takes.** a preset the brief never names has to
be declared a primitive with a reason, which is the same discipline `PROCEDURAL` applies to models.

## 10. node ui is borrowed: @xyflow for the canvas, dagre for the layout

nobody should hand-roll a node editor in 2026. **@xyflow/react** (React Flow 12, MIT) draws the
node layer and **@dagrejs/dagre** (MIT) decides where nodes sit. both are the boring choice, which
is the point: the interesting part of this project is the seam between the two views, not bezier
maths and hit-testing.

what that changed in python: `scene.pipeline()` stopped emitting pixel positions. it used to
invent a grid (`320 + column * 240`) which the renderer then laid out again with its own engine, so
the two disagreed by default and a dragged node was lost on the next render. it now emits `rank`
(depth in the graph, which dagre turns into columns) and `row` (which element a node hangs off), and
geometry has exactly one owner: the renderer.

the reason this library over the others: LiteGraph.js is a canvas renderer whose look you fight for
weeks, Rete.js is plugin-shaped and assumes you want its dataflow semantics, Drawflow and jsPlumb
are lower level than the problem. React Flow is MIT, it is what React developers already know, and
its viewport is \`screen = page * zoom + translate\`, which is exactly the shape `align.mjs` already
converts from tldraw's camera. so the node layer and the spatial layer share one camera convention
without a new coordinate system.

## 11. tldraw: the source is open, the licence is not, and the version matters

the owner pushed back on an earlier draft of this section, and the pushback was fair, so here are
the terms at the tags rather than the terms at `main`, which is what the npm stub points at:

| version | licence | commercial use |
| --- | --- | --- |
| 2.0.0 to 3.x | "tldraw License": "You may use this Software for any non-commercial purpose… You may not use or distribute this Software… in any form for commercial purposes" | needs a paid licence |
| 4.0.0 and later | the same document rewritten for 4.0: "Not to use the Software in Production Environments", with licence-key enforcement and a watermark | needs a licence key even to deploy |

so the honest phrasing is **source-available, not open source**: nothing is hidden, you can read it,
fork it, and hack on it for free, and on 2.x there is no key and no watermark in development. what
you cannot do on any of these versions is ship it commercially without paying. that is a different
claim from "closed", which is what the first draft of this section implied, and it is the claim
that matters when the question is whether this repo can become a product.

the dependency in this checkout was also fictional: it named `@tldraw/tldraw@^2.6.1`, a package and
version that do not exist, so `web` could never install and had never been built, which is why
there was no tsconfig and eight type errors in a file nobody could compile. that is fixed
(`tldraw@2.4.6`, a tsconfig, `@types/react-dom`), and dev works.

this checkout pins 2.4.6 and treats the spatial layer as **on loan**. when shipping becomes real,
the owner picks one:

* buy the tldraw licence and stop thinking about it,
* accept the watermark on 4.x, which is the free tier,
* or swap the spatial canvas for an MIT one. the swap is contained: tldraw is touched by
  `web/src/useAlignedCamera.ts` and the spatial component only, because the coordinate contract
  lives in `align.mjs` behind a pure function with its own test. Konva (MIT) covers frames,
  transforms, selection and snapping; the 3d overlay does not care which canvas is underneath it.

what is not on loan is the node layer: **@xyflow/react and @dagrejs/dagre are MIT, with no version
of this question.**

## 12. motion is the smoothness layer, and reduced motion is not optional

**motion** (Framer Motion 14, MIT) animates the node layer, and the spec lives in
`web/src/anim.mjs` as data rather than in the component as numbers, for the same reason the wire
colours live in `wires.mjs`: a spec is a pure function with a test, and a component that hardcodes
`stiffness: 420` is a component nobody can check.

what "smooth" turned out to mean, concretely, and why each piece is not decoration:

* **stagger by rank.** nodes arrive left to right at 18ms per rank, capped at 180ms, because that is
  the direction execution flows. a 20-rank chain that animates in sequence for a second reads as a
  slow app, not a smooth one, which is why the cap is tested.
* **springs for touch, tweens for lines.** a spring settles where the pointer leaves it; a fixed
  duration snaps. mixing the two in one transition throws in motion, so the test asserts the spring
  carries no duration.
* **wires draw themselves** (`pathLength` 0 to 1). it is the cheapest way to say "these two are now
  connected", and it is the one thing a screenshot cannot show, so the edge is tested as a spec.
* **prefers-reduced-motion returns no animation at all**, not a faster one. three of the eight tests
  in `web/tests/anim.test.mjs` exist only to enforce that.

cost, measured rather than assumed: the full `motion` import took the bundle from 388 kB to 519 kB.
the slim entry (`m` + `LazyMotion` + `domAnimation`, `strict`) brings it to 480 kB, and motion's
engine then loads after first paint. the remaining ~90 kB buys every animation in the product, which
is the right trade for a canvas that is the product; it would not be for a marketing page.

## 13. what is not decided here

the licence. whether boards are multiplayer. whether a preset can be authored by a user inside the product, which both products in `docs/research.md` are moving toward and which is a different product surface than shipping six of them.

they are left open on purpose rather than answered quietly by the code.
