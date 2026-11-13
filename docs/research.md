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

## fuser's docs screenshots, looked at (2026-11-09)

the last pass downloaded all 26 stills and watched 4 of 41 clips. this one looked at the stills: the
interface overview, the properties panel, the left asset panel, the gallery browse and recipe pages,
the socket diagrams, and the six node types. each was cropped to a readable size first, because a
tall contact sheet scaled into a viewport is too small to read, and the first look at the overview was
exactly that. the clips beyond the four are still unwatched.

### the properties panel is the node seen larger, with sections

* a header with a panel toggle, a **zoom dropdown** and the Share button. zoom lives in the panel, not
  floating on the canvas.
* **named sections with a fold dash**: Content, Settings, Advanced. so folding is by group, and
  "3 properties hidden" on the card is the same idea compressed.
* every property keeps its **socket dot inside the panel**, so the panel is still a place to wire from.
* the **result sits inline** between the prompt and the negative prompt, with a Download button under it.
* controls: a filled text area for prompts, a number field with a re-roll `R` for the seed, plain fields
  for steps and scale, and a **toggle switch** for a boolean.

### the asset panel

* a floating, rounded panel with a gap from the canvas edge, not docked. a project title and collapse
  toggle at the top, a slim icon rail down its left edge, the active icon marked by a violet bar.
* Assets is a **two-column thumbnail grid**, each image in a dashed-border cell, with a refresh icon.
* a **storage meter is pinned to the bottom, always visible**: "Using 3GB of 4GB", 78%, an amber to
  violet bar. the quota is never hidden behind a settings page.

### the node types, empty and filled

