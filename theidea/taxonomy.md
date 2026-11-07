# taxonomy

*the seven things a user can reach for, and the one rule that keeps them from blurring*

**status: proposed, not decided.** the owner named the seven kinds on 2026-11-07 (styles, tools,
techniques, recipes, workflows, presets, factories later) and said vectary only has presets. the
*ordering*, the definitions and the one rule below are this tree's reading of that list, written
after the vectary canvas video and the fuser docs were looked at, and they have not been confirmed.

vectary has one of these (presets). flowby has seven. the risk is not too few kinds, it is seven
kinds that mean the same thing under different names, so each is defined by **what it contains**.

## the ladder

    style      a look. trained, weighted, reusable.            "a thing the model learns"
    tool       one operation on one node.                      "a thing a node does"
    technique  a method: tools in a known order for a craft.   "a way of doing it"
    preset     a vectary-style task card: one input, one job,  "a button for a job"
               a sweep of variants, a thumbnail and a line.
    recipe     a saved graph with its own inputs and outputs.  "a graph you can call"
    workflow   recipes and presets chained across a project.   "a project's path"
    factory    a workflow that runs unattended, at volume.     "a line that never stops"   (later)

each rung is built from the one below it, and nothing is allowed to skip a rung silently.

## what each one *is*, so they stay different

| kind | contains | is chosen by | owns | example |
| --- | --- | --- | --- | --- |
| **style** | trained weights (a lora), a trigger, a default strength, sample images | taste | a strength slider and a blend with other styles | "tecca-x matte, 0.8" |
| **tool** | one model call and its parameters | knowing what you want | the parameters of one node | depth-map paint, upscale, relight |
| **technique** | tools in an order, with the reason for the order | craft | a method, not a result | "paint a depth map, then displace, then bake" |
| **preset** | a technique pointed at one input, with sliders and a sweep | the task | variants of one input | vectary: "recreate graphics to flat 2D" |
| **recipe** | a whole graph, parameterised, with named inputs and outputs | the outcome | a reusable graph | "product shot from a sketch" |
| **workflow** | recipes and presets across stages, with state between them | the project | stages and hand-offs | research, explore, refine, validate |
| **factory** | a workflow plus a trigger, a queue, a budget and a reviewer | volume | throughput and cost | "every new SKU gets its 6 views" |

## the rule

**a thing is the highest rung that is true of it, and is built only from rungs below it.**

* a style never contains a tool; it is something a tool *takes* (a lora input on the generate node).
* a tool never contains another tool; two tools in order is a technique.
* a preset is a technique plus a task: it has one input slot and one sweep. if it has no input slot
  it is a technique. if it needs a second input it is a recipe.
* a recipe is the first rung that has several inputs and outputs of its own.
* a workflow is the first rung with *state across time* (what stage the project is in).
* a factory is the first rung with no human in the loop, which is why it is later and why it needs
  a budget and a reviewer before it needs anything else.

## how this maps onto what is already built

| today | becomes |
| --- | --- |
| `presets.Preset` (steps, edges, sliders, sweep, slots) | **preset** (unchanged) |
| `presets.Step` (one node: op, model, inputs, outputs) | **tool** instance |
| `presets.PROCEDURAL`, the model-free ops | **tools** that cost nothing |
| a preset's `steps` + `edges` as a sequence | **technique** (today it is inlined in each preset) |
| `catalogue.Tool` (one sidebar bullet) | **rename**: it is a *menu entry*, not a tool |
| `modes.MODES` freeform / fixed / style | **doors**, not kinds: three ways to reach the same ladder |
| `compile` (flattened execution plan) | how a **recipe** or **workflow** runs |
| nothing | **style**, **recipe**, **workflow**, **factory** are not built |

the clash to fix first: `catalogue.Tool` is named for the owner's *bullet list*, and "tool" now has a
precise meaning here (one operation on one node). it becomes `MenuEntry`, or the two meanings will
collide the first time someone reads the code.

## styles are the new one, and they change the compute story

a style is the only kind with **training**, which is a long job, not a node. so a style has a
lifecycle the others do not:

    uploaded images -> captioned -> training (colab, minutes to hours) -> validated -> usable

and it is the only kind that is *weighted*: strength 0..1, and several can be blended
(`0.6 tecca-x + 0.3 matte-clay`). that is the exactly.ai shape. it needs an entity of its own
(owner, trigger word, weights file, base model it was trained against, sample renders, strength
default), and a rule that a style is only usable on the base model it was trained for.

this is also where the cost visibility matters most: training is the one thing a user can start
that costs real money and cannot be previewed by running a smaller version first.

## what is deliberately not decided

* whether a user can author a **technique** directly, or only by promoting a preset. vectary says
  custom presets are "coming soon" for teams, which suggests they are the unit people want to make.
* whether a **recipe** can contain a **style** by value (frozen) or by reference (follows updates).
  by reference is more useful and breaks reproducibility.
* whether the **factory** needs its own door or is a setting on a workflow.
* the studio base44 style transfer flow, which was not seen. it is the most likely source of the
  right answer on how a style is *extracted from an upload* rather than trained.
