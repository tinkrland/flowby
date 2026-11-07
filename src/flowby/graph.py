"""the graph under the board: nodes, typed ports, wires, and the refusals that keep it sane.

the pipeline layer is not a picture of a pipeline, it is the pipeline. the spatial layer is a
projection of this: a slider is a parameter on a node, a preset is a subgraph, and the frame you
drag around is a node with a position. that ordering matters, because it means the board can
never describe something the graph cannot run, which is the failure that makes node tools feel
like two applications stapled together.

nothing here imports a renderer. a graph is data, and every rule below is a refusal.
"""

from dataclasses import dataclass, field

from . import dtypes


class GraphRefused(Exception):
    """the graph said no. the message is the sentence shown in the inspector."""


@dataclass(frozen=True)
class Port:
    dtype: str
    role: str | None = None
    many: bool = False
    optional: bool = False

    def describe(self) -> str:
        bits = [dtypes.wire(self.dtype).colour]
        if self.role:
            bits.append(self.role)
        return " ".join(bits)


@dataclass
class Node:
    id: str
    op: str
    inputs: dict[str, Port] = field(default_factory=dict)
    outputs: dict[str, Port] = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    requires: dict = field(default_factory=dict)
    label: str = ""
    instance: str | None = None

    def __post_init__(self):
        for port in self.inputs.values():
            dtypes.wire(port.dtype)
        for port in self.outputs.values():
            dtypes.wire(port.dtype)
        for name, dtype in (self.requires.get("needs") or {}).items():
            dtypes.wire(name)

    def out_dtype(self, port: str) -> str:
        try:
            return self.outputs[port].dtype
        except KeyError:
            raise GraphRefused(f"{self.id} has no output {port!r}") from None

    def minutes(self) -> float:
        return float(self.requires.get("minutes", 0) or 0)


@dataclass(frozen=True)
class Edge:
    src: tuple[str, str]
    dst: tuple[str, str]

    def __str__(self) -> str:
        return f"{self.src[0]}:{self.src[1]} -> {self.dst[0]}:{self.dst[1]}"


class Graph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.order: list[str] = []

    # -- structure ---------------------------------------------------------

    def add(self, node: Node) -> Node:
        if node.id in self.nodes:
            raise GraphRefused(f"{node.id} already exists in this graph")
        self.nodes[node.id] = node
        self.order.append(node.id)
        return node

    def remove(self, node_id: str) -> list[Edge]:
        if node_id not in self.nodes:
            raise GraphRefused(f"{node_id} is not in this graph")
        gone = [e for e in self.edges if node_id in (e.src[0], e.dst[0])]
        self.edges = [e for e in self.edges if e not in gone]
        del self.nodes[node_id]
        self.order.remove(node_id)
        return gone

    def add_edge(self, src: str, src_port: str, dst: str, dst_port: str) -> Edge:
        for node_id, port, side in ((src, src_port, "out"), (dst, dst_port, "in")):
            if node_id not in self.nodes:
                raise GraphRefused(f"{node_id} is not in this graph")
            node = self.nodes[node_id]
            table = node.outputs if side == "out" else node.inputs
            if port not in table:
                raise GraphRefused(f"{node_id} has no {side}put port {port!r}")
        src_spec = self.nodes[src].outputs[src_port]
        dst_spec = self.nodes[dst].inputs[dst_port]
        if not dtypes.accepts(src_spec.dtype, dst_spec.dtype):
            raise GraphRefused(f"{src}:{src_port} -> {dst}:{dst_port}: "
                               + dtypes.mismatch(src_spec.dtype, dst_spec.dtype))
        if src == dst:
            raise GraphRefused(f"{src} cannot wire into itself")
        edge = Edge((src, src_port), (dst, dst_port))
        if edge in self.edges:
            raise GraphRefused(f"{edge} is already wired")
        existing = self.edges_into(dst, dst_port)
        if existing and not dst_spec.many:
            raise GraphRefused(
                f"{dst}:{dst_port} takes one wire and already has one from "
                f"{existing[0].src[0]}:{existing[0].src[1]}"
            )
        if self._reaches(dst, src):
            raise GraphRefused(f"{edge} closes a cycle: {self._cycle_path(dst, src)}")
        self.edges.append(edge)
        return edge

    def remove_edge(self, edge: Edge) -> None:
        keep = [e for e in self.edges if e != edge]
        if len(keep) == len(self.edges):
            raise GraphRefused(f"{edge} is not in this graph")
        self.edges = keep

    # -- queries -----------------------------------------------------------

    def edges_into(self, node_id: str, port: str) -> list[Edge]:
        return [e for e in self.edges if e.dst == (node_id, port)]

    def edges_out_of(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.src[0] == node_id]

    def successors(self, node_id: str) -> list[str]:
        return [e.dst[0] for e in self.edges_out_of(node_id)]

    def upstream(self, node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = [e.src[0] for e in self.edges if e.dst[0] == node_id]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(e.src[0] for e in self.edges if e.dst[0] == n)
        return seen

    def _reaches(self, start: str, target: str) -> bool:
        seen: set[str] = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n == target:
                return True
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.successors(n))
        return False

    def _cycle_path(self, start: str, target: str) -> str:
        """the path, so the refusal names the loop instead of pointing at it."""
        parent: dict[str, str] = {}
        stack = [start]
        seen = set()
        while stack:
            n = stack.pop(0)
            if n in seen:
                continue
            seen.add(n)
            if n == target:
                break
            for m in self.successors(n):
                parent.setdefault(m, n)
                stack.append(m)
        path = [target]
        while path[-1] != start and path[-1] in parent:
            path.append(parent[path[-1]])
        path.append(start)
        return " -> ".join(reversed(path))

    def topo(self, only: set[str] | None = None) -> list[str]:
        """topological order, tie-broken by insertion, so the plan is stable between runs."""
        nodes = [n for n in self.order if only is None or n in only]
        inside = set(nodes)
        index = {n: i for i, n in enumerate(self.order)}
        indegree = {n: 0 for n in nodes}
        succ: dict[str, list[str]] = {n: [] for n in nodes}
        for e in self.edges:
            if e.src[0] in inside and e.dst[0] in inside:
                indegree[e.dst[0]] += 1
                succ[e.src[0]].append(e.dst[0])
        ready = sorted((n for n in nodes if indegree[n] == 0), key=index.__getitem__)
        out: list[str] = []
        while ready:
            n = ready.pop(0)
            out.append(n)
            for m in succ[n]:
                indegree[m] -= 1
                if indegree[m] == 0:
                    ready.append(m)
            ready.sort(key=index.__getitem__)
        if len(out) != len(nodes):
            stuck = sorted(set(nodes) - set(out))
            raise GraphRefused(f"these nodes cannot be ordered: {', '.join(stuck)}")
        return out

    def check(self) -> list[str]:
        """everything wrong with the graph, in one pass, for `doctor`."""
        problems = []
        for node_id in self.order:
            node = self.nodes[node_id]
            for port, spec in node.inputs.items():
                wires = self.edges_into(node_id, port)
                if not wires and not spec.optional:
                    problems.append(f"{node_id}.{port} has no wire, and it is not optional")
                if len(wires) > 1 and not spec.many:
                    problems.append(f"{node_id}.{port} has {len(wires)} wires and takes one")
        for e in self.edges:
            if e.dst[0] not in self.nodes or e.src[0] not in self.nodes:
                problems.append(f"{e} points at a node that is gone")
        return problems

    def subgraph(self, instance: str) -> list[str]:
        return [n for n in self.order if self.nodes[n].instance == instance]
