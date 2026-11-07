"""the terminal view of a board, which is also how a test looks at one without a browser.

every verb here answers a question the frontend asks: what presets exist, what does this element's
sidebar hold, what does the plan look like, will this route take it. the board itself is built in
memory by `demo`, because persistence belongs to the app layer and this file is not the app layer.

    flowby presets                    the menu, with each preset's honest state
    flowby legend                     the four wires
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

from . import compile as compiler
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
    scene = demo_board()
    if args.element:
        if args.element not in scene.elements:
            print(f"no element {args.element}. the board has {', '.join(scene.elements)}",
                  file=sys.stderr)
            return 2
        recipe = scene.record(args.element)
        if args.json:
            print(json.dumps(recipe, indent=2))
            return 0
        print(f"{recipe['name']}: {' -> '.join(s['preset'] for s in recipe['steps'])}")
        print(f"  about {recipe['estimate']['minutes']} min, "
              f"{recipe['estimate']['gpu_minutes']} of it on a gpu")
        for step in recipe["steps"]:
            values = ", ".join(f"{k}={v}" for k, v in step["values"].items())
            print(f"  - {step['preset']}: {values or 'defaults'}")
        return 0
    if args.json:
        print(json.dumps([scene.record(e) for e in scene.elements], indent=2))
        return 0
    for element_id in scene.elements:
        recipe = scene.record(element_id)
        label = scene.elements[element_id].label
        if not recipe["steps"]:
            print(f"{label}: nothing applied yet")
            continue
        print(f"{label}: {' -> '.join(s['preset'] for s in recipe['steps'])}")
        print(f"  about {recipe['estimate']['minutes']} min "
              f"({recipe['estimate']['gpu_minutes']} on a gpu)")
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
    subs.add_parser("legend", help="the four wires").set_defaults(func=cmd_legend)
    subs.add_parser("demo", help="build the demo board and show both views").set_defaults(func=cmd_demo)

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

    subs.add_parser("doctor", help="check the board against itself").set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
