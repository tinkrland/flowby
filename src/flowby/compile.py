"""the scene compiles to a plan a shell script can execute, and to nothing else.

the worker on the far end of this is a bash script in a container that has never heard of nodes.
so the graph is flattened here, once: steps come out in topological order with every input already
resolved to `step:port` or `asset:<digest>`, and nothing downstream has to interpret a wire. that
is the contract, and it is why the frontend can spawn nodes freely without the worker caring.

two refusals matter more than the rest. a step whose required input has no wire is refused rather
than run with a null, and a plan that will not survive its route is refused before a browser is
opened, because the expensive failures are the ones you find out about at hour nine.

only what the board is actually showing gets compiled. a sketch with five presets on it and one of
them displayed costs one branch, not five, which is what lets a board stay cheap while it is messy.
"""

import hashlib
import json
import time

from . import dtypes, presets, routes
from .graph import GraphRefused

CONTRACT = "flowby/1"

ARTIFACT_SUFFIX = {"mesh": "glb", "video": "mp4", "image": "png", "text": "txt"}

# what a board holds, by wire. used when something has to stand in for a missing asset.
KIND_FOR = {"image": "image", "video": "video", "mesh": "model", "text": "text"}


class CompileRefused(Exception):
    """the board cannot become a plan, and the message says which part."""


def _out_port(node) -> str:
    return next(iter(node.outputs))


def needed(scene) -> tuple[set[str], dict[str, dict]]:
    """the nodes the visible board depends on, and where each element's pixels come from."""
    required: set[str] = set()
    display = {}
    for element in scene.elements.values():
        node_id = element.display or element.id
        if node_id not in scene.graph.nodes:
            raise CompileRefused(f"{element.label} is displayed by {node_id}, which is not a node")
        required |= scene.graph.upstream(node_id) | {node_id}
        node = scene.graph.nodes[node_id]
        display[element.id] = {
            "element": element.id,
            "node": node_id,
            "port": _out_port(node),
            "dtype": node.outputs[_out_port(node)].dtype,
            "preset": node.instance or None,
        }
    return required, display


def plan(scene, route: str | None = None, present: set[str] | None = None,
         now: float | None = None) -> dict:
    required, display = needed(scene)
    try:
        order = scene.graph.topo(only=required)
    except GraphRefused as refusal:
        raise CompileRefused(str(refusal)) from None

    steps = []
    for node_id in order:
        node = scene.graph.nodes[node_id]
        inputs = {}
        for port, spec in node.inputs.items():
            wires = scene.graph.edges_into(node_id, port)
            if not wires:
                if spec.optional:
                    continue
                owner = f" ({node.instance.split('/')[-1]})" if node.instance else ""
                raise CompileRefused(
                    f"{node.label or node_id}{owner} needs a {dtypes.wire(spec.dtype).colour} "
                    f"wire on {port}, and has none. an unwired input is a question, not a default."
                )
            edge = wires[0]
            inputs[port] = f"{edge.src[0]}:{edge.src[1]}"
        if node.op.startswith("element.") and node.params.get("asset") is None \
                and node.params.get("text") is None:
            raise CompileRefused(f"{node.label} has no bytes behind it, so there is nothing to send")
        steps.append({
            "id": node_id,
            "op": node.op,
            "label": node.label or node_id,
            "minutes": node.minutes(),
            "gpu": bool((node.requires or {}).get("gpu")),
            "inputs": inputs,
            "outputs": {p: s.dtype for p, s in node.outputs.items()},
            "params": dict(node.params),
        })

    pip: list[str] = []
    models: list[str] = []
    gpu = False
    for node_id in order:
        requires = scene.graph.nodes[node_id].requires or {}
        for name in requires.get("pip", []) or []:
            if name not in pip:
                pip.append(name)
        for name in requires.get("models", []) or []:
            if name not in models:
                models.append(name)
        gpu = gpu or bool(requires.get("gpu"))

    artifacts = []
    for element_id, shown in display.items():
        suffix = ARTIFACT_SUFFIX[shown["dtype"]]
        artifacts.append({"name": f"{element_id}.{suffix}", "dtype": shown["dtype"],
                          "element": element_id})

    board = [
        {"id": e.id, "label": e.label, "plane": e.plane,
         "display_dtype": display[e.id]["dtype"],
         "transform": vars(e.transform)}
        for e in scene.elements.values()
    ]

    minutes = sum(scene.graph.nodes[n].minutes() for n in order)
    gpu_minutes = sum(scene.graph.nodes[n].minutes() for n in order
                      if (scene.graph.nodes[n].requires or {}).get("gpu"))
    cost = {
        "total_minutes": round(minutes, 1),
        "gpu_minutes": round(gpu_minutes, 1),
        "cpu_minutes": round(minutes - gpu_minutes, 1),
        "models": list(models),
    }
    document = {
        "contract": CONTRACT,
        "job_id": None,
        "scene": scene.id,
        "title": scene.title,
        "compiled": None,
        "steps": steps,
        "env": {"pip": pip, "models": models, "gpu": gpu},
        "artifacts": artifacts,
        "display": display,
        "board": board,
        "cost": cost,
        "estimate_minutes": round(minutes, 2),
    }

    if route is None:
        chosen, notes = routes.choose(document, present)
        document["route"] = chosen.name
        document["route_caveats"] = notes
    else:
        chosen = routes.get(route)
        reasons = routes.fit(chosen, document, present)
        if reasons:
            raise CompileRefused(f"{chosen.label} will not take this plan: {'; '.join(reasons)}")
        document["route"] = chosen.name
        document["route_caveats"] = routes.caveats(chosen, document)

    document["job_id"] = digest(document)
    document["compiled"] = int(now if now is not None else time.time())
    return document


