# the dashboard: four tabs, and what an artifact is

the owner's description (2026-11-07): the dashboard has tabs for **assets**, **artifacts** and
**boards**, aside from just projects, and "artifacts are the outputs". this file records what was
built for the artifacts tab and what was only decided.

## the four tabs

| tab | the question it answers | what already exists | state |
| --- | --- | --- | --- |
| projects | which piece of work is this part of | nothing | **not built** |
| boards | where is the spatial work | `scene.Scene`, the board that holds elements | exists, no list view |
| assets | what came in | asset digests (`sha256:...`) on elements | exists as hashes, no tab |
| artifacts | what came out | `artifacts.py` | **built, tested, simulated bytes only** |

only the artifacts tab has code. the other three are named so the model has somewhere to hang, not
because they are done. in particular **no tab has a user interface**: `artifacts.tab()` returns the
rows a tab would render, and nothing draws them.

## an artifact is not a wire

the four wires say what flows *between* nodes. an artifact is what leaves the graph, and the two
questions have different answers. a font is the case that forced the split: nobody wires a font into
a paint step, so it is not a fifth colour. it is also not an image, and it is a **bundle**. the same
outlines leave as .otf, .ttf, .woff and .woff2, and a lone .woff is a worse deliverable than the
set. so an artifact has a `kind`, a `bundle` of files, and a `source` (which board and job made it),
and the compiler now gets its file suffix from here instead of a private table.

kinds: image, video, model (a mesh wire ends as a glb), text, **font**, **lettering**, and **lora**
(the adapter a style trains is an output like any other, so it lands in the same tab).

## fonts, from the owner's three repos

read from fresh clones of kqrla/fontasy, kqrla/fontasy-mask and kqrla/fontasy_fork.

* **fontasy** (MIT): handwriting scan to font. detect glyphs by connected components, group into
  rows, trace contours (moore), simplify (douglas-peucker), smooth (catmull-rom to bezier), export
  .otf/.ttf/.woff/.woff2 through opentype.js. 101 characters. runs entirely in the browser.
* **fontasy-mask**: pattern lettering (gingham, polka, stripes, checkered) with edge stitching and
  fabric texture over any text. outputs PNG and SVG.
* **fontasy_fork**: fontasy plus **alphabetic, dingbat and bead modes**, k-means colour zones, five
  texture modes (clean, rough, crayon, pencil, chalk), and video-frame extraction.

three findings that change what a font artifact is:

1. **fontasy-mask's "SVG" is not vector.** `download SVG` wraps `canvas.toDataURL('image/png')` in
   an `<image>` tag (fontasy-mask/web/index.html, line 490), so the file is a raster in an SVG
   envelope. only its figma plugin produces real vectors. the `lettering` kind therefore says
   `png` is primary, and a real-vector claim would be wrong for the web version.
2. **none of the three runs headless.** all depend on `createImageBitmap`, `OffscreenCanvas` and the
   DOM, and load opentype.js and jszip from a CDN. flowby's worker is python on a bare container.
   using fontasy means running it in a browser (the `colab-browserbase` route already drives one) or
   porting the pipeline. neither is done.
3. **licences differ.** fontasy is MIT. fontasy-mask and fontasy_fork have no LICENSE file in the
   clone, which under default copyright means no permission is granted to others. the owner wrote
   them, so this is theirs to settle, but a font tool in a public repo should say.

a font also has to be a font: `check_font` refuses one with no family name (every app would list it
"Untitled") or no stated codepoints, and `coverage()` reports what share of basic latin it maps, so
a practice sheet that only had uppercase files as a **partial** font with `lowercase, digits` listed
as missing instead of passing as complete.

## what is and is not true

* **no font has been made.** `file_artifact("font", ...)` checks files that are handed to it. nothing
  runs fontasy, so every font artifact in the tests is a fixture with fake hashes.
* **simulated is the default.** an artifact says `simulated: true` until bytes from a real worker
  have been checked, and its lineage line says so.
* **opentype.js is the dependency that matters.** the pipeline's output step is one library on a
  CDN; pinning and vendoring it is the first thing a port would do.
* **woff2 is not real in fontasy.** its own readme says woff2 "falls back to woff", and its roadmap
  lists proper brotli compression as unbuilt. flowby should not list a woff2 as an output until it
  is one.

## how a font gets into the seven kinds

a font is an **artifact kind**, not a kind of thing the user reaches for. but the thing that makes
one, the handwriting-to-font pipeline, is a **factory** on the owner's ladder (an editable-asset
mini-generator), and it is the first concrete one. that is a proposal, and the owner has said
factories come later.
