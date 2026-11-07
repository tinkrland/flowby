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


## seen on the page, not read in the copy

both sites were opened in a real browser and sampled frame by frame through screenshots, because the
copy describes a workflow and the hero videos demonstrate one. what follows is only what the pixels
showed. the hero on vectary is an autoplaying demo inside a window frame; it was sampled at intervals
rather than decoded, so this is a set of observations and not a shot list.

### vectary canvas

**the demo window is a mac app frame with the product's own controls.** the traffic lights sit top
left, the project path runs across the top bar (`C26 / Work - Alberic / stool`), and the interesting
part is the right panel, which has two tabs: **Properties** and **Presets**. properties holds
material, a colour swatch and a `roughness` slider sitting at 100%. so the preset layer and the
parameter layer are two tabs of one sidebar, not two modes.

**a preset announces itself as a card over the canvas.** bottom left of the demo, a small white card
with a thumbnail reads *"Sketch to photo: transform a sketch into a polished, fully rendered visual
based on reference image."* one name, one sentence, no parameters. the slider arrives after you
accept it.

**the node graph is shown in marketing, which means it is not a developer secret.** the research
section draws a dotted grid with an `Input shape` node holding a brown mouse, wired to two cards
side by side both titled `Recolor`, surrounded by a grid of six reference textures on one side and a
grid of six lattice-sphere results on the other. two parallel nodes, not one: **variants are visible
in the graph itself**, as siblings.

**the explore section is a wall of results from one model.** a 4 by 3 grid, twelve variations of the
same white mouse with a copper wheel, each a different structure (voronoi, lattice, wireframe,
hexagonal cutout, woven). a badge over the top left reads *"4 Design variations — view unique design
variations for the mouse model, all rendered within minutes,"* and a label top right says `Shape
exploration`. so one click on one model produced a **grid**, and the grid is the deliverable, not an
intermediate step.

### fuser

**the front door is a prompt, not a canvas.** the hero is a single floating pill reading *"Make a
picture to pixel weaver for your mom"* with one `Generate` button, sitting over a carousel of
finished project windows. the node graph is the second sentence, never the first impression.

**the recipe library is faceted like a catalogue.** 188 recipes, filtered by output type (3d, audio,
image, text, video) and by around twenty-eight categories, each card carrying a name, an author
handle, a category and one sentence of intent.

**and the recipe sentences are fan-out sentences.** this is the finding. from the library itself:

* *relight an image*: "upload one image to **explore six lighting versions**, from studio daylight
  and soft white to dramatic spotlight and golden hour."
* *change interior room style*: "upload one room image to explore japandi, art deco maximalist, dark
  academia, classical, and mid century modern variations."
* *merch mockups from a logo*: "turn **one logo into** business card, letterhead, tote bag, socks,
  hat, and shirt mockups."
* *product e-commerce photography*: "transform a product image into website-ready **front, side, and
  back** product photos."

so the repeated unit across both products is not the preset. it is **one input, a named set of
parallel results, side by side.** fuser names the set in the recipe; vectary renders it as a labelled
grid. both then ask you to pick one and keep going.


## the two screenshots the owner sent

both are from vectary's own preset marketing, and together they answer a question the landing page
only gestures at: *what* is in the catalogue, and *why* a preset rather than a prompt.

### the presets are named after surfaces and run models

four families, each with a demo video attached:

* **texturing and materials**: extract, generate and test physical pbr textures, normal maps and
  realistic 3d materials *on your shapes*.
* **surface details and textures**: crease (realistic clothing wrinkles), stitches (tailored lines),
  emboss and deboss (flat or 3d embroidery effects).
* **lighting and environments**: modify, test and adapt studio lighting styles or colour palettes
  **instantly across your infinite board**.
* **design and ideation**: rough sketches into photoreal visuals, mapping geometric patterns,
  generating 3d variations from 2d layers, replacing a specific object in a frame.

that list is a designer's vocabulary, and **every entry is a model call underneath it.** this was
written down wrongly here first, as "named after surfaces, not by model", and the correction matters
because it changes what the architecture has to be: crease and stitch are **diffusion passes** that
produce a detail map, not a carved edge. "extract a normal map" is a model. even the material family,
generate and test physical pbr textures, is inference rather than arithmetic.

so the surface words are not a substitute for the models. they are the **interface on top of them**:
337 models behind nine words a designer already had. the names are the wrapper and the models are
the product, which is the same bet this tree makes, and it means a preset with no model in it is
making a claim rather than saving money.

### their benefits table is this tree's architecture, one row short

| their feature | their claim | what it is in flowby |
| --- | --- | --- |
| less prompting | replaces long text instructions with curated task blocks | the preset, as a subgraph with sliders |
| preset chaining | combine and stack multiple presets on top of the same concept asset | `scene.apply` reading the element's *current display* |
| design dna matching | presets configured to transfer a specific design language **across layouts** | the one row this tree did not have |

the middle row was already the rule that made chaining work. the third row is a **scope**: a preset
whose head runs once and whose tail reaches several frames. "across layouts", "across your infinite
board", "brand consistency" are all the same sentence about a single expensive read feeding many
cheap applications.

### what that changed

`Preset.scope`, as a `shared_seam` and a `tail_port`. `studio-light` is the board preset: one
lighting reference frame, graded onto every frame you point at it, so three frames cost one style
read and three grades.

and once the family turned out to be models rather than maths, `surface-detail` got rebuilt from two
nodes into three: read the surface, **paint a detail map from a sentence** (`flux-depth-lora`), then
displace the geometry with that map. the choice control now carries a prompt fragment, so `deboss`
arrives at the model as "a recess cut into the surface, as in a stamped logo" instead of as a mode
name nobody was going to read.

two details worth keeping in mind from their framing rather than their mechanism:

* **the videos are per feature, not per product.** four families, four demos. a preset that needs a
  video to explain itself is a preset whose name is not doing its job, and that is a reason to keep
  the labels as sentences.
* **the model is the product and the word is the door.** 337 models, four families, nine words. the
  moment a preset is named after the model instead of the task, the catalogue has to be read by
  somebody who already knows the models, which is the audience it was built to avoid.
* **nothing in their copy mentions a node graph, and the graph is still there.** the user's summary
  of it was exact: it is a node canvas whose nodes are premade presets. the abstraction is the
  product and the graph is the honesty underneath it, which is the same bet this tree makes.

## what the visual pass changed in this tree

one thing, and it was the biggest gap: flowby produced exactly one artifact per element, so every
preset was a single shot and the board could only ever show one answer.

`Preset.sweep` is that finding as a compiler rule. a preset may declare one slider, a discrete list
of values and a label ("six lighting versions"), and the compiler splits its subgraph at the swept
node: **the head runs once, the tail is copied per value.** `relight` is the shipped example, and it
mirrors fuser's recipe almost line for line, because the recipe is the thing that made the shape
obvious.

three details came from looking rather than from either site's copy:

* **the fan is addresses, not files.** an element comes back with `sketch-1#1.png` through `#6`,
  and the socket groups them by element so the frame receives one update with six results rather
  than six updates that each replace the last.
