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

## 9. what is not decided here

the licence. whether boards are multiplayer. whether a preset can be authored by a user inside the product, which both products in `docs/research.md` are moving toward and which is a different product surface than shipping six of them.

they are left open on purpose rather than answered quietly by the code.
