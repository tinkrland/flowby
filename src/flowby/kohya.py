"""kohya.py: the style's training run as files a free colab can execute.

a plan says "train flux lora, dim 16, 10 epochs". a plan is not a run: between them sit a dataset
layout kohya can read, a toml it parses, a metadata file whose captions start with the trigger, and an
argv with the flags a T4 needs. this module makes those four things, and nothing in it touches the
network, a browser or a gpu.

the flags are not invented. they come from illustrace's first live run on a free colab T4
(vendor/illustrace/runner/colab_micro_lora.py), where the model was trained end to end, and each one
carries the failure it prevents in its comment. a run built here is the same run, with the style's own
images and captions.
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass

from . import styles as S


KOHYA_REPO = "https://github.com/kohya-ss/sd-scripts"


class KohyaRefused(Exception):
    """the style cannot be turned into a run yet, and the message says which part is missing."""


@dataclass(frozen=True)
class Layout:
    """where kohya looks for things inside the colab session. drive paths, because a free runtime dies."""

    root: str = "/content/drive/MyDrive/flowby"
    kohya: str = "/content/sd-scripts"

    @property
    def dataset(self) -> str:
        return f"{self.root}/dataset"

    @property
    def weights(self) -> str:
        return f"{self.root}/weights"

    @property
    def out(self) -> str:
        return f"{self.root}/out"

    def as_dict(self) -> dict:
        return {"root": self.root, "kohya": self.kohya, "dataset": self.dataset,
                "weights": self.weights, "out": self.out}


FLUX_WEIGHTS = {
    "unet": "flux1-dev.safetensors",
    "clip_l": "clip_l.safetensors",
    "t5xxl": "t5xxl_fp16.safetensors",
    "ae": "ae.safetensors",
}


def captions(style: S.Style) -> list[dict]:
    """one metadata line per image, and the trigger is enforced rather than hoped for.

    kohya learns the trigger word from the captions. a corpus whose captions do not start with it
    trains a lora that answers to a word the style does not claim, which is a silent, expensive bug.
    """
    if not style.items:
        raise KohyaRefused(f"{style.id} has no images: a style trains on a corpus, and this one is empty")
    rows, bad = [], []
    for item in style.items:
        caption = " ".join(str(item.caption or "").split())
        if not caption:
            bad.append(f"{item.name} has no caption")
            continue
        if not caption.startswith(style.trigger):
            caption = f"{style.trigger}, {caption}"
        rows.append({"image_path": item.name, "caption": caption})
    if bad:
        raise KohyaRefused("; ".join(bad[:4]) + (f"; and {len(bad) - 4} more" if len(bad) > 4 else ""))
    return rows


def dataset_toml(style: S.Style, layout: Layout, repeats: int = S.REPEATS) -> str:
    """the [[datasets]] block kohya parses. buckets, because a corpus is not one shape."""
    return f"""[general]
shuffle_caption = true
caption_extension = ".txt"
keep_tokens = 1

[[datasets]]
batch_size = 1
enable_bucket = true
min_bucket_reso = 512
max_bucket_reso = 1024
caption_dropout_rate = 0.1

  [[datasets.subsets]]
  image_dir = "{layout.dataset}"
  metadata_file = "{layout.dataset}/metadata.jsonl"
  num_repeats = {repeats}
