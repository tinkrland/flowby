"""the celery side: one task that opens a browser and one that never gets written.

`dispatch_job` is the only place in this tree that would touch browserbase, and it is the only
place that needs to know a colab notebook exists. everything upstream hands it a job id and a plan
file, which is why the routing decision can move to a paid worker later without the board noticing.

celery is not installed here, so this file is `designed`. it stays short on purpose: the moment it
grows a decision, that decision belongs in `flowby/routes.py` instead.
"""

import json
import os
import tempfile

try:  # pragma: no cover
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover
    Celery = None

STATE = "designed"
EVIDENCE = "no job has been dispatched: celery and browserbase are not configured here"

if Celery is not None:  # pragma: no cover
    app = Celery("flowby", broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    app.conf.task_acks_late = True
    app.conf.worker_prefetch_multiplier = 1
    app.conf.task_time_limit = 60 * 70  # under the colab ceiling, so a stuck job is ours to fail

    @app.task(bind=True, max_retries=1)
    def dispatch_job(self, job_id: str):
        """write the plan where the runtime can read it, then drive the browser to it."""
        from flowby.job import Store  # the store is the app's, not the worker's
        from flowby.routes import get

        store = Store()
        job = store.jobs[job_id]
        route = get(job.route)
        handle, path = tempfile.mkstemp(prefix=f"{job_id}-", suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as plan_file:
            json.dump(job.plan, plan_file)

        if route.name == "colab-browserbase":
            # the cookie is the credential, and it is the first thing to expire. keeping the
            # session injection in one place is what makes that failure legible.
            from .browser import ColabSession

            with ColabSession(cookies=os.environ["GOOGLE_SESSION_COOKIES"],
                              notebook=os.environ["COLAB_NOTEBOOK_ID"]) as session:
                session.open_notebook()
                session.run_kernel_sh(plan_path=path,
                                      job_id=job_id,
                                      callback=os.environ["FLOWBY_CALLBACK"])
        else:
            raise NotImplementedError(
                f"{route.name} is designed and not wired. kernel/kernel.sh runs anywhere a shell "
                f"and a gpu exist together; only the colab driver is named here."
            )
        return {"job": job_id, "route": route.name}