* image, video, audio and mesh are each a **pair**: an empty node that is a drop zone ("Drop your image
  here, or" plus a `select a file` button) and a separate **borderless media-only node** once filled.
  video gets a scrubber and transport controls, audio a waveform, mesh a lit render.
* **the empty node is the creation tool.** the toolbar's type icons make empty nodes; dropping on the bare
  canvas is the shortcut around that. flowby has the shortcut and not the empty node.
* a style node shows a cover image, its name and tagline, then the Master Prompt text, with a labelled
  Master Prompt output socket.
* socket colours: text orange, image green, video blue, audio magenta, mesh red.

### sockets, drawn

* a circle is one connection and a tall pill is many. an **unconnected output is drawn dim**, a connected
  one is bright, so an idle port is visible without a label. flowby draws every socket the same.
* a triangle is a passthrough and sits on the output side.
* **many-to-one**: three images wire into one pill on a chat node, and the wires bundle where they meet.
  the chat node prints its answer as its body.
* **one-to-many**: one text node fans out to three generators of equal width, stacked and aligned, each
  showing its prompt socket, "8 properties hidden" and its image as the body.
* cards are near-black with **no border**, about a 12px radius, on a slightly lighter canvas with a faint
  dot grid. contrast does the separating. flowby cards have a 1px line.

### the gallery and a recipe page (the chrome around the canvas is light)

* the gallery is pale: a warm white page, a peach glow, a huge black display heading. this is where
  fuser's own surfaces are light, so it is not copied. flowby stays dark.
* structure worth keeping: a top bar with the title, a **centred pill search**, then Import project
  (outlined) and New project (filled). a featured hero with a label, author, a two-line description, and
  **View recipe** (primary) beside **Try it** (secondary). five variants of one input shown as vertical
  slices side by side with prev and next arrows.
* **a recipe page is Description, Inputs, Outputs**: inputs and outputs are small cards, each a thumbnail,
  a name and a type. it describes a workflow by what it takes and gives, with real pictures.
  flowby's command bar says `IMG -> 3D` and has no example media to show, and inventing thumbnails would
  be dishonest, so this waits until presets have actually been run.

### what to build from this, in order

1. borderless cards with a dot-grid canvas, and dim idle sockets (small, visible at once).
2. the **empty media node**: a drop zone that is also the toolbar's creation action.
3. a **properties panel** with named sections, inline result, and re-roll on seeds.
4. an **assets panel** with the dashed thumbnail grid and an always-visible quota meter. flowby's quota
   is the store's size, which it can actually report.
5. zoom in the panel header.

## the one thing both are doing and this tree is not

both are moving toward **authoring presets inside the product**: vectary says custom presets are "coming soon" for teams, and fuser's recipes are already user-recorded. flowby ships six presets in a python file, which is appropriate for a tree with no accounts and no storage, and is the first thing that would have to change for a real studio to adopt it. that is named in `theidea/decisions.md` under what is not decided rather than left to be discovered.

## why this reads as more intuitive than a raw graph

the answer both products give, from opposite directions, is the same: **start from the task, keep the graph.** a raw node editor asks a person to translate an intention into a topology before anything appears on screen, and to know which of three hundred models the topology wants. a preset answers the intention in the language it was asked in, and leaves the topology behind it for the person who needs to open it. the presets are not a simplification of the graph; they are a vocabulary for it, and this tree's contribution is to insist that both are the same object rather than two tools kept in sync.

## fuser's youtube tutorials, the ones that were actually heard (2026-11-12)

the channel's playlist is 19 videos, 2:09 to 11:27 each. the sandbox is refused by youtube (bot check),
so nothing was downloaded and no frames were looked at. what was read is the **description and spoken
transcript** of three of them, through the browser: *Using The Compositor Node* (6:03), *Fuser Tutorial:
Recipes* (9:21) and *Create Infinite Variations* (7:06). the other sixteen are not read. this is
narration, so it says what the people do and what they call things, and it cannot say how anything looks.

### recipes (the one that matters for presets)

heard, in order:

* **a recipe is made by selecting nodes, not by writing one.** shift and drag a box over the nodes, a small
  bar appears at the bottom, the stack-of-papers icon is *create recipe from selection*, and the selection
  **collapses into one node**.
* **inputs and outputs are chosen by wire.** the new recipe opens with its inputs on the left; the author
  *disconnects* the wires they do not want exposed and *drags in* others (duration, aspect) to add one.
  outputs work the same way.
* **a recipe has a name, description, tags, a hero image, and a name and description per input and per
  output.** tags are what the gallery filters by.
* **recipes nest.** one recipe can sit inside another, e.g. a render-style recipe cleaning an input photo
  before a lighting recipe runs.
* **recipes chain on the canvas**: output of one wired to the input of the next, nothing else to set,
  because a recipe with no prompt has the prompt baked in.
* **two ways to use one.** *use this recipe* opens a new workspace with it loaded in **focus mode** (a
  full-screen form: write the input, press generate, download). an X in the corner leaves focus mode and
  shows the same recipe as a node on the canvas. the speaker's point: a teammate can use it "and never have to
  know that the nodes even exist".
* **you can open any recipe to see how it was built, and clone it.** publishing is a separate step from saving,
  and community sharing requires publishing first. a published recipe can be edited later (swap a model for
  a newer one).
* **the library lives on the left toolbar**: tabs for featured, your own, and recently used, with search.

### compositor

* **it is a node that opens an editor**, and closing the editor is called "exit, saving and closing". the
  editor has a **layers panel on the left** ("keeps everything organized and non-destructive"), a
  **properties panel on the right** (brush size, colour, opacity, hardness, streamline), and a **transform
  tool that rotates a 3D layer on x, y and z**.
* **a brush stroke is an input, not a drawing.** the orange strokes mark where something should go, and the
  downstream image model is told to replace them with a style. the speaker: "i'm indicating placement and
  color", the compositor is "the layer between your idea and your prompt".
* three start points were shown: a 3D mesh, a logo and text stack, a brush stroke.

### infinite variations

* **daisy-chaining is the editing method**: one instruction per node, each fed by the one before (hair clips,
  then t-shirt colour, then head turn). a reference image is just a second input to the same node.
* three models were compared on the same chain. the speaker reports one has a lower success rate with
  multiple images, and that the aspect ratio of two follows the input while the third uses what you pick.
  the **canvas is how the comparison is made**: copy the chain, swap the model.

### what this changes in flowby, and what it does not

nothing here contradicts the 2026-11-08 reading; it confirms the closing paragraph of this file (fuser's
recipes are user-recorded) and gives the shape of the gesture.

* **already true:** a preset is a subgraph spawned and left visible; presets expose a parameter list
  (`exposed`); the board can fan one head out to several tails (`sweep`). the daisy chain is what flowby
  already draws.
* **missing, in the order it would pay off:**
  1. *create preset from selection*: box-select nodes, collapse to one node, with its inputs and outputs
     chosen by which wires are left connected. flowby's presets are a python file today, so this is also
     the first thing that needs the store.
  2. *focus mode*: a preset as a form (inputs, generate, result) with the graph one click away. flowby
     has the data (`exposed`, the compiled steps) and no screen for it.
  3. *a library with featured / mine / recent*: the kits menu is the start of the left half of this.
  4. *tags and a hero image per preset*, which only means something once presets have been run.
* **not taken:** the compositor. flowby has a frame and a scene already, and the editor is a product
  of its own. what is worth taking is the idea that a mark on an image is a **placement input** for a
  model, which flowby has no node for.

### not verified

sixteen of nineteen videos are unread, including *Getting Started with Fuser Apps*, the three Apps builds
and the Creative Code ones, and nothing here was seen, only heard. no frames, so no layout, spacing or
motion claims come from this section.

## the tutorials, seen rather than heard (2026-11-12, later)

youtube refuses this sandbox's address, so the videos were fetched from a **tenki.cloud sandbox VM**
instead: yt-dlp with `--extractor-args "youtube:player_client=web_embedded"` and deno for the js challenge.
four videos were downloaded at 480p and sampled at one frame every 8 seconds (217 frames), read as
4x4 contact sheets; two moments were re-fetched at 720p for legible text. the frames looked at:
*Recipes* (5 sheets), *Using The Compositor Node* (1 sheet), *Getting Started with Fuser Apps* (1 sheet),
*Infinite Variations* (none). **19 minutes of the 19 videos were looked at out of 2 hours**, so this is
samples, not a shot list. two frames are kept in `docs/frames/`.

### the two surfaces are not the same colour

this corrects the earlier assumption that fuser is one pale product.

* **the graph canvas is pale**: `#f4f4f4` to `#f9f9f9`, white cards, thin grey bezier wires, dark grey
  text. toolbar icons are line icons on the same pale field.
* **the compositor editor is dark**: near-black canvas, `#252525` panels, a layers list on the left and a
  properties list on the right.
* a **recipe's focus view is pale again**, and looks like a web app, not an editor.

flowby is dark only, so the honest transfer is: borrow the *pale canvas + white cards + grey wires*
hierarchy as **layering and restraint**, not as colours. what makes it read calmly is that nothing on
the canvas has a fill except the cards themselves.

### the canvas chrome, from a real frame

`docs/frames/selection-toolbar.jpg` (Recipe Making, 1280x720):

* **top bar**: a square app icon, the workspace name, a chevron to rename, then on the right an avatar,
  a **zoom readout (109%)** and Share.
* **left edge**: a floating vertical toolbar (pointer, square/frame, comment bubble, plus, gear).
* **bottom left**: a credits figure (5,303,556 on that account), help, and a grid icon.
* **bottom centre**: an "open chat" input, always visible.
* **selected nodes glow purple** and their ports are small filled green circles; unconnected ports are
  hollow. **the wires carry no labels.**
* **when two or more nodes are selected, a pill-shaped bar floats at the bottom centre**: expand/focus,
  duplicate, delete, lock, then a number the video reads as the **credit cost of the selection (2,538)**, a "..." and an
  arrow. that cost-in-the-toolbar detail is the one thing here flowby should copy first; a selection is
  a proposal, and its price belongs next to it.

### a recipe used in focus mode, from a real frame

`docs/frames/recipe-focus-mode.jpg` (Storyboard Maker):

* **top bar**: icon, recipe name, author handle, and a single X on the right. no canvas, no nodes.
* **left sidebar, about a third of the width** (not measured): a "Description" heading with one sentence of what it does, an "Inputs" heading
  with a "Reset inputs" control, then one labelled field per exposed input (`Story Brief - Text`, a
  textarea), a full-width primary button, and the remaining credits under it.
* **main area**: the output, large, with a progress bar along the bottom of the frame labelled
  `Fusing 0/1`, and `Output  Prev  Run 1/1  Next` for more than one result.
* **there is exactly one action.** no re-roll beside generate, no settings. the input, the button, the
  result, and a way to step between results.

this is the whole of focus mode: a sentence, its inputs, a button, the result, and prev/next. it is small
enough to build, and it is the piece that lets someone use a preset without meeting the graph.

### what apps look like

*Getting Started with Fuser Apps* shows an app as an **input on the left, output on the right**: a
prompt field with a placeholder, a generated card, and a right-hand panel of configuration (selects,
toggles) when the app is being built. the published app is a page, not a canvas.

### still not settled

english captions were captured for **nine** of the nineteen videos (kept outside the repo, in the
conversation workspace) and read closely for three; nothing of the other ten is known. the four
downloaded videos are sampled, not watched. in particular nothing
here shows: how the selection pill animates in, what the library panel looks like, how a recipe's input
wiring is edited (only that it is), or any keyboard shortcut. the earlier statement that flowby has no
selection-to-preset, no focus mode and no marquee select still stands, and is now joined by a shape to
build rather than a name to argue about.

## flora's action catalog, read from their own API (2026-11-13)

With the owner signed in, `flora_search_actions` and `flora_get_action` answered directly, which is
better evidence than any marketing page. 42 prebuilt actions, every one `charged_cost: 0`, every one a
single code file whose header annotations (`@flora-name`, `-inputs`, `-outputs`, `-params` with `min`/
`max`/`step`/`visibleIf`) *are* its node definition. 19 run `python` (ffmpeg on files), 23 run
`javascript` with a `-browser` suffix (canvas/shader). The contract and what flowby took from it are in
`docs/actions.md`. The five names in the "Effects & looks" menu (Risograph, Halftone, Datamosh, Y2K VHS,
Line hatching) match Fuser's Tools list verbatim and return nothing from FLORA's action search, so that
menu is most likely Fuser's creative-code family.

## flora, read from its public site and docs (2026-11-13)

flora (florafauna.ai, now flora.ai) needs a login for the app, but its marketing site and its whole
documentation (docs.flora.ai, gitbook) are public, and the docs are precise about behaviour. read as
text, nothing here was watched or used: the app itself was not opened, so every claim below is what the
docs say a node does, not what the canvas looks like.

**what it is.** an "every model on one infinite canvas" tool: text, image, video, audio, 3D and document
nodes, 50+ models behind one subscription, plus an MCP server and an API so claude, chatgpt or codex can
drive a canvas. the page's own numbers: 20M generations, 17M nodes, 5M exports.

**the part that matters here: its nodes do not run on their own.** from *How Nodes Run*:

* running a node does **not** run what is upstream of it. an unready input shows "Can't run yet:
  waiting for the connected image to be ready". to run a chain you select it and press Run all, which
  runs in dependency order, up to 50 nodes, and the tooltip shows the node count and total cost first.
* changing an upstream node never re-runs downstream ones. they keep their last output until run again.
* **every run adds a generation to the node's history and the old ones are kept** (up to 1,000 per node).
  a strip of thumbnails sits under the node, and the *active* generation is the one that flows
  downstream. picking a different one and re-running downstream is how you compare.
* generating several outputs from one node is a counter (up to 20) with a setting for whether results
  go into the node's history or onto the canvas as separate copies.
* a failed run shows an error card with the reason and what to try, credits are refunded automatically,
  and there is no retry button: you just run it again. free accounts run one generation at a time and
  the rest show a clock and queue.
* a connected text node **replaces** the typed prompt rather than adding to it, and the node's own prompt
  box locks while it is connected. a prompt over the model's character limit disables Generate and says
  by how much; flora never silently trims it.

**techniques, which is flora's word for flowby's recipe.** *Technique Builder* turns a canvas workflow
into one reusable node: the canvas locks, you click the starting nodes that become **inputs** and the end
nodes that become **outputs**, name each (40 character description, optional toggle, up to 100 example
presets each), the graph is validated (no cycles, everything connected, no batch nodes multiplying out of
control), and you publish with a name, a 200 character description, an **automatically computed usage
cost**, a thumbnail, a category and visibility of private, workspace or community. the published thing can
run as a node or as a standalone app page with no canvas. this is the same idea as fuser's recipe and the
same shape as `scene.record`, which means three products agree on it independently.

**two other nodes worth knowing.**

* **router**: many sources in, one output, branchable to any number of nodes, and **transparent**: a
  downstream node resolves through it to the original sources and it adds no cost or step. it exists to
  stop one reference set being wired into five nodes. flowby's board preset already has the stronger
  version of this (a head that runs once), but flora's router is only a wiring convenience, not a shared
  computation.
* **elements**: a reusable reference built from up to eight images of one subject plus a category (model,
  character, product, object, material, setting, style, moodboard) and optional guidelines. flora studies
  the images and generates **one unified reference preview** with a history you can step back through, and
  you attach it to nodes or mention it in a prompt. this is the nearest thing flora has to a flowby
  **style**, minus training: it is made by inference, not by weights.

### what flora did that flowby should look at

* **a node keeps its history and the active one flows downstream.** flowby's sweep already produces
  several variants and `show_variant` picks one, but that is per preset instance and flora's is on every
  node. it is the cleaner model and the cost is one list per node.
* **"can't run yet" with the reason.** a refusal that names its cause is the same rule the compiler
  already follows (`compile` refuses by name before a browser opens), and flora applies it at the button.
* **never trimming input.** the prompt limit that disables the button instead of cutting is the right
  default for a tool that charges by the run.
* **the cost shown before the run, on the group.** flora puts it in the Run all tooltip, fuser in the
  selection pill, flowby now in the pill too. that is three for three.

### what flora is, set against flowby

flora's claim is breadth: every model, one price. it is subscription, cloud only, and freeform by
design, which is why its answer to repeatable work is Techniques that people publish rather than a fixed
catalogue of task cards. flowby's claim is the opposite order: a small set of task-named presets you can
open, running on a gpu you plug in. neither contradicts the other. the useful borrow is the *run model*
(explicit, ordered, never silent), not the surface.

## vectary canvas, re-checked (2026-11-13)

nothing on `vectary.com/canvas` has changed the picture in the section above: the page still sells a
single sentence (one canvas across 2D, 3D and AR, with presets that chain) and the launch video was
already watched frame by frame. the only new input is the owner's note that the login wall hides the
product but not the marketing videos, which is how both were read.

## the three clips the owner attached (2026-11-13)

three mp4 files were attached with the note about flora and vectary. two are the same file byte for byte
(a 3840x2160, 1.77 second h264 clip) and the third is a 480x270 downscale of it. all three show a short
brand animation for a company called **cardinal**: hand-drawn blob and asterisk shapes in coral, olive
and orange on cream, the words "build flows" circled twice, a "Good sales takes thinking creatively"
slide, and a logo lockup. it is not a screen recording of flora or vectary and shows no canvas, node or
preset, so it contributes nothing to the product findings above. if a different clip was meant, it did
not come through.

## vectary's preset picker, from the owner's two clips (2026-11-13)

the first three clips sent today were the wrong files (a brand animation). these two are the right ones:
`vectary1.mp4` (19.8s, 1200x1080) and `vectary2.mp4` (2:17, 1920x1080). nothing here was used in the app,
and the frames were read by on-screen text (tesseract) and by measuring pixels, not by eye, so the
layout claims are limited to what text and numbers can say.

### vectary2 is the launch video already in this file

the long clip is the same product film as the one described under *the vectary canvas launch video*
(five products, one reference then a grid of variants, sticky notes, a typeform embed, a live 3D scene),
so it adds confirmation and a few extra boards rather than new findings. what its on-screen text adds:

* **the breadcrumb is a workspace path**: `C26 / Work - Alberic / Voronoi mouse`, then `Canvas - Stool`,
  `Canvas - Trimmer`, `Canvas - Bike`, `Canvas - Packaging`, `Canvas - Fashion`. one canvas per
  product, filed under a project inside a workspace. the bottom of the video is `Demo / Recordings`.
* **a board names what the work is for**: `BRIEF W.26`, `Shape exploration`, `Development basis`, and
  a frame called `CAD views`. a preset result lands inside a named frame rather than loose.
* **a result can be a decision, not only a picture**: a vote card (`Which airvent shape`, Option A,
  B, C, powered by Typeform) sits on the canvas beside the generated options, and colours are named on
  the board (`Moody Blue`, `Cornflower Blue`, `Cobalt Blue`, `Powder Blue`, `Baby Pink`) with hex codes.
* **a node is a place to leave a note for a person**: `Let's try this orange fabric on the stool`,
  `@John can you bring the colors picked by the CMF team here`, `I would add the logo in bigger here
  in the center`. review happens on the board, addressed to people, next to the thing it is about.
* **refinement is a mode of the same node**: `Remove and inpaint` with `Draw mask (Double-click image to
  delete mask)`, `Edit image`, `Upscale 2x`, `Generate 3D`. the node stays one node.
* **a 3D result is a scene with an object list**: `Properties / Objects` lists `Back logo
  SQUARE_PLANE`, `Front logo SQUARE_PLANE`, `Rectangle Light 1`, and a `3D Embed` tab, so a generated
  model arrives as a scene a person can keep editing.
* **the last chapter is fashion**: `Fashion sketch to model`, `Match pose`, `Extract Pose`, and an
  `AI 3D Model` result, which is the sketch-to-model path flowby's `extract-pose` and `sketch-to-mesh`
  already approximate.

### vectary1: the picker itself

a 19.8 second capture of one image node (a brushed-metal device) with a second image beneath it (nine
grey shapes, one orange) and the picker open beside it. the picker scrolls through the whole list. what
is solid, from reading every frame at 5 per second:

* **layout**: a white card with rounded corners, a search field at the top (`Search presets`) with a
  **violet outline** (measured rgb 96,55,174, so a deep purple, not the pale lavender fuser uses), then
  a single scrolling column. the canvas behind it is flat light grey (measured 239,239,239) with a faint
  dot grid. the picker is anchored beside the node it will act on, joined to it by a thin wire.
* **a row is a thumbnail, a bold title and a two-line grey description.** the thumbnail is a small
  picture of what the preset does, not an icon. nothing else is on the row: no price, no model name, no
  badge. (the tabs `All`, `Images`, `Text`, `3D`, `Custom` that the longer clip shows sit above this
  list in the full UI; this capture crops them out.)
* **the titles carry the argument in a short suffix**: `Handheld move to detail (6s)` puts the duration
  in the name, `Interior - vacant room` / `Interior - pristine` / `Interior - paint job` / `Interior -
  clean up` / `Interior - refurbish & repurpose` is a **family sharing a prefix**, `View - Top` / `Left`
  / `Right` likewise, and a leading number counts the results: `4 Material sample extraction`, `4 Context
  aware shape variations`, `16 Design variations`, `4 Design Variations`, `16 Material variants`.

### the catalogue as it reads, in about 125 distinct titles

grouped by what they do (my grouping, the product shows one flat list):

* **extract and read an image**: Material sample extraction, Sphere material extraction, Depth Map,
  Normal Map, Extract pose - Depth map, Spherical map, Seam line, Isolate object, Isolate object - 4
  views, Isolate - White model, Remove Background, Precise Line Art, Line-art stencil, Color palette 3x3,
  Color code, Describe - Detail & Joinery, Describe - Material, Critique & Improvement suggestions.
* **variations, always with a count**: 4 Context aware shape variations, 16 Design variations, 4 Design
  variations, 16 Material variants, Color variations, Material variations.
* **change one thing**: Match pose, Match proportions, Match view, Match aesthetic, Match Design Language,
  Recolor, Replace material, Replace selected object, Add hands, Add realism, Add reflections (clear
  coat), Ground reflection, Ground object, Remove markings, Remove branding, Remove reflections, Remove
  and inpaint, Improve lighting, Night shot, Dark mode, Light mode, Ultra sharp focus, Strong depth of
  field, Focus selected, Enhance detail.
* **move between media**: Generate 3D (High), Retexture 3D, Generate texture, Seamless texture, Make
  tileable, HDRI texture, Generate 360-degree map for 3D, Sketch to photo, Simple pencil sketch, Dynamic
  Pen Sketch, Concept Marker Sketch, Architectural render to photo, 2D plan to 3D top-down interior,
  Product from technical drawing, Fashion sketch to model, Recreate graphics to flat 2D.
* **camera and views**: Camera orbits scene, Handheld move to detail (6s), View - Top / Left / Right,
  CAD views, CAD View - Top, Exploded view - marked, Detach - exploded view, Hero Asset (multi-view),
  Volumetric three-quarter perspective view.
* **reference boards**: Material Moodboard, Designer - surface cinema board, Design definition board,
  a reference board for style analysis, 4 part technical sheet.
* **interiors**: the five `Interior` rows above, plus Clear entire room or marked area.

### what this says about flowby's catalogue

flowby has **24 presets**. the picker lists roughly **125 titles**, and the two numbers are not the same
kind of number, because the owner's brief collapsed 29 bullets into 16 presets and 16 controls on
purpose. so the honest comparison is which *jobs* are missing, not which titles:

* **already covered by a preset or a control**: material extraction (`extract-material`), apply
  material (`apply-material`), texture maps and normal/depth (`texture-maps`), relight and improve
  lighting (`relight`, `studio-light`), replace selected object (`replace-object`), remove background
  (`cut-out`), swap environment (`swap-background`), extract pose (`extract-pose`), clean up a room
  (`clear-interior`), inpaint (`inpaint`), place graphic (`place-graphic`), sketch to render
  (`sketch-to-render`), sketch to mesh (`sketch-to-mesh`), layers to 3d (`layers-to-3d`).
* **a family that flowby models as one preset plus a control**: the five `Interior` rows and the `View -
  Top / Left / Right` rows are one job with a choice. vectary lists each as a row because a picker has
  no sliders; flowby's `surface-detail` already shows the other answer. **this is the strongest argument
  in the clip for keeping controls**, since 125 rows is what a menu without them looks like.
* **not in flowby, and each a plausible preset**: *views* (a multi-view or CAD-style sheet of one
  object, which is a sweep of four fixed cameras), *exploded view*, *describe* (a model reads the image
  and returns text, which would be the first preset that goes image to amber), *critique*, *match
  pose / proportions / view / aesthetic* (a reference image and a one-line instruction, which is a slot
  preset like `style-transfer`), *recolor*, *add or remove reflections*, *night shot* and *dark / light
  mode* (a relight with a fixed target), *seamless / tileable*, *HDRI*, *upscale*, *remove branding*,
  *technical drawing to product*, and the whole **reference board** family (a grid of swatches or
  views assembled into one image).

### the three things worth taking

1. **a count in the name.** `4 Material sample extraction` and `16 Design variations` tell the person
   how many results to expect before they press anything. flowby's sweep knows its count and prints it
   in the cost line, but the sidebar card does not lead with it. cheap to copy, and it is also the
   honest price signal, since six results cost six tails.
2. **a thumbnail of what the preset does.** every row is a picture, not an icon. this is the part
   flowby cannot copy cheaply, because a thumbnail is a rendered example per preset and flowby has not
   produced one asset yet. it is recorded as blocked on the first real worker, not as a styling task.
3. **a prefix family.** `Interior - ...` and `View - ...` group by shared first word with no header at
   all, so search for `interior` finds the family. flowby groups by stage; a prefix is an extra axis
   that costs nothing and answers a different question (what is this about, not when do I use it).

### what is deliberately not taken

* the **violet outline and the pale grey canvas**: flowby is dark only, and takes structure, not palette.
* a **flat list of every title**. flowby's sidebar offers what can apply now, and 125 rows is the thing a
  fixed catalogue does when it has no way to hide what would refuse.
* **thumbnails as the identity of a preset** until there is a real result to draw one from.

### limits of this pass

read by text and by measurement. what is *not* known: how the picker animates open, whether the list is
grouped under hidden headers, what a click does after it (the capture never selects a row), how long a
result takes to land, and whether the `Custom` tab is empty for a normal account (an earlier note says
custom presets are "coming soon" for teams). the title list came from OCR over a scrolling list, so a
few names above are best guesses at a misread (`Match aesth` is cut off, `Designer - surface cinema
board` is probably `Designer - surface cinema board 5` or similar), and the figure of about 125 is a
count of distinct strings after merging near-duplicates, not an official catalogue size.

## fuser's compositor, from the feature page and its docs (2026-11-13)

read at `fuser.studio/features/compositor` and `docs.fuser.studio/docs/compositor` and four of its
child pages. both serve clean **markdown** when `.md` is appended to the URL, which is how this was
read; nothing here was seen, only read, so no layout or motion claims.

### what it is

a full-screen editor that lives **inside one node**. click `Edit` on a Compositor node, get layers left,
canvas centre, eight-tool floating toolbar, context-aware properties right, then `Save` commits the
scene as the node's output and `Exit` returns to the flow. the earlier note in this file said the
compositor was "not taken" because "flowby has a frame and a scene already". that call stands for the
**editor**, which is a Figma-sized build (see the count below), but it was too quick about the rule the
editor exists to enforce, which is the interesting part and is recorded next.

### the rule: the scene is the source of truth, and inputs do not recompute geometry

this is the load-bearing sentence in the docs, and it is a refutation of the thing flowby currently
does:

> if you reconnect a different image to a Compositor input, the layer it represents keeps its existing
> position, size and rotation. the new image just replaces the pixel source. the first input you ever
> connect sets the canvas dimensions; later input changes don't resize the canvas.

so a compositor node is **stateful**. the graph feeds it pixels; it owns geometry. re-running upstream,
swapping a generation, A/B testing a model: the layout does not move. and the escape hatch is explicit:
`splitting an image into layers` turns a connected input into editable scene layers, after which "later
upstream changes will not overwrite that split group". pinning is a deliberate act, not a default.

in flowby the same property is true for a different reason: geometry lives on the **board** (tldraw
elements with transforms), and the graph only reads it. so "your layout doesn't shift when the pixels
change" already holds, and the price is paid in a licence instead of a scene object. that is worth
writing down because it is the clearest example yet of tldraw's non-commercial licence buying something
real: fuser built a scene object to get the rule, and flowby rented one.

### downstream output is not export

the compositor emits **the scene** on its socket. Image, Video and other Compositor nodes render that
scene themselves, live, with their own play/pause/scrub, and two compositors chain without re-encoding.
export (`Save Asset`: PNG at canvas size, or MP4 from `0:00` to `Duration`) is only for getting a file
out. the docs state the distinction twice, which suggests users conflate them constantly.

a scene is therefore a **candidate fifth wire type** in flowby's terms, and the four-colour rule says a
fifth thing gets a `role`, not a colour. scene-as-role-on-image is the consistent answer, since what
travels downstream is renderable pixels plus an editable stack, and the editable part is not a wire.

### the size of the thing, counted

* **twelve layer types**: rectangle, ellipse, vector, raster, eraser mask, text, image, video, 3D,
  adjustments, and **nested compositors** (the docs list groups separately, as an organising feature).
* **eight tools**, each with a one-key shortcut: select `V`, hand `H`, rectangle `R`, ellipse `O`,
  text `T`, pen `P`, brush `B`, eraser `E`. the pen's four point types map onto Figma's vocabulary
  (corner, smooth, asymmetric, auto with Catmull-Rom).
* **groups** parent layers with visibility, lock, opacity, blend and transform cascading to children;
  nesting allowed; grouping requires a common parent.
* **three masks**, chosen by what drives the reveal and by scope: per-layer alpha (a shape as a window),
  per-layer luminance (white shows, black hides, grey partly), and a **global alpha mask** for the whole
  scene (a circular preview, a custom frame, a TV-style mask).
* **variable fonts**: a text layer adjusts weight, width and optical size with sliders, and individual
  axes can be **animated** for a looping morph. this is the fontasy overlap, and it is the second product
  in this file to treat a font's axes as animatable state rather than a static choice.
* **3D**: import glTF/GLB with PBR materials, control rotation and scale in the canvas.
* **timeline**: only renders when the scene holds video or a non-zero `Duration`. several video layers
  share one clock, the longest sets the scene length unless overridden, and each video layer has its own
  independent `Loop`.
* **raster persistence**: painted pixels go to the project's media library and the scene records a
  reference, so project files stay small and scenes load asynchronously. an export waits for an
  in-flight upload; an inference node downstream may not.
* **multiplayer**: live cursors and selections, and **only one person may edit a given compositor at a
  time** (others see who has it open). with collaborators present, a minute idle closes the editor with
  a toast, saving first.
* **desktop and tablet only.** on a phone, compositor nodes "still display their output, but you can't
  open the editor."

### what i would take, and what i would not

**taken:**

1. **the desktop-only editor rule.** this is the answer to the defect measured on 2026-11-12: flowby's
   board opens at **21% zoom** on a 390px screen, which is unreadable before you select anything. fuser
   does not solve a phone canvas; it declines to open the editor there and keeps showing output. a phone
   is allowed to be a viewer. that is the cheapest honest fix available to flowby and it is in this
   build (see the note at the end of this file).
2. **a mask is a role, not a colour.** the three mask concepts fit flowby's existing rule exactly: an
   image wire with `role: mask`, with per-layer and global scope as a property of the consuming node.
   no fifth wire, no new palette entry.
3. **split-into-layers as the pin.** the idea that an input becomes editable the moment you say so, and
   stops being overwritten, is a better mental model than "detach" and costs one flag.
4. **variable-font axes as animatable state**, which is the same slope fontasy is already on.

**not taken:**

* the **editor itself**: twelve layer types, eight tools, groups, pen handles, blend modes, timeline and
  export is a product, not a preset system's side panel, and flowby's board already owns the geometry
  this editor exists to own.
* **scenes as a stored artefact with async media references.** flowby has no media library and no
  storage layer yet; copying the persistence model without the storage would be a lie in the shape of an
  architecture.
* **multiplayer**, for the same reason: presence is a backend feature and flowby has no accounts.

### the correction this page forced

the earlier entry said the compositor was "not taken: flowby has a frame and a scene already". the
second half was wrong in a useful way: flowby has a **board**, which is not the same as a scene that a
node owns and edits. the board is shared and always visible; fuser's scene is the output of one node. so
the honest statement is not "we have this already", it is "we get the layout-survives-swap property from
tldraw instead, and we do not have a node whose output is an editable stack". that distinction is now in
the vocabulary table's scope, since `board preset` is the only thing in flowby that currently reaches
across more than one frame.

### the note this build acted on: a phone is a viewer

the compositor page settles the defect measured on 2026-11-12. fuser does not try to make its editor
work on a phone; it keeps showing output and refuses to open the editor. flowby now does the same at
**760px**, the width fuser draws its own line at (tablet and up):

* `web/src/viewer.mjs` holds the rule and the words, and `web/tests/viewer.test.mjs` holds them still
  (nine tests, and eight mutations of the rule that the tests catch: an inclusive boundary, a string
  width being trusted, `unknown` reading as `free`, a cost block with no number reading as known, the
  total hiding its unknowns, and rows dropping nodes that have no cost).
* `Viewer.tsx` draws the graph as text: one row per node in graph order, the label, the op, one bar per
  rounded-up minute (violet when the node needs a gpu, grey otherwise), and the same price the pill
  would charge. the total is a **floor** and says so: `5.4 min at least, 2 not counted`.
* the toolbox is not drawn either, because "add node" with no canvas is a button that lies.

verified by DOM measurement in headless chrome, not by eye (integration credits are spent): at 1500px
the canvas is present and the list is absent; at 390px the canvas is absent, the list has **7 rows**,
the first row reads `the owl / element.sketch / free`, the total reads **5.4 min across 7 nodes**, which
agrees with python's own sum, and there is no horizontal overflow and no clipped row.

## bridgette: the import bridges, read to build psd import (2026-11-13)

`arsoninstigator/bridgette` is the owner's own repo, and it is the right shape for this: every domain
is `source reader -> shared model -> target writer`, with a readme that says what each crossing drops.

* `designs/` (imported from `kqrla/porter`) reads figma frames, psd, ai and eps into one `LayerNode`
  tree, and writes psd, svg, sketch, tiff, png and json back out. `ag-psd` (MIT) does the psd.
* the two ideas taken: the **layer tree** (`id, name, kind, path, depth, visible, effects, box`) and
  the **editable policy** (`locked / partial / customizable` plus flags for text, image, fill, stroke,
  position). a layer that looks editable and is not is worse than one that says it is locked.
* what was not taken: the writers. flowby's job ends at elements on a board, not at another file, and
  promising a psd round trip would be a claim nothing here could keep.

built from it: `web/src/psd.mjs` (walk + `boardPlan` + `FIDELITY`), `intake.sniff` recognises the
`8BPS` magic rather than the extension, and a dropped psd becomes one element per visible layer with a
place on the canvas. `ag-psd` is a dependency now (MIT, 31.x). fifteen tests, including one that writes
a layered psd with `writePsdBuffer`, reads it back and plans the board from the real bytes.

two honest findings from that test, both of which changed the code:

1. **ag-psd does not restore a text layer's size.** left and top come back, right and bottom return
   equal to them, so `w` and `h` read zero. so the plan reports `null` for an unsized layer and the host
   measures the words; placing a 0x0 card would have been a silent way to lose the text.
2. **a layer with no pixel data is a shape, not an image.** a psd whose layers carry no channel bytes
   yields `shape` layers, and `boardPlan` counts those rather than placing empty boxes.

### what illustrace's decoupling means for our style transfer

`tinkrland/illustrace` argues that "style similarity: 0.81" is a meaningless number, because style is
not one thing: mark-making, shape language, colour language, texture and rendering are separable, and a
transfer should move **one factor** while proving the others did not move.

* each transfer declares what must change and what must not, and returns a **delta vector across every
  factor**; the claim is a measured sentence, not a slider position.
* the target is a vector, not a strength: `{"stroke_roughness": 0.8, "palette": 0.0}`.
* stylebench underneath checks six things, and the two that matter here are *preserve non-requested
  attributes* and *prevent reference-content leakage*, which is exactly the failure flowby's
  `style-transfer` preset would inherit from a diffusion model left to its own judgement.

so the shape this implies for flowby is a change to `style-transfer` rather than a new preset: its
sliders become a factor vector, and its output carries a delta so the board can say "moved stroke
roughness 91%, colour changed 4%". not built, and the measurement half is the expensive part; recorded
here because it is a better contract than the one we have.

### vectary's preset families, as a backlog (not built)

from the 20-second picker clip, the families flowby does not have yet, in the order they are worth
building. the three at the top now exist as of this commit.

* **recolour to a palette** -> `swatch-swap`, `palette-9`. built.
* **view** (top, left, right, front) -> `view-ortho`. built.
* **exploded view, detach** -> needs `mesh.explode` before `view-ortho`, and a real mesh to explode.
* **remove reflections, improve lighting, night shot** -> `light.grade` variants; the ops exist and the
  difference between them is a parameter, which is what a control is for.
* **match pose, match proportions, match view** -> `pose.estimate` plus a comparison read; the honest
  blocker is that nothing here can yet say how far off the match is.
* **interior - vacant / pristine / paint job / clean up** -> `clear-interior` exists; the other three
  are scope variants of it.
* **make tileable, upscale 2x, edge cleanup, correct proportions** -> arithmetic on pixels, so they
  belong in the browser module next to `swatch.mjs`, not in a worker.
* **describe, critique** (image -> words) -> a text-producing preset, which this tree has only one of.
* **design variations with a count in the name** (`16 design variations`) -> the sweep already does
  this; what is missing is putting the count in the sidebar's label, as noted on 2026-11-13.
