"""the terminal view of a board, which is also how a test looks at one without a browser.

every verb here answers a question the frontend asks: what presets exist, what does this element's
sidebar hold, what does the plan look like, will this route take it. the board itself is built in
memory by `demo`, because persistence belongs to the app layer and this file is not the app layer.

    flowby presets                    the menu, with each preset's honest state
    flowby legend                     the four wires
    flowby modes                      freeform, fixed and style, and the crossings
    flowby catalogue                  the owner's tool list, resolved into presets and controls
    flowby graph                      the node layer for the browser, with no geometry in it
    flowby demo                       build a board, show both views
    flowby sidebar <element>          what clicking that element opens
    flowby plan --preset sketch-to-mesh --set detail=90000
    flowby routes                     every route, its ceiling, its gates
    flowby fit --preset animate-composition
    flowby emit --preset sketch-to-mesh --out plan.json
    flowby doctor
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import compile as compiler
from . import catalogue
from . import modes
from . import dtypes, presets, routes
from .scene import Scene, SceneRefused, Transform


def demo_board() -> Scene:
    """one board that exercises most of the machine: a sketch, a caption, and a chain."""
    scene = Scene(id="board-1", title="ceramic owl")
    sketch = scene.add("sketch", "the owl", asset="sha256:" + "a" * 64,
                       transform=Transform(x=0, y=0, width=640, height=640))
    scene.add("text", "caption", text="a ceramic owl on a plinth, studio light",
              transform=Transform(x=700, y=0, width=420, height=140))
    scene.apply(sketch.id, "sketch-to-mesh", {"detail": 90000, "fidelity": 0.85})
    scene.apply(sketch.id, "frosted-glass", {"frost": 0.42, "clarity": 0.7})
    return scene


def _say(text: str, as_json: bool, payload=None) -> None:
    if as_json:
        print(json.dumps(payload if payload is not None else text, indent=2, default=str))
    else:
        print(text)


def cmd_catalogue(args) -> int:
    if args.json:
        print(json.dumps({"tree": catalogue.tree(), "coverage": catalogue.coverage()}, indent=2))
        return 0
    for line in catalogue.tree():
        print(line)
    cover = catalogue.coverage()
    print()
    print(f"{cover['tools']} bullets -> {cover['presets_named']} presets and "
          f"{cover['controls']} controls")
    print(f"presets the brief never names, and why: {len(catalogue.PRIMITIVES)}")
    for name, reason in catalogue.PRIMITIVES.items():
        print(f"  {name:20} {reason}")
    if not cover["ok"]:
        for key in ("gaps", "misfiled", "unclaimed", "stale_primitives"):
            for line in cover[key]:
                print(f"  {key}: {line}")
        return 1
    print("every bullet resolves")
    return 0


def cmd_modes(args) -> int:
    legend = modes.legend()
    if args.json:
        print(json.dumps(legend, indent=2))
        return 0
    for mode in legend["modes"]:
        print(f"{mode['name']}: {mode['label']}")
        print(f"  first move   {mode['first_move']}")
        print(f"  opens        {mode['opens']}")
        print(f"  leaves for   {', '.join(mode['crosses_to'])}")
        print(f"  crossing     {mode['crossing']}")
        print(f"  before press {mode['cost_before_press']}")
        print()
    print("presets by door:")
    for door, names in legend["presets_by_door"].items():
        print(f"  {door:9} {', '.join(names) or 'none yet'}")
    print(f"\nevery door reaches every other: {legend['reachable']}")
    return 0


def cmd_kits(args) -> int:
    from . import kits as kitmod, looks as looksmod
    shelf = looksmod.catalogue(args.looks) if Path(args.looks).is_dir() else {}
    payload = kitmod.menu(presets=presets.PRESETS, looks=shelf)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    for kit in payload["kits"]:
        print(f"{kit['label']}  ({kit['ready']} of {kit['total']} ready)  {kit['blurb']}")
        for m in kit["members"]:
            indent = "      " if m["parent"] else "    "
            mark = "run" if m["runnable"] else m["state"]
            worded = "worded" if m["worded"] else ""
            print(f"{indent}{m['label']:18} {m['kind']:8} {mark:8} {worded:7} {m['blurb']}")
    return 0


def cmd_looks(args) -> int:
    """the catalogue of directions, grouped by the slot each one occupies."""
    from . import looks as looksmod
    try:
        shelf = looksmod.catalogue(args.looks)
    except looksmod.LookRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(looksmod.shelf(shelf), indent=2))
        return 0
    panel = looksmod.shelf(shelf)
    print(f"{panel['total']} looks, at most {panel['max_stack']} to a brief, one per slot")
    for group in panel["groups"]:
        print(f"\n{group['slot']}")
        for look in group["looks"]:
            families = ", ".join(look["families"])
            print(f"  {look['name']:16} {look['kit'] or '-':10} {families:22} {look['description'][:60]}")
            if look["conflicts"]:
                print(f"  {'':16} conflicts with {', '.join(look['conflicts'])}")
    print("\nthe slots: a mark is how the line was made, a surface what it was made on, a finish what "
          "happened to it after")
    return 0


def cmd_look(args) -> int:
    """compile a brief, or eject one look as the two steps a board would hold."""
    from . import looks as looksmod
    try:
        shelf = looksmod.catalogue(args.looks)
        if args.place:
            if len(args.look) != 1:
                raise looksmod.LookRefused("place takes one look, because a placement is one node")
            from .scene import Scene
            payload = looksmod.place(Scene(id="board", title="placed"), args.look[0],
                                     preset=args.preset, mode=args.mode, shelf=shelf)
        elif args.eject:
            if len(args.look) != 1:
                raise looksmod.LookRefused("eject takes one look, because it opens one graph")
            payload = looksmod.eject(args.look[0], model=args.model, mode=args.mode, looks=shelf)
        else:
            payload = looksmod.compile_looks(tuple(args.look), model=args.model, mode=args.mode,
                                             prompt=args.prompt, looks=shelf).as_dict()
    except (looksmod.LookRefused, presets.PresetRefused) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    if args.place:
        print(f"{payload['name']} placed as {payload['element']}, with {len(payload['nodes'])} nodes behind it:")
        for node in payload["nodes"]:
            print(f"  {node}")
        print(f"sliders set: {payload['values'] or 'nothing'}")
    elif args.eject:
        print(f"{payload['name']} as {len(payload['steps'])} steps:")
        for step in payload["steps"]:
            print(f"  {step['op']:14} {step['label']}")
            for key, value in step["params"].items():
                print(f"    {key:10} {value}")
    else:
        print(payload["prompt"])
        print(f"\napplied: {', '.join(payload['applied'])}")
        print(f"settings: {payload['params'] or 'nothing the look itself sets'}")
    for warning in payload["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _style_from_file(path: str):
    """a style read from json, because nothing persists styles yet and a plan is not a fixture.

    the file is the shape `Style.as_dict` prints plus its items. it is not trusted: `styles.gate` is the
    authority on whether a corpus may train, so a file that claims to be ready and is not gets refused
    here, with the gate's own reasons.
    """
    from . import kohya as kohya_mod, styles as S

    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    items = tuple(S.Item(name=str(i.get("name", "")), caption=str(i.get("caption", "")),
                         subject=str(i.get("subject", "")), technique=str(i.get("technique", "")))
                  for i in raw.get("items") or ())
    style = S.Style(id=str(raw.get("id") or "style"), label=str(raw.get("label") or raw.get("id") or "style"),
                    trigger=str(raw.get("trigger") or ""), base=str(raw.get("base") or "flux-dev"),
                    items=items, state=str(raw.get("state") or "corpus"),
                    weight=float(raw.get("weight") or 0.6))
    reasons = S.gate(style)
    if reasons:
        raise kohya_mod.KohyaRefused("; ".join(reasons))
    return S.advance(style, "gated")


def cmd_kohya(args) -> int:
    from . import kohya as kohya_mod, styles as S

    try:
        style = _style_from_file(args.style)
        layout = kohya_mod.Layout(root=args.root, kohya=args.kohya)
        payload = kohya_mod.run(style, layout, base=args.base)
    except (kohya_mod.KohyaRefused, S.StyleRefused, OSError) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    if args.write:
        os.makedirs(args.write, exist_ok=True)
        for name, body in payload["writes"].items():
            with open(os.path.join(args.write, name), "w", encoding="utf-8") as handle:
                handle.write(body)
        payload["wrote"] = [os.path.join(args.write, name) for name in payload["writes"]]
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    if args.write:
        print(f"wrote {len(payload['writes'])} files to {args.write}: {', '.join(sorted(payload['writes']))}")
    print(f"{payload['style']} ({payload['images']} images, trigger {payload['trigger']})")
    print(f"  estimate: {payload['estimate_minutes']} min on a free t4, and it resumes from the last epoch")
    print(f"  gates:    {', '.join(payload['gates'])}")
    print(f"  runs:     {payload['shell']}")
    print(f"  after:    {payload['after']}")
    return 0


def _book(path):
    """the history this command should use: a file when one is named, a fresh book otherwise."""
    from . import runs as runs_mod

    if not path:
        return runs_mod.Book()
    try:
        return runs_mod.Book.load(path, clock=time.time)
    except FileNotFoundError:
        # a path that is not there yet is a book with nothing in it, not an error: the first run
        # writes it
        return runs_mod.Book(clock=time.time)
    except runs_mod.RunsRefused as problem:
        # a history that does not hold up is worse than none: it would answer "already done" for a
        # node whose record was cut off. refuse the file, not the board.
        print(f"refused: {problem}", file=sys.stderr)
        raise SystemExit(1) from problem


def cmd_inspector(args) -> int:
    """the contextual panel's payload: one entry per node, with its history and its verdict.

    this is the seam the web board reads, the way `graph` is the seam the canvas reads. it carries no
    geometry and no styling: what is stale, what would be reused, and what each node last did.
    """
    from . import runs as runs_mod

    scene = demo_board()
    book = _book(args.book)
    work = runs_mod.work(scene.graph, book)
    nodes = {}
    for node_id in scene.graph.topo():
        node = scene.graph.nodes[node_id]
        held = book.runs_for(node_id)
        nodes[node_id] = {
            "id": node_id,
            "op": node.op,
            "label": node.label,
            "instance": node.instance,
            "params": dict(node.params),
            "minutes": round(node.minutes(), 3),
            "gpu": bool(node.requires.get("gpu")),
            "runs": [run.as_dict() for run in reversed(held)],
            "count": len(held),
            "verdict": work["detail"][node_id]["verdict"],
            "because": work["detail"][node_id].get("because", ""),
        }
    payload = {
        "kind": "flowby.inspector",
        "scene": scene.id,
        "title": scene.title,
        "book": args.book or None,
        "work": {"run": work["run"], "reuse": work["reuse"], "minutes": work["minutes"],
                 "targets": work["targets"]},
        "nodes": nodes,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    for node_id, entry in nodes.items():
        print(f"{entry['verdict']:5} {node_id:38} {entry['count']} runs  {entry['minutes']} min")
    print(f"next run: {len(work['run'])} to execute, {len(work['reuse'])} reused, {work['minutes']} min")
    return 0


def cmd_runs(args) -> int:
    """per-node history, and what the next run would actually execute."""
    from . import runs as runs_mod

    scene = demo_board()
    book = _book(args.book)
    # with no --book the book is empty: the demo board has not been run by anyone, and every node is
    # stale, which is what the command says rather than inventing a past.
    # the command exists to show that, and to show the reuse arithmetic once a run is filed.
    work = runs_mod.work(scene.graph, book, args.node or None)
    payload = {"work": work, "stale": runs_mod.stale(scene.graph, book),
               "runs": book.as_dict()}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"{len(scene.graph.nodes)} nodes, {len(payload['runs'])} with a history")
    print(f"next run: {len(work['run'])} to execute, {len(work['reuse'])} reused, "
          f"{work['minutes']} min")
    for node_id in work["order"]:
        detail = work["detail"][node_id]
        mark = "run " if detail["verdict"] == "run" else "reuse"
        why = detail.get("because", "")
        print(f"  {mark} {node_id:38} {why}")
    return 0


def cmd_run(args) -> int:
    """file a run against a node, so the history and the reuse arithmetic have something real in them.

    this is the seam the app layer drives when a job finishes; the cli exposes it so the rule can be
    exercised without a browser, and so a person can see a reuse instead of taking it on trust.
    """
    from . import runs as runs_mod

    scene = demo_board()
    book = _book(args.book)
    if args.node not in scene.graph.nodes:
        print(f"refused: {args.node!r} is not on this board", file=sys.stderr)
        return 1
    if args.all:
        for node_id in scene.graph.topo():
            fed = {port: (book.last_ok(source).id if book.last_ok(source) else None)
                   for port, source in runs_mod.upstream_of(scene.graph, node_id).items()}
            book.record(node_id, runs_mod.signature(scene.graph.nodes[node_id], fed),
                        minutes=scene.graph.nodes[node_id].minutes())
        ran = sorted(book.runs)
    else:
        sigs = runs_mod.signatures(scene.graph, book)
        book.record(args.node, sigs[args.node], minutes=scene.graph.nodes[args.node].minutes())
        ran = [args.node]
    work = runs_mod.work(scene.graph, book)
    if args.book:
        book.save(args.book)
    payload = {"recorded": ran, "work": work, "runs": book.as_dict(),
               "book": args.book or None}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"recorded {len(ran)} run{'s' if len(ran) != 1 else ''}: {', '.join(ran)}")
    print(f"next run: {len(work['run'])} to execute, {len(work['reuse'])} reused, "
          f"{work['minutes']} min")
    for node_id in work["run"] or ():
        print(f"  run  {node_id:38} {work['detail'][node_id].get('because', '')}")
    return 0


def cmd_serve(args) -> int:
    """run the bridge: the board a page talks to, and the gpus plugged into it."""
    import signal
    from . import server as srv
    from .session import Session
    from .store import Store

    host = args.host
    if host not in srv.LOOPBACK and not args.i_know:
        print(f"refusing to listen on {host}: this server has no login, and anyone who can reach it can "
              f"add things to the board and read what is on it. use 127.0.0.1, or pass --i-know-it-is-open "
              f"if it is behind something that authenticates.", file=sys.stderr)
        return 2
    store = Store(args.store)
    session = Session(store, title="untitled")
    origins = tuple(o for o in (args.origin or []))
    httpd = srv.make_server(session, host=host, port=args.port, allow_origins=origins)
    bound = httpd.server_address[:2]
    print(f"flowby is listening on http://{bound[0]}:{bound[1]}  (assets in {args.store})")
    if origins:
        print("pages allowed to call it: " + ", ".join(origins))
    signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        httpd.server_close()
    return 0


def cmd_presets(args) -> int:
    if args.json:
        print(json.dumps(presets.legend(), indent=2))
        return 0
    print(f"{'preset':17} {'wire':14} {'model':18} {'nodes':>5} {'controls':>8}  state")
    for line in presets.legend()["presets"]:
        wire = f"{dtypes.colour(line['from'])}->{dtypes.colour(line['to'])}"
        model = ", ".join(line["models"]) or "no model (see PROCEDURAL)"
        print(f"{line['name']:17} {wire:14} {model:18} {line['nodes']:>5} "
              f"{line['controls']:>8}  {line['state']}")
    print("\nevery preset is designed: the graphs wire and refuse correctly, and no asset has "
          "come back from a worker yet. every preset either names the model it calls or says, in "
          "PROCEDURAL, why it does not need one.")
    return 0


def cmd_actions(args) -> int:
    """the shelf: every action in a directory, what it takes, and that it is free."""
    from . import actions as actionmod
    try:
        shelf = actionmod.shelf(args.dir)
    except actionmod.ActionRefused as problem:
        print(f"refused: {problem}")
        return 1
    if args.json:
        print(json.dumps({name: {"runtime": a.runtime, "means": a.means, "minutes": a.minutes,
                                 "inputs": [{"name": p.name, "dtype": p.dtype} for p in a.inputs],
                                 "outputs": [{"name": p.name, "dtype": p.dtype} for p in a.outputs],
                                 "params": [{"key": p.key, "kind": p.kind, "default": p.default} for p in a.params]}
                          for name, a in shelf.items()}, indent=2))
        return 0
    print(f"{'action':14} {'runtime':10} {'wires':20} {'params':>6} {'minutes':>7}  what it does")
    for name, action in shelf.items():
        wires = ",".join(f"{p.dtype}" for p in action.inputs) + "->" + ",".join(p.dtype for p in action.outputs)
        print(f"{name:14} {action.runtime:10} {wires:20} {len(action.params):>6} {action.minutes:>7.1f}  {action.means}")
    print("\nevery action here is code, so a run costs nothing and takes seconds. the header in each file "
          "is the whole contract: name, wires, params and which params only apply sometimes.")
    return 0


def cmd_action(args) -> int:
    """one action's panel: the controls a page would draw, with the conditional ones marked."""
    from . import actions as actionmod
    try:
        shelf = actionmod.shelf(args.dir)
        if args.name not in shelf:
            print(f"refused: there is no action called {args.name!r}: the shelf has {', '.join(shelf)}")
            return 1
        values = json.loads(args.values) if args.values else None
        print(json.dumps(shelf[args.name].panel(values), indent=2))
    except actionmod.ActionRefused as problem:
        print(f"refused: {problem}")
        return 1
    except ValueError as problem:
        print(f"refused: --values is not json ({problem})")
        return 1
    return 0


