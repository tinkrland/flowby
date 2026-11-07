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

## what illustrace already knows about styles (read from tinkrland/illustrace, 2026-11-07)

the owner pointed at their own repo as research for the **style** kind and said it is "not turnkey"
and that flowby would do **lora training on diffusion images instead**, so it differs. read as such:
illustrace is a *benchmark and measurement* project; its learned layer is a small part of it. what
carries over and what does not:

### what carries over (the learned half, which is the half flowby needs)

* **a working colab recipe, debugged against a real run.** `runner/colab_micro_lora.py` trains a
  flux.1-dev lora with kohya sd-scripts on a free t4. it uses `--fp8_base`, fp16 (the t4 has no
  bf16), cached latents and text-encoder outputs, rank/alpha 16, lr 1e-4, 10 epochs x 3 repeats.
  the commit trail shows what actually broke: the kohya install had to run from inside the checkout,
  a partial clone had to be healed, and the first live run was **killed silently by the host's
  ~12gb of system ram** while loading the 23.8gb checkpoint. `--lowram` plus `--blocks_to_swap 8`
  fixed that. this is the answer to "will it fit": yes, but only with those flags, and the failure
  was an out-of-memory kill with no traceback.
* **resume is already built.** weights are cached on the user's drive, a checkpoint and training
  state are saved every 2 epochs, and a rerun resumes from the last state. this is the
  checkpoint-and-resume requirement written up in the section above, already solved in code.
* **time on a t4 is measured, not guessed:** 15 images x 3 repeats x 10 epochs is 450 steps, about
  10 to 20 seconds a step, a **1.5 to 2.5 hour** session. that is shorter than the 3 to 4 hours
  found by search, because it is a deliberately tiny corpus. 10 to 30 images is the stated range for
  a coherent style, and 20 to 50 at 1024px for a "consistent" one.
* **a dataset contract.** one caption file per image, every caption must start with a **trigger
  word** that is not an english subword (`skrfrnt`, `dgtlwc`), the run refuses to start if a caption
  lacks it, and a corpus is checked **before** a gpu-hour is spent. their profiling caught two
  artists' worth of technique mixed into one folder before it trained a "mush". a style needs this
  gate.
* **composition limits, from the diffusers docs they cite:** adapter interference grows past 2 or 3
  simultaneous style loras. house rules: each weight 0.3 to 0.7, total near 1.0 to 1.2, and prefer
  spatial or attention masking over raw stacking. this is the budget for "weighted" styles, and it
  caps how many a single node can blend.
* **weights update in memory**, so a strength slider can be live with no retraining. a style's
  strength is a runtime input, not a property of the trained file.
* **the job ledger.** a queue of jobs (queued, running, done, failed) that cannot be rewound, a
  pull-model runner that claims one job, and a preregistered gate and kill condition written before
  each run. flowby's `compute.md` lanes are the same idea.
* **the node UI conclusion matches ours:** react flow (xyflow, MIT) as the canvas, no execution on
  the canvas, preset = graph json. a "gravity" order resolves conflicts between references
  independently of strength (rank decays at 0.65 per step). it is a ready answer to "two styles
  claim the same thing, who wins".

### what does not carry over, and why the owner is right to split from it

* **the classical operators.** illustrace measures style as numbers (stroke width, palette in lab
  space, edge entropy) and moves one at a time by deterministic image operators with no model.
  flowby's styles are *learned weights*, so the numbers are not the mechanism. the useful
  residue is their **probe**: after training, re-measure the adapter's outputs against the corpus
  (palette distance in cie lab, delta-e under 10 for fidelity; unclaimed factors no worse than the
  untrained model plus one standard deviation for leakage). it is a way to *test* a trained style
  without a human, and it does not depend on how the style was made.
