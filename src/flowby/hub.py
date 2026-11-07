"""the fan-out to whoever has the board open, and the replay that makes switching views cheap.

a socket that drops a message silently is worse than no socket, because the board keeps showing
the old state and nobody knows. so the two rules are: a subscriber that cannot keep up is closed
rather than skipped past, and a subscriber that reconnects is handed the last messages it missed.

that second rule is why toggling between the spatial view and the pipeline view costs nothing: the
inspector is another subscriber, it opens, it replays, it agrees with what is on screen.
"""

import itertools
from collections import deque
from dataclasses import dataclass, field


class HubRefused(Exception):
    """a subscriber that is not open cannot be written to. reopening is how you fix it."""


@dataclass
class Subscriber:
    id: str
    workspace: str
    buffer: int = 256
    queue: deque = field(default_factory=deque)
    dropped: int = 0
    open: bool = True

    def drain(self) -> list:
        out = list(self.queue)
        self.queue.clear()
        return out


class Hub:
    def __init__(self, replay: int = 32):
        self.replay = replay
        self._log: dict[str, deque] = {}
        self._subs: dict[str, Subscriber] = {}
        self._ids = itertools.count(1)
        self.sent = 0
        self.dropped = 0

    def open(self, workspace: str, buffer: int = 256, replay: bool = True) -> Subscriber:
        sub = Subscriber(id=f"sub-{next(self._ids)}", workspace=workspace, buffer=buffer)
        self._subs[sub.id] = sub
        if replay:
            for message in self._log.get(workspace, ()):
                sub.queue.append(message)
        return sub

    def close(self, sub: Subscriber) -> None:
        sub.open = False
        self._subs.pop(sub.id, None)

    def broadcast(self, workspace: str, message: dict) -> int:
        log = self._log.setdefault(workspace, deque(maxlen=self.replay))
        log.append(message)
        delivered = 0
        for sub in list(self._subs.values()):
            if sub.workspace != workspace:
                continue
            if len(sub.queue) >= sub.buffer:
                sub.dropped += 1
                self.dropped += 1
                self.close(sub)
                continue
            sub.queue.append(message)
            delivered += 1
            self.sent += 1
        return delivered

    def subscribers(self, workspace: str | None = None) -> list[Subscriber]:
        return [s for s in self._subs.values()
                if workspace is None or s.workspace == workspace]

    # -- the two messages the frontend actually needs ----------------------

    def artifacts(self, workspace: str, job, artifacts: list) -> dict:
        """fresh pixels for the board, addressed by element so the frame updates in place."""
        message = {
            "kind": "artifacts",
            "job": job.id if hasattr(job, "id") else str(job),
            "artifacts": artifacts,
            "by_element": {a["element"]: a for a in artifacts},
        }
        self.broadcast(workspace, message)
        return message

    def progress(self, workspace: str, job_id: str, step: str, index: int, total: int) -> dict:
        message = {"kind": "progress", "job": job_id, "step": step,
                   "index": index, "total": total}
        self.broadcast(workspace, message)
        return message