def cmd_legend(args) -> int:
    if args.json:
        print(json.dumps({"wires": dtypes.palette(), "roles": dict(dtypes.ROLES)}, indent=2))
        return 0
    for wire in dtypes.palette():
        print(f"{wire['colour']:8} {wire['hex']}  {wire['dtype']:6} {wire['means']}")
    print("\nroles ride green, so a depth map and a portrait stay the same colour:")
    for name, means in dtypes.ROLES.items():
        print(f"  {name:8} {means}")
    return 0


def cmd_demo(args) -> int:
    scene = demo_board()
    if args.json:
        print(json.dumps({"board": scene.board(), "pipeline": scene.pipeline()}, indent=2))
        return 0
    print(f"{scene.title}: {len(scene.elements)} elements, {len(scene.graph.nodes)} nodes, "
          f"{len(scene.graph.edges)} wires")
    print("\nthe spatial layer:")
    for row in scene.board():
        print(f"  {row['label']:14} {row['kind']:7} {row['plane']:3} "
              f"showing {dtypes.colour(row['dtype']):6} presets={','.join(row['presets']) or '-'}")
    print("\nthe pipeline under it:")
    for row in scene.pipeline()["nodes"]:
        ins = ", ".join(f"{p}:{dtypes.colour(s['dtype'])}" for p, s in row["inputs"].items())
        print(f"  {row['id']:38} {row['op']:16} in[{ins or '-'}]")
    for element_id in scene.elements:
        recipe = scene.record(element_id)
        if recipe["steps"]:
            chain = " -> ".join(step["preset"] for step in recipe["steps"])
            print(f"\nrecipe for {scene.elements[element_id].label}: {chain}")
            print(f"  about {recipe['estimate']['minutes']} min "
                  f"({recipe['estimate']['gpu_minutes']} on a gpu)")
    print("\nwires:")
    for wire in scene.pipeline()["wires"]:
        print(f"  {wire['colour']:6} {wire['from']['node']}:{wire['from']['port']} -> "
              f"{wire['to']['node']}:{wire['to']['port']}")
    return 0


