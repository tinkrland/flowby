"""the board a person is working on, as something a web page can talk to.

a Scene is built to be mutated in place and to refuse illegal moves by raising. that is right for
the scene and wrong for a page: a request that fails halfway must not leave the board half-changed,
two requests must not interleave, and a mistake has to be undoable. one design gives all three
without any of them being a special case:

    every action runs on a COPY of the scene. only a result that came back clean replaces the live
    one, and the scene it replaced goes on an undo stack.

so a refusal changes nothing (the copy is thrown away), requests are serialised behind one lock,
and undo is "put the last scene back". it costs a copy per action, which is nothing at the size of
a board and buys the property that the live scene is always a scene that passed every check.

this module knows scenes, presets and the store. it does not know HTTP; `server.py` is the only
file that does, so every rule here is testable by calling a method.
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass

from . import presets as presetmod
from . import runs
from .presets import PresetRefused
from .scene import KIND_DTYPE, Scene, SceneRefused
from .store import Store, StoreRefused

UNDO_DEPTH = 50

# the elements a person can drop in: what a file or a figma frame becomes. a "model" arrives as a
# .glb, a "frame" is a figma frame, and the rest are the things a board already holds.
FILE_KINDS = ("frame", "sketch", "image", "video", "model")


class SessionRefused(Exception):
    """the action was understood and cannot be done. the board is exactly as it was."""


@dataclass
class Receipt:
    """what an action did, in words and in ids, so the page can say it and select the result."""

    action: str
    said: str
    ids: list[str]

    def as_dict(self) -> dict:
        return {"action": self.action, "said": self.said, "ids": list(self.ids)}


class Session:
    def __init__(self, store: Store, scene: Scene | None = None, title: str = "untitled"):
        self.store = store
        self.scene = scene or Scene(id="board", title=title)
        self._undo: list[Scene] = []
        self._redo: list[Scene] = []
        self._lock = threading.RLock()
        self.version = 0  # bumps on every change, so a page can tell a stale view from a current one
        # per-node history. it sits beside the scene rather than inside it: undo reverts the board,
        # and a run that happened still happened.
        self.runs = runs.Book()

    # -- the one way anything changes ----------------------------------------------------------

    def _do(self, action: str, fn) -> dict:
        """run `fn(copy)`. a clean return replaces the live scene; anything raised changes nothing."""
        with self._lock:
            trial = copy.deepcopy(self.scene)
            try:
                receipt = fn(trial)
            except (SceneRefused, PresetRefused, StoreRefused, SessionRefused, KeyError) as problem:
                raise SessionRefused(self._words(problem)) from problem
            self._undo.append(self.scene)
            del self._undo[:-UNDO_DEPTH]
            self._redo.clear()
            self.scene = trial
            self.version += 1
            return self.view(receipt)

    @staticmethod
    def _words(problem: Exception) -> str:
        # a KeyError's str() is the repr of the key, which reads as noise in a sentence
        if isinstance(problem, KeyError):
            return f"{problem.args[0]!r} is not something this board knows"
        return str(problem)

    # -- actions --------------------------------------------------------------------------------

    def add_file(self, kind: str, label: str, digest: str, name: str | None = None) -> dict:
        """put an uploaded or imported file on the board. the bytes must already be in the store."""
        def run(scene: Scene) -> Receipt:
            if kind not in FILE_KINDS:
                raise SessionRefused(f"{kind!r} is not something a file becomes. it becomes {', '.join(FILE_KINDS)}.")
            if not self.store.has(digest):
                raise SessionRefused(f"{str(digest)[:19]}… is not in the store, so there is nothing to put on the board")
            el = scene.add(kind, label or name or kind, asset=digest)
            return Receipt("add_file", f"added {el.label}", [el.id])
        return self._do("add_file", run)

    def add_text(self, text: str, label: str | None = None) -> dict:
        def run(scene: Scene) -> Receipt:
            if not str(text).strip():
                raise SessionRefused("a text node needs words")
            el = scene.add("text", label or str(text).strip()[:24], text=str(text))
            return Receipt("add_text", f"added {el.label}", [el.id])
        return self._do("add_text", run)

    def apply_preset(self, element_id: str, preset: str, values: dict | None = None) -> dict:
        def run(scene: Scene) -> Receipt:
            if element_id not in scene.elements:
                raise SessionRefused(f"{element_id!r} is not on this board")
            before = set(scene.graph.nodes)
            scene.apply(element_id, preset, values or {})
            made = sorted(set(scene.graph.nodes) - before)
            label = presetmod.get(preset).label
            return Receipt("apply_preset", f"{label} on {scene.elements[element_id].label}", made or [element_id])
        return self._do("apply_preset", run)

    def remove(self, element_id: str) -> dict:
        def run(scene: Scene) -> Receipt:
            if element_id not in scene.elements:
                raise SessionRefused(f"{element_id!r} is not on this board")
            label = scene.elements[element_id].label
            scene.remove(element_id)
            return Receipt("remove", f"removed {label}", [])
        return self._do("remove", run)

    def set_value(self, instance_id: str, slider: str, value) -> dict:
        """move one control on a preset that is already on the board."""
        def run(scene: Scene) -> Receipt:
            inst = scene.instances.get(instance_id)
            if inst is None:
                raise SessionRefused(f"{instance_id!r} is not a preset on this board")
            scene.apply(inst.element, inst.preset, {slider: value})
            return Receipt("set_value", f"set {slider} to {value}", [instance_id])
        return self._do("set_value", run)

    def rename(self, element_id: str, label: str) -> dict:
        def run(scene: Scene) -> Receipt:
            if element_id not in scene.elements:
                raise SessionRefused(f"{element_id!r} is not on this board")
            clean = str(label).strip()
            if not clean:
                raise SessionRefused("a name cannot be empty")
            scene.elements[element_id].label = clean[:80]
            scene.graph.nodes[element_id].label = clean[:80]
            return Receipt("rename", f"renamed to {clean[:80]}", [element_id])
        return self._do("rename", run)

    # -- undo -----------------------------------------------------------------------------------

    def undo(self) -> dict:
        with self._lock:
            if not self._undo:
                raise SessionRefused("there is nothing to undo")
            self._redo.append(self.scene)
            self.scene = self._undo.pop()
            self.version += 1
            return self.view(Receipt("undo", "undid the last change", []))

    def redo(self) -> dict:
        with self._lock:
            if not self._redo:
                raise SessionRefused("there is nothing to redo")
            self._undo.append(self.scene)
            self.scene = self._redo.pop()
            self.version += 1
            return self.view(Receipt("redo", "redid it", []))

    # -- what the page reads -----------------------------------------------------------------

    # -- per-node history ----------------------------------------------------------------------

    def record_run(self, node_id: str, *, state: str = runs.OK, minutes: float = 0.0,
                   artifacts=(), note: str = "") -> dict:
        """file one run against the node's current signature.

        the signature is read here rather than passed in, so a run can only ever be filed against what
        the node is being asked for now. that is what keeps the history usable as a reuse key instead of
        a wish about the past.
        """
        with self._lock:
            if node_id not in self.scene.graph.nodes:
                raise SessionRefused(f"{node_id!r} is not on this board")
            sigs = runs.signatures(self.scene.graph, self.runs)
            run = self.runs.record(node_id, sigs[node_id], state=state, minutes=minutes,
                                   artifacts=artifacts, note=note)
            return {"run": run.as_dict(), "version": self.version}

    def work(self, targets: list[str] | None = None) -> dict:
        """what a run would execute now, and what it would stand on."""
        with self._lock:
            return runs.work(self.scene.graph, self.runs, targets)

    def history(self, element_id: str | None = None) -> dict:
        """every node's history, or one element's."""
        with self._lock:
            if element_id is None:
                return {"nodes": self.runs.as_dict(),
                        "stale": runs.stale(self.scene.graph, self.runs)}
            if element_id not in self.scene.elements:
                raise SessionRefused(f"{element_id!r} is not on this board")
            book = runs.element_runs(self.scene.graph, self.runs,
                                     self.scene._nodes_for(self.scene.elements[element_id]))
            return {"element": element_id, "nodes": book,
                    "stale": [n for n, held in book.items() if held["stale"]]}

    def sidebar(self, element_id: str) -> dict:
        """the contextual panel, with the history of the nodes that put this element on the board."""
        with self._lock:
            return self.scene.sidebar(element_id, book=self.runs)

    def view(self, receipt: Receipt | None = None) -> dict:
        """the whole board as the renderer reads it, with the version it is at."""
        with self._lock:
            return {
                "version": self.version,
                "title": self.scene.title,
                "pipeline": self.scene.pipeline(),
                "board": self.scene.board(),
                "can_undo": bool(self._undo),
                "can_redo": bool(self._redo),
                "receipt": receipt.as_dict() if receipt else None,
                # the pictures the cards show as their bodies, by element id. only elements whose
                # bytes are actually in the store appear, so a card never links a file that is gone
                "assets": {
                    e.id: e.asset for e in self.scene.elements.values()
                    if e.asset and KIND_DTYPE[e.kind] in ("image",) and self.store.has(e.asset)
                },
            }
