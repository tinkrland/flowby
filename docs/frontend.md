# frontend

*two canvases, one camera, and why the toggle is cheap*

## the problem the brief does not mention

tldraw draws the spatial layer into a dom canvas it owns, and its camera is a `{x, y, z}` it updates on every pan and zoom. react-three-fiber draws into a second canvas. those two agree only if the webgl camera is **derived from tldraw's on every frame**, and only if the derivation is a pure function, because a camera that lags by one frame looks exactly like a bug in three.js.

so the arithmetic is the product. it lives in `web/src/align.mjs`, has no imports, and is tested under node:

```
screen = (page - camera.xy) * camera.z
```

that single convention means the camera's x and y are the page coordinates of the container's top-left, and z is the scale. everything else falls out of it:

| function | answers |
| --- | --- |
| `cameraFromTldraw` | converts tldraw's screen-space translation into that convention |
| `visiblePage` | the page rectangle the container is showing |
| `pageToScene` / `sceneToPage` | page coordinates into the space three.js objects are positioned in |
| `orthoFrustum` | the orthographic frustum, in page units, with the zoom baked in |
| `disagreement` | the corner error between the two layers, in css pixels, for a dev overlay |

**the zoom goes in the frustum, never in the object.** a 12cm mesh next to a 12cm sketch stays the same size when the board zooms because nothing in the scene is scaled; the camera's projection changed. this is the one rule that keeps a hybrid board from feeling like a 3d viewer pasted onto a 2d tool.

`node --test web/tests/align.test.mjs` runs eight tests over that file, including corner agreement at four zooms and offsets, a screen round trip, the frustum carrying the zoom, the tldraw conversion landing on the same pixel under both conventions, and a zero-scale camera being refused rather than divided by.

## the toggle, and why it is not a second app

"inspect pipeline" is a view, not a mode. the graph does not change when you flip it, and it is not rebuilt: the inspector is another `Hub` subscriber, it opens, it replays the last messages for that board, and it agrees with what is on screen. that is why switching costs one round trip and never a re-render of the scene.

the spatial view and the pipeline view read the same two projections of the same graph, which is the point of `scene.board()` and `scene.pipeline()` returning plain dicts from one source:

```python
scene.board()      # elements: kind, plane, transform, what dtype they are drawing
scene.pipeline()   # nodes with positions, params, typed ports, and wires coloured by dtype
```

## what a frame is

a frame is an element, and an element is a node with a position. clicking one opens `scene.sidebar(element_id)`, which returns exactly the presets that can be applied to what that frame is **currently showing**, each with its controls, its estimated cost, its stage, and the state of any slot it has not filled.

the sidebar is the whole product in one function, so it is the one thing worth reading before building a component: if a control is not in that payload, the frontend should not invent it.

## what is built and what is not

| part | state |
| --- | --- |
| the camera maths | verified, `node --test` |
| the react binding (`useAlignedCamera.ts`) | designed, no `node_modules` here |
| a tldraw custom shape that draws a mesh | **not written** |
| the sidebar, the container, the overlay | **not written** |

the missing tldraw shape is the next real decision rather than a missing file: a mesh cannot be a native tldraw shape, so a 3d element is either a proxy shape that carries an asset id and lets the r3f overlay draw the pixels on top of it, or a snapshot shape that renders to a texture. the proxy is cheaper and keeps the mesh live; the snapshot is what you want for a hundred meshes on one board. that choice belongs in this document with measurements attached, which is why it is not made here.