* **its scope is narrow on purpose:** hand-drawn and graphic illustration, icons, sprites,
  low-poly. it excludes photoreal, people and product work. flowby does 3d and product shots
  (vectary's whole territory), so illustrace's findings may not transfer there.
* **its one-factor-at-a-time claim.** "move stroke roughness without moving palette" is the
  scientific point of that project. a lora moves everything it learned together; a trained style is
  the *opposite* of a controllable single factor. that is the real trade the owner is making, and it
  is why styles are a different kind from presets and tools.

### what illustrace has **not** shown, so it cannot be cited as proof

its own readme says it plainly: **nothing has trained yet, zero checkpoints.** the colab script has
been hardened by failures, but there is no recorded finished run, no loss, no adapter and no probe
score on a real adapter. the commit trail ends at "harden colab training against timeouts". the
repo also gitignores `adapters/` and `data/micro/`, so a finished run, if one exists, would not be
visible here. so:

| claim | illustrace's evidence | state |
| --- | --- | --- |
| the recipe fits a free t4 | flags chosen to survive an oom kill, estimate of 1.5 to 2.5 h | **designed and debugged, not shown finishing** |
| resume survives a cut session | resume path written | **written, not exercised in the record** |
| a trained adapter is faithful and leak-free | a probe with thresholds | **instrument built, never pointed at a real adapter** |
| flux.1-dev may be used | repo notes the non-commercial licence and a licence swap for commercial use | **known, matches the open risk above** |

### things this changes in the plan

* **the licence question is now answered by their own note:** flux.1-dev is non-commercial research
  use; a commercial product needs a different base or a licence. for flowby that decides the base
  model before any style is trained, so it should be settled first.
* **training needs a hugging face token from an account that accepted the flux licence.** that is a
  second credential the user supplies, besides google. flowby must not hold it either.
* **the "lend colab to the agent through a browser" idea has a simpler version:** the illustrace
  script is meant to be run by the user pasting cells into a notebook, with the corpus as a zip
  upload and a token as an environment variable. the browser-driving route is only needed if the
  user does not want to paste anything. the script is also usable as a generated notebook the user
  opens and runs, which avoids driving google's ui at all (and the terms risk with it).

### the prose on foreground and background (illustrace `RASTER_ASSESSMENT_CONTRACT.md`)

the owner pointed at the repo's prose specifically "for a bit of reference on weighted foreground,
background etc." for the style kind. the relevant text is the raster assessment contract, plus two
lines in `llm/README.md`. what it says, restated for flowby:

* **a style has a region, and the region has an authority order.** the contract scores a finished
  image over `whole`, `subject` or `background`, and settles who decides where the subject is, in
  this order: (1) a mask the user or dataset supplies; (2) a mask from a version-pinned segmentation
  model, with model and confidence logged; (3) a deterministic border-contrast foreground heuristic,
  labelled as a heuristic; (4) the whole frame, labelled as a fallback. its stated reason: opencv can
  find contours and saliency, but "high contrast, central placement, and semantic importance are
  different concepts", so a pixel heuristic must never silently decide what the focus is.
* **nothing decides silently.** "neither saliency nor a vision model is allowed to silently decide
  which image contributes which factor." the user assigns a reference to a factor; the machine only
  measures. for flowby this is the rule for a style node with a mask input: if the mask came from a
  model or a guess, the node says so, and it falls back to the whole frame with lower confidence
  when no credible foreground exists.
* **subject and background are scored separately.** "subject and background scorecards remain
  separate when a mask exists." so a styled output has two results, not one averaged number. the
  contract also refuses a single universal style score: factors "cannot be averaged honestly".
* **a source image is content, never style, unless assigned.** the source is "a content anchor,
  never a style reference unless the user explicitly assigns it to a factor". that is the same
  separation vectary and fuser make by having a distinct input slot for what to draw.
* **weighting is two axes, not one** (from the composer): *strength* is magnitude and *gravity* is
  who wins a conflict. the top-ranked reference wins a component even at a lower percentage, and
  lower ranks blend in at a decay of 0.65 per step. in lora terms, strength is the adapter weight
  and gravity is the priority between adapters that claim the same region.
* **the way to apply a style to a region is masking, not stacking.** the engine doc and `llm/README`
  both say to prefer spatial or attention masks over raw stacking, because adapters interfere past
  2 or 3 at once. so "this style on the foreground, that one on the background" is a masked
  application of two loras, each at a normal 0.3 to 0.7 weight, instead of two loras fighting over
  the whole frame.

what this means for the **style** kind in flowby, as a proposal, not a decision:

| a style node takes | notes |
| --- | --- |
| the image (content, never style) | the thing being restyled |
| one or more styles, each with a **strength** | the trained lora and its weight |
| an optional **mask** with a stated origin | user-drawn, model-made (pinned and logged), or heuristic |
| a **region** per style | whole, subject or background, so foreground and background can carry different styles |
| an optional **priority** among styles | decides conflicts where regions overlap |

and it returns the styled image, the mask it used with where it came from, and a scorecard for the
subject and the background separately. the part this repo has **not** built is the application: the
contract is an instrument for *scoring* finished images, and the masked multi-lora generation it
recommends is design only. flowby would be the first to run it.

### the studio token (2026-11-07)

the owner supplied a Base44 personal access token for reading studio. it authenticates only as an
`Authorization: Bearer` header, and lists exactly three apps on the account (this agent, another
agent, and an imported public app). studio's app id is not among them, so the token does not reach
studio's code or data. studio is treated as unread, and its style transfer flow is still the one
piece of research missing. the token is held as a secret and never written to the repo.

### fluxgym, checked (2026-11-07)

the owner asked for fluxgym to be checked as an open-source option for the style trainer. read from
a fresh clone, not from a summary.

* **licence: MIT** (copyright cocktailpeanut, 2024). the app itself is free to use, modify and
  sell. last commit 2026-07-28, 3.3k stars, 372 forks, 399 open issues. a gradio web ui over kohya
  sd-scripts, which does the training. the `Advanced` tab exposes every kohya flag.
* **the models it trains on are not MIT.** its `models.yaml` lists `flux-dev` and `flux1-dev2pro`
  under the **flux-1-dev non-commercial licence**, and `flux-schnell` under **apache-2.0**. so the
  tool is open source but the default base is not, which is the licence question from earlier,
  restated by the tool's own config. the readme says schnell gave "couldn't get high quality
  results, so not really recommended". a sold style therefore trades quality (dev) against licence
  (schnell). custom bases can be added by editing `models.yaml`.
* **it is a local app, not a notebook.** it installs through pinokio, a manual venv, or docker, and
  serves a ui on port 7860. there is no colab path in the repo (no mention of colab anywhere in it).
* **it does not run on a free colab t4 as shipped.** the generated training command hard-codes
  `--mixed_precision bf16` and `--save_precision bf16` (app.py lines 454, 467, 468) and `--highvram`
  (line 476), and never branches on fp16. a t4 has no bf16. it also never sets `--lowram` or
  `--blocks_to_swap`, which is exactly what stopped the host-ram oom kill in illustrace's first live
  run. the 12g profile adds `--split_mode` and adafactor, which helps vram, not host ram.
* **so the two recipes line up like this:**

| | fluxgym | illustrace colab script |
| --- | --- | --- |
| licence | MIT | the owner's own repo |
| ui | gradio, captions and sample images in the browser | none, a script run from notebook cells |
| precision | bf16 (needs an ampere gpu or newer) | fp16 (works on a t4) |
| host ram | not handled | `--lowram` and `--blocks_to_swap 8` |
| resume | not seen | drive-cached weights, state saved every 2 epochs |
| runs on a free t4 | **no, not without changing flags** | **designed and debugged for it, never shown finishing** |

what to take from fluxgym is its **ui and dataset flow** (upload, caption with the trigger word,
sample images every n steps with a fixed seed so you watch the lora evolve, publish to hugging face)
and its flag table per vram size. what to take from illustrace is the **colab-safe flags and
resume**. the cheapest honest plan is to generate illustrace's script as the notebook and borrow
fluxgym's sample-image-every-n-steps idea, so a user can see a style forming during a 2 hour run
instead of finding out at the end.

### base44 studio: what the docs say (2026-11-07)

the owner said studio is in alpha and asked whether the docs cover it. they do not.

* the base44 docs were searched in full (the 205kb index and the 5mb full-text file). there is **no
  page, section or mention of a studio product**, and the word "alpha" does not appear. the only
  "studio" hits are an example push notification about a yoga class and a "studio lighting" prompt.
* a news search and a web search found nothing about a base44 studio either. an unreleased alpha is
  not expected to be documented, so this is an absence of public evidence, not evidence of absence.
* the fetch tool refuses `studio.base44.com` and `base44.com/studio` outright ("blocked domain"), a
  separate wall from the login redirect seen in the browser.
* the personal access token the owner supplied does not list studio's app among the account's apps.

so nothing about studio's style transfer flow is known beyond what the owner has told us. the
remaining routes are the owner signing in through the live browser view, or the owner describing or
screenshotting the flow. nothing in this tree should claim to match studio until one of those
happens.

## the style kind, built (2026-11-07)

the owner said two things that cut the earlier discussion short, and they are recorded as given:

* **training goes through the browserbase / kernel.sh route on the user's colab**, which the tree
  already had as `colab-browserbase` in `routes.py`, with its gates, its ceiling and its `contested`
  policy. this was said before and was re-argued here by mistake. it is the route, not a question.
* **style transfer with lora training "isn't very complicated"**, and base44's version of it "isn't a
  brand new thing". so the style kind is built as small as the illustrace prose makes it, not as the
  larger node proposed a few sections up.

what was built is `src/flowby/styles.py` and 52 tests, and nothing in it is new research. every
number is illustrace's, and the file says so where it uses one.

| piece | what it is | where it comes from |
| --- | --- | --- |
| `Style` | a trigger, a base, a corpus, a default weight and a state | illustrace's inspo contract |
| `gate()` | seven refusals before any gpu minute: rare trigger, trigger that names the look, 10+ images, no subject over 40%, one technique, captions that say the medium or the light, weight 0.3 to 0.7 | `DATASET_PACKAGING.md`, `MICRO_LORA_PROBES.md` |
| lifecycle | corpus, gated, training, validating, ready (or refused, failed), final once ready | new, from "a retrain is a new style" |
| `training_plan()` | a flat plan with the t4 flags, the resume seam and the credentials named as gates | `colab_micro_lora.py` |
| `check_stack()` | max 3 styles, each 0.3 to 0.7, sum at most 1.2 per region, one base, a mask for any regional use | `STYLE_LORA_ENGINE.md`, `RASTER_ASSESSMENT_CONTRACT.md` |
| `rank_weights()` | strength and gravity as two axes, 0.65 decay per rank | the composer's gravity view |
| `validate_probe()` | fidelity under 10 delta-e and no leakage past the base floor, refused without a floor | `adapter_probe.py` |

three things the tests caught that reading the prose did not:

* **the gate missed illustrace's own example.** `mntwash` passed, because "wash" was in the
  ordinary-word list and not the style-word list. the check now looks across both as a substring.
* **a refusal that names every image is not a refusal anyone reads.** one bad corpus produced 29
  lines. it now groups per kind of problem with a count and three examples: 7 lines.
* **two statements about the same disk contradicted each other.** the route said weights would be
  fetched again, the plan said they were cached on the user's drive. the route's caveat now defers to
  the plan.

### not built, and not claimed

* **nothing has trained.** `training_plan` produces the job and the route accepts it. no browser has
  been opened, no colab driven, no adapter produced. the same is true of illustrace, and this tree
  inherits that: the recipe is debugged on paper and by that repo's failures, not by a finished run.
* **the probe is arithmetic over numbers handed to it.** `validate_probe` judges a measurement; it
  does not take one. the measuring (cie lab palette distance against the training profile) lives in
  illustrace's `engine/adapter_probe.py` and has not been ported.
* **no preset applies a style yet.** `check_stack` and `rank_weights` say whether a combination is
  allowed and how to weigh it. wiring a `style.apply` step into a preset, and a mask input on the
  wire, is the next piece.
* **the captioner is not here.** illustrace captions with a vision model (minicpm-v or a gpt model)
  and keeps the style unspoken. `check_captions` only refuses bad captions; it does not write good
  ones.
* **flux dev versus schnell is unsettled.** both are in `BASES` with their licences. dev is better
  and cannot be sold; schnell can, and fluxgym's readme says it trained poorly. no run has compared
  them.