def digest(document: dict) -> str:
    """the plan's identity: the same board compiled twice is the same job, so it is not redone."""
    body = {k: v for k, v in document.items()
            if k not in ("job_id", "compiled", "route_caveats")}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return "fb_" + hashlib.sha256(blob.encode()).hexdigest()[:32]


def as_shell_environment(document: dict) -> dict:
    """what kernel.sh exports so the python on the far end does not re-parse the graph."""
    return {
        "FLOWBY_JOB": document["job_id"],
        "FLOWBY_CONTRACT": document["contract"],
        "FLOWBY_ROUTE": document["route"],
        "FLOWBY_STEPS": str(len(document["steps"])),
        "FLOWBY_PIP": " ".join(document["env"]["pip"]),
        "FLOWBY_MODELS": " ".join(document["env"]["models"]),
        "FLOWBY_GPU": "1" if document["env"]["gpu"] else "0",
    }


def summary(document: dict) -> list[str]:
    """the one-screen version, for a terminal and for a test that reads it."""
    lines = [
        f"plan {document['job_id']} on {document['route']} "
        f"(about {document['estimate_minutes']:.1f} min)",
        f"  {len(document['steps'])} steps, {len(document['artifacts'])} artifacts",
    ]
    for step in document["steps"]:
        wires = ", ".join(f"{k}<-{v}" for k, v in step["inputs"].items()) or "no inputs"
        lines.append(f"  {step['id']}: {step['op']}  [{wires}]")
    cost = document.get("cost", {})
    if cost:
        lines.append(f"  cost: {cost['total_minutes']} min "
                     f"({cost['gpu_minutes']} on a gpu, {cost['cpu_minutes']} on a cpu)")
    for caveat in document.get("route_caveats", []):
        lines.append(f"  ! {caveat}")
    return lines


def preset_plan(preset_name: str, values: dict | None = None, route: str | None = None) -> dict:
    """a board holding exactly one element, so a preset can be compiled and read on its own."""
    from .scene import Scene

    preset = presets.get(preset_name)
    scene = Scene(id=f"preset:{preset_name}", title=preset.label)
    kind = {"text": "text", "image": "sketch", "video": "video", "mesh": "model"}[preset.input_dtype]
    element = scene.add(kind, label=preset.label.lower(), asset="sha256:" + "0" * 64,
                        text="a placeholder sentence")
    instance = scene.apply(element.id, preset_name, values or {})
    # a preset with a slot cannot compile alone, so the fixture board fills the slot with a
    # placeholder asset. the placeholder is labelled as one, and nothing here claims it is art.
    for index, slot in enumerate(preset.slots, start=1):
        stand_in = scene.add(KIND_FOR[slot.dtype], f"{slot.name} (placeholder {index})",
                             asset="sha256:" + format(index, "x") * 64,
                             text=f"placeholder for {slot.name}")
        scene.link(instance.id, slot.name, stand_in.id)
    return plan(scene, route=route)
