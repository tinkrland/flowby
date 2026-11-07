"""the far end of the plan: a python process with no graph in it.

this is what runs inside the disposable container after kernel.sh has built the environment. it
reads the flattened plan, resolves nothing, and walks the steps in the order they were compiled to.
that is the point of flattening: by the time work reaches here, every wire is a `step:port` string
and the only thing left to decide is which model to call.

honesty note, since this file is the one people will over-read: **no model call is implemented.**
the ops that would call one are named in `UNIMPLEMENTED` and refuse. `--simulate` produces artifacts
whose bytes are deterministic and whose hashes are real, which is enough to verify the plumbing
(manifest, digests, tar, webhook, board update) without pretending a gpu ran.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import tarfile
import time

CONTRACT = "flowby/1"

# ops that would call a model, and the honest sentence about each
UNIMPLEMENTED = {
    "image.gen": "diffusers + sdxl-turbo",
    "control.depth": "a depth estimator",
    "mesh.triposr": "triposr weights",
    "mesh.bake": "trimesh uv bake",
    "shade.pbr": "a pbr material pass",
    "shade.light": "a lighting pass",
    "scene.stage": "a scene assembler",
    "anim.orbit": "a camera rig",
    "render.frames": "blender (bpy)",
    "style.read": "an ip-adapter encoder",
    "image.stylize": "diffusers + ip-adapter",
}

ELEMENT = "element."


class WorkerRefused(Exception):
    """the plan asked for a model that is not in this image, and saying so beats a zero byte glb."""


def resolve(plan: dict, ref: str, produced: dict) -> str:
    """a plan's wire is already `step:port`. this is the whole of the runtime graph interpretation."""
    node, _, port = ref.partition(":")
    if node not in produced:
        raise WorkerRefused(f"{ref} points at a step that has not run")
    return f"{produced[node]}#{port}"


def run(plan: dict, outdir: pathlib.Path, simulate: bool = False) -> dict:
    if plan.get("contract") != CONTRACT:
        raise WorkerRefused(f"this worker speaks {CONTRACT}, not {plan.get('contract')!r}")
    outdir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    produced: dict[str, str] = {}
    trace = []
    for index, step in enumerate(plan["steps"], start=1):
        inputs = {port: resolve(plan, ref, produced) for port, ref in step["inputs"].items()}
        op = step["op"]
        if op.startswith(ELEMENT):
            produced[step["id"]] = step["params"].get("asset") or f"text:{step['params'].get('text')}"
        elif op in UNIMPLEMENTED:
            if not simulate:
                raise WorkerRefused(
                    f"{step['id']} wants {UNIMPLEMENTED[op]}, which is not installed here. "
                    f"run with --simulate to exercise the plumbing without the model."
                )
            produced[step["id"]] = f"simulated://{plan['job_id']}/{op}"
        else:
            raise WorkerRefused(f"{op} is not an op this worker knows")
        trace.append({"step": step["id"], "op": op, "index": index,
                      "inputs": inputs, "out": produced[step["id"]]})

    artifacts = []
    for declared in plan["artifacts"]:
        shown = plan["display"][declared["element"]]
        body = (
            f"flowby {CONTRACT}\n"
            f"job {plan['job_id']}\n"
            f"element {declared['element']}\n"
            f"from {shown['node']}:{shown['port']} ({shown['dtype']})\n"
            f"simulated {simulate}\n"
        ).encode()
        path = outdir / declared["name"]
        path.write_bytes(body)
        artifacts.append({
            "name": declared["name"],
            "dtype": declared["dtype"],
            "element": declared["element"],
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        })

    manifest = {
        "contract": CONTRACT,
        "plan_digest": plan["job_id"],
        "simulated": simulate,
        "seconds": round(time.time() - started, 3),
        "steps": trace,
        "artifacts": artifacts,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def bundle(outdir: pathlib.Path, name: str = "scene.tar") -> pathlib.Path:
    """one file to hand back, because a webhook posting six files is six ways to lose one."""
    target = outdir / name
    with tarfile.open(target, "w:gz") as archive:
        for path in sorted(outdir.glob("*")):
            if path.name == name:
                continue
            archive.add(path, arcname=path.name)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="worker", description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True)
    parser.add_argument("--outdir", default="out")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--tar", action="store_true", help="also bundle the artifacts")
    args = parser.parse_args(argv)
    plan = json.loads(pathlib.Path(args.plan).read_text())
    try:
        manifest = run(plan, pathlib.Path(args.outdir), simulate=args.simulate)
    except WorkerRefused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    if args.tar:
        path = bundle(pathlib.Path(args.outdir))
        print(f"bundled {path}")
    print(json.dumps({k: manifest[k] for k in ("plan_digest", "simulated", "seconds")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
