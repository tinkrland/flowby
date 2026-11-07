# 2026-11-07, the brief as data

*29 bullets, 16 presets, 16 controls*

the tool list arrived as a tree: materials, surfaces, lighting, 2d to 3d, scene curation, each with sections and then tools and then controls under them. the tempting move is to read it as a backlog of 29 presets. that would be vectary with a worse sidebar, and it would be worse in a way worth naming: twenty-nine model calls in a list is a menu, and the argument this project makes is that the list should be short and the graph behind each entry long.

so the first work was a decision per bullet, and the decision rule turned out to be one sentence: **a bullet is a preset if it changes what the graph produces, and a control if it changes a number or a word the same graph already takes.**

under that rule the list collapses hard, and the collapses are the interesting part:

* `roughness intensity`, `metalness intensity`, `opacity control`, `emission maps` and `normal maps` are five bullets and five sliders on one node of one preset. four are params of the paint step; the fifth is a sobel pass over the height that step already produced, which is why it is a strength slider rather than a preset called "normal maps".
* `crease`, `stitch`, `emboss`, `deboss` are four bullets and four values of `surface-detail.detail`, because the node they land on is a diffusion pass that takes a sentence. this is the correction from earlier today, still holding.
* `skate park` and `outdoor option presets` are the same control twice: a place is a choice, not a preset each.
* `explore material variations` is a **sweep**, which is the one bullet whose shape needed the compiler rather than the sidebar. six finishes now cost one unwrap and six paints: nine steps, seven artifacts. if it had been six presets the unwrap would run six times and someone would have called that a feature.

## what made it checkable

`catalogue.py` holds the brief as data: groups, sections, tools, and for each tool either the preset it is or the preset and control it moves. `coverage()` refuses a bullet that resolves to nothing, a control naming a slider that does not exist, a preset no bullet names, and a primitive whose excuse has outlived its reason. `bin/flowby catalogue` prints the whole mapping and exits non-zero on a gap.

the second half of that discipline: seven presets in the registry are not in the brief at all, and they are written down in `catalogue.PRIMITIVES` with a reason each. `text-to-image` is there because the brief assumes somewhere to put words. `relight` is there because one cheap light is the primitive that `studio-light` and `environment` scale. an absence is a claim somebody made, which is the rule `PROCEDURAL` already applies to models, and it reads the same in both places.

## the two presets that needed something new

`apply-material` is the first preset in the tree that has a **slot and a sweep at once**, which is a shape the compiler had never been asked for: the material set arrives as a second asset, and the six finishes are branches after the unwrap. it compiles to one unwrap and six paints, and `test_every_preset_compiles_once_its_slots_are_filled` now walks every preset in the registry and fills its slots, because a preset that only exists in the sidebar is not a preset.

`environment` is the first preset that passes geometry *through* a step that does not consume it: `place` builds the scene and hands the mesh on untouched, so the relight has both a subject and somewhere for its reflections to come from. that is a passthrough port, and it was worth a node rather than a rule.

## where the count stopped

23 presets, 19 of them calling 15 models, and four that say why they do not. 122 python tests and 8 node tests. and a number that will be the useful one to watch: 29 bullets is now a test, so when the brief grows the suite says so instead of the readme quietly lagging.
