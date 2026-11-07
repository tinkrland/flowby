# 2026-11-07, borrow the canvas

*@xyflow for the nodes, dagre for the layout, and a licence problem found on the way*

the instruction was blunt and correct: don't reinvent the node ui. so the node layer is now **@xyflow/react** (React Flow 12, MIT) drawing the boxes and **@dagrejs/dagre** (MIT, the layered layout engine) deciding where they go. the only thing left in this repo is what only this repo has: python's graph, the seam that turns it into nodes, and the camera handshake with the spatial layer.

the choice among the OSS options came down to one line of arithmetic. React Flow's viewport is `screen = page * zoom + translate`. `align.mjs` already converts tldraw's camera of exactly that shape into this repo's `screen = (page - camera.xy) * camera.z`. so the node canvas and the spatial canvas share a coordinate convention through a function that already exists and already has a test. LiteGraph would have meant fighting a canvas renderer for a look; Rete would have meant adopting its dataflow semantics; Drawflow and jsPlumb are further from the problem than the problem is.

## what this deleted

a second layout system. `scene.pipeline()` was inventing a grid in python (`320 + column * 240`, `index * 160 + row * 60`) which the renderer would then have laid out again with its own engine. two systems, disagreeing by default, and any node a person dragged lost on the next render. python now emits `rank` (depth, which dagre turns into columns) and `row` (which element a node hangs off), and geometry has one owner. the test that used to assert `pos.x` now asserts that `pos` is **absent**, which is the better assertion: it fails if anyone reintroduces the second layout.

## what it exposed

`web` had never been built. its package.json named `@tldraw/tldraw@^2.6.1`, a package and version that do not exist, so `npm install` always failed, which is why there was no tsconfig and no node_modules and why `useAlignedCamera.ts` had eight type errors nobody could have seen. all of that is fixed: `tldraw@2.4.6`, a tsconfig, `@types/react-dom`, and a hook that typechecks.

and the fix surfaced a licence question, which i got wrong on the first pass and the owner caught.
i read the npm tarball, which ships a one-line stub pointing at the repository's *current* licence,
and concluded tldraw had gone non-open. the terms are per tag: **2.0.0 through 3.x is the tldraw
License, non-commercial only; 4.0.0 rewrote it to forbid production use without a key** and added
enforcement. so: source-available, not open source, on every version we could use, but with no key
and no watermark in development on 2.x. the owner's instinct ("tldraw is still open") is right about
the source and wrong about the licence, and the distinction is the whole thing.

so the spatial layer is on loan at `tldraw@2.4.6` and decision 11 lists the three exits: buy it,
take the watermark, or swap in an MIT canvas. the swap is contained because the coordinate contract
lives in `align.mjs` behind a pure function, so only `useAlignedCamera.ts` and the spatial component
would change. the node layer has no such question: MIT, no version of it.

## verified, not assumed

the canvas builds (`tsc --noEmit`, `vite build`, 388 kB) and 12 node tests cover the seam from node with no DOM: the browser palette is compared against `bin/flowby --json legend` so a wire colour cannot drift, a wire into a port that does not exist refuses by name, the layout is deterministic across two runs, no two nodes overlap, and every edge runs left to right along the depth python reports.

then it was actually rendered and screenshotted: 7 nodes, 5 wires, 12 handles, minimap and controls, the owl's chain in green and red and the caption's text wire in amber. a build passing is not proof that a canvas drew something.

123 python, 20 node.