* **picking is a pointer.** `show_variant` moves the frame's display to variant n. nothing re-runs,
  which is what makes comparing six results cheaper than generating one.
* **the shared head is the cost story.** the plan for six relights is eight steps and 6.9 minutes,
  not twelve steps and 7.2, and that difference is the argument for a compiler over a loop.

what was deliberately not taken: vectary's two-tab sidebar (properties and presets) is right and is
already the shape of `scene.sidebar`, which returns controls with real ranges rather than a mode
switch, so nothing changed there. fuser's prompt-first hero was not taken either, because flowby's
brief starts from a board rather than a sentence, and a prompt bar over a canvas is the one thing a
preset card already does better on a spatial layer.

## fuser's docs, with the screenshots actually looked at

docs.fuser.studio has real canvas screenshots, and they say more than the prose does. read from
`/docs/interface/sockets` and `/docs/interface/flows`, seen rather than described:

* **a node is a card with property rows, not a box with ports.** header (icon, title, collapse),
  then the prompt as a text area inside the card, then one labelled row per property (`Images`,
  `Aspect Ratio` with a dropdown), each with its **own socket on the card edge**, then a fold:
  "2 properties hidden" / "5 properties hidden". complexity is folded, not removed.
* **the result is the node body.** the generated image sits inside the card under the properties.
  there is no separate "preview" panel; the node is the output.
