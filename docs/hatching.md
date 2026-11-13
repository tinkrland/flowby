# hatching: a shader in the browser, ported to a file operation

Read 2026-11-13 from Amagi's pen "Hatching Effect with VFX-JS" (`codepen.io/fand/pen/RNovGmR`), whose
GLSL I pulled out of the pen itself because CodePen is behind Cloudflare: `cdpn.io/fand/fullpage/RNovGmR`
serves the whole pen unauthenticated, and the fragment shader is in it verbatim. This page is what that
shader actually does, and what it became in `actions/hatching.py`.

## what the shader does

The effect is not "draw lines over a picture". It is a halftone-shaped screen whose *cells are strokes*,
and four decisions are what make the result read as drawn rather than printed:

**Strips, indexed along one normal.** `baseIndex = floor(dot(px, normal) / spacing)`, exactly like a
halftone screen's cell index. Everything after this is per-index jitter.

**Every strip has its own angle, spacing and pivot.** For strip `i`, with `h()` the noise:

```
angle_i  = angle + (h(i*1.37 + seed) - 0.5) * angleJitter
centre_i = (i + 0.5) * spacing + (h(i*3.91 + seed) - 0.5) * 2 * spacingJitter
drift_i  = (h(i*7.13 + seed) * 2 - 1) * jitterFrac * 0.5 * extent
pivot_i  = normal * centre_i + along * drift_i
```

The third line is the one that is easy to miss and hard to live without: the strip's pivot is pushed
*along* its own direction, so a tilted strip walks away from where the spacing put it. Parallel strips
whose only difference is angle look mechanical; strips that also drift look drawn. The shader widens its
neighbour search (`K`) to cover that drift, which is the giveaway that the author knew this mattered.

**The stroke is a capsule, not a clipped band.** The shader finds the nearest *covered* point on the
strip's centreline within half a pen (`g`), then inks where `sqrt(dperp² + g²) < hw`. That is a capsule
built around the part of the line inside the region: thick along the middle, round at the ends, and it
terminates in an arc at the silhouette. A strip merely multiplied by a mask ends in a square cut, which
is the difference between a hatch and a fill pattern.

**Overhang is where the ink stops, not where the line goes.** `offsetJitter` shifts *coverage* along the
line (`base = foot - s * dir`) while ink is measured at `foot`. So the stroke's ends wander in and out
along their own direction by up to `offsetJitter`, which is what stops ninety strokes from all starting
on the same edge.

Two smaller things: overlapping strips take the **max** ink, so a crossing is no darker than a line; and
`originalColor` lets the stroke take the colour underneath it instead of one flat ink.

## what became PIL

Per-pixel distance fields are not available at this size without numpy, and pulling numpy in for one
action is a poor trade, so the same geometry is rasterised instead:

| shader | here |
| --- | --- |
| strip centreline | a 1 px line through the jittered pivot, `ImageDraw.line` |
| "the part inside the region" | `multiply` of that line with the region mask, itself `offset` by `−s·dir` |
| max over strips | `ImageChops.lighter` over every strip's covered span |
| capsule around the covered span | one dilation for the whole file: union of the span mask and a disc's offsets |
| nearest covered point, sub-pixel `g` | the dilation's disc, which is the same set of pixels, reached in one pass |
| flat or sampled stroke colour | `Image.composite` with either the ink colour or the source itself |

One dilation for the whole file rather than one per stroke is what keeps it fast: 960×540 hatches in
about a second, where a per-strip thickening would have been hundreds of full-canvas passes.

Params carried across with the shader's own names (`angle`, `spacing`, `width`, `angleJitter`,
`spacingJitter`, `offsetJitter`, `seed`, and the colour option) so the technique stays recognisable;
`roundCap`, `soft`, `speed`, `bypass` and `originalColor`-as-a-flag became either the only behaviour
(caps are round, `soft` is the disc edge) or the `ink` choice. `speed` only existed to re-roll the jitter
over time, and a file operation has no time.

## the one deliberate difference: ink stays inside the silhouette

The shader thickens a centreline that is *already* clipped, so its capsule spills half a pen past the
shape's edge. Over a DOM element that is invisible: the element's box is bigger than its glyphs. Painting
into a picture, the same spill is a ring of dark pixels on transparent ones, a fringe on anything
composited underneath.

So the dilate happens first and the clip after: `stroke = multiply(dilate(spans), region)`. The visible
difference is that a stroke's end is the half-disc that falls inside the shape rather than the whole
disc straddling the edge. The test that caught this (`test_a_stroke_never_extends_the_shape`) was written
expecting zero and failed with 494 pixels; the fix was in the action, not the test.

## `tone`, which is flowby's and not the pen's

The pen hatches DOM elements, whose *alpha* is the region, so every stroke is equally warranted. A
photograph has no alpha: hatching it uniformly is wallpaper. `tone` multiplies the ink by darkness
(`0` leaves the stroke untouched, `1` inks only where the picture is dark), which is what a person means
by "hatch this". It is marked as an addition in the action's own docstring, and it defaults to 0.6.

## where the rest of this family should come from

The point the owner made, and it is right: this whole layer is deterministic code, and there is a decade
of it already written in two specific places.

- **CSS Houdini's Painting API** (`CSS.paintWorklet.addModule(...)`) is a real, standard way to paint a
  background procedurally from a class with a `paint(ctx, size, props)` method, i.e. exactly the shape an
  action's `run()` already has, with custom properties as params. Any worklet is a candidate action.
- **SVG filter chains** need no JS at all: `feTurbulence` for noise, `feDisplacementMap` for the scratchy
  edge that makes a clean vector look hand-drawn, `feMorphology` to roughen, `feTurbulence` + 
  `feComponentTransfer` for grain. These are in every browser and are pure functions of their inputs,
  which is the best possible fit for an action whose promise is "same seed, same picture".
- **The pen's own library**, `@vfx-js/core`, rasterises a DOM element to a canvas and runs a fragment
  shader over it, which is the browser-side runner this port would eventually move into.

Not read yet, and therefore not claimed: any specific Houdini worklet's source. This page records one
shader read end to end, not a survey.
