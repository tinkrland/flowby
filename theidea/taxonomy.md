# taxonomy

*the seven things a user can reach for, and the one rule that keeps them from blurring*

**status: proposed. one question settled (techniques are authored directly); the rest is not decided.** the owner named the seven kinds on 2026-11-07 (styles, tools,
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

* ~~whether a user can author a **technique** directly, or only by promoting a preset.~~ **decided
  by the owner, 2026-11-07: a technique is authored directly.** so a technique is a first-class
  entity with its own editor (an ordered list of tools plus the reason for the order), not a thing
  that only exists once someone has built a preset around it. a preset then *references* a technique
  instead of inlining its steps, which is the refactor in the table above.
* whether a **recipe** can contain a **style** by value (frozen) or by reference (follows updates).
  by reference is more useful and breaks reproducibility.
* whether the **factory** needs its own door or is a setting on a workflow.
* the studio base44 style transfer flow, which was not seen. it is the most likely source of the
  right answer on how a style is *extracted from an upload* rather than trained.

## styles: where training runs (owner's plan, 2026-11-07)

the owner's proposal: do not host training. the user lends flowby their **own google colab** through
a browserbase session they authorise, and the agent drives it. nothing runs on flowby's bill, and a
style is trained on hardware the user already has a free allowance of.

**what is claimed, and how much of it is checked** (the claims are the owner's, from r/StableDiffusion;
the checking is a search, not a run):

| claim | state |
| --- | --- |
| a FLUX LoRA can train on a free-tier T4 (~15gb) with fluxgym or a 4-bit qlora notebook | **supported**: fluxgym documents 12, 16 and 20gb profiles. not run here |
| it takes **hours**, not minutes, at that size | **found, not in the claim**: one 12gb run was ~1230 steps in under 3 hours; a 16gb run was 4 hours. a colab session can be cut off before that |
| FLUX.1-dev inference fits on a free T4 | **supported**: gguf q4/q5 variants exist for comfyui's gguf node; fp8 diffusers is the other route. not run here |
| comfyui with gguf stacks several loras | **supported in principle**: multi-lora is a normal comfyui graph. weights per lora is what a blended style needs |
| FLUX.1-**dev** is licensed for this | **not checked**: dev is non-commercial by default. schnell is apache-2.0. this decides which base a *sold* style can be trained against |

so the claim holds, with two things it leaves out: **wall-clock time** and **session limits**. the
free tier disconnects idle sessions and caps runtime, and a 3 to 4 hour job is exactly the kind of
thing that gets cut off. a style trainer therefore needs to **checkpoint and resume**, or it will
fail at hour three with nothing to show.

### the shape this gives a style

    upload images -> caption -> train (colab, hours, resumable) -> validate -> usable
                                  ^
                          the only step that is not a node

training is the one step that is a *job*, not a node, and it runs on the **user's** compute. that
makes `compute.md` two lanes instead of one: flowby's worker for generation, the user's colab for
training. the browserbase session is the hand-off and the user authorises it.

### what has to be true before this is built

* **consent is per session, not once.** the agent drives a logged-in google account in a browser. the
  user opens the live view, signs in, and can end it. flowby never holds the google credentials.
* **colab's terms.** automated driving of colab, and long-running or heavy use on the free tier, may
  breach google's terms and can get the account limited. this is the largest unchecked risk and it
  falls on the *user's* account, not flowby's. it needs reading, not assuming.
* **a fallback that is not colab.** if the session is refused or cut, the style cannot be left
  half-trained. a resumable checkpoint in the user's drive is the minimum.

## what exactly.ai shows (read from its site, not used)

exactly.ai is a different business from the one assumed, and the difference is useful.

* **it is not self-serve style transfer.** the pricing page sells a **custom AI workflow**: 30-minute
  assessment, ~10 approved example images, "define what good looks like", then *their ML team builds
  the workflow* and the customer tests it in two feedback rounds. plans are £500/month (3 month
  pilot), £6,000/year and £60,000/year, and credits are £10 per 100.
* **a style is delivered as a workflow, not as a slider.** the pitch is "a hundred images, one style:
  line weight, palette and mood hold across a full campaign", plus "same face in every image" and
  "edit a detail, keep the picture". consistency is the product, not the look.
* **it ships a guard.** "brand guardian" checks every output against agreed brand, legal and cultural
  rules. that is a *reviewer* attached to a style, and it is the thing the factory rung will need.
* **it also sells the other models.** the app exposes third-party image and video models next to the
  custom one, plus masks, background removal, vectorise, upscale and reframe. a style sits beside
  general tools instead of replacing them, which matches the ladder.

what was **not** seen: the actual training UI. it is behind a login or a sales call, and the public
site does not show how a style is weighted or blended. "weighted, like exactly.ai" is the owner's
description and has not been confirmed from the product.
