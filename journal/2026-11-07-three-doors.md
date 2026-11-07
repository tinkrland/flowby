# 2026-11-07, three doors

*the correction that came with a link i could not open*

the framing offered was: flowby bridges **freeform** (fuser leads with a prompt), **fixed presets** (vectary leads with a card), and **style transfer** (base44's studio, in alpha, leads with a reference and carries it).

that is three products described in one sentence, and the sentence is only useful if the three are one thing. so the job was not to add a third mode. it was to state the crossings and then do them:

* freeform into fixed: apply a preset to a text element, and the words you typed are still a node with a `text` parameter, wired into a `text.compose` above the image model. the difference between a prompt box and a prompt node is whether you can rewire it afterwards.
* fixed into freeform: `scene.show` a frame at an intermediate node of its own preset. the frame now draws the depth pass instead of the mesh, which is the smallest possible proof that the card was a graph all along.
* style into fixed: `scene.show` a frame at the *shared head* of a board preset, so it draws the palette rather than the grade. the preset stays applied; what changed is which node the frame is pointed at.
* style into freeform: `style-transfer` refuses to compile with a sentence naming its missing reference wire, and `link` fills it from another frame. a refusal that is also the instruction is the whole ergonomic argument for slots.

`bin/flowby modes` prints all of it and asserts `every door reaches every other`, and six tests perform the crossings rather than trusting the table, because the table was the optimistic artifact.

## the part that did not happen

i could not look at studio.base44.com. it is an app behind base44's own sso (`app_id=6a6f3b530ae563a8d04fdc18`), the marketing path is a 404, the docs index has no entry, and a fresh browser has no session. so the style door is modelled from the description.

which is worth being precise about, because "i looked at it" and "i built something that behaves like the description of it" are different claims and only one of them is true. the crossings are verified. the appraisal is not. `docs/research.md` says which is which, and what three questions would settle it in one signed-in session: is a style chosen from a library or extracted from an upload, what is a kept style called, and does it reach one artifact or a whole project.

## the shape that fell out

three modes, one graph, and one rule that keeps them honest: **a mode you cannot leave is a product, not a mode.** that is now a test (`every door reaches every other`), and it is the reason `modes.py` is a registry of crossings rather than a list of features.

it also settles where the next work goes. the crossings are cheap because every door lands on the same scene: nothing had to be converted, only pointed at. what is expensive is the thing none of the three doors can do yet, which is draw a frame that shows six results at once.
