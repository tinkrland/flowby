# 2026-11-07, later

*what the landing pages actually show, and the one feature it turned out we were missing*

## why this was worth doing

the copy on both sites had already been read and it said the right things: presets, recipes, visible steps, cost before the run. none of it said the shape.

two screenshots said the shape. on vectary, the explore section is not a picture of a result, it is a **4 by 3 grid of twelve variations of one mouse**, badged "4 Design variations, all rendered within minutes", sitting under a label that reads `Shape exploration`. on fuser, four of the first nine recipe descriptions in the library are fan-outs in words: *explore six lighting versions*, *explore japandi, art deco maximalist, dark academia, classical, and mid century modern variations*, *turn one logo into business card, letterhead, tote bag, socks, hat, and shirt mockups*.

flowby produced exactly one artifact per element. every preset was a single shot. the board could show one answer and the whole comparison step, which is where creative work actually happens, had nowhere to live.

## what got built for it

`Preset.sweep`: one slider, a discrete list of values, and a label. the compiler splits the subgraph at the swept node, runs the head once and copies the tail per value. `relight` ships as the example because fuser's recipe is one sentence and the sentence is the specification.

the numbers make the case better than the prose: six relights of one plate is **eight steps and 6.9 minutes**, one white-balance read and six renders, not twelve steps and 7.2. a loop would have been correct and five times more expensive.

three smaller things came out of the same look:

* the socket groups results **by element**, so six variants are one update on one frame rather than six updates that each overwrite the last. this is the bug that a fan-out introduces if nobody thinks about it, and it was caught by writing the test first.
* picking a variant is a pointer. `show_variant` moves what the frame draws, and compiling again still runs the whole fan, because the point of six results is comparing six results.
* vectary keeps **Properties and Presets as two tabs of one sidebar**, which is what `scene.sidebar` already returns: controls with real ranges. that was a confirmation rather than a change, and it is worth saying which of those two happened.

## what the screenshots cost and what they did not settle

the hero demos are autoplaying video inside a window frame, and they were sampled at intervals through screenshots rather than decoded frame by frame, so the notes in `docs/research.md` are observations and not a shot list. that is enough for a shape and not enough for choreography: nobody here knows how vectary animates a preset from card to result, and guessing would be the kind of detail that reads as knowledge and is not.

the next thing the fan makes obvious: a frame needs to *draw* six results, which is a contact sheet rather than an image, and `web/` still has no tldraw shape for anything. so the order has not changed, it has just gotten more specific.
