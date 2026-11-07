"""the http binding. designed, and deliberately empty of logic.

everything this file does is transport: take a plan the compiler already produced, hand it to the
job store, dispatch it, and push whatever comes back down the open sockets. if a rule lives here
instead of in `flowby/`, then the tests in `tests/selftest.py` stop covering it, which is the whole
reason the modules are importable without a web framework.

fastapi and celery are not installed in this checkout, so this module is imported behind a guard
and its state is `designed`. `python3 -m flowby.app` says so rather than crashing.
"""

import json
import time

from flowby import compile as compiler
from flowby import hub as hubmod
from flowby import job as jobs
from flowby import routes

try:  # pragma: no cover - the binding only exists where the stack is installed
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from pydantic import BaseModel
    HAVE_STACK = True
except ModuleNotFoundError:  # pragma: no cover
    HAVE_STACK = False

STORE = jobs.Store()
HUB = hubmod.Hub()

STATE = "designed"
EVIDENCE = "no request has been served: fastapi is not installed in this checkout"


if HAVE_STACK:  # pragma: no cover

    app = FastAPI(title="flowby", version="0.1.0")

    class PlanIn(BaseModel):
        plan: dict

    class CompleteIn(BaseModel):
        plan_digest: str
        artifacts: list

    def ws_name(session: str) -> str:
        """one name per board, so the inspector and the canvas share a socket's worth of state."""
        return session

    @app.post("/jobs")
    def submit(body: PlanIn):
        if body.plan.get("contract") != compiler.CONTRACT:
            raise HTTPException(400, f"this service speaks {compiler.CONTRACT}")
        route = routes.get(body.plan["route"])
        job, created = STORE.submit(body.plan)
        if created:
            STORE.dispatch(job.id)
            from .tasks import dispatch_job

            dispatch_job.delay(job.id)
        HUB.broadcast(ws_name(body.plan["scene"]),
                      {"kind": "job", "job": job.as_dict(), "created": created})
        return {"job": job.as_dict(), "created": created, "route": route.name}

    @app.get("/jobs/{job_id}")
    def read(job_id: str):
        try:
            return STORE.jobs[job_id].as_dict()
        except KeyError:
            raise HTTPException(404, "no such job") from None

    @app.get("/jobs/{job_id}/plan")
    def config(job_id: str):
        """what the runtime fetches by job id once it is awake: the plan, and nothing else."""
        try:
            job = STORE.jobs[job_id]
        except KeyError:
            raise HTTPException(404, "no such job") from None
        STORE.start(job_id)
        return job.plan

    @app.post("/hook/job/{job_id}/beat")
    def beat(job_id: str):
        try:
            STORE.beat(job_id)
        except jobs.JobRefused as refusal:
            raise HTTPException(409, str(refusal)) from None
        return {"ok": True, "beats": STORE.jobs[job_id].beats}

    @app.post("/hook/job/{job_id}/complete")
    def complete(job_id: str, body: CompleteIn):
        try:
            job = STORE.complete(job_id, body.model_dump())
            STORE.stored(job_id)
        except jobs.JobRefused as refusal:
            raise HTTPException(409, str(refusal)) from None
        HUB.artifacts(ws_name(job.plan["scene"]), job, job.artifacts)
        return {"ok": True, "artifacts": job.artifacts}

    @app.websocket("/board/{session}")
    async def board(websocket: WebSocket, session: str):
        await websocket.accept()
        sub = HUB.open(ws_name(session))
        try:
            while True:
                for message in sub.queue:
                    await websocket.send_text(json.dumps(message))
                sub.queue.clear()
                await websocket.receive_text()  # the client's own pings keep this honest
        except WebSocketDisconnect:
            HUB.close(sub)

    @app.get("/routes")
    def route_list():
        return {"state": STATE, "evidence": EVIDENCE,
                "routes": [r.as_dict() for r in routes.ROUTES.values()]}

    @app.get("/health")
    def health():
        return {"ok": True, "state": STATE, "evidence": EVIDENCE,
                "jobs": len(STORE.jobs), "sockets": len(HUB.subscribers())}


def main() -> int:
    if not HAVE_STACK:
        print("the http binding is designed, not installed.")
        print(f"  {EVIDENCE}")
        print("  the modules it wraps are all importable: bin/flowby doctor")
        return 1
    import uvicorn  # pragma: no cover

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    raise SystemExit(main())
