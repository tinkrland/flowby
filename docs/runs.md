# runs: per-node history, and the reuse key

A graph says what would happen. `runs.py` is the record of what did happen, one history per node, and it
exists for a rule the products above learned the hard way: **running a node does not run its upstream.**
The nodes above it are reused when the book has a run for exactly what they are now being asked for.

## the key is a run, not a param

A run is filed under a signature: the node's op, its params, and **the id of the run each input came
from**.

That last part is the design. Two nodes can be asked for the same thing and hand back different pixels,
because a diffusion pass samples rather than computes. Keying on the upstream node's *params* would let a
re-run upstream be silently skipped below it: the kind of stale cache that looks like a bug in the model.
Keying on the upstream *run id* means a new upstream run invalidates exactly the nodes below it.

While a node is waiting on an upstream that will run again, its input is marked `pending:<node>`. That
marker is not any real run, so the signature built from it matches nothing in the book and the refusal to
reuse propagates down the whole chain instead of stopping one node below the change.

## what a book keeps, and what it will not

- The newest 20 runs per node. The cap drops the oldest.
- A failed run is kept, and **can never be reused**: a failure sharing a signature is evidence the node
  does not work, not permission to skip it. `last_ok` looks past it, `latest` does not.
- A run id is a counter, not a clock, so a node asked for the same thing twice in the same instant still
  has two distinct runs to point at downstream.
- `forget` drops a node's history when the node leaves the board, or a new node reusing its id would
  inherit runs it never performed.

## where the book lives

Beside the scene, not inside it. The session copies the board for every action and undo swaps the copy
back in; a run that happened is a fact about the past, and undo does not un-happen it. `session.record_run`
reads the node's signature at the moment it files, so a run can only be filed against what the node is
being asked for now, never against a stale key.

Nothing in this module executes, measures or estimates a run. A run is recorded by whoever performed it,
and a node with no runs says so by having none.

## the history outlives the process

`Book.save(path)` writes the whole book atomically (temp file, `fsync`, `os.replace`), and
`Book.load(path)` reads one back under protest: every run is checked, so a state that is not a state, a
missing signature or a signature that is not a sha256 is refused with one sentence instead of being
trusted. A half-written history is worse than none, because it would answer "already done" for a node
whose record was cut off.

The command line carries it across processes:

```
bin/flowby run sketch-1 --all --book out/runs.json    # file a whole board, and keep it
bin/flowby inspector --book out/runs.json             # the panel's payload, reading that book
bin/flowby runs --book out/runs.json                  # the table, same book
```

`npm run graph` picks `out/runs.json` up when it exists, so the web panel shows real history when there
is any and an honest empty one when there is not.

## the panel

`bin/flowby --json inspector` is the seam the board reads, beside `--json graph`. The panel opens when
exactly one node is selected, because a panel that could only describe one node has no business being
open for five. What it says is decided in `web/src/inspector.mjs` and tested under node:
`web/src/Inspector.tsx` only draws it.
