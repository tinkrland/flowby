# 2026-11-07, the models were the point

*the correction: they are connecting ai models, and the surface words are the door*

i had the shape of it wrong by exactly one layer. i read the four families (texturing and materials, surface details, lighting and environments, design and ideation) and concluded the catalogue was organised by **surface rather than by model**, then built `surface-detail` as a procedural carve: `mesh.read` made a depth guide, `mesh.detail` displaced geometry from it, and nothing was inferred anywhere.

wrong. crease, stitch, emboss and deboss are **diffusion passes**. "generate physical pbr textures" is a model. the whole reason the catalogue can say *crease* instead of model names is that a model is behind the word doing the work, and swapping which one is a detail the word is designed to hide.

## what that changed, and where

`surface-detail` is three nodes instead of two:

* `mesh.read` takes the mesh and makes a depth guide (geometry, trimesh, honest)
* `detail.paint` takes the guide and a **sentence** and returns a detail map (`flux-depth-lora`, 1.4 min on a gpu)
* `mesh.relief` applies the map to the geometry (geometry again, no model)

so the choice control carries a prompt fragment rather than a mode name, and `deboss` reaches the model as *"a recess cut into the surface, as in a stamped logo"*. an hour earlier i had "fixed" the same control the other way, to identity pairs, on the reasoning that a mode name should arrive as itself. it should, when it lands on a switch. it lands on a model, so it should land as language. the bug was a correct rule applied to the wrong node, which is the kind of thing only looking at the node type can settle.

## and the absence became checkable

the two products are right, and the useful thing about being corrected is not the apology, it is the invariant. so:

* `presets.PROCEDURAL` is a written list of the three presets that honestly call no model: shading maths on a material, a camera move and a render, and your own code in the container. each with a sentence saying why.
* a test refuses a preset that names no model and has no reason, which is the shape of a preset that quietly does nothing.
* a second test refuses a stale excuse, so the list cannot outlive the preset it excused.
* `bin/flowby presets` prints the model next to the name, and the readme table has a model column, so the claim is visible where a person looks rather than buried in `requires`.
* a prose test reads the census back out of the readme, so the docs cannot drift from the models list the way they drifted from the truth today.

six of nine presets are model calls. the three that are not are shading maths, a camera move, and your own code, and now the tree says so out loud instead of leaving me to infer it and get it wrong.

## the general rule this leaves behind

a friendly label is a promise that the thing under it is doing more work than the label says. every time this tree names something in a designer's vocabulary (crease, warmth, frosted glass), there has to be a model or a node genuinely earning the simplicity. the failure mode is a word that sounds expensive and compiles to arithmetic, because it is indistinguishable from a feature and costs nothing to ship.
