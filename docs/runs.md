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