"""


def argv(style: S.Style, plan: dict, layout: Layout,
         resume: str | None = None, base: str = "flux.1-dev") -> list[str]:
    """the command illustrace ran, with this style's numbers.

    `resume` is the state directory kohya saved. a two hour job on a free colab will be cut at least
    once, so resuming is part of the run rather than a repair after it fails.
    """
    if plan.get("kind") != "style.train":
        raise KohyaRefused(f"{style.id}'s plan is {plan.get('kind')!r}, not a training plan")
    step = (plan.get("steps") or [{}])[0]
    params = step.get("params") or {}
    if not params:
        raise KohyaRefused("the plan has no training step to translate")
    if base != "flux.1-dev":
        raise KohyaRefused(f"{base} has no argv here: only flux.1-dev has been run on a free t4")
    weights = layout.weights
    cmd = [
        "accelerate", "launch", "--num_cpu_threads_per_process", "2",
        f"{layout.kohya}/flux_train_network.py",
        "--pretrained_model_name_or_path", f"{weights}/{FLUX_WEIGHTS['unet']}",
        "--clip_l", f"{weights}/{FLUX_WEIGHTS['clip_l']}",
        "--t5xxl", f"{weights}/{FLUX_WEIGHTS['t5xxl']}",
        "--ae", f"{weights}/{FLUX_WEIGHTS['ae']}",
        "--dataset_config", f"{layout.dataset}/dataset.toml",
        "--output_dir", layout.out,
        "--output_name", f"{style.trigger}_{plan.get('style', style.id)}",
        "--network_module", "networks.lora_flux",
        "--network_dim", str(params.get("dim", 16)),
        "--network_alpha", str(params.get("alpha", 16)),
        "--learning_rate", str(params.get("lr", 1e-4)),
        "--max_train_epochs", str(params.get("epochs", S.EPOCHS)),
        "--save_every_n_epochs", str(params.get("save_every_epochs", S.SAVE_EVERY)),
        "--save_state",                       # the resume point, without which a cut run starts over
        "--timestep_sampling", "shift",
        "--discrete_flow_shift", "3.1582",
        "--model_prediction_type", "raw",
        "--guidance_scale", "1.0",
        "--fp8_base",                         # 12b of unet in 16gb of vram
        "--mixed_precision", "fp16",          # a t4 has no bf16
        "--save_precision", "fp16",
        "--cache_latents_to_disk",
        "--cache_text_encoder_outputs_to_disk",
        "--persistent_data_loader_workers",
        "--lowram",                           # t4 has ~12gb system ram; without this flux dies silently
        "--blocks_to_swap", "8",
    ]
    if resume:
        cmd += ["--resume", resume]
    return cmd


def session_script(style: S.Style, plan: dict, layout: Layout, base: str = "flux.1-dev") -> str:
    """the shell a person pastes into a fresh colab cell, in the order that survives a reconnect.

    setup once, download once to drive, then what differs per style: the dataset, the config, the run.
    weights and the kohya checkout are skipped when they are already on the drive, because a free
    session re-downloads 24GB otherwise.
    """
    gates = (plan.get("env") or {}).get("gates") or []
    quoted = " ".join(shlex.quote(x) for x in argv(style, plan, layout, base=base))
    gate_note = (
        "# this run reads: " + ", ".join(gates) + "\n"
        "# each one is a gate: the run refuses before training rather than failing inside kohya\n"
        if gates else ""
    )
    return f"""#!/usr/bin/env bash
# flowby style {style.id}: generated, not hand-written. run it in a colab cell, top to bottom.
set -euo pipefail
{gate_note}
mkdir -p {layout.root} {layout.dataset} {layout.weights} {layout.out}

if [ ! -d {layout.kohya} ]; then
  git clone --depth 1 {KOHYA_REPO} {layout.kohya}
  pip install -q -r {layout.kohya}/requirements.txt
fi

if [ ! -f {layout.weights}/{FLUX_WEIGHTS['unet']} ]; then
  pip install -q hf_transfer
  HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download black-forest-labs/FLUX.1-dev \\
    --local-dir {layout.weights}
fi

# the dataset and its config were written by flowby; upload them beside this script
test -f {layout.dataset}/metadata.jsonl || {{ echo "missing {layout.dataset}/metadata.jsonl"; exit 1; }}

{quoted}
"""


def run_files(style: S.Style, plan: dict, layout: Layout, base: str = "flux.1-dev") -> dict[str, str]:
    """every file a run needs, as text. the images are the user's and are not copied here."""
    rows = captions(style)
    return {
        "metadata.jsonl": "".join(json.dumps(row) + "\n" for row in rows),
        "dataset.toml": dataset_toml(style, layout),
        "run.sh": session_script(style, plan, layout, base=base),
    }


def run(style: S.Style, layout: Layout | None = None, base: str = "flux.1-dev") -> dict:
    """the whole crossing as one payload: what it writes, what it will run, and what it needs first."""
    plan = S.training_plan(style)
    layout = layout or Layout()
    files = run_files(style, plan, layout, base=base)
    command = argv(style, plan, layout, base=base)
    return {
        "contract": "flowby/1",
        "kind": "style.kohya",
        "style": style.id,
        "trigger": style.trigger,
        "images": len(style.items),
        "layout": layout.as_dict(),
        "files": sorted(files),
        "writes": files,
        "argv": command,
        "shell": " ".join(shlex.quote(x) for x in command),
        "estimate_minutes": plan.get("estimate_minutes"),
        "gates": (plan.get("env") or {}).get("gates") or [],
        # said plainly, because this is the part the run cannot check for itself
        "after": "the adapter is the .safetensors in the output dir; flowby uses it by path, at the"
                 " weight the style declares, and never bakes the weight into the file",
    }
