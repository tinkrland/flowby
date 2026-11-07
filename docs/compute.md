# compute

*the loop, the seams that decide whether it survives, and what a job actually hands back*

## the loop, as it runs

```
board  ->  compile.plan  ->  routes.choose  ->  job.Store.submit  ->  dispatch
                                                                        |
   browser  -------------------------------- opens the runtime -------<-+
      |
   kernel.sh   reads the flat plan, exports the environment, starts the heartbeat,
               pip installs what the plan asked for, runs worker.py, tars, posts back
      |
   POST /hook/job/{id}/complete   ->  artifact check  ->  hub.broadcast  ->  the frame redraws
```

two properties make that diagram worth drawing. every arrow after `compile.plan` carries a json document and no graph, and every arrow before it is testable without a network.

## the flat plan, and why

the plan is a topologically ordered list of steps, and each step's inputs already name another step:

```json
{"id": "sketch-1/sketch-to-mesh/mould",
 "op": "mesh.triposr",
 "inputs": {"control": "sketch-1/sketch-to-mesh/read:out"},
 "params": {"target_faces": 60000},
 "outputs": {"out": "mesh"},
 "minutes": 3.2, "gpu": true}
```

`kernel.sh` does not resolve a wire; `worker.py` does not resolve a wire; `resolve()` in the worker turns `step:port` into a string and that is the whole of the runtime's graph interpretation. the reason is not tidiness. a container that is reclaimed after ninety seconds, on a machine nobody can ssh into, is the worst possible place to discover a type error.

the plan also carries `display` (which node feeds which element, so fresh pixels know where to land), `board` (page coordinates, so a worker that renders a composition knows the arrangement), and `cost` (minutes, split by whether they need a gpu).

## the four seams

the brief's loop is a browser driving a free colab runtime, and it has four constraints that a job can violate silently. they are route fields rather than documentation:

| seam | what happens | how the tree handles it |
| --- | --- | --- |
| **ceiling** | the runtime is reclaimed at twelve hours, mid-job | `ceiling_minutes`, and `fit` refuses a plan over it |
| **quiet** | ninety seconds without a beat and the runtime goes | `idle_kill_seconds`, and `job.Store.stale()` names the job |
| **disk** | no persistent storage, so weights are fetched every time | `persistence`, and `caveats` says the models will be re-downloaded |
| **credential** | a session cookie, which expires on google's schedule and is not really a key | `policy: contested` and one module that touches it |

the last one is the one worth being blunt about. cookie injection works until it does not, it fails in a way that looks like a network error, and the terms of the free runtime do not invite automation. that is exactly why `routes.py` has four entries and why moving a job is a table change: the colab route should be the cheap first rail, not the only rail with the customer's work on it.

## the heartbeat

```bash
FLOWBY_CALLBACK=https://host/hook/job kernel.sh --plan plan.json
```

with a callback set, `kernel.sh` starts a background `POST /beat` every thirty seconds before it installs anything, because a `pip install` of torch can outlast the idle timeout on its own. the trap kills the loop on the way out. `job.Store.stale()` uses the route's own `idle_kill_seconds`, so a local job never goes stale and a colab job goes stale at ninety seconds and not at some global constant.

## what comes back

`worker.py` writes each declared artifact plus `manifest.json`, and the manifest is the only thing that is posted:

```json
{"contract": "flowby/1",
 "plan_digest": "fb_...",
 "simulated": true,
 "artifacts": [{"name": "sketch-1.glb", "element": "sketch-1",
                "sha256": "...", "bytes": 135}]}
```

the store refuses three payloads on purpose: one whose `plan_digest` is not this job, one that is missing a file the plan promised, and one whose bytes arrive without a sha256. the third is the one that matters, because a zero-byte glb with no hash is indistinguishable from a worker that crashed halfway and a worker that never ran.

## the honest gap

`worker.py` implements **no model call**. every op that would call one is named in `UNIMPLEMENTED` with the model it needs, and refuses with that sentence unless `--simulate` is passed. simulate writes deterministic bytes and real hashes, so the whole plumbing (plan, env, manifest, tar, webhook, artifact check, broadcast) is exercised end to end on a cpu with no gpu and no account anywhere.

that is a smaller claim than "it works", and it is the one the tree can actually support. `readme.md` says the same thing in the state table.