* **size follows importance.** in the building-flows hero a text node feeds three small flux nodes
  and the final image is a node several times larger. intermediates stay small, the answer is big.
* **the socket vocabulary is shape plus colour.** colour is the dtype (text, image, video, audio,
  3d, style, number, generic). shape is cardinality: a **circle** takes one connection, an
  **oval** takes many. a **triangle** is a passthrough that shares a value (prompt, style, seed)
  with a downstream node, and a **line plus triangle** is a passthrough that fans out.
* **chrome is minimal and floats.** a small project pill top left, zoom and Share top right, and a
  **bottom toolbar of node-type buttons with a `+`**. nothing docks.
* **the canvas is dark even though the docs site is pale.** the docs page is a light theme with a
  sun/moon toggle, and every canvas screenshot inside it is near-black with a faint dot grid.

what the owner decided from this: **flowby is dark mode only.** no light theme, no toggle, no
`prefers-color-scheme`. fuser's marketing and docs surfaces are pale; the canvas inside them is not,
and the canvas is the product. borrow the structure, not the palette.

### the gap this leaves in this tree

| fuser, seen | flowby today | state |
| --- | --- | --- |
| a socket per property row | one port per wire | missing |
| result embedded as the node body | text-only card | missing |
| "N properties hidden" fold | all or nothing | missing |
| passthrough triangle | none | missing |
| circle vs oval cardinality | one shape | missing |
| size follows importance | every node the same width | missing |
| bottom toolbar of node types | none | missing |
| dark canvas with dot grid | dark, with dot grid | **done** |

what was *not* seen: the vectary canvas launch video (youtube.com/watch?v=5KhZKzW67PU, 1:46). the
page loads and the thumbnail is visible, but playback did not start in the browser session and the
embed player refused with error 153. the vectary pages above are still read as text, not watched.

## the vectary canvas launch video, actually watched

the page embeds one vimeo video (id 1216133325, 2:17, 1920x1080, looped and muted). its hls stream
was pulled with ffmpeg and sampled every 4 seconds into three contact sheets, then the key frames
were opened at full size and looked at. the youtube trailer (5KhZKzW67PU) would not play in the
browser session, so this is the same product from the source instead. seen, not read:

* **the same move repeats across five products** (mouse, binoculars, car vents, hiking shoe, spray
  bottle): one reference, then a grid of parallel variants, then one picked and enlarged. the grid
  is the unit of work, which is what `Preset.sweep` already does.
* **a preset is a card with a thumbnail, a name and one line.** "Recreate graphics to flat 2D:
  extract graphic from products into completely flat 2D design", with a picture of what it does. the
  picker is a small floating panel with tabs (All, Images, Text, 3D, Custom) and a search field.
* **a node is also an editor.** a selected image grows a floating toolbar under it (lasso, two ai
  brushes, delete, confirm), so refinement happens on the node, not in a separate screen.
* **a node can be a live 3D scene.** the last frames show a spray bottle as an embedded vectary
  scene with dimension callouts and an **AR** badge, so the spatial side is real 3D, not pictures.
