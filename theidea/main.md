# the brief

*the owner's description of flowby, kept as written, because the argument for the product should not be rewritten by the person implementing it*

this page is the source. `decisions.md` beside it says what this tree concluded from it, and where it disagreed.

---

## 1. core vision

build an intuitive, web-based creative platform that bridges the gap between infinite-board multimedia layout software and programmatic visual automation. the application combines the spatial, preset-driven, dimensionally fluid user experience of vectary canvas with the infinite-canvas multi-model node orchestration of fuser.studio.

## 2. frontend user interface layers

the front-end features a dual-layer infinite board built on tldraw and react three fiber. users can instantly toggle between two distinct modes or views for the exact same workspace.

### the spatial layout layer (vectary style)

* a clean, visual-first creative canvas.
* users manipulate 2d reference frames, images, video assets, typography, and 3d gltf/obj models directly on infinite design layers.
* clicking any spatial element opens a contextual sidebar displaying high-level creative presets.
* example presets include: "convert sketch to 3d mesh", "apply matte frosted glass material", "animate scene composition", or "style transfer".
* users adjust artistic parameters using simple sliders, completely abstracting away python strings or generative math terms.

### the node pipeline layer (fuser style)

* a structural node graph hidden directly underneath the spatial layer.
* clicking an "inspect pipeline" toggle exposes the mechanical graph routing for that specific workspace segment.
* every visual asset behaves as an active node.
* wires are strictly color-coded by obvious creative intent and data types: amber for raw text prompts, green for image assets, blue for sequential video layers, and red for structural 3d meshes.
* clicking a preset in the spatial view implicitly spawns and links the necessary underlying nodes behind the scenes.
* advanced developers can enter this view to break apart a preset, wire custom code containers, inject secondary controlnets, or manually route parameters to fine-tune outputs.

## 3. headless backend infrastructure & runtime execution

to maintain low-cost prototyping and high compute efficiency, the platform skips permanent cloud-allocated virtual machine pools or direct cloud gpus. instead, it utilizes a decoupled automation stack running on disposable environments.

### backend architecture

* built on python fastapi and a celery background task queue backed by redis.
* handles session tracking, mapping frontend geometric states into structured execution json scripts, and dispatching tasks to automated workers.

### compute routing loop

* rather than triggering traditional container images on aws or gcp compute layers, the backend leverages browserbase to automate free or pro google colab runtime configurations.
* the orchestration layer invokes the browserbase headless api, injecting pre-authenticated google session credentials and cookies to authenticate without multi-factor prompts.
* browserbase opens a target colab notebook file ID and triggers the runtime engine headlessly via execution macros or cell interactions.

### kernel.sh execution flow

* the automated browser triggers a universal runtime script named kernel.sh inside the colab virtual container.
* kernel.sh spins up an isolated execution zone, resolving custom system models, setting up pip requirements, and calling a core python asset processor.
* the colab instance fetches active spatial coordinates and canvas variables from a fastapi configuration endpoint using a specific job id.
* the core model executes heavy tasks locally using the colab gpu architecture.
* when execution completes, kernel.sh archives the resulting 3d structural assets, materials, or texturing maps into a compact tar file and fires a post request back to the fastapi webhook layer.
* the backend extracts the payload, updates persistent state layers, and broadcasts the fresh visual components to the active frontend client workspace using open websockets connections.