def cmd_graph(args) -> int:
    """the node layer as the browser wants it: nodes, wires, the palette, and no geometry.

    this is the seam where the renderer takes over. the graph decides what exists and what is
    wired to what; @xyflow decides where a node sits and how a wire curves to it.
    """
    scene = demo_board()
    payload = {
        "scene": scene.id,
        "title": scene.title,
        "pipeline": scene.pipeline(),
        "board": scene.board(),
        "legend": dtypes.palette(),
        "roles": dict(dtypes.ROLES),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    nodes = payload["pipeline"]["nodes"]
    wires = payload["pipeline"]["wires"]
    print(f"{payload['title']}: {len(nodes)} nodes, {len(wires)} wires, ranks "
          f"0..{max(n['rank'] for n in nodes)}")
    for node in nodes:
        ins = ", ".join(f"{p}:{dtypes.colour(v['dtype'])}" for p, v in node["inputs"].items())
        print(f"  r{node['rank']} {node['id']:38} {node['op']:16} in[{ins or '-'}]")
    return 0


def cmd_sidebar(args) -> int:
    scene = demo_board()
    if args.element not in scene.elements:
        print(f"no element {args.element}. the board has {', '.join(scene.elements)}",
              file=sys.stderr)
        return 2
    payload = scene.sidebar(args.element)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    element = payload["element"]
    print(f"{element['label']} ({element['kind']}, {element['plane']}) "
          f"showing {dtypes.colour(element['rendered'])}")
    for entry in payload["presets"]:
        print(f"\n  {entry['label']}  [{entry['state']}]")
        print(f"    {entry['blurb']}")
        print(f"    {dtypes.colour(entry['changes']['from'])} -> "
              f"{dtypes.colour(entry['changes']['to'])}"
              + (f", plane {entry['changes']['plane']}" if entry["changes"]["plane"] else ""))
        for control in entry["applied"] or []:
            print(f"    - {control['label']}: {control['value']}"
                  f"{control['unit']}  ({control['low']}..{control['high']}) {control['means']}")
    return 0


def cmd_recipe(args) -> int:
    """the chain on a board, read back as a recipe: named, versioned, with its inputs exposed."""
    from . import recipes
    scene = demo_board()

    def as_recipe(element_id: str):
        record = scene.record(element_id)
        if not record["steps"]:
            return None
        return recipes.of(record, inputs=recipes.default_inputs(record), author="the board",
                          category=record["kind"],
                          brief=f"{scene.elements[element_id].label}: bring your own "
                                f"{record['kind']} and get "
                                f"{presets.get(record['steps'][-1]['preset']).out_dtype()} back")

    if args.element:
        if args.element not in scene.elements:
            print(f"no element {args.element}. the board has {', '.join(scene.elements)}",
                  file=sys.stderr)
            return 2
        made = as_recipe(args.element)
        if made is None:
            print(f"{scene.elements[args.element].label}: nothing applied yet")
            return 0
        if args.card:
            drawn = recipes.card(made)
            if args.json:
                print(json.dumps(drawn, indent=2))
                return 0
            print(f"{drawn['name']} v{drawn['version']}  {drawn['brief']}")
            for item in drawn["inputs"]:
                mark = "*" if item["required"] else " "
                example = item["example"]["value"] if item["example"] else "nothing saved"
                print(f"  {mark} {item['label']}: saved at {example!r}")
            for slot in drawn["slots"]:
                print(f"  {'*' if slot['required'] else ' '} {slot['slot']} slot on {slot['preset']}"
                      f"{'' if slot['filled'] else ': nothing in it'}")
            for row in drawn["advanced"]:
                print(f"  advanced {row['name']}={row['value']!r} ({row['means']})")
            for row in drawn["hidden"]:
                print(f"  fixed    {row['preset']}.{row['name']}: {row['means']}")
            needs = drawn["needs"]
            print(f"  needs    {needs['runtime']}{', a gpu' if needs['gpu'] else ''}, "
                  f"weights: {', '.join(needs['weights']) or 'none'}, "
                  f"{'costs' if needs['paid'] else 'free'}")
            run = drawn["run"]
            print(f"  [{run['label']}]" + ("" if run["enabled"] else f"  blocked by {', '.join(run['blocked_by'])}"))
            return 0
        if args.json:
            print(json.dumps(made.panel(), indent=2))
            return 0
        print(f"{made.name} v{made.version}")
        print(f"  {made.brief}")
        for exposed in made.inputs:
            print(f"  input  {exposed.label}: {exposed.start!r} -> {exposed.preset}.{exposed.param}")
        print(f"  output {made.output} ({dtypes.colour(made.dtype)})")
        print(f"  models {', '.join(made.models) if made.models else 'none: every step is procedural'}")
        print(f"  about {made.estimate()['minutes']} min, "
              f"{made.estimate()['gpu_minutes']} of it on a gpu")
        for step in made.steps:
            values = ", ".join(f"{k}={v}" for k, v in step["values"].items())
            print(f"  - {step['preset']}: {values or 'defaults'}")
        return 0

    panels = []
    for element_id in scene.elements:
        made = as_recipe(element_id)
        label = scene.elements[element_id].label
        if made is None:
            if not args.json:
                print(f"{label}: nothing applied yet")
            continue
        if args.json:
            panels.append(made.panel())
            continue
        print(f"{label}: {made.name} v{made.version}  "
              f"{' -> '.join(step['preset'] for step in made.steps)}")
        print(f"  input {', '.join(e.label for e in made.inputs) or 'none'} -> "
              f"{made.output}, about {made.estimate()['minutes']} min")
    if args.json:
        print(json.dumps(panels, indent=2))
    return 0


def cmd_plan(args) -> int:
    try:
        if args.preset:
            values = dict(pair.split("=", 1) for pair in args.set or [])
            document = compiler.preset_plan(args.preset, values, route=args.route)
        else:
            document = compiler.plan(demo_board(), route=args.route,
                                     present=set(os.environ) if args.gates else None)
    except (compiler.CompileRefused, routes.RouteRefused, SceneRefused) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(document, indent=2))
        return 0
    for line in compiler.summary(document):
        print(line)
    return 0


