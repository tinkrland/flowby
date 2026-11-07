"""the spatial layer: elements on a board, and the node each one already is.

the rule this file exists to hold: an element and a node are the same object seen twice. adding a
sketch to the board adds a red-source node called by the sketch's name. there is no import step,
no "convert to pipeline", and no way to have a visual thing that is not part of the graph, which
is what stops the two views from drifting.

what the board adds on top of the graph is placement: where the thing sits, how big it is, what it
is called, and which node's output it is currently drawing. that last one is the whole of the
"preset" story. applying a preset does not modify the element, it points the element's display at
a new node.
"""

from dataclasses import dataclass, field

from . import dtypes, presets
from .graph import Graph, GraphRefused, Node, Port

KIND_DTYPE = {
    "frame": "image",
    "sketch": "image",
    "image": "image",
    "video": "video",
    "text": "text",
    "model": "mesh",
}

PLANES = ("2d", "3d")


class SceneRefused(Exception):
    """the board said no, in words meant for the sidebar rather than a stack trace."""


@dataclass
class Transform:
    """page coordinates, which are tldraw's, not world coordinates."""

    x: float = 0.0
    y: float = 0.0
    width: float = 480.0
    height: float = 480.0
    rotation: float = 0.0
    z: float = 0.0


@dataclass
class Element:
    id: str
    kind: str
    label: str
    plane: str = "2d"
    transform: Transform = field(default_factory=Transform)
    asset: str | None = None
    display: str | None = None
    text: str | None = None
    chosen: int = 0
    params: dict = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    @property
    def dtype(self) -> str:
        return KIND_DTYPE[self.kind]


@dataclass
class Instance:
    """one preset applied to one element. the nodes exist; this is the handle onto them."""

    id: str
    element: str
    preset: str
    nodes: list[str] = field(default_factory=list)
    sink: str = ""
    values: dict = field(default_factory=dict)
    aux: dict = field(default_factory=dict)
    detached: bool = False

    def complete(self) -> bool:
        """false while a slot is still empty, which is what makes the preset refuse to compile."""
        return all(self.aux.values())

    def as_dict(self) -> dict:
        return {"id": self.id, "element": self.element, "preset": self.preset,
                "nodes": list(self.nodes), "sink": self.sink,
                "values": dict(self.values), "aux": dict(self.aux),
                "complete": self.complete(), "detached": self.detached}


