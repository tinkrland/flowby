# kohya: from a plan to a run a free colab can execute

`styles.py` decides whether a corpus may train and emits a plan. A plan is not a run. Between them sit
four artefacts, and `kohya.py` makes them without touching a network, a browser or a gpu:

| artefact | what kohya reads | what flowby writes |
| --- | --- | --- |
| `metadata.jsonl` | one `image_path` and `caption` per line | every caption forced to **start** with the style's trigger |
| `dataset.toml` | buckets, batch size, repeats, caption dropout | buckets on, 512 to 1024, dropout 0.1 |
| `run.sh` | a colab cell run top to bottom | clone once, download weights once to drive, then train |
| `--resume` | the last `*-state` directory | appended when one exists, because a two hour job on free tier is cut |

## the flags are not invented

They come from the one FLUX LoRA that has actually trained: `vendor/illustrace/runner/colab_micro_lora.py`.
Each is in the argv with the failure it prevents beside it in code.

- `--lowram` and `--blocks_to_swap 8`: a T4 has ~15GB of vram and ~12GB of system ram. Without `--lowram`,
  kohya loads the 23.8GB checkpoint through host memory and the process is OOM-killed with no traceback.
- `--fp8_base`, `--mixed_precision fp16`, `--save_precision fp16`: 12B weights in 16GB, on a card with no bf16.
- `--save_state` plus `--resume`: the job outlives the session, so the state directory is part of the run.
- `--timestep_sampling shift`, `--discrete_flow_shift 3.1582`, `--model_prediction_type raw`,
  `--guidance_scale 1.0`: FLUX flow matching, at the shift that run used.

Only `flux.1-dev` has a proven argv. Any other base is refused rather than guessed at, which is the same
rule `routes.py` applies to a route that has never run.

## what it refuses

- a style with no images, or an image with no caption, named in the message;
- a corpus `styles.gate` rejects, using the gate's own wording rather than a second opinion;
- a style that is not gated, because only a gated style has a plan;
- a plan that is not `style.train`;
- a base with no proven command.

## the seam this leaves open

The adapter is the `.safetensors` in the output directory. flowby uses it **by path**, at the weight the
style declares, and never bakes the weight into the file, so the same style can be used at 0.4 on one board
and 0.8 on another without a second training run.
