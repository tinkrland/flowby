# directory: how to read this repo

the rule is the same one the other repos here keep: **a folder with a readme is a description, a `.py` is the work.** if a behaviour changes, the module and the prose move in the same commit, and `tests/selftest.py` fails when they drift apart. that last part is not a metaphor: `Prose` in the suite reads this file and the readme and compares them to the registries.

## the shape

```
.
  readme.md                     what flowby is, the two views, and the honest state of each part
  directory.md                  this map
  bin/flowby                    the shim a clone runs
  src/flowby/                   everything that runs, and nothing that needs a web framework
    dtypes.py                   the four wires, the roles that ride green, and the refusal to coerce
    graph.py                    nodes, typed ports, wires, cycles, topological order
    presets.py                  the subgraphs a slider stands in for, plus slots and estimates
    scene.py                    elements as nodes with a position, the chain, and recipes
    compile.py                  the plan a shell script can run, flattened once
    modes.py                    the three doors in (freeform, fixed, style) and the
                                crossings between them, which the tests perform
    catalogue.py                the owner's 29 bullets as data, and what each one became
    routes.py                   where a job runs and what each place honestly cannot do
    job.py                      a plan's life, its illegal moves, its artifacts, its watchdog
    hub.py                      the fan-out to every board that is open, with replay
    cli.py                      the terminal view of a board
  kernel/
    kernel.sh                   what runs inside the disposable container: env, beats, steps, tar
    worker.py                   the far end: walks a flat plan, and refuses a model it does not have
  app/
    main.py                     the http binding: jobs, hooks, and the board socket
    tasks.py                    celery, and the one place that would open a browser
  web/
    src/align.mjs               the camera maths that makes the two canvases one board
    src/useAlignedCamera.ts     the react binding around it (designed, not built)
    src/graph.mjs               python's graph -> @xyflow nodes and edges, laid out by dagre
    src/anim.mjs                the motion spec: stagger, springs, draw-in, reduced motion
    src/wires.mjs               the four wire colours, mirrored from dtypes.py and tested
    src/NodeCanvas.tsx          the node layer: two node shapes, one edge shape, borrowed canvas
    src/main.tsx                the dev harness, which draws whatever `flowby graph` wrote
    tests/align.test.mjs        the maths, run under node
    tests/graph.test.mjs        the seam: palette drift, dangling wires, layout, overlaps
    tests/anim.test.mjs         the spec, including that reduced motion means none
    tests/dark.test.mjs         dark only: no light theme, no toggle, near-black page
  tests/selftest.py             the suite: stdlib only, no network, no gpu
  docs/
    presets.md                  how a preset is written, and what a good one has to say
    compute.md                  the routing loop, the colab seams, and the failure modes
    frontend.md                 two canvases, one camera, and why the toggle is cheap
    research.md                 what vectary canvas and fuser already know, and what was taken
  theidea/
    main.md                     the owner's brief, kept as written
    decisions.md                the decisions this tree makes on top of it
  journal/
    2026-11-07.md               the day the board existed and the graph under it
    2026-11-07-what-the-videos-showed.md
                                the visual pass, and the fan-out it turned up
    2026-11-07-scope.md         the benefits table with one row missing, and board presets
    2026-11-07-borrow-the-canvas.md
                                @xyflow and dagre instead of a hand-rolled node ui
    2026-11-07-the-brief-as-data.md
                                twenty-nine bullets, sixteen presets, sixteen controls
    2026-11-07-three-doors.md   freeform, fixed and style, and why a door you cannot
                                leave is a product and not a mode
    2026-11-07-the-models-were-the-point.md
                                crease is a diffusion pass, and the absence of a model
                                became a test
```

two things are deliberately absent from `src/`. there is no database layer, so a board lives in memory and the cli builds its own; and there is no queue, so `job.Store` is a dict with a state machine rather than redis. both are seams the app layer is expected to fill, and neither changes a single rule above them.

## how a change travels

a preset added to `presets.py` shows up in the sidebar, the legend, the cli, the plan and the suite without anything else being edited, because every one of those reads the same registry. that is the test of whether a module is in the right place: adding to it should not require touching the layers around it.

a new wire is the one change that is not local, which is why `dtypes.py` is four lines of data and a refusal. if a fifth colour is ever right, it will be because a whole class of asset has nowhere to go, and the argument belongs in `docs/presets.md` before it belongs in code.