* **references and people share the canvas.** stool photos with a purple sticky note ("love this
  minimal design"), named frames ("shape exploration", "CAD views"), a collaborator avatar on a
  selected node, and a top-right Share. the research step is a board you pin things to.
* **the properties panel is a column of sliders** (material, roughness-style values) on the right,
  opened by selecting a node. nothing is modal.
* **light canvas, purple selection.** pale grey dot grid, a single violet outline for the selected
  node, white cards with soft shadows. flowby takes the structure and keeps its own dark palette.

not recovered: the studio base44 style transfer flow. `studio.base44.com` redirects to an sso login
that renders blank without a signed-in session, and there is no credential in this environment.

## illustrace: the owner's earlier style research, read

`github.com/tinkrland/illustrace` (public, 94 commits, 521 files) is a benchmark for measuring and
moving visual style one factor at a time. its learned half, the style lora engine, the colab micro
lora script, the gpu runner and the react flow composer, is what flowby's **style** kind needs. it is
summarised, with what carries over and what does not, in `theidea/taxonomy.md` under "what illustrace
already knows about styles". the one-line version: it has a debugged colab recipe, a resume path and
a probe, and it has **never finished a training run** by its own account.

## base44 studio: the third idiom, /tools

studio.base44.com is base44's own alpha and the closest thing to the third instinct: bring a
reference, then carry it. the path is `/tools`. **the shell is public and the catalogue is not.**

what is visible from outside:

* `/tools` returns 200 with a 32kb html shell and one bundle, `assets/index-C38rLxdA.js` (1.2mb).
  there is no redirect at the edge, which is why `/` and `/tools` both looked closed rather than
  merely empty: the gate is the client booting and sending you to
  `app.base44.com/apps-sso/login?...app_id=6a6f3b530ae563a8d04fdc18&from_url=...`.
* the shell's own description calls it *"Tools on Base44 Studio. An AI-powered creative workspace
  where you can generate high-quality images."*
* the bundle's routes are `/tools`, `/tool/`, `/tool/:id` and `/admin/tools`, with a `ToolPage`
  component. a tool per job, chosen by id, with an admin surface for the registry.
* the tool list itself is not in the bundle. it arrives authenticated, so the names, the parameters
  and the style transfer flow are not visible without a session, and there is no credential here to
  open one with. `base44.com/studio` is a 404 and the documentation index has no entry for it.

### and that settles one thing already

a tool-per-job catalogue is the **fixed** door, not a third architecture. what makes style transfer
feel like a different product is not its structure, it is its input: a reference instead of a
phrase. so `modes.MODES["style"]` is correctly a first move and a set of crossings rather than a
separate shape, which was the right guess for the wrong reason until the route list arrived.

### what four questions would settle the rest

one signed-in session in the browser this research runs in, since the context is persistent. then:
is a style chosen from a library or extracted from an upload; what is a kept style called; does it
reach one artifact or a whole project; and is `/admin/tools` per-workspace or base44's own. the last
one matters most, because a registry a customer maintains is a different product from a catalogue
the product ships, and it would change what `presets.py` is.

## fuser's clips and docs, the ones the first pass did not read (2026-11-08)

the earlier pass read the sockets and flows pages. this one read the rest of docs.fuser.studio
(fourteen interface pages, as markdown from `/docs/interface/*.md`) and downloaded every screenshot
and clip they reference: 26 images and 41 clips, 16 minutes of the interface in motion, all
1440x1080, all decoded and checked. four of the clips were then looked at as contact sheets (six
frames each): the toolbar, media drop, node anatomy and style training. the rest were read through
the prose that sits beside them and have not been watched. nothing below comes from youtube: the
docs carry the clips themselves, so the channel was not needed for the interface.

### how media gets in, which is not a panel

this is the finding that most changes the panel built on 2026-11-07.

* **dropping on the bare canvas is the creation action.** three files dragged from the desktop
  became three nodes in a row, each sized to its content (a portrait is tall, a square is square),
  with no dialog and no confirmation.
* **a drop target shows itself before release.** dragging a file over an existing node tints that
  node violet, and releasing replaces its content. dropping onto a *property* uploads into that
  property.
* **paste works too** (cmd/ctrl+v), including images copied from a web page.
* **there is a library behind it:** an Assets tab (everything uploaded) and a Generations tab
  (everything a node has made), both in a narrow left rail. dragging from either onto the canvas
  or into a training panel is the same gesture.
* the limit is 50 MB a file. formats: png, jpg, webp, gif; mp4, webm; mp3, wav; glb, gltf.

### the node, seen

* header with a provider icon, a title that renames on double-click (the field opens in place and
  the header updates at once), and a menu. hovering the title shows the model's one-line description.
* a prompt area, then one row per property, each with a coloured dot socket on the card edge and its
  control on the right (number field, dropdown, seed with a re-roll button).
* a faint "3 properties hidden" fold, then the output row with its own socket. the generated image
  becomes the card body, so the node is its own preview.
* a small action bar appears under a *selected* node only: properties, chat, focus, download, run.
  each has a tooltip. the run button is violet and is the only saturated colour on the canvas.
* selection is a soft violet glow and not a hard border.

### the chrome

* a floating pill at the bottom centre: six type icons (text, image, video, audio, mesh, 3d), a `+`,
  and an **Execute** button that appears only when an executable node is selected.
* the `+` opens a command bar: fuzzy search over type, provider and function, and every row shows its
  type signature as coloured chips (`TXT + IMG -> IMG`), so what a node takes and gives is visible
  before it is added. shift+A or cmd/ctrl+K opens it.
* a project pill top left (double-click to rename), zoom percentage and a violet Share button top
  right, a narrow icon rail on the left (Nodes, Assets, Generations, Styles, Templates, Learn), and a
  context-aware properties panel that slides in on the right (shift+P).
* errors stack at the bottom centre and expand on hover.
* keyboard: cmd/ctrl+0 fits all, cmd/ctrl+1 fits the selection, double-click a node to zoom to it,
  F opens focus mode (a fullscreen single node), shift+scroll pans horizontally.
* **quick connect**: drag from a socket to empty space and a small search menu lists every
  compatible node and property; picking one creates and wires it in a single move.

### style training, seen (this is the page the style kind should be compared against)

* three training modes in a segmented control: **Style**, **Object**, **Portrait**, each with a
  one-line description. portrait requires consent from every person depicted, and a style found in
  breach is removed.
* a name with example placeholders, a Publish to Community toggle with its trade-off written under
  it (published styles do not count against storage), and a reference-images drop zone that reads
  "provide 5-15 high-quality, diverse images".
* the button is disabled and reads "add at least 5 more images" until the minimum is met.
* **the cost is stated before the press**: "training a style will incur a $2.4 charge to your fal
  account". a toast then says "style training started" with a View link, and a green progress bar
  replaces the button.
* training takes 1 to 5 minutes, on their own GPUs.
* **trigger words are generated and appended for you.** the user never types or sees one.
* **every style carries a Master Prompt**: a long text description of the look, as a socket on the
  style node. it lets a style work on models that cannot load a lora (gpt image, gemini, ideogram,
  recraft), and it can be copied from the style card.
* the trained style lands as a **Style node** on the canvas (reference image plus the master prompt
  text) and quick connect wires it to a generator.
* styles currently work only with flux dev and flux krea dev.

### what this changes in flowby, and where flowby already differs on purpose

| fuser, seen | flowby today | verdict |
| --- | --- | --- |
| dropping on the canvas creates the node | a panel with a drop zone behind a button | **wrong centre of gravity.** keep the panel as the figma door and the queue, add canvas drop and paste |
| drop target highlights before release | none | missing |
| paste from clipboard | none | missing |
| assets and generations libraries | an artifacts tab designed, no assets tab, nothing built | missing |
| cost shown before the press | cost is shown for figma imports and training plans, not on the canvas | partly there |
| trigger words managed for you | the style gate makes the user pick a rare token and refuses ordinary words | **the gate is right for a corpus and wrong as a surface.** generate the token, keep the check as a guard on custom ones |
| three training modes | one kind of style | missing: object and portrait, and the portrait consent gate |
| master prompt on every style | none | missing, and cheap: it makes a style usable without a lora |
| 5 to 15 images, 1 to 5 minutes | 10 to 30 images, 75 to 150 minutes | different on purpose: fuser trains on its own gpus, flowby on the user's colab. say so in the ui instead of copying their numbers |
| type signature chips in the command bar | none | missing, and the type system to drive it already exists |
| quick connect | none | missing |
| node result as the card body | text-only card | missing |
| execute button only when something is selected | none | missing |
| node toolbar under a selected node | none | missing |

what fuser does not have, and flowby does: a gate that refuses a bad training corpus before any
gpu time, a stack limit with a stated reason, a font as a file kind, a preset that says whether it
runs on a model, and routes that state what each place honestly cannot do. fuser's cost line is a
price; flowby's is a price and a time and a way it can fail.

## the one thing both are doing and this tree is not

both are moving toward **authoring presets inside the product**: vectary says custom presets are "coming soon" for teams, and fuser's recipes are already user-recorded. flowby ships six presets in a python file, which is appropriate for a tree with no accounts and no storage, and is the first thing that would have to change for a real studio to adopt it. that is named in `theidea/decisions.md` under what is not decided rather than left to be discovered.

## why this reads as more intuitive than a raw graph

the answer both products give, from opposite directions, is the same: **start from the task, keep the graph.** a raw node editor asks a person to translate an intention into a topology before anything appears on screen, and to know which of three hundred models the topology wants. a preset answers the intention in the language it was asked in, and leaves the topology behind it for the person who needs to open it. the presets are not a simplification of the graph; they are a vocabulary for it, and this tree's contribution is to insist that both are the same object rather than two tools kept in sync.