class Scene:
    def __init__(self, id: str = "scene", title: str = "untitled"):
        self.id = id
        self.title = title
        self.graph = Graph()
        self.elements: dict[str, Element] = {}
        self.instances: dict[str, Instance] = {}
        self._serial = 0

    # -- the board ---------------------------------------------------------

    def next_name(self, prefix: str) -> str:
        self._serial += 1
        return f"{prefix}-{self._serial}"

    def add(self, kind: str, label: str | None = None, plane: str | None = None,
            asset: str | None = None, text: str | None = None,
            transform: Transform | None = None) -> Element:
        if kind not in KIND_DTYPE:
            raise SceneRefused(f"{kind!r} is not something a board holds. it holds "
                               f"{', '.join(KIND_DTYPE)}.")
        dtype = KIND_DTYPE[kind]
        if plane is not None and plane not in PLANES:
            raise SceneRefused(f"a plane is {PLANES[0]} or {PLANES[1]}, not {plane!r}")
        element = Element(
            id=self.next_name(kind),
            kind=kind,
            label=label or self.next_name(kind),
            plane=plane or ("3d" if dtype == "mesh" else "2d"),
            transform=transform or Transform(),
            asset=asset,
            text=text,
        )
        if dtype in ("image", "video", "mesh") and not asset:
            raise SceneRefused(
                f"a {kind} needs bytes to be a node. an element with nothing behind it is a "
                f"rectangle, and a rectangle does not compile."
            )
        if dtype == "text" and text is None:
            raise SceneRefused("a text element needs its words")
        self.elements[element.id] = element
        self.graph.add(Node(
            id=element.id,
            op=f"element.{kind}",
            inputs={},
            outputs={"media": Port(dtype)},
            params={"asset": asset, "text": text, "label": element.label},
            label=element.label,
            requires={"minutes": 0.0},
        ))
        element.display = element.id
        return element

    def remove(self, element_id: str) -> None:
        element = self._element(element_id)
        for inst in list(self.instances.values()):
            if inst.element == element_id:
                for node_id in list(inst.nodes):
                    if node_id in self.graph.nodes:
                        self.graph.remove(node_id)
                del self.instances[inst.id]
        self.graph.remove(element_id)
        del self.elements[element_id]
        for other in self.elements.values():
            if other.display and other.display not in self.graph.nodes:
                other.display = other.id

    def _element(self, element_id: str) -> Element:
        try:
            return self.elements[element_id]
        except KeyError:
            raise SceneRefused(f"there is no element {element_id!r} on this board") from None

    def media_dtype(self, element_id: str) -> str:
        return self.graph.nodes[element_id].outputs["media"].dtype

    def rendered_dtype(self, element_id: str) -> str:
        """what the frame is actually drawing, which is not always what the element is."""
        element = self._element(element_id)
        node = self.graph.nodes[element.display or element.id]
        return next(iter(node.outputs.values())).dtype

    # -- presets -----------------------------------------------------------

    def apply(self, element_id: str, preset_name: str, values: dict | None = None) -> Instance:
        """spawn the preset's subgraph and point the element at its result.

        the source is whatever the element is currently showing, not what it started as, which is
        what makes presets chain: a sketch becomes a mesh, the mesh gets a material, the material
        gets a camera move. the raw media stays a node behind all of it, so nothing is destructive.
        """
        element = self._element(element_id)
        preset = presets.get(preset_name)
        values = dict(values or {})
        for name, value in values.items():
            if name not in preset.sliders:
                raise SceneRefused(
                    f"{preset.name} has no control {name!r}. it has "
                    f"{', '.join(preset.sliders)}."
                )
            preset.sliders[name].check(value)

        instance = self._live_instance(element_id, preset_name)
        if instance is None:
            source = element.display or element.id
            source_node = self.graph.nodes.get(source)
            if source_node is None:
                raise SceneRefused(f"{element.label} is showing {source}, which is not a node")
            port = next(iter(source_node.outputs))
            source_dtype = source_node.outputs[port].dtype
            if source_dtype != preset.input_dtype:
                hint = _how_to_get_there(source_dtype, preset.input_dtype)
                raise SceneRefused(
                    f"{preset.label} reads a {dtypes.colour(preset.input_dtype)} wire, and "
                    f"{element.label} is showing a {dtypes.colour(source_dtype)} one."
                    + (f" {hint}" if hint else "")
                )
            instance = self._spawn(element, preset, source, port)

        merged = {s.name: s.default for s in preset.sliders.values()}
        merged.update(instance.values)
        merged.update(values)
        instance.values = merged
        for slider in preset.sliders.values():
            for role, param, machine in slider.project(merged[slider.name]):
                self.graph.nodes[f"{instance.id}/{role}"].params[param] = machine
        element.display = instance.sink
        if preset.flips_plane and element.plane != preset.flips_plane:
            element.plane = preset.flips_plane
            element.history.append(f"{preset.name}: plane {element.plane}")
        return instance

    def variant_count(self, element_id: str) -> int:
        """how many results the thing the frame is drawing produced. 1 for a plain preset."""
        element = self._element(element_id)
        for instance in self.instances.values():
            if instance.sink == element.display and not instance.detached:
                preset = presets.get(instance.preset)
                return len(preset.sweep.values) if preset.sweep else 1
        return 1

    def show_variant(self, element_id: str, index: int) -> int:
        """pick one of the fan's results to keep looking at. 0 based, and it is only a pointer:
        every variant was produced, and a later compile still runs the whole fan."""
        element = self._element(element_id)
        count = self.variant_count(element_id)
        if not 0 <= index < count:
            raise SceneRefused(
                f"{element.label} has {count} variant{'s' if count != 1 else ''}; "
                f"there is no {index}. variants are 0 to {count - 1}."
            )
        element.chosen = index
        element.history.append(f"variant {index + 1} of {count}")
        return index

    def show(self, element_id: str, node_id: str | None = None) -> str:
        """what the frame draws. `None` puts the element's own media back, which is the
        "show the original" toggle, and which is also how a branch stops being compiled."""
        element = self._element(element_id)
        target = node_id or element.id
        if target not in self.graph.nodes:
            raise SceneRefused(f"{target} is not a node on this board")
        element.display = target
        return target

    def _live_instance(self, element_id: str, preset_name: str) -> Instance | None:
        """the one already on this element, so clicking twice lowers the same slider twice."""
        for inst in self.instances.values():
            if (inst.element == element_id and inst.preset == preset_name
                    and not inst.detached):
                return inst
        return None

    def _spawn(self, element: Element, preset: presets.Preset,
               source: str, source_port: str) -> Instance:
        index = 1 + sum(1 for i in self.instances.values()
                        if i.element == element.id and i.preset == preset.name)
        instance_id = f"{element.id}/{preset.name}" + (f"@{index}" if index > 1 else "")
        instance = Instance(id=instance_id, element=element.id, preset=preset.name)
        for role, step in preset.steps.items():
            self.graph.add(Node(
                id=f"{instance_id}/{role}",
                op=step.op,
                inputs=dict(step.inputs),
                outputs=dict(step.outputs),
                params=dict(step.params),
                requires=dict(step.requires),
                label=step.label,
                instance=instance_id,
            ))
            instance.nodes.append(f"{instance_id}/{role}")
        instance.sink = f"{instance_id}/{preset.sink}"
        instance.aux = {slot.name: None for slot in preset.slots}
        try:
            self.graph.add_edge(source, source_port,
                                f"{instance_id}/{preset.entry}", preset.entry_port)
            for a, ap, b, bp in preset.edges:
                self.graph.add_edge(f"{instance_id}/{a}", ap, f"{instance_id}/{b}", bp)
        except GraphRefused as refusal:
            for node_id in instance.nodes:
                if node_id in self.graph.nodes:
                    self.graph.remove(node_id)
            raise SceneRefused(f"{preset.name} could not be wired onto {element.label}: {refusal}")
        self.instances[instance_id] = instance
        return instance

    def link(self, instance_id: str, slot_name: str, source_element: str) -> Instance:
        """fill a slot with another element's current render, which is the second asset."""
        try:
            instance = self.instances[instance_id]
        except KeyError:
            raise SceneRefused(f"there is no preset instance {instance_id!r}") from None
        preset = presets.get(instance.preset)
        slot = next((s for s in preset.slots if s.name == slot_name), None)
        if slot is None:
            offered = ", ".join(s.name for s in preset.slots) or "none"
            raise SceneRefused(
                f"{preset.name} has no slot {slot_name!r}. its slots are {offered}."
            )
        source = self._element(source_element)
        node_id = source.display or source.id
        node = self.graph.nodes[node_id]
        port = next(iter(node.outputs))
        carried = node.outputs[port].dtype
        if carried != slot.dtype:
            raise SceneRefused(dtypes.mismatch(carried, slot.dtype))
        self.graph.add_edge(node_id, port, f"{instance.id}/{slot.node}", slot.port)
        instance.aux[slot.name] = source_element
        return instance

    def detach(self, instance_id: str) -> Instance:
        """breaking a preset apart is bookkeeping, because the graph was never hidden."""
        try:
            instance = self.instances[instance_id]
        except KeyError:
            raise SceneRefused(f"there is no preset instance {instance_id!r}") from None
        if instance.detached:
            raise SceneRefused(f"{instance_id} is already loose")
        for node_id in instance.nodes:
            self.graph.nodes[node_id].instance = None
            self.graph.nodes[node_id].label = f"{self.graph.nodes[node_id].label} (loose)"
        instance.detached = True
        return instance

    def sidebar(self, element_id: str) -> dict:
        """what the contextual panel shows when an element is clicked."""
        element = self._element(element_id)
        applicable = []
        rendered = self.rendered_dtype(element_id)
        for preset in presets.PRESETS.values():
            already = any(i.element == element.id and i.preset == preset.name
                          and not i.detached for i in self.instances.values())
            if preset.input_dtype != rendered and not already:
                continue
            entry = {
                "preset": preset.name,
                "label": preset.label,
                "blurb": preset.blurb,
                "state": preset.state,
                "changes": {"from": preset.input_dtype, "to": preset.out_dtype(),
                            "plane": preset.flips_plane},
                "applied": None,
            }
            for inst in self.instances.values():
                if inst.element == element.id and inst.preset == preset.name and not inst.detached:
                    panel = preset.sidebar(inst.values)
                    entry["applied"] = panel["controls"]
                    entry["estimate"] = panel["estimate"]
                    entry["stage"] = panel["stage"]
                    entry["slots"] = [
                        {"name": slot["name"], "means": slot["means"],
                         "filled": inst.aux.get(slot["name"])}
                        for slot in panel["slots"]
                    ]
                    entry["instance"] = inst.id
            applicable.append(entry)
        return {
            "element": {
                "id": element.id,
                "label": element.label,
                "kind": element.kind,
                "plane": element.plane,
                "dtype": element.dtype,
                "rendered": self.rendered_dtype(element.id),
                "display": element.display,
                "variants": self.variant_count(element.id),
                "chosen": element.chosen,
                "history": list(element.history),
            },
            "presets": applicable,
        }

    # -- recipes -----------------------------------------------------------

    def record(self, element_id: str, name: str | None = None) -> dict:
        """the chain on an element, in the order it was built.

        this is the thing both products above sell as the front door: a preset is one click and a
        recipe is a whole workflow in one click. nothing new is stored, because the chain was
        always the recipe, which is why it can be read back instead of saved.
        """
        element = self._element(element_id)
        steps = [
            {"preset": inst.preset, "values": dict(inst.values),
             "slots": {k: v for k, v in inst.aux.items() if v}}
            for inst in self.instances.values()
            if inst.element == element.id
        ]
        return {
            "name": name or f"{element.label} chain",
            "kind": element.kind,
            "steps": steps,
            "estimate": {
                "minutes": round(sum(presets.get(s["preset"]).minutes() for s in steps), 1),
                "gpu_minutes": round(sum(presets.get(s["preset"]).estimate()["gpu_minutes"]
                                         for s in steps), 1),
            },
        }

    def replay(self, element_id: str, recipe: dict) -> list[Instance]:
        """apply a chain in order. a recipe that starts on a different wire refuses, loudly."""
        element = self._element(element_id)
        if recipe.get("kind") and recipe["kind"] != element.kind:
            raise SceneRefused(
                f"{recipe['name']} was recorded on a {recipe['kind']} and {element.label} is a "
                f"{element.kind}."
            )
        applied = []
        for step in recipe["steps"]:
            instance = self.apply(element_id, step["preset"], dict(step.get("values") or {}))
            for slot, source in (step.get("slots") or {}).items():
                if source in self.elements:
                    self.link(instance.id, slot, source)
            applied.append(instance)
        return applied

    # -- views -------------------------------------------------------------

    def board(self) -> list[dict]:
        """the spatial layer, as the renderer reads it."""
        return [
            {
                "id": e.id,
                "kind": e.kind,
                "label": e.label,
                "plane": e.plane,
                "dtype": self.rendered_dtype(e.id),
                "display": e.display,
                "variants": self.variant_count(e.id),
                "chosen": min(e.chosen, max(0, self.variant_count(e.id) - 1)),
                "transform": vars(e.transform),
                "presets": [i.preset for i in self.instances.values()
                            if i.element == e.id and not i.detached],
            }
            for e in self.elements.values()
        ]

    def pipeline(self) -> dict:
        """the node layer, as the inspector reads it: nodes placed, wires coloured by dtype."""
        positions = {}
        for index, element in enumerate(self.elements.values()):
            positions[element.id] = {"x": 0.0, "y": index * 160.0}
            attached = [i for i in self.instances.values() if i.element == element.id]
            for row, inst in enumerate(attached):
                for column, node_id in enumerate(inst.nodes):
                    positions[node_id] = {"x": 320.0 + column * 240.0,
                                          "y": index * 160.0 + row * 60.0}
        nodes = []
        for node_id in self.graph.order:
            node = self.graph.nodes[node_id]
            nodes.append({
                "id": node_id,
                "op": node.op,
                "label": node.label,
                "instance": node.instance,
                "params": dict(node.params),
                "pos": positions.get(node_id, {"x": 0.0, "y": 0.0}),
                "inputs": {p: {"dtype": s.dtype, "role": s.role, "many": s.many}
                           for p, s in node.inputs.items()},
                "outputs": {p: {"dtype": s.dtype, "role": s.role}
                            for p, s in node.outputs.items()},
            })
        wires = [
            {
                "from": {"node": e.src[0], "port": e.src[1]},
                "to": {"node": e.dst[0], "port": e.dst[1]},
                "dtype": self.graph.nodes[e.src[0]].outputs[e.src[1]].dtype,
                "colour": dtypes.colour(self.graph.nodes[e.src[0]].outputs[e.src[1]].dtype),
            }
            for e in self.graph.edges
        ]
        return {"scene": self.id, "nodes": nodes, "wires": wires}

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "elements": [vars(e) | {"transform": vars(e.transform)}
                         for e in self.elements.values()],
            "instances": [i.as_dict() for i in self.instances.values()],
        }


def _how_to_get_there(have: str, want: str) -> str:
    """name the preset that bridges the two wires, because that is the actual next click."""
    for preset in presets.PRESETS.values():
        if preset.input_dtype == have and preset.out_dtype() == want:
            return f"apply {preset.label} first."
    return ""
