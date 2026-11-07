# presets

*how a task gets written down, and what a good one has to say out loud*

## the shape

a preset is a frozen dataclass in `presets.py` with seven load-bearing fields.

| field | what it is | what goes wrong without it |
| --- | --- | --- |
| `name` | the id, kebab, stable | a saved recipe cannot be replayed |
| `label` | the sentence in the sidebar | the menu reads like a model list |
| `applies_to`, `input_dtype` | what it reads | it gets offered on frames it will refuse |
| `entry`, `entry_port` | where the frame's wire lands | there is no way to know which node is first |
| `sink` | which node's output the frame draws | it compiles but nothing displays |
| `steps`, `edges` | the actual subgraph | the abstraction has nothing underneath it |
| `sliders` | the parameters a person may touch | the sidebar is empty and every edit is a number |

plus three optional ones that are worth knowing before you write a preset that needs them: `slots` (an input the preset cannot fill itself), `stage` (which of the four moves it belongs to), and `flips_plane` (whether it changes the frame's dimensionality).

## writing the steps

a step is an op, a label, typed ports, default params, and a `requires` block.

```python
"mould": Step(
    op="mesh.triposr",
    label="build the mesh",
    inputs={"control": image("depth")},
    outputs={"out": Port("mesh")},
    params={"target_faces": 60000, "guidance": 4.5},
    requires={"pip": ["trimesh", "torch"], "models": ["triposr"],
              "gpu": True, "minutes": 3.2},
)
```

`requires` is not decoration. `pip` and `models` become the plan's environment, `gpu` decides which routes will take the job, and `minutes` is the cost shown before anything runs. a step that lies about its minutes is a step that makes the whole route table lie.

the labels are the part people skip. they are what the node view shows, and the node view is read by someone debugging at 2am, so they are sentences about the work and not restatements of the op name.

## writing the sliders

a slider is a human range, a machine range, and the sentence that connects them.

```python
"detail": Slider(
    name="detail", label="surface detail", low=4000, high=150000, default=60000,
    means="the polygon budget. detail you can see, at the price of load time.",
    targets=(Target("mould", "target_faces"),),
    unit=" faces",
)
```

`Target("mould", "target_faces")` with no bounds means the slider's number goes through unchanged. `Target("rig", "frames", 48, 360)` means the slider says seconds and the node receives frames, which is the entire abstraction this product is selling: **a person sets 5 seconds, the graph receives 120 frames**, and neither view has to know about the other.

two rules a slider has to obey, both enforced at import and both tested:

* its default must project. a choice slider defaulting to `0` is a typo that makes every application of the preset throw, so `Slider.__post_init__` refuses it while the module is loading.
* its targets must exist. `Preset.__post_init__` checks every target against the step's params, so a renamed parameter fails at import instead of at the third click.

## when a bullet is a preset and when it is a slider

a catalogue arrives as a tree four levels deep and flowby is three, so the first job on any new
bullet is deciding which level it belongs to. the test is not "does it feel like a feature":

**a bullet is a preset if it changes what the graph produces. it is a control if it changes a number
or a word the same graph already takes.**

`roughness intensity` changes a number the pbr node already takes, so it is a slider. `normal maps`
looks like a preset and is not: the map is derived from the height the paint step already made, by a
sobel pass, so it is a slider on the strength of an edge that already exists. `extract materials`
produces something that did not exist, so it is a preset.

three consequences, and each of them is a test:

* **a control has to name a parameter that exists.** `catalogue.Tool.control` has to resolve to a
  slider on that preset, and `coverage()` says which bullet is misfiled if it does not. this is what
  stops a sidebar growing a slider nobody wired.
* **a word that arrives at a model is a choice, not a mode.** `crease`, `stitch`, `emboss` and
  `deboss` are four values of `surface-detail.detail`, and each value is a prompt fragment, because
  the node they land on is a diffusion pass. see the correction in `docs/research.md`.
* **a bullet that asks to explore is a sweep.** `explore material variations` is
  `apply-material.finish` with six values, which the compiler turns into one unwrap and six paints.
  if it were six presets, the unwrap would happen six times and somebody would call that a feature.

the reverse case is worth stating too: a preset the brief never names has to be declared in
`catalogue.PRIMITIVES` with a reason, exactly like `presets.PROCEDURAL` for models. `text-to-image`
is not in the brief because the brief assumes it, and saying so is cheaper than discovering the gap
later.

## what a preset is not allowed to do

the three refusals are the product's constitution.

**it cannot read a wire it did not declare.** `graph.add_edge` compares dtypes and refuses with both colours named. there is no casting rule to appeal to.

**it cannot fill an input it needs from somewhere it does not own.** that is a slot, and an unfilled slot makes the preset incomplete rather than silently wrong.

**it cannot hide a step.** `detach` exists, so every node a preset spawns is a node an advanced user can wire to, re-parameterise, or delete.

## adding one

four files, in this order, and the suite tells you when you have forgotten the fourth:

1. the `register(Preset(...))` block in `presets.py`;
2. a row in the readme's preset table (the `Prose` test reads it);
3. a note in `docs/compute.md` if it needs a model the route table has never seen;
4. nothing in the cli, the sidebar, the legend or the plan. those read the registry, and if they do not, that is the bug.