def cmd_routes(args) -> int:
    if args.json:
        print(json.dumps([r.as_dict() for r in routes.ROUTES.values()], indent=2))
        return 0
    print(f"{'route':20} {'gpu':5} {'cap':>7} {'idle':>6}  cost")
    for route in routes.ROUTES.values():
        print(f"{route.name:20} {str(route.gpu):5} {route.ceiling_minutes:>6}m "
              f"{route.idle_kill_seconds:>5}s  {route.cost}")
        if route.policy != "fine":
            print(f"    policy {route.policy}: {route.note}")
    return 0


def cmd_fit(args) -> int:
    values = dict(pair.split("=", 1) for pair in args.set or [])
    try:
        document = compiler.preset_plan(args.preset, values)
    except (compiler.CompileRefused, SceneRefused) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    present = set(os.environ) if args.gates else None
    for route in routes.ROUTES.values():
        reasons = routes.fit(route, document, present)
        mark = "takes it" if not reasons else "refuses"
        print(f"{route.name:20} {mark}")
        for reason in reasons:
            print(f"    - {reason}")
        for note in routes.caveats(route, document):
            print(f"    ! {note}")
    return 0


def cmd_emit(args) -> int:
    try:
        document = compiler.preset_plan(args.preset, {}, route=args.route)
    except (compiler.CompileRefused, SceneRefused) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    body = json.dumps(document, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
        print(f"wrote {args.out} ({len(document['steps'])} steps)")
    else:
        print(body)
    return 0


def cmd_doctor(args) -> int:
    scene = demo_board()
    problems = scene.graph.check()
    for name in presets.names():
        preset = presets.get(name)
        if preset.sink not in preset.steps:
            problems.append(f"{name}: sink is not a step")
    for element_id in scene.elements:
        payload = scene.sidebar(element_id)
        if not payload["element"]["display"]:
            problems.append(f"{element_id} has nothing displayed")
    if problems:
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print(f"the board is coherent: {len(scene.graph.nodes)} nodes, "
          f"{len(scene.graph.edges)} wires, {len(presets.PRESETS)} presets, "
          f"{len(routes.ROUTES)} routes")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowby", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("presets", help="the preset menu").set_defaults(func=cmd_presets)
    kits_cmd = subs.add_parser("kits", help="the preset kits, and how far each member really is")
    kits_cmd.add_argument("--looks", default="looks", help="the folder of look rows")
    kits_cmd.set_defaults(func=cmd_kits)

    look_cmd = subs.add_parser("looks", help="the catalogue of directions, one group per slot")
    look_cmd.add_argument("--looks", default="looks", help="the folder of look rows")
    look_cmd.add_argument("--json", action="store_true")
    look_cmd.set_defaults(func=cmd_looks)

    one = subs.add_parser("look", help="compile a brief, or eject one look as editable steps")
    one.add_argument("look", nargs="+", help="look ids, at most three, one per slot")
    one.add_argument("--model", default="flux-dev", help="the model the wording is for")
    one.add_argument("--mode", default="image", choices=("image", "image_edit"))
    one.add_argument("--prompt", default="", help="the sentence the directions wrap around")
    one.add_argument("--looks", default="looks")
    one.add_argument("--eject", action="store_true", help="show the steps a board would hold")
    one.add_argument("--place", action="store_true", help="put the look on a board as nodes")
    one.add_argument("--preset", default="text-to-image", help="the preset the look feeds when placed")
    one.add_argument("--json", action="store_true")
    one.set_defaults(func=cmd_look)
    subs.add_parser("legend", help="the four wires").set_defaults(func=cmd_legend)

    acts = subs.add_parser("actions", help="the shelf of code actions, and what each one takes")
    acts.add_argument("--dir", default="actions")
    acts.add_argument("--json", action="store_true")
    acts.set_defaults(func=cmd_actions)

    act = subs.add_parser("action", help="one action's panel, as the sidebar would draw it")
    act.add_argument("name")
    act.add_argument("--dir", default="actions")
    act.add_argument("--values", help="json overrides, e.g. '{\"cell\": 10}'")
    act.set_defaults(func=cmd_action)
    cat = subs.add_parser("catalogue", help="the brief's tool list, and what each one became")
    cat.add_argument("--json", action="store_true")
    cat.set_defaults(func=cmd_catalogue)
    mods = subs.add_parser("modes", help="the three doors into the graph")
    mods.add_argument("--json", action="store_true")
    mods.set_defaults(func=cmd_modes)
    subs.add_parser("demo", help="build the demo board and show both views").set_defaults(func=cmd_demo)

    subs.add_parser("graph", help="the node layer, for the renderer").set_defaults(func=cmd_graph)
    sidebar = subs.add_parser("sidebar", help="the contextual panel for one element")
    sidebar.add_argument("element")
    sidebar.set_defaults(func=cmd_sidebar)

    plan = subs.add_parser("plan", help="compile a board into an execution plan")
    plan.add_argument("--preset")
    plan.add_argument("--set", action="append", metavar="NAME=VALUE")
    plan.add_argument("--route")
    plan.add_argument("--gates", action="store_true", help="check route gates against the environment")
    plan.set_defaults(func=cmd_plan)

    subs.add_parser("routes", help="every route and its ceiling").set_defaults(func=cmd_routes)

    recipe = subs.add_parser("recipe", help="the chain on a board, read back as a recipe")
    recipe.add_argument("element", nargs="?")
    # the card is what a stranger reads before pressing run: required marks, an Advanced fold
    # holding only the seed, and what the recipe needs. the panel is what its author reads.
    recipe.add_argument("--card", action="store_true", help="the card a stranger reads, not the panel")
    recipe.set_defaults(func=cmd_recipe)

    fit = subs.add_parser("fit", help="which routes would take a preset's plan")
    fit.add_argument("--preset", required=True)
    fit.add_argument("--set", action="append", metavar="NAME=VALUE")
    fit.add_argument("--gates", action="store_true")
    fit.set_defaults(func=cmd_fit)

    emit = subs.add_parser("emit", help="write a plan for kernel.sh")
    emit.add_argument("--preset", required=True)
    emit.add_argument("--route")
    emit.add_argument("--out")
    emit.set_defaults(func=cmd_emit)

    kohya = subs.add_parser("kohya", help="turn a gated style into the files a free colab trains from")
    kohya.add_argument("style", help="a style as json: id, trigger, base, items with captions")
    kohya.add_argument("--write", metavar="DIR", help="write metadata.jsonl, dataset.toml and run.sh here")
    kohya.add_argument("--root", default="/content/drive/MyDrive/flowby", help="where the colab session keeps things")
    kohya.add_argument("--kohya", default="/content/sd-scripts", help="where the colab session clones sd-scripts")
    kohya.add_argument("--base", default="flux.1-dev", help="only flux.1-dev has a proven argv")
    kohya.set_defaults(func=cmd_kohya)
    runs_cmd = subs.add_parser("runs", help="per-node history, and what the next run would execute")
    runs_cmd.add_argument("--node", action="append", help="limit to one node, and what it consumes")
    runs_cmd.add_argument("--book", help="read the history from this file")
    runs_cmd.set_defaults(func=cmd_runs)

    run_cmd = subs.add_parser("run", help="file a run against a node, and show what that makes stale")
    run_cmd.add_argument("node", help="the node that ran")
    run_cmd.add_argument("--all", action="store_true", help="run the whole board, upstream first")
    run_cmd.add_argument("--book", help="keep this run in this file, and read the rest from it")
    run_cmd.set_defaults(func=cmd_run)

    inspect_cmd = subs.add_parser("inspector", help="the contextual panel's payload, one entry per node")
    inspect_cmd.add_argument("--book", help="read the history from this file")
    inspect_cmd.set_defaults(func=cmd_inspector)

    serve = subs.add_parser("serve", help="run the bridge a page talks to (loopback only unless told otherwise)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--store", default="out/assets", help="where uploaded files are kept, by digest")
    serve.add_argument("--origin", action="append", help="a page origin allowed to call it, like http://localhost:5173 (repeatable)")
    serve.add_argument("--i-know-it-is-open", dest="i_know", action="store_true", help="allow a non-loopback host")
    serve.set_defaults(func=cmd_serve)
    subs.add_parser("doctor", help="check the board against itself").set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
