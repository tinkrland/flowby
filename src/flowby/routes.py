"""where a job runs, and what each place honestly cannot do.

the compute question is the one place this design is tempted to lie, so the constraints are data
rather than prose. a route declares its ceiling, how long it survives without a heartbeat, whether
the disk outlives the job, and what it costs. `fit` refuses a plan that will not survive there, and
`choose` walks cheapest first while handing back the reasons it is nervous.

the colab route is in this table because it is the cheap one. it is also the one whose ceiling is
twelve hours, whose runtime dies ninety seconds after the browser stops talking to it, whose disk
lives in someone else's drive, and whose terms do not welcome automation. those four facts are the
four fields below, so a job that does not fit is refused here instead of dying at hour nine.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    name: str
    label: str
    state: str
    gpu: bool | None
    ephemeral: bool
    ceiling_minutes: int
    idle_kill_seconds: int
    persistence: str
    cost: str
    gates: tuple[str, ...]
    note: str
    policy: str = "fine"

    def as_dict(self) -> dict:
        return {
            "name": self.name, "label": self.label, "state": self.state,
            "gpu": self.gpu, "ephemeral": self.ephemeral,
            "ceiling_minutes": self.ceiling_minutes,
            "idle_kill_seconds": self.idle_kill_seconds,
            "persistence": self.persistence, "cost": self.cost,
            "gates": list(self.gates), "policy": self.policy, "note": self.note,
        }


ROUTES = {
    "local": Route(
        name="local",
        label="the machine you are on",
        state="designed",
        gpu=False,
        ephemeral=False,
        ceiling_minutes=1440,
        idle_kill_seconds=0,
        persistence="the disk you already have",
        cost="free",
        gates=(),
        note="the honest default. no gpu is assumed, so anything that asks for one is routed past it.",
    ),
    "colab-browserbase": Route(
        name="colab-browserbase",
        label="a colab runtime, driven by a browser",
        state="designed",
        gpu=True,
        ephemeral=True,
        ceiling_minutes=720,
        idle_kill_seconds=90,
        persistence="the account's google drive, and nothing else",
        cost="free, at the price of someone else's queue",
        gates=("GOOGLE_SESSION_COOKIES", "COLAB_NOTEBOOK_ID"),
        policy="contested",
        note=("a session cookie is the credential and cookies expire on google's schedule, not "
              "ours; the runtime is reclaimed when it goes quiet; and colab's terms do not invite "
              "automation of the runtime, so this route is a prototype rail with a known ceiling "
              "rather than a place to put a customer's work."),
    ),
    "runpod-serverless": Route(
        name="runpod-serverless",
        label="a serverless gpu worker",
        state="designed",
        gpu=True,
        ephemeral=True,
        ceiling_minutes=240,
        idle_kill_seconds=30,
        persistence="a network volume, if you pay for one",
        cost="per second, from pennies",
        gates=("RUNPOD_API_KEY", "RUNPOD_ENDPOINT"),
        note="the boring answer, and the one a job over a few hours actually wants.",
    ),
    "replicate": Route(
        name="replicate",
        label="someone else's model, called directly",
        state="designed",
        gpu=True,
        ephemeral=True,
        ceiling_minutes=60,
        idle_kill_seconds=0,
        persistence="none",
        cost="per prediction",
        gates=("REPLICATE_API_TOKEN",),
        note=("no shell, so kernel.sh is not what runs there. it fits plans whose steps are all "
              "single-model calls, and refuses the rest."),
    ),
}


class RouteRefused(Exception):
    """no route will take this plan, and the reasons are the message."""


def get(name: str) -> Route:
    try:
        return ROUTES[name]
    except KeyError:
        raise RouteRefused(
            f"there is no route {name!r}. the routes are {', '.join(sorted(ROUTES))}."
        ) from None


def fit(route: Route, plan: dict, present: set[str] | None = None) -> list[str]:
    """every reason this route would refuse the plan. empty means it will take it.

    `present` is the set of environment keys the caller actually has. None means "do not check
    gates", which is what a compiler that does not read secrets should pass.
    """
    env = plan.get("env", {})
    reasons = []
    if env.get("gpu") and not route.gpu:
        reasons.append(f"{route.label} has no gpu and the plan needs one")
    minutes = plan.get("estimate_minutes", 0)
    if minutes > route.ceiling_minutes:
        reasons.append(
            f"the plan is about {minutes:.0f} minutes and {route.label} caps at "
            f"{route.ceiling_minutes}"
        )
    if present is not None:
        missing = [gate for gate in route.gates if gate not in present]
        if missing:
            reasons.append(f"{route.label} needs {', '.join(missing)}")
    if route.name == "replicate" and any(
        step["op"] in ("render.frames", "anim.orbit", "mesh.bake")
        for step in plan.get("steps", [])
    ):
        reasons.append("the plan needs a shell, and replicate runs one model per call")
    return reasons


def caveats(route: Route, plan: dict) -> list[str]:
    """what a route will do, that the caller should know while it is still cheap to change."""
    notes = []
    if route.policy != "fine":
        notes.append(f"policy: {route.policy}. {route.note}")
    cached = plan.get("resume", {}).get("weights_cached_on_drive")
    if route.ephemeral and plan.get("env", {}).get("models") and not cached:
        notes.append(
            f"{', '.join(plan['env']['models'])} will be fetched again on {route.label}, "
            f"because its disk does not outlive the job"
        )
    if route.idle_kill_seconds and plan.get("steps"):
        notes.append(
            f"the runtime is reclaimed after {route.idle_kill_seconds}s of silence, so "
            f"kernel.sh beats while it works"
        )
    return notes


def choose(plan: dict, present: set[str] | None = None) -> tuple[Route, list[str]]:
    """cheapest first that will take it, with the caveats attached rather than hidden."""
    refusals = {}
    for route in ROUTES.values():
        reasons = fit(route, plan, present)
        if reasons:
            refusals[route.name] = reasons
            continue
        return route, caveats(route, plan)
    lines = [f"{name}: {'; '.join(reasons)}" for name, reasons in refusals.items()]
    raise RouteRefused("no route takes this plan:\n  " + "\n  ".join(lines))
