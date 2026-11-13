"""runs.py: what each node has actually done, and what a change makes stale.

a graph is a claim about the future; this module is the record of the past. every node keeps its own
runs, and only its own, because the rule the products above learned the hard way is that *a node does
not run its upstream*. running one node again should reuse the runs of the ones before it, and the
node's history is what makes that possible.

the key a run is filed under is a signature: the node's op, its params, and the **run** each input came
from, not the input node's params. that distinction is the whole design. two nodes can be asked for the
same thing and hand back different pixels, because a diffusion pass is a sample, not a function. keying
on params alone would let a re-run upstream be silently skipped downstream, which is the same class of
bug as a stale cache and much harder to see. keying on the upstream run id means a new upstream run
invalidates exactly the nodes below it and nothing else.

nothing here executes, measures or estimates a run. a run is recorded by whoever performed it, and a
node with no runs says so by having none.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from . import graph as G


MAX_RUNS = 20  # per node. a history is for reading and reusing, not an archive.
BOOK_KIND = "flowby.runs"
BOOK_VERSION = 1
OK, FAILED = "ok", "failed"
STATES = (OK, FAILED)


class RunsRefused(Exception):
    """the record asked for is not one a history can keep, and the message says why."""


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def signature(node: G.Node, upstream: dict[str, str | None]) -> str:
    """the key one run is filed under: what this node was asked for, and what it was fed.

    `upstream` maps an input port to the id of the run whose output arrives on it, or None when that
    input is not fed. the ids are part of the key, so a new upstream run is a new signature here and
    the node is stale without anyone having to remember to mark it.
    """
    unknown = sorted(set(upstream) - set(node.inputs))
    if unknown:
        raise RunsRefused(f"{node.id} has no input {unknown[0]!r}: its inputs are {sorted(node.inputs)}")
    material = {
        "op": node.op,
        "params": node.params or {},
        "requires": {k: v for k, v in (node.requires or {}).items() if k != "needs"},
        "upstream": {port: upstream[port] for port in sorted(upstream)},
    }
    return hashlib.sha256(_canonical(material).encode()).hexdigest()


@dataclass
class Run:
    """one node, one execution, and the facts about it that a person would ask for."""

    node: str
    signature: str
    state: str = OK
    minutes: float = 0.0
    artifacts: list = field(default_factory=list)
    note: str = ""
    at: float = 0.0
    id: str = ""

    def __post_init__(self):
        if self.state not in STATES:
            raise RunsRefused(f"{self.state!r} is not a run state. the states are {', '.join(STATES)}")
        if not self.id:
            raise RunsRefused("a run is filed under an id, and only a book assigns one")
        self.minutes = round(float(self.minutes), 2)
        self.artifacts = list(self.artifacts)

    def as_dict(self) -> dict:
        return {"id": self.id, "node": self.node, "state": self.state, "at": self.at,
                "minutes": self.minutes, "artifacts": list(self.artifacts), "note": self.note,
                "signature": self.signature}


class Book:
    """every node's history. one per board, kept beside the graph and never inside it."""

    def __init__(self, clock=time.time, keep: int = MAX_RUNS):
        self.clock = clock
        self.keep = keep
        self.runs: dict[str, list[Run]] = {}
        # a run id is what the nodes below point at, so it has to be unique even when a node is asked
        # for the same thing twice in the same instant. a clock cannot promise that; a counter can.
        self.made = 0

    # -- writing -----------------------------------------------------------

    def record(self, node: str, sig: str, *, state: str = OK, minutes: float = 0.0,
               artifacts=(), note: str = "", at: float | None = None) -> Run:
        """file one run. a node's history is capped, and the cap drops the oldest, not the newest."""
        self.made += 1
        run = Run(node=node, signature=sig, state=state, minutes=minutes,
                  artifacts=artifacts, note=note, at=self.clock() if at is None else at,
                  id=f"{node}#{self.made}")
        held = self.runs.setdefault(node, [])
        held.append(run)
        if len(held) > self.keep:
            del held[: len(held) - self.keep]
        return run

    def forget(self, node: str) -> None:
        """a node that left the board takes its history with it, or a new node reusing its id would
        inherit runs it never performed."""
        self.runs.pop(node, None)

    # -- reading -----------------------------------------------------------

    def runs_for(self, node: str) -> list[Run]:
        return list(self.runs.get(node, ()))

    def latest(self, node: str) -> Run | None:
        held = self.runs.get(node) or ()
        return held[-1] if held else None

    def last_ok(self, node: str) -> Run | None:
        for run in reversed(self.runs.get(node) or ()):
            if run.state == OK:
                return run
        return None

    def reuse(self, node: str, sig: str) -> Run | None:
        """the run this node may stand on, or None when it has to run.

        the newest matching run wins, and only a successful one may be reused: a failed run that shares
        a signature is evidence the node does not work, not permission to skip it.
        """
        for run in reversed(self.runs.get(node) or ()):
            if run.signature == sig and run.state == OK:
                return run
        return None

    # -- outliving the process ---------------------------------------------------------------

    def save(self, path: str) -> str:
        """write the history where the next process can read it.

        atomic, like the store: a half-written book is worse than no book, because it would answer
        "this has run" for a node whose record was cut off mid-write.
        """
        import os
        import tempfile

        body = {"kind": BOOK_KIND, "version": BOOK_VERSION, "made": self.made,
                "runs": {node: [run.as_dict() for run in held]
                         for node, held in sorted(self.runs.items())}}
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=folder, prefix=".runs-", suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(body, out, indent=1, sort_keys=True)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, path)
        except BaseException:
            if os.path.exists(temp):
                os.unlink(temp)
            raise
        return path

    @classmethod
    def load(cls, path: str, clock=time.time, keep: int = MAX_RUNS) -> "Book":
        """read a history back, and refuse one that does not hold up rather than trusting it.

        a run is a claim that something happened, so every field is checked: a state that is not a
        state, a missing signature, or a signature that is not a sha256 all mean the file is not this
        file, and the caller gets one sentence instead of a board that quietly lies.
        """
        with open(path, encoding="utf-8") as handle:
            try:
                raw = json.load(handle)
            except json.JSONDecodeError as problem:
                raise RunsRefused(f"{path} is not json: {problem}") from problem
        if not isinstance(raw, dict) or raw.get("kind") != BOOK_KIND:
            raise RunsRefused(f"{path} is not a run history: it does not say {BOOK_KIND}")
        if raw.get("version") != BOOK_VERSION:
            raise RunsRefused(f"{path} is version {raw.get('version')!r}, and this flowby reads "
                              f"{BOOK_VERSION}")
        book = cls(clock=clock, keep=keep)
        book.made = int(raw.get("made") or 0)
        for node, held in (raw.get("runs") or {}).items():
            if not isinstance(held, list):
                raise RunsRefused(f"{path}: {node} holds something that is not a list of runs")
            for entry in held:
                book._adopt(node, entry)
        return book

    def _adopt(self, node: str, entry: dict) -> Run:
        """take one run from a file, after checking it is one."""
        if not isinstance(entry, dict):
            raise RunsRefused(f"{node}: a run in the file is not a record")
        sig = entry.get("signature")
        if not isinstance(sig, str) or len(sig) != 64 or any(c not in "0123456789abcdef" for c in sig):
            raise RunsRefused(f"{node}: a run's signature is not a sha256")
        run = Run(node=node, signature=sig, state=entry.get("state", OK),
                  minutes=entry.get("minutes") or 0.0, artifacts=entry.get("artifacts") or (),
                  note=entry.get("note") or "", at=float(entry.get("at") or 0.0),
                  id=str(entry.get("id") or ""))
        held = self.runs.setdefault(node, [])
        held.append(run)
        if len(held) > self.keep:
            del held[: len(held) - self.keep]
        return run

    def empty(self) -> bool:
        return not self.runs

    def as_dict(self) -> dict:
        return {node: [run.as_dict() for run in held] for node, held in sorted(self.runs.items())}


