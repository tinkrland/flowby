"""a job is a plan with a life, and the life has legal moves.

the state machine is here because the interesting failures are not "it broke", they are "it came
back twice", "it came back for the wrong plan", and "it came back without the file it promised".
each of those is a refusal below, and each refusal is a sentence a person can act on.

the dedupe is the other half. a plan's digest is its identity, so dragging a slider back to where
it was does not queue the same work twice, and a double click on a preset is one job rather than
two runtimes racing to write the same artifact.
"""

import re
import time
from dataclasses import dataclass, field

from . import compile as compiler

STATES = ("queued", "dispatched", "running", "returned", "stored", "failed", "refused")

TRANSITIONS = {
    "queued": {"dispatched", "refused", "failed"},
    "dispatched": {"running", "refused", "failed"},
    "running": {"returned", "failed"},
    "returned": {"stored", "failed"},
    "stored": set(),
    "failed": set(),
    "refused": set(),
}

LIVE = ("queued", "dispatched", "running", "returned")

SHA = re.compile(r"^[0-9a-f]{64}$")


class JobRefused(Exception):
    """the transition, the payload, or the artifacts did not hold up."""


@dataclass
class Job:
    id: str
    plan: dict
    state: str = "queued"
    created: float = 0.0
    updated: float = 0.0
    last_beat: float = 0.0
    beats: int = 0
    attempts: int = 0
    artifacts: list = field(default_factory=list)
    reason: str | None = None

    @property
    def digest(self) -> str:
        return self.plan["job_id"]

    @property
    def route(self) -> str:
        return self.plan["route"]

    def as_dict(self) -> dict:
        return {"id": self.id, "state": self.state, "route": self.route,
                "created": self.created, "updated": self.updated,
                "beats": self.beats, "attempts": self.attempts,
                "artifacts": list(self.artifacts), "reason": self.reason}


class Store:
    def __init__(self, clock=time.time):
        self.jobs: dict[str, Job] = {}
        self.clock = clock

    # -- lifecycle ---------------------------------------------------------

    def submit(self, plan: dict) -> tuple[Job, bool]:
        if plan.get("contract") != compiler.CONTRACT:
            raise JobRefused(
                f"this store speaks {compiler.CONTRACT}, not {plan.get('contract')!r}"
            )
        for job in self.jobs.values():
            if job.digest == plan["job_id"] and job.state in LIVE:
                return job, False
        now = self.clock()
        job = Job(id=plan["job_id"], plan=plan, created=now, updated=now, last_beat=now)
        self.jobs[job.id] = job
        return job, True

    def _can_move(self, job: Job, state: str) -> None:
        if state not in TRANSITIONS[job.state]:
            raise JobRefused(
                f"{job.id} is {job.state} and cannot become {state}. "
                f"from {job.state} it can become {', '.join(sorted(TRANSITIONS[job.state])) or 'nothing'}."
            )

    def _move(self, job: Job, state: str, reason: str | None = None) -> Job:
        self._can_move(job, state)
        job.state = state
        job.updated = self.clock()
        if reason:
            job.reason = reason
        return job

    def _get(self, job_id: str) -> Job:
        try:
            return self.jobs[job_id]
        except KeyError:
            raise JobRefused(f"there is no job {job_id!r}") from None

    def dispatch(self, job_id: str) -> Job:
        job = self._get(job_id)
        job.attempts += 1
        job.last_beat = self.clock()
        return self._move(job, "dispatched")

    def start(self, job_id: str) -> Job:
        return self._move(self._get(job_id), "running")

    def beat(self, job_id: str) -> Job:
        job = self._get(job_id)
        if job.state not in ("dispatched", "running"):
            raise JobRefused(f"{job.id} is {job.state}, so there is nothing to keep alive")
        job.beats += 1
        job.last_beat = self.clock()
        return job

    def fail(self, job_id: str, reason: str) -> Job:
        return self._move(self._get(job_id), "failed", reason)

    def refuse(self, job_id: str, reason: str) -> Job:
        return self._move(self._get(job_id), "refused", reason)

    def complete(self, job_id: str, payload: dict) -> Job:
        job = self._get(job_id)
        self._can_move(job, "returned")  # state first: a queued job has no artifacts to argue about
        if payload.get("plan_digest") != job.digest:
            raise JobRefused(
                f"this payload is for {payload.get('plan_digest')!r} and the job is {job.digest}"
            )
        job.artifacts = self.check_artifacts(job, payload.get("artifacts") or [])
        return self._move(job, "returned")

    def stored(self, job_id: str) -> Job:
        return self._move(self._get(job_id), "stored")

    # -- the payload -------------------------------------------------------

    def check_artifacts(self, job: Job, artifacts: list) -> list:
        """the files the plan promised, or a refusal that names the ones missing."""
        declared = {a["name"]: a for a in job.plan["artifacts"]}
        seen = {}
        for record in artifacts:
            name = record.get("name")
            if name not in declared:
                raise JobRefused(
                    f"{name!r} was not in the plan. the plan promised {', '.join(declared)}."
                )
            if name in seen:
                raise JobRefused(f"{name} arrived twice")
            digest = str(record.get("sha256") or "")
            if not SHA.match(digest):
                raise JobRefused(f"{name} arrived without a sha256, so its bytes are a rumour")
            seen[name] = {
                "name": name,
                "dtype": declared[name]["dtype"],
                "kind": declared[name].get("kind"),
                "element": declared[name]["element"],
                "sha256": digest,
                "bytes": int(record.get("bytes") or 0),
                "preview": record.get("preview"),
            }
        missing = [name for name in declared if name not in seen]
        if missing:
            raise JobRefused(f"the plan promised {', '.join(missing)} and they are not in the payload")
        return [seen[name] for name in declared]

    # -- the watchdog ------------------------------------------------------

    def stale(self) -> list[Job]:
        """jobs whose runtime has gone quiet past its route's own kill line."""
        from . import routes

        now = self.clock()
        out = []
        for job in self.jobs.values():
            if job.state not in ("dispatched", "running"):
                continue
            kill = routes.get(job.route).idle_kill_seconds
            if kill and now - job.last_beat > kill:
                out.append(job)
        return out
