# research

*what the two products in the brief already know, read from their own pages, and what was taken*

the brief names two products as the reference points, and both are explicit enough on their own sites that the design questions mostly answer themselves. what follows is what was read, what it implies, and which part of it this tree adopted.

## vectary canvas: the spatial half

from [vectary.com/canvas](https://www.vectary.com/canvas/), which is in beta:

* the flow has four named moves: **research** (bring in sketches, photos, references, models), **explore** ("use purpose-built AI presets to test forms, finishes, layouts, and variations as ideas evolve"), **refine** ("edit geometry, materials, lighting, and models without interrupting your workflow or switching tools"), **validate** (compare options, gather feedback, AR in context).
* "hundreds of presets", each "fine-tuned for a specific creative task, helping guide AI toward the result you have in mind. **No perfect prompt required.**"
* the presets are named as tasks, not models: extract and apply materials, transform sketches or basic 3d models into photorealistic visuals, generate 3d from 2d, replace selected objects, adapt lighting, extract a pose, clear an interior.
* "**Combine presets as your idea evolves**, so you can explore directions without losing momentum."
* 2d, 3d and AR in one environment: "move freely between information, visuals, 3d models, and AR without breaking your flow."

what that implies, and what this tree took:

1. **the stage is part of a preset's identity.** `Preset.stage` is `explore` / `refine` / `output`, and the sidebar groups by it. a menu of thirteen presets sorted by model is a menu nobody scans.
2. **chaining is the documented model, not an advanced move.** `scene.apply` reads the element's current display, so presets compose in the order a person applies them. this is the single most important sentence on vectary's canvas page and it decided `scene.py`.
3. **dimensional fluidity is a state change, not an import.** `flips_plane` moves a frame from 2d to 3d in place, and the move is recorded in the element's history.
4. **the sidebar offers the next step, not the whole menu.** offering `frosted-glass` on a raw sketch, where it would immediately refuse, is the failure mode vectary avoids by naming presets after tasks.

## fuser: the pipeline half

from [fuser.studio](https://fuser.studio/) and the studio's own writing:

* the pitch is "**One click, whole workflow.** Recipes are here. Package a whole workflow and run it in one click." and "Never start with a blank canvas."
* "Every generation node shows its **credit cost on the canvas before it runs**, and a Recipe shows its estimate beside Execute."
* "**Every prompt, reference and step stays visible in the graph**, so you can see exactly how each result was made."
* 341 models and 113 llms on one infinite canvas, with `Compositor` turning results into editable layouts, and `Apps` turning a canvas into something a client can operate.
* the canvas is built for thousands of nodes and stays smooth to pan, zoom and drag.
* the [Creative Code Node](https://fuserstudio.substack.com/p/code-meets-canvas) puts three.js, p5.js and html5 inside the canvas: "describe what you want to build in plain language and the node will generate a working sketch", with per-line explanations, and the sketch can then be captured as an asset that feeds the rest of the workflow.

what that implies, and what this tree took:

1. **cost is shown before the run, on the node.** `compile` puts `minutes` and `gpu` on every step, `cost` on the plan, and `estimate` on the sidebar payload. a board that only tells you what a click cost afterwards is a slot machine with a receipt.
2. **the graph is visible evidence, not a debug view.** a preset that hides its steps cannot answer "why does this look like that", which is the question a studio actually asks. this is why `detach` exists and why the node labels are sentences.
3. **a recipe is the front door.** `scene.record` / `scene.replay`, with the estimate travelling alongside.
4. **a code container belongs in the chain.** `code-container` is a preset with one node and no sliders, so source code is an asset with wires rather than a separate feature.
5. **a canvas should survive a lot of nodes.** not verified here, but it is the reason `hub.Hub` closes a slow subscriber instead of dropping messages for it: a second view that silently falls behind is worse than a view that reconnects.

## the one thing both are doing and this tree is not

both are moving toward **authoring presets inside the product**: vectary says custom presets are "coming soon" for teams, and fuser's recipes are already user-recorded. flowby ships six presets in a python file, which is appropriate for a tree with no accounts and no storage, and is the first thing that would have to change for a real studio to adopt it. that is named in `theidea/decisions.md` under what is not decided rather than left to be discovered.

## why this reads as more intuitive than a raw graph

the answer both products give, from opposite directions, is the same: **start from the task, keep the graph.** a raw node editor asks a person to translate an intention into a topology before anything appears on screen, and to know which of three hundred models the topology wants. a preset answers the intention in the language it was asked in, and leaves the topology behind it for the person who needs to open it. the presets are not a simplification of the graph; they are a vocabulary for it, and this tree's contribution is to insist that both are the same object rather than two tools kept in sync.
