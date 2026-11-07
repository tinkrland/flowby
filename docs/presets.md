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