# -- the board's view ------------------------------------------------------

def upstream_of(graph: G.Graph, node_id: str) -> dict[str, str]:
    """which node feeds each input port of one node."""
    feeds = {}
    for edge in graph.edges:
        if edge.dst[0] == node_id:
            feeds[edge.dst[1]] = edge.src[0]
    return feeds


def signatures(graph: G.Graph, book: Book, order: list[str] | None = None) -> dict[str, str]:
    """each node's current signature, upstream first.

    the signature of a node depends on the runs its inputs came from, so this walks in topological
    order and reads the book as it goes.
    """
    out: dict[str, str] = {}
    for node_id in order or graph.topo():
        node = graph.nodes[node_id]
        fed = {port: (lambda run: run.id if run else None)(book.last_ok(source))
               for port, source in upstream_of(graph, node_id).items()}
        out[node_id] = signature(node, fed)
    return out


def stale(graph: G.Graph, book: Book) -> list[str]:
    """the nodes whose current signature has no successful run behind it: what a run would touch."""
    sigs = signatures(graph, book)
    return [node_id for node_id, sig in sigs.items() if book.reuse(node_id, sig) is None]


def work(graph: G.Graph, book: Book, targets: list[str] | None = None) -> dict:
    """what running these nodes would actually execute, and what it would stand on.

    this is the answer to "does clicking run on this node run everything before it": no. the nodes
    before it are reused when the book has a run for exactly the thing they are now asked for, and only
    the ones that changed, or never ran, are executed.
    """
    for node_id in targets or []:
        if node_id not in graph.nodes:
            raise RunsRefused(f"{node_id!r} is not on this board")
    wanted = set(targets or graph.nodes)
    if targets:
        # a target pulls in what it consumes, and only that: siblings are not in scope
        stack = list(wanted)
        while stack:
            for source in upstream_of(graph, stack.pop()).values():
                if source not in wanted:
                    wanted.add(source)
                    stack.append(source)
    order = graph.topo(only=wanted)
    reuse, run = [], []
    detail = {}
    # a node that will run has no run to point at yet, and its downstream must not reuse on the run it
    # is about to replace. the marker is deliberately not any real id, so a signature built from it
    # matches nothing in the book and the refusal to reuse propagates down the whole chain.
    pending: set[str] = set()
    for node_id in order:
        node = graph.nodes[node_id]
        fed, because = {}, []
        for port, source in upstream_of(graph, node_id).items():
            held_upstream = book.last_ok(source)
            if source in pending:
                fed[port] = f"pending:{source}"
                because.append(f"{source} will run again")
            elif held_upstream is None:
                fed[port] = None
                because.append(f"{source} has not run")
            else:
                fed[port] = held_upstream.id
        sig = signature(node, fed)
        held = None if because else book.reuse(node_id, sig)
        if held is not None:
            reuse.append(node_id)
            detail[node_id] = {"verdict": "reuse", "run": held.id, "signature": sig}
        else:
            run.append(node_id)
            pending.add(node_id)
            detail[node_id] = {"verdict": "run", "signature": sig,
                               "because": "; ".join(because) or "no run for this signature"}
    return {
        "targets": list(targets or []),
        "order": order,
        "reuse": reuse,
        "run": run,
        "minutes": round(sum(graph.nodes[n].minutes() for n in run), 2),
        "detail": detail,
    }


def element_runs(graph: G.Graph, book: Book, nodes: list[str]) -> dict:
    """the history a panel shows for one element: its nodes, newest run first, and what is stale."""
    sigs = signatures(graph, book, [n for n in nodes if n in graph.nodes])
    out = {}
    for node_id in nodes:
        if node_id not in graph.nodes:
            continue
        held = book.runs_for(node_id)
        out[node_id] = {
            "node": node_id,
            "op": graph.nodes[node_id].op,
            "runs": [run.as_dict() for run in reversed(held)],
            "count": len(held),
            "last": (held[-1].as_dict() if held else None),
            "stale": book.reuse(node_id, sigs[node_id]) is None,
            "signature": sigs[node_id],
        }
    return out
