"""flowby selftests: stdlib only, no network, no gpu. run: python3 tests/selftest.py

the suite holds the tree to the claims the readme makes. the four that matter most:

  a wire carries one dtype and never coerces, so a conversion is a node you can see;
  a preset is a subgraph that chains off whatever the element is currently showing;
  a plan is flat and every wire in it already names a step, so the worker interprets nothing;
  a route refuses a job that will not survive it, before a browser is opened.

the kernel and alignment halves run as subprocesses because they are not python: `bash -n` and
`node --test` either work here or the tree is lying about itself.
"""

import contextlib
import io
import json
import re
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowby import compile as compiler  # noqa: E402
from flowby import catalogue, dtypes, modes, presets, routes  # noqa: E402
from flowby import hub as hubmod  # noqa: E402
from flowby import job as jobs  # noqa: E402
from flowby.graph import Graph, GraphRefused, Node, Port  # noqa: E402
from flowby.scene import Scene, SceneRefused, Transform  # noqa: E402

ASSET = "sha256:" + "a" * 64
MODEL_ASSET = "sha256:" + "b" * 64


def worker_run(plan: dict, directory: pathlib.Path) -> dict:
    """the worker, in process, with simulated bytes. used wherever artifacts are asserted."""
    sys.path.insert(0, str(ROOT / "kernel"))
    import worker

    return worker.run(plan, directory, simulate=True)


def board() -> Scene:
    """a board with one sketch, one caption, and nothing applied."""
    scene = Scene(id="t", title="test board")
    scene.add("sketch", "owl", asset=ASSET, transform=Transform(x=0, y=0))
    scene.add("text", "caption", text="a ceramic owl")
    return scene


# ---------------------------------------------------------------------------


class Wires(unittest.TestCase):
    def test_four_wires_and_four_colours(self):
        self.assertEqual(len(dtypes.WIRES), 4)
        colours = [w.colour for w in dtypes.WIRES.values()]
        self.assertEqual(len(set(colours)), 4)
        for name in ("text", "image", "video", "mesh"):
            self.assertIn(name, dtypes.WIRES)

    def test_a_colour_comes_from_the_dtype_and_nowhere_else(self):
        self.assertEqual(dtypes.colour("image"), "green")
        with self.assertRaises(dtypes.UnknownDtype):
            dtypes.colour("mask")  # a role is not a wire
        with self.assertRaises(dtypes.UnknownDtype):
            dtypes.colour("audio")

    def test_roles_ride_green_instead_of_earning_a_colour(self):
        for name in dtypes.ROLES:
            self.assertEqual(dtypes.of_role(name), "image")
        with self.assertRaises(dtypes.UnknownDtype):
            dtypes.role("vibes")

    def test_nothing_coerces(self):
        self.assertTrue(dtypes.accepts("image", "image"))
        self.assertFalse(dtypes.accepts("image", "mesh"))
        self.assertIn("green", dtypes.mismatch("image", "mesh"))
        self.assertIn("red", dtypes.mismatch("image", "mesh"))


class Graphs(unittest.TestCase):
    def graph(self) -> Graph:
        g = Graph()
        g.add(Node("a", "make.image", outputs={"out": Port("image")}))
        g.add(Node("b", "use.image", inputs={"in": Port("image")},
                   outputs={"out": Port("image")}))
        return g

    def test_a_wire_between_two_dtypes_is_refused(self):
        g = self.graph()
        g.add(Node("m", "want.mesh", inputs={"in": Port("mesh")}))
        with self.assertRaises(GraphRefused) as caught:
            g.add_edge("a", "out", "m", "in")
        self.assertIn("green", str(caught.exception))
        self.assertIn("red", str(caught.exception))

    def test_a_port_that_does_not_exist_is_refused(self):
        g = self.graph()
        with self.assertRaises(GraphRefused):
            g.add_edge("a", "nope", "b", "in")
        with self.assertRaises(GraphRefused):
            g.add_edge("ghost", "out", "b", "in")

    def test_an_input_takes_one_wire_unless_it_says_many(self):
        g = self.graph()
        g.add(Node("c", "other.image", outputs={"out": Port("image")}))
        g.add_edge("a", "out", "b", "in")
        with self.assertRaises(GraphRefused) as caught:
            g.add_edge("c", "out", "b", "in")
        self.assertIn("one wire", str(caught.exception))
        g.add(Node("d", "handles.image", inputs={"in": Port("image", many=True)}))
        g.add_edge("a", "out", "d", "in")
        g.add_edge("c", "out", "d", "in")
        self.assertEqual(len(g.edges_into("d", "in")), 2)

    def test_a_cycle_is_refused_and_the_message_names_it(self):
        g = Graph()
        for name in ("a", "b"):
            g.add(Node(name, "pass.through", inputs={"in": Port("image", optional=True)},
                       outputs={"out": Port("image")}))
        g.add_edge("a", "out", "b", "in")
        with self.assertRaises(GraphRefused) as caught:
            g.add_edge("b", "out", "a", "in")
        self.assertIn("cycle", str(caught.exception))
        self.assertIn("->", str(caught.exception))

    def test_a_node_cannot_wire_into_itself(self):
        g = Graph()
        g.add(Node("a", "loop", inputs={"in": Port("image")}, outputs={"out": Port("image")}))
        with self.assertRaises(GraphRefused):
            g.add_edge("a", "out", "a", "in")

    def test_the_same_wire_twice_is_refused(self):
        g = self.graph()
        g.add_edge("a", "out", "b", "in")
        with self.assertRaises(GraphRefused):
            g.add_edge("a", "out", "b", "in")

    def test_topological_order_respects_wires_and_does_not_wander(self):
        g = self.graph()
        g.add(Node("c", "last", inputs={"in": Port("image")}))
        g.add_edge("a", "out", "b", "in")
        g.add_edge("b", "out", "c", "in")
        first = g.topo()
        self.assertLess(first.index("a"), first.index("b"))
        self.assertLess(first.index("b"), first.index("c"))
        self.assertEqual(first, g.topo())

    def test_removing_a_node_takes_its_wires_with_it(self):
        g = self.graph()
        g.add_edge("a", "out", "b", "in")
        gone = g.remove("a")
        self.assertEqual(len(gone), 1)
        self.assertEqual(g.edges, [])
        self.assertNotIn("a", g.nodes)

    def test_check_reports_an_input_that_nobody_wired(self):
        g = Graph()
        g.add(Node("lonely", "op", inputs={"in": Port("image")}))
        problems = g.check()
        self.assertEqual(len(problems), 1)
        self.assertIn("lonely.in", problems[0])


class PresetGraphs(unittest.TestCase):
    def test_every_preset_wires_into_a_clean_graph_on_its_own(self):
        for name in presets.names():
            preset = presets.get(name)
            graph = Graph()
            graph.add(Node("source", "element.anything", outputs={"media": Port(preset.input_dtype)}))
            for role, step in preset.steps.items():
                graph.add(Node(role, step.op, inputs=dict(step.inputs),
                               outputs=dict(step.outputs), params=dict(step.params)))
            graph.add_edge("source", "media", preset.entry, preset.entry_port)
            for a, ap, b, bp in preset.edges:
                graph.add_edge(a, ap, b, bp)  # raises if a preset disagrees with itself
            if preset.tail_port:
                # a board preset takes its frames from outside the template, so the fixture has to
                # stand one frame in or the template looks broken when it is only incomplete.
                graph.add(Node("frame", "element.standin",
                               outputs={"media": Port(preset.input_dtype)}))
                graph.add_edge("frame", "media", preset.sink, preset.tail_port)
            for slot in preset.slots:
                graph.add(Node(f"slot:{slot.name}", "element.standin",
                               outputs={"media": Port(slot.dtype)}))
                graph.add_edge(f"slot:{slot.name}", "media", slot.node, slot.port)
            self.assertEqual(graph.check(), [], name)
            self.assertIn(preset.sink, graph.nodes, name)

    def test_no_preset_claims_it_has_run(self):
        for preset in presets.PRESETS.values():
            self.assertEqual(preset.state, "designed", preset.name)
            self.assertIn("no asset", preset.evidence)

    def test_a_slider_hits_both_ends_of_the_machine_range(self):
        preset = presets.get("sketch-to-mesh")
        slider = preset.sliders["detail"]
        low = dict((node, value) for node, _, value in slider.project(slider.low))
        high = dict((node, value) for node, _, value in slider.project(slider.high))
        self.assertEqual(low["mould"], 4000)
        self.assertEqual(high["mould"], 150000)

    def test_a_slider_is_monotonic(self):
        preset = presets.get("animate-composition")
        slider = preset.sliders["duration"]
        values = [slider.project(v)[0][2] for v in (2, 5, 10, 15)]
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[0], 48)
        self.assertEqual(values[-1], 360)

    def test_a_slider_outside_its_range_is_refused(self):
        preset = presets.get("frosted-glass")
        with self.assertRaises(presets.PresetRefused):
            preset.sliders["frost"].project(4.0)
        with self.assertRaises(presets.PresetRefused):
            preset.sliders["frost"].project("a lot")

    def test_a_choice_slider_carries_a_payload_not_a_number(self):
        preset = presets.get("text-to-image")
        slider = preset.sliders["mood"]
        self.assertEqual(slider.project("neon")[0][2], "neon, wet streets")
        self.assertEqual(slider.where("clean"), 0.0)
        self.assertEqual(slider.where("paper"), 1.0)
        with self.assertRaises(presets.PresetRefused):
            slider.project("baroque")

    def test_a_choice_default_that_is_not_a_choice_is_refused_at_import(self):
        with self.assertRaises(presets.PresetRefused):
            presets.Slider(name="x", label="x", low=0, high=1, default=0,
                           means="", targets=(), kind="choice",
                           choices=(("a", "a"), ("b", "b")))

    def test_a_dtype_change_hands_over_through_a_node(self):
        preset = presets.get("animate-composition")
        self.assertNotEqual(preset.input_dtype, preset.out_dtype())
        crossing = [step for step in preset.steps.values()
                    if {p.dtype for p in step.inputs.values()} != {p.dtype for p in step.outputs.values()}]
        self.assertTrue(crossing, "red to blue must be a node, not a rule")
        self.assertEqual(preset.steps["film"].outputs["out"].dtype, "video")

    def test_every_preset_declares_the_gpu_it_would_need(self):
        """generating presets need a gpu, and a preset without one has to be procedural.

        the carve-out used to be 'input is text', which stopped being true the moment 3d text
        arrived: extruding a font is arithmetic on a laptop. so the rule is the same one the models
        get, because the two are the same claim.
        """
        for preset in presets.PRESETS.values():
            needs_gpu = any(step.requires.get("gpu") for step in preset.steps.values())
            if needs_gpu:
                continue
            self.assertIn(preset.name, presets.PROCEDURAL,
                          f"{preset.name} declares no gpu step, so it has to say why in "
                          f"PROCEDURAL")


class Board(unittest.TestCase):
    def test_every_element_is_a_node(self):
        scene = board()
        self.assertEqual(set(scene.elements), set(scene.graph.nodes))
        for element in scene.elements.values():
            self.assertEqual(scene.graph.nodes[element.id].outputs["media"].dtype,
                             element.dtype)

    def test_an_element_without_bytes_is_refused(self):
        scene = Scene()
        with self.assertRaises(SceneRefused) as caught:
            scene.add("image", "blank")
        self.assertIn("bytes", str(caught.exception))
        with self.assertRaises(SceneRefused):
            scene.add("text", "words")
        with self.assertRaises(SceneRefused):
            scene.add("hologram", "no")

    def test_a_model_lands_on_a_three_dimensional_plane(self):
        scene = Scene()
        model = scene.add("model", "bust", asset=MODEL_ASSET)
        self.assertEqual(model.plane, "3d")
        self.assertEqual(model.dtype, "mesh")

    def test_a_preset_chains_off_what_the_element_is_showing(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        self.assertEqual(scene.rendered_dtype(owl.id), "mesh")
        scene.apply(owl.id, "frosted-glass")
        self.assertEqual(scene.rendered_dtype(owl.id), "mesh")
        shell = [n for n in scene.graph.nodes if n.endswith("/frosted-glass/shell")][0]
        upstream = {e.src[0] for e in scene.graph.edges if e.dst[0] == shell}
        self.assertEqual(upstream, {n for n in scene.graph.nodes if n.endswith("/bake")})
        # the raw sketch is still a node, so nothing was consumed
        self.assertIn(owl.id, scene.graph.nodes)

    def test_converting_a_sketch_flips_the_plane(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        self.assertEqual(owl.plane, "2d")
        scene.apply(owl.id, "sketch-to-mesh")
        self.assertEqual(owl.plane, "3d")
        self.assertTrue(any("plane" in note for note in owl.history))

    def test_applying_the_same_preset_twice_lowers_one_slider(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        first = scene.apply(owl.id, "sketch-to-mesh", {"detail": 20000})
        before = len(scene.graph.nodes)
        second = scene.apply(owl.id, "sketch-to-mesh", {"detail": 120000})
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(scene.graph.nodes), before)
        mould = scene.graph.nodes[f"{first.id}/mould"]
        self.assertEqual(mould.params["target_faces"], 120000)

    def test_detaching_keeps_every_wire_and_forks_the_next_one(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        instance = scene.apply(owl.id, "sketch-to-mesh")
        edges = list(scene.graph.edges)
        nodes = list(scene.graph.order)
        scene.detach(instance.id)
        self.assertEqual(scene.graph.edges, edges)
        self.assertEqual(scene.graph.order, nodes)
        self.assertTrue(all(scene.graph.nodes[n].instance is None for n in instance.nodes))
        # the loose nodes are still what the frame draws (a mesh), so the same preset cannot be
        # applied to them again: it needs a green wire and the element is showing red.
        with self.assertRaises(SceneRefused):
            scene.apply(owl.id, "sketch-to-mesh")
        scene.show(owl.id)
        forked = scene.apply(owl.id, "sketch-to-mesh")
        self.assertNotEqual(forked.id, instance.id)
        self.assertTrue(forked.id.endswith("@2"))
        self.assertEqual(len(scene.graph.nodes), len(nodes) + 3)

    def test_the_wrong_wire_is_refused_with_the_next_click_named(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        model = scene.add("model", "bust", asset=MODEL_ASSET)
        with self.assertRaises(SceneRefused) as caught:
            scene.apply(model.id, "style-transfer")
        self.assertIn("blue" if False else "red", str(caught.exception))

    def test_a_text_element_can_become_an_image(self):
        scene = board()
        caption = scene.elements["text-2"]
        scene.apply(caption.id, "text-to-image")
        self.assertEqual(scene.rendered_dtype(caption.id), "image")

    def test_removing_an_element_takes_its_presets_with_it(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        scene.remove(owl.id)
        self.assertNotIn(owl.id, scene.graph.nodes)
        self.assertFalse([n for n in scene.graph.order if "sketch-to-mesh" in n])
        self.assertEqual(scene.instances, {})

    def test_the_sidebar_offers_what_can_actually_be_applied_now(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        offered = [p["preset"] for p in scene.sidebar(owl.id)["presets"]]
        self.assertIn("sketch-to-mesh", offered)
        self.assertIn("style-transfer", offered)
        self.assertIn("code-container", offered)
        # frosted glass reads a red wire and the owl is still green: it is not offered yet, and
        # that is the product's whole argument for chaining rather than a menu of everything.
        self.assertNotIn("frosted-glass", offered)
        self.assertNotIn("text-to-image", offered)
        caption = scene.elements["text-2"]
        # every preset that reads a text wire, which is now two doors rather than one
        text_doors = [name for name, p in presets.PRESETS.items() if "text" in p.applies_to]
        self.assertEqual([p["preset"] for p in scene.sidebar(caption.id)["presets"]],
                         text_doors)
        self.assertIn("3d-text", text_doors)
        scene.apply(owl.id, "sketch-to-mesh")
        after = [p["preset"] for p in scene.sidebar(owl.id)["presets"]]
        self.assertIn("frosted-glass", after)
        self.assertIn("animate-composition", after)
        self.assertIn("sketch-to-mesh", after)          # already applied, still adjustable
        self.assertNotIn("style-transfer", after)       # it reads green, the owl shows red

    def test_showing_the_original_drops_the_branch_from_the_side_bar(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        scene.show(owl.id)
        self.assertEqual(scene.rendered_dtype(owl.id), "image")
        self.assertEqual(scene.board()[0]["dtype"], "image")

    def test_a_preset_with_a_slot_spawns_incomplete_and_says_what_it_wants(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        look = scene.add("image", "the reference", asset=MODEL_ASSET)
        instance = scene.apply(owl.id, "style-transfer")
        self.assertFalse(instance.complete())
        self.assertEqual(instance.aux, {"the look": None})
        with self.assertRaises(compiler.CompileRefused) as caught:
            compiler.plan(scene)
        self.assertIn("style-transfer", str(caught.exception))
        scene.link(instance.id, "the look", look.id)
        self.assertTrue(instance.complete())
        document = compiler.plan(scene)
        read = [step for step in document["steps"] if step["op"] == "style.read"][0]
        self.assertIn(look.id, read["inputs"]["reference"])

    def test_a_slot_refuses_the_wrong_wire_and_a_slot_that_does_not_exist(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        model = scene.add("model", "bust", asset=MODEL_ASSET)
        instance = scene.apply(owl.id, "style-transfer")
        with self.assertRaises(SceneRefused) as caught:
            scene.link(instance.id, "the look", model.id)
        self.assertIn("red", str(caught.exception))
        with self.assertRaises(SceneRefused) as caught:
            scene.link(instance.id, "a coffee", owl.id)
        self.assertIn("no slot", str(caught.exception))

    def test_a_recipe_is_the_chain_read_back_and_replayed_in_one_call(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh", {"detail": 100000})
        scene.apply(owl.id, "frosted-glass", {"frost": 0.5})
        recipe = scene.record(owl.id, "owl pipeline")
        self.assertEqual([s["preset"] for s in recipe["steps"]],
                         ["sketch-to-mesh", "frosted-glass"])
        self.assertGreater(recipe["estimate"]["minutes"], 0)
        self.assertGreater(recipe["estimate"]["gpu_minutes"], 0)

        second = scene.add("sketch", "the second owl", asset=ASSET)
        applied = scene.replay(second.id, recipe)
        self.assertEqual([i.preset for i in applied], ["sketch-to-mesh", "frosted-glass"])
        self.assertEqual(scene.rendered_dtype(second.id), "mesh")
        self.assertEqual(applied[0].values["detail"], 100000)
        self.assertEqual(applied[1].values["frost"], 0.5)

    def test_a_recipe_refuses_a_board_it_was_not_recorded_on(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        recipe = scene.record(owl.id)
        caption = scene.elements["text-2"]
        with self.assertRaises(SceneRefused) as caught:
            scene.replay(caption.id, recipe)
        self.assertIn("recorded on a sketch", str(caught.exception))

    def test_every_preset_knows_which_stage_it_belongs_to(self):
        for preset in presets.PRESETS.values():
            self.assertIn(preset.stage, presets.STAGES, preset.name)
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        panel = [p for p in scene.sidebar("sketch-1")["presets"]
                 if p["preset"] == "sketch-to-mesh"][0]
        self.assertEqual(panel["stage"], "explore")
        self.assertGreater(panel["estimate"]["gpu_minutes"], 0)

    def test_the_pipeline_view_colours_wires_by_dtype_only(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        view = scene.pipeline()
        for wire in view["wires"]:
            self.assertEqual(wire["colour"], dtypes.colour(wire["dtype"]))
        self.assertEqual({w["colour"] for w in view["wires"]}, {"green", "red"})

    def test_the_pipeline_view_places_every_node(self):
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        view = scene.pipeline()
        self.assertEqual(len(view["nodes"]), len(scene.graph.nodes))
        for node in view["nodes"]:
            # geometry moved to the renderer (@dagre); python emits depth and grouping only
            self.assertNotIn("pos", node, "python does not lay out nodes any more")
            self.assertIsInstance(node["rank"], int)
            self.assertIsInstance(node["row"], int)


class Catalogue(unittest.TestCase):
    """the owner's tool list, and whether the registry answers to all of it.

    the list is data, so a bullet that resolves to nothing is a test failure rather than a
    paragraph somebody means to get to.
    """

    def test_every_bullet_resolves_or_the_suite_says_which_does_not(self):
        cover = catalogue.coverage()
        self.assertEqual(cover["gaps"], [])
        self.assertEqual(cover["misfiled"], [])
        self.assertEqual(cover["unclaimed"], [],
                         "a preset the brief never names has to be declared a primitive")
        self.assertEqual(cover["stale_primitives"], [],
                         "a primitive the brief now names is an excuse that outlived its reason")
        self.assertTrue(cover["ok"])

    def test_the_brief_has_twenty_nine_bullets_and_they_are_all_still_here(self):
        # this number is the brief. it changes when the owner says a bullet was added, not when a
        # refactor makes the tree tidier.
        self.assertEqual(catalogue.coverage()["tools"], 29)

    def test_the_brief_collapses_further_than_it_reads(self):
        """29 bullets are not 29 presets, and the ratio is the product decision."""
        cover = catalogue.coverage()
        self.assertEqual(cover["presets_named"], 16)
        self.assertEqual(cover["controls"], 16,
                         "controls are sliders on a preset, not presets of their own")
        self.assertEqual(cover["tools"], cover["presets_named"] + cover["controls"] - 3,
                         "seven bullets share a preset; recount before changing this")
        texture = presets.get("texture-maps")
        for control in ("roughness", "metalness", "opacity", "emission", "normal_strength"):
            self.assertIn(control, texture.sliders,
                          "the texture map bullets are sliders on one node")

    def test_exploring_variations_is_a_sweep_and_sweeps_share_the_work(self):
        material = presets.get("apply-material")
        self.assertIsNotNone(material.sweep, "'explore material variations' is a sweep")
        self.assertEqual(len(material.sweep.values), 6)
        scene = Scene()
        model = scene.add("model", "a chair", asset=ASSET)
        instance = scene.apply(model.id, "apply-material")
        sheet = scene.add("image", "the material", asset=ASSET)
        scene.link(instance.id, "the material", sheet.id)
        steps = compiler.plan(scene)["steps"]
        self.assertEqual(len([s for s in steps if s["op"] == "mesh.uv"]), 1,
                         "the unwrap happens once, not once per finish")
        self.assertEqual(len([s for s in steps if s["op"] == "material.apply"]), 6)
        self.assertEqual(len(compiler.plan(scene)["artifacts"]), 7,
                         "six finishes plus the material sheet you supplied")

    def test_a_graphic_is_a_second_asset_not_a_setting(self):
        preset = presets.get("place-graphic")
        self.assertEqual([slot.name for slot in preset.slots], ["the graphic"])
        self.assertIn("pattern", preset.sliders,
                      "geometric pattern mapping is a control on the graphic, not a preset")

    def test_every_preset_compiles_once_its_slots_are_filled(self):
        """the sweep plus a slot was a shape this tree had not had before, so it gets a test."""
        kinds = {"text": "text", "image": "image", "mesh": "model", "video": "video"}
        for name, preset in presets.PRESETS.items():
            with self.subTest(preset=name):
                scene = Scene()
                kind = kinds[preset.input_dtype]
                target = scene.add(kind, "target",
                                   asset=None if kind == "text" else ASSET,
                                   text="words" if kind == "text" else None)
                instance = scene.apply(target.id, name)
                for slot in preset.slots:
                    filler = scene.add(kinds[slot.dtype], slot.name,
                                       asset=None if slot.dtype == "text" else ASSET,
                                       text="filler" if slot.dtype == "text" else None)
                    scene.link(instance.id, slot.name, filler.id)
                plan = compiler.plan(scene)
                self.assertTrue(plan["steps"], f"{name} compiled to nothing")
                self.assertTrue(plan["artifacts"], f"{name} produced no artifacts")

    def test_the_cli_says_what_the_brief_became(self):
        result = subprocess.run(
            [str(ROOT / "bin" / "flowby"), "catalogue"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("29 bullets -> 16 presets and 16 controls", result.stdout)
        self.assertIn("every bullet resolves", result.stdout)


class Doors(unittest.TestCase):
    """the three ways in are only worth calling modes if you can walk between them.

    every crossing below is performed rather than asserted from a docstring, because the docstring
    was the thing most likely to be optimistic.
    """

    def test_freeform_typing_becomes_a_node_and_stays_one(self):
        scene = Scene()
        words = scene.add("text", "brief", text="a cracked celadon vase, three quarter light")
        instance = scene.apply(words.id, "text-to-image")
        composed = [s for s in compiler.plan(scene)["steps"]
                    if s["op"] == "text.compose"][0]
        self.assertIn(f"{words.id}:media", composed["inputs"]["draft"])
        self.assertEqual(scene.graph.nodes[words.id].params["text"],
                         "a cracked celadon vase, three quarter light",
                         "the words are a parameter of a node, not a setting of the app")
        self.assertEqual(instance.preset, "text-to-image")

    def test_a_preset_can_be_left_for_the_graph_underneath_it(self):
        scene = Scene()
        plate = scene.add("sketch", "line sketch", asset=ASSET)
        instance = scene.apply(plate.id, "sketch-to-mesh")
        self.assertEqual(scene.rendered_dtype(plate.id), "mesh")
        scene.show(plate.id, instance.nodes[0])
        self.assertEqual(scene.rendered_dtype(plate.id), "image",
                         "the frame can be pointed at an intermediate node, which is the way out "
                         "of the fixed door")

    def test_a_board_style_can_be_narrowed_to_one_frame_or_one_head(self):
        scene = Scene()
        frames = [scene.add("image", f"plate {i}", asset=ASSET) for i in (1, 2, 3)]
        shared = scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        scene.show(frames[1].id, f"{shared.id}/study")
        self.assertEqual(scene.rendered_dtype(frames[1].id), "image")
        self.assertEqual(scene.board()[1]["presets"], ["studio-light"],
                         "showing the shared palette does not unapply the preset")

    def test_a_style_preset_says_what_it_is_missing_before_it_runs(self):
        scene = Scene()
        plate = scene.add("image", "plate", asset=ASSET)
        instance = scene.apply(plate.id, "style-transfer")
        with self.assertRaises(compiler.CompileRefused) as caught:
            compiler.plan(scene)
        self.assertIn("reference", str(caught.exception))
        look = scene.add("image", "the look", asset=ASSET)
        scene.link(instance.id, "the look", look.id)
        compiled = compiler.plan(scene)
        self.assertEqual(len(compiled["artifacts"]), 2,
                         "the restyled plate and the reference frame, which keeps its own media")
        paint = [s for s in compiled["steps"] if s["op"] == "image.stylize"][0]
        self.assertIn(f"{plate.id}:media", paint["inputs"]["content"])
        read = [s for s in compiled["steps"] if s["op"] == "style.read"][0]
        self.assertIn(f"{look.id}:media", read["inputs"]["reference"],
                      "the reference is a second wire, not a setting on the same one")
        self.assertTrue(paint["inputs"]["reference"].endswith("/read:out"))
        self.assertIn("style-transfer/paint", scene.board()[0]["display"])

    def test_every_door_reaches_every_other_door(self):
        legend = modes.legend()
        self.assertTrue(legend["reachable"])
        for name, targets in legend["crossings"].items():
            self.assertEqual(sorted(targets), sorted(set(modes.MODES) - {name}),
                             f"{name} does not advertise a way out to every other door")

    def test_every_preset_opens_on_exactly_one_door(self):
        by_door = modes.legend()["presets_by_door"]
        seen = [name for names in by_door.values() for name in names]
        self.assertEqual(sorted(seen), sorted(presets.PRESETS),
                         "a preset on two doors is a preset whose card is in two places")
        self.assertIn("text-to-image", by_door["freeform"])
        self.assertIn("style-transfer", by_door["style"])
        self.assertIn("studio-light", by_door["style"])


class BoardScope(unittest.TestCase):
    """a preset whose head runs once and whose tail reaches several frames."""

    def frames(self, count=3):
        scene = Scene()
        return scene, [scene.add("image", f"plate {i}", asset=ASSET) for i in range(1, count + 1)]

    def test_one_style_read_grades_every_frame(self):
        scene, frames = self.frames(3)
        scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        document = compiler.plan(scene)
        studies = [s for s in document["steps"] if s["op"] == "light.study"]
        grades = [s for s in document["steps"] if s["op"] == "light.grade"]
        self.assertEqual(len(studies), 1, "a board reads its light once, not once per frame")
        self.assertEqual(len(grades), 3)
        for grade in grades:
            self.assertIn(studies[0]["id"] + ":palette", grade["inputs"]["palette"])
        self.assertEqual({g["inputs"]["plate"] for g in grades},
                         {f"image-{i}:media" for i in (1, 2, 3)})

    def test_the_shared_head_is_one_node_and_not_one_per_frame(self):
        scene, frames = self.frames(3)
        scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        attached = [n for n in scene.graph.nodes if n.startswith("board/studio-light/")]
        self.assertEqual(len(attached), 1 + 3, "three elements, one head, three tails")

    def test_the_style_is_paid_for_once(self):
        scene, frames = self.frames(3)
        scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        cost = compiler.plan(scene)["cost"]
        self.assertAlmostEqual(cost["gpu_minutes"], 0.6 + 3 * 0.9, places=1)
        self.assertEqual(len(compiler.plan(scene)["artifacts"]), 3)

    def test_a_frame_that_joins_later_does_not_reread_the_light(self):
        scene, frames = self.frames(3)
        scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        fourth = scene.add("image", "plate 4", asset=ASSET)
        scene.apply_shared(frames[0].id, [fourth.id], "studio-light")
        document = compiler.plan(scene)
        self.assertEqual(len([s for s in document["steps"] if s["op"] == "light.study"]), 1)
        self.assertEqual(len(document["artifacts"]), 4)

    def test_a_board_preset_on_one_frame_still_goes_through_the_head(self):
        scene, frames = self.frames(1)
        instance = scene.apply(frames[0].id, "studio-light")
        self.assertTrue(instance.shared)
        self.assertEqual([s["op"] for s in compiler.plan(scene)["steps"]],
                         ["element.image", "light.study", "light.grade"])

    def test_a_board_preset_refuses_a_frame_showing_the_wrong_wire(self):
        scene = Scene()
        plate = scene.add("image", "plate", asset=ASSET)
        bust = scene.add("model", "bust", asset=MODEL_ASSET)
        with self.assertRaises(SceneRefused) as caught:
            scene.apply_shared(plate.id, [bust.id], "studio-light")
        self.assertIn("red", str(caught.exception))

    def test_the_sidebar_says_which_frames_a_board_preset_reaches(self):
        scene, frames = self.frames(2)
        scene.apply_shared(frames[0].id, [f.id for f in frames], "studio-light")
        panel = [p for p in scene.sidebar(frames[1].id)["presets"]
                 if p["preset"] == "studio-light"][0]
        self.assertEqual(panel["scope"], "board")
        self.assertEqual(panel["reaches"], [frames[0].id, frames[1].id])
        self.assertEqual(panel["estimate"]["gpu_minutes"], 0.6 + 2 * 0.9)

    def test_surface_detail_offers_the_four_things_the_reference_names(self):
        preset = presets.get("surface-detail")
        self.assertEqual([c[0] for c in preset.sliders["detail"].choices],
                         ["crease", "stitch", "emboss", "deboss"])

    def test_surface_detail_is_a_diffusion_pass_and_not_a_carve(self):
        """the correction: crease and stitch are models doing the work, not a carved edge.

        so the choice has to arrive at a node as a prompt fragment, and the geometry node after it
        only applies the map that came back. a preset that carved it directly would be pretending
        to be cheaper than it is and worse at the job.
        """
        scene = Scene()
        bust = scene.add("model", "bust", asset=MODEL_ASSET)
        scene.apply(bust.id, "surface-detail", {"detail": "deboss", "depth": 0.2})
        paint = scene.graph.nodes["model-1/surface-detail/paint"]
        relief = scene.graph.nodes["model-1/surface-detail/relief"]
        self.assertIn("recess", paint.params["prompt"], "the model gets a sentence, not a mode")
        self.assertIn("flux-depth-lora", paint.requires["models"])
        self.assertAlmostEqual(relief.params["depth"], 0.2)
        self.assertNotIn("models", relief.requires, "applying a map is geometry, not inference")


class Models(unittest.TestCase):
    """every preset either calls a model or says why it does not."""

    def test_no_preset_hides_an_absence_of_models(self):
        census = presets.model_census()
        for name, models in census.items():
            if models:
                continue
            self.assertIn(name, presets.PROCEDURAL,
                          f"{name} names no model and gives no reason, which is the shape of a "
                          f"preset that quietly does nothing")

    def test_every_excuse_is_a_reason_and_not_a_placeholder(self):
        for name, reason in presets.PROCEDURAL.items():
            self.assertIn(name, presets.PRESETS, f"{name} is excused and does not exist")
            self.assertGreater(len(reason.split()), 6, f"{name}'s reason is not a sentence")

    def test_the_models_are_named_where_a_person_would_look_for_them(self):
        readme = (ROOT / "readme.md").read_text().lower()
        for name, models in presets.model_census().items():
            for model in models:
                self.assertIn(model.lower(), readme,
                              f"{model} runs {name} and the readme does not say so")

    def test_the_two_products_were_right_about_this(self):
        """both reference catalogues name surfaces and run models. the census is that sentence
        as a thing a test can hold: most presets are model calls, and the ones that are not are
        exactly the ones PROCEDURAL excuses, in writing."""
        census = presets.model_census()
        called = [name for name, models in census.items() if models]
        self.assertEqual(len(called), 19)
        self.assertEqual(sorted(set(census) - set(called)), sorted(presets.PROCEDURAL),
                         "a preset with no model and no excuse is a gap, not a decision")


class Sweeps(unittest.TestCase):
    """one input, several results. the shape both reference products lead with."""

    def test_relight_declares_six_lighting_versions(self):
        preset = presets.get("relight")
        self.assertIsNotNone(preset.sweep)
        self.assertEqual(len(preset.sweep.values), 6)
        self.assertEqual(preset.branch_point(), "relight")
        self.assertEqual(preset.tail(), {"relight"})
        for value in preset.sweep.values:
            self.assertGreaterEqual(value, preset.sliders["warmth"].low)
            self.assertLessEqual(value, preset.sliders["warmth"].high)

    def test_a_sweep_that_repeats_itself_is_refused(self):
        with self.assertRaises(presets.PresetRefused):
            presets.Sweep(slider="warmth", label="repeats", values=(2, 2))
        with self.assertRaises(presets.PresetRefused):
            presets.Sweep(slider="warmth", label="nothing", values=())

    def test_a_sweep_of_a_slider_the_preset_lacks_is_refused(self):
        from dataclasses import replace

        bad = presets.Sweep(slider="glow", label="nothing", values=(1, 2))
        with self.assertRaises(presets.PresetRefused):
            replace(presets.get("relight"), sweep=bad)

    def test_the_head_of_the_fan_runs_once_and_only_the_tail_is_copied(self):
        document = compiler.preset_plan("relight")
        meters = [s for s in document["steps"] if s["op"] == "light.meter"]
        relights = [s for s in document["steps"] if s["op"] == "light.relight"]
        self.assertEqual(len(meters), 1, "reading the plate six times is five wasted reads")
        self.assertEqual(len(relights), 6)
        for step in relights:
            self.assertTrue(step["inputs"]["plate"].startswith(meters[0]["id"] + ":"),
                            "every branch reads the one shared plate")

    def test_each_copy_carries_its_own_value_and_its_own_wire(self):
        document = compiler.preset_plan("relight")
        relights = [s for s in document["steps"] if s["op"] == "light.relight"]
        kelvins = [step["params"]["kelvin"] for step in relights]
        self.assertEqual(kelvins, [4500.0, 5200.0, 5600.0, 6500.0, 7500.0, 8500.0])
        self.assertEqual([step["params"]["variant"] for step in relights], [1, 2, 3, 4, 5, 6])
        self.assertEqual(len({step["id"] for step in relights}), 6)

    def test_a_fan_produces_one_artifact_per_version(self):
        document = compiler.preset_plan("relight")
        names = [a["name"] for a in document["artifacts"]]
        self.assertEqual(names, [f"sketch-1#{i}.png" for i in range(1, 7)])
        shown = document["display"]["sketch-1"]
        self.assertEqual(len(shown["variants"]), 6)
        self.assertTrue(shown["variants"][0].endswith("@1:out"))
        self.assertEqual(shown["chosen"], 0)

    def test_the_cost_counts_the_copied_part_six_times_and_the_shared_part_once(self):
        document = compiler.preset_plan("relight")
        gpu = routes.ROUTES["colab-browserbase"]
        self.assertAlmostEqual(document["cost"]["gpu_minutes"], 6 * 1.1, places=1)
        self.assertAlmostEqual(document["cost"]["cpu_minutes"], 0.3, places=1)
        self.assertLess(document["cost"]["total_minutes"], gpu.ceiling_minutes)

    def test_the_sidebar_says_how_many_versions_before_you_press_it(self):
        scene = Scene()
        photo = scene.add("image", "studio plate", asset=ASSET)
        scene.apply(photo.id, "relight")
        panel = [p for p in scene.sidebar(photo.id)["presets"] if p["preset"] == "relight"][0]
        self.assertEqual(panel["estimate"]["gpu_minutes"], 6.6)
        self.assertEqual(scene.variant_count(photo.id), 6)

    def test_choosing_a_version_is_a_pointer_and_not_a_rerun(self):
        scene = Scene()
        photo = scene.add("image", "studio plate", asset=ASSET)
        scene.apply(photo.id, "relight")
        self.assertEqual(scene.show_variant(photo.id, 3), 3)
        self.assertEqual(scene.board()[0]["chosen"], 3)
        self.assertEqual(len(compiler.plan(scene)["artifacts"]), 6)
        with self.assertRaises(SceneRefused):
            scene.show_variant(photo.id, 9)

    def test_the_whole_fan_survives_the_worker_and_the_job_store(self):
        plan = compiler.preset_plan("relight")
        directory = pathlib.Path(tempfile.mkdtemp())
        manifest = worker_run(plan, directory)
        self.assertEqual([a["variant"] for a in manifest["artifacts"]], [1, 2, 3, 4, 5, 6])
        store = jobs.Store()
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        store.start(job.id)
        store.complete(job.id, manifest)
        self.assertEqual(len(job.artifacts), 6)
        self.assertEqual(job.artifacts[5]["name"], "sketch-1#6.png")


class Plans(unittest.TestCase):
    def test_a_plan_is_flat_and_every_wire_names_an_earlier_step(self):
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        document = compiler.plan(scene)
        seen = set()
        for step in document["steps"]:
            for port, ref in step["inputs"].items():
                node, _, port_name = ref.partition(":")
                self.assertIn(node, seen, f"{step['id']}.{port} points forward at {ref}")
                self.assertIn(port_name, scene.graph.nodes[node].outputs)
            seen.add(step["id"])

    def test_only_what_is_displayed_gets_compiled(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        scene.apply(owl.id, "sketch-to-mesh")
        full = compiler.plan(scene)
        scene.show(owl.id)
        thin = compiler.plan(scene)
        self.assertGreater(len(full["steps"]), len(thin["steps"]))
        self.assertEqual(len(thin["steps"]), 2)  # the sketch and the caption, nothing else

    def test_an_unwired_required_input_is_refused(self):
        scene = board()
        owl = scene.elements["sketch-1"]
        instance = scene.apply(owl.id, "sketch-to-mesh")
        scene.graph.remove(f"{instance.id}/read")
        with self.assertRaises(compiler.CompileRefused) as caught:
            compiler.plan(scene)
        self.assertIn("wire", str(caught.exception))

    def test_the_environment_is_aggregated_once(self):
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        document = compiler.plan(scene)
        self.assertIn("trimesh", document["env"]["pip"])
        self.assertEqual(len(document["env"]["pip"]), len(set(document["env"]["pip"])))
        self.assertIn("triposr", document["env"]["models"])
        self.assertTrue(document["env"]["gpu"])

    def test_the_same_board_compiles_to_the_same_job(self):
        first = compiler.preset_plan("sketch-to-mesh")
        second = compiler.preset_plan("sketch-to-mesh")
        self.assertEqual(first["job_id"], second["job_id"])

    def test_a_slider_makes_it_a_different_job(self):
        calm = compiler.preset_plan("sketch-to-mesh", {"detail": 20000})
        fine = compiler.preset_plan("sketch-to-mesh", {"detail": 140000})
        self.assertNotEqual(calm["job_id"], fine["job_id"])

    def test_artifacts_are_named_per_element(self):
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        document = compiler.plan(scene)
        names = {a["name"] for a in document["artifacts"]}
        self.assertIn("sketch-1.glb", names)
        self.assertIn("text-2.txt", names)

    def test_the_contract_is_on_the_plan(self):
        document = compiler.preset_plan("frosted-glass")
        self.assertEqual(document["contract"], compiler.CONTRACT)
        self.assertTrue(document["job_id"].startswith("fb_"))

    def test_a_route_that_cannot_take_the_plan_is_refused_before_dispatch(self):
        with self.assertRaises(compiler.CompileRefused) as caught:
            compiler.preset_plan("sketch-to-mesh", route="local")
        self.assertIn("gpu", str(caught.exception))

    def test_the_cost_is_on_the_plan_before_anything_runs(self):
        document = compiler.preset_plan("animate-composition")
        cost = document["cost"]
        self.assertGreater(cost["gpu_minutes"], 0)
        self.assertEqual(round(cost["gpu_minutes"] + cost["cpu_minutes"], 1),
                         cost["total_minutes"])
        self.assertEqual(sum(step["minutes"] for step in document["steps"]),
                         round(document["estimate_minutes"], 2))
        self.assertTrue(any(step["gpu"] for step in document["steps"]))
        self.assertIn("cost:", "\n".join(compiler.summary(document)))

    def test_the_board_travels_with_the_plan(self):
        scene = board()
        scene.apply("sketch-1", "sketch-to-mesh")
        document = compiler.plan(scene)
        self.assertEqual(len(document["board"]), 2)
        self.assertEqual(document["display"]["sketch-1"]["dtype"], "mesh")


class Routing(unittest.TestCase):
    def test_every_route_declares_its_own_limits(self):
        for route in routes.ROUTES.values():
            self.assertGreater(route.ceiling_minutes, 0)
            self.assertGreaterEqual(route.idle_kill_seconds, 0)
            self.assertTrue(route.persistence)
            self.assertIn(route.state, ("designed", "verified", "refused"))

    def test_the_colab_route_states_its_ceiling_instead_of_hiding_it(self):
        colab = routes.get("colab-browserbase")
        self.assertEqual(colab.ceiling_minutes, 720)
        self.assertEqual(colab.idle_kill_seconds, 90)
        self.assertTrue(colab.ephemeral)
        self.assertEqual(colab.policy, "contested")
        self.assertIn("cookie", colab.note)

    def test_nothing_here_claims_to_have_run(self):
        for route in routes.ROUTES.values():
            self.assertEqual(route.state, "designed", route.name)

    def test_the_cheapest_route_that_fits_wins_and_brings_its_caveats(self):
        plan = compiler.preset_plan("sketch-to-mesh")
        route, notes = routes.choose(plan)
        self.assertEqual(route.name, "colab-browserbase")
        self.assertTrue(any("contested" in note for note in notes))

    def test_a_plan_that_fits_a_plain_machine_stays_on_it(self):
        plan = compiler.preset_plan("frosted-glass")
        route, _ = routes.choose(plan)
        self.assertEqual(route.name, "local")

    def test_gates_are_only_checked_when_the_caller_has_the_environment(self):
        plan = compiler.preset_plan("sketch-to-mesh")
        blind = routes.fit(routes.get("colab-browserbase"), plan)
        strict = routes.fit(routes.get("colab-browserbase"), plan, present=set())
        self.assertEqual(blind, [])
        self.assertTrue(any("GOOGLE_SESSION_COOKIES" in reason for reason in strict))

    def test_a_job_longer_than_the_ceiling_is_routed_elsewhere(self):
        plan = compiler.preset_plan("animate-composition")
        long_plan = dict(plan, estimate_minutes=900)
        reasons = routes.fit(routes.get("colab-browserbase"), long_plan)
        self.assertTrue(any("caps at 720" in reason for reason in reasons))

    def test_a_plan_that_needs_a_shell_is_refused_by_a_model_api(self):
        plan = compiler.preset_plan("animate-composition")
        reasons = routes.fit(routes.get("replicate"), plan)
        self.assertTrue(any("shell" in reason for reason in reasons))


class Jobs(unittest.TestCase):
    def clock(self, start=1000.0):
        ticks = [start]

        def now():
            ticks[0] += 0.0
            return ticks[0]

        now.advance = lambda seconds: ticks.__setitem__(0, ticks[0] + seconds)
        return now

    def manifest(self, plan: dict) -> dict:
        sys.path.insert(0, str(ROOT / "kernel"))
        import worker

        return worker.run(plan, pathlib.Path(tempfile.mkdtemp()), simulate=True)

    def test_a_double_click_is_one_job(self):
        store = jobs.Store()
        plan = compiler.preset_plan("sketch-to-mesh")
        first, created = store.submit(plan)
        second, created_again = store.submit(plan)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(store.jobs), 1)

    def test_a_store_from_another_contract_is_refused(self):
        store = jobs.Store()
        with self.assertRaises(jobs.JobRefused):
            store.submit({"contract": "flowby/0", "job_id": "x"})

    def test_the_life_has_legal_moves_only(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        with self.assertRaises(jobs.JobRefused) as caught:
            store.complete(job.id, {"plan_digest": job.digest, "artifacts": []})
        self.assertIn("queued", str(caught.exception))
        store.dispatch(job.id)
        store.start(job.id)
        with self.assertRaises(jobs.JobRefused):
            store.dispatch(job.id)

    def test_a_payload_for_another_plan_is_refused(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        store.start(job.id)
        with self.assertRaises(jobs.JobRefused) as caught:
            store.complete(job.id, {"plan_digest": "fb_wrong", "artifacts": []})
        self.assertIn("fb_wrong", str(caught.exception))

    def test_a_promise_without_the_file_is_refused(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        store.start(job.id)
        with self.assertRaises(jobs.JobRefused) as caught:
            store.complete(job.id, {"plan_digest": job.digest, "artifacts": []})
        self.assertIn("model-1.glb", str(caught.exception))

    def test_bytes_without_a_hash_are_a_rumour(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        store.start(job.id)
        with self.assertRaises(jobs.JobRefused) as caught:
            store.complete(job.id, {"plan_digest": job.digest,
                                    "artifacts": [{"name": "model-1.glb", "sha256": "nope"}]})
        self.assertIn("rumour", str(caught.exception))

    def test_a_real_manifest_completes_a_job(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        store.start(job.id)
        store.complete(job.id, self.manifest(plan))
        self.assertEqual(job.state, "returned")
        self.assertEqual(job.artifacts[0]["name"], "model-1.glb")
        self.assertEqual(len(job.artifacts), 1)
        store.stored(job.id)
        self.assertEqual(job.state, "stored")

    def test_the_watchdog_uses_the_route_s_own_kill_line(self):
        clock = self.clock()
        store = jobs.Store(clock=clock)
        plan = compiler.preset_plan("sketch-to-mesh")  # routed to colab, 90s
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        clock.advance(89)
        self.assertEqual(store.stale(), [])
        clock.advance(2)
        self.assertEqual([j.id for j in store.stale()], [job.id])

    def test_a_route_with_no_kill_line_never_goes_stale(self):
        clock = self.clock()
        store = jobs.Store(clock=clock)
        plan = compiler.preset_plan("frosted-glass")  # local, no idle kill
        job, _ = store.submit(plan)
        store.dispatch(job.id)
        clock.advance(86400)
        self.assertEqual(store.stale(), [])

    def test_a_heartbeat_only_lands_while_something_is_running(self):
        store = jobs.Store()
        plan = compiler.preset_plan("frosted-glass")
        job, _ = store.submit(plan)
        with self.assertRaises(jobs.JobRefused):
            store.beat(job.id)
        store.dispatch(job.id)
        self.assertEqual(store.beat(job.id).beats, 1)


class Hubs(unittest.TestCase):
    def test_a_broadcast_reaches_every_socket_on_that_board(self):
        hub = hubmod.Hub()
        one = hub.open("board-1")
        two = hub.open("board-1")
        other = hub.open("board-2")
        delivered = hub.broadcast("board-1", {"kind": "hello"})
        self.assertEqual(delivered, 2)
        self.assertEqual(one.drain(), [{"kind": "hello"}])
        self.assertEqual(two.drain(), [{"kind": "hello"}])
        self.assertEqual(other.drain(), [])

    def test_a_socket_that_cannot_keep_up_is_closed_rather_than_skipped_past(self):
        hub = hubmod.Hub()
        slow = hub.open("board-1", buffer=1)
        fast = hub.open("board-1", buffer=8)
        hub.broadcast("board-1", {"n": 1})
        hub.broadcast("board-1", {"n": 2})
        self.assertFalse(slow.open)
        self.assertEqual(slow.dropped, 1)
        self.assertTrue(fast.open)
        self.assertEqual([m["n"] for m in fast.drain()], [1, 2])

    def test_a_reconnecting_inspector_is_handed_what_it_missed(self):
        hub = hubmod.Hub(replay=8)
        canvas = hub.open("board-1")
        hub.broadcast("board-1", {"n": 1})
        hub.broadcast("board-1", {"n": 2})
        hub.close(canvas)
        hub.broadcast("board-1", {"n": 3})
        inspector = hub.open("board-1")
        self.assertEqual([m["n"] for m in inspector.drain()], [1, 2, 3])

    def test_a_fresh_board_gets_no_replay_from_another(self):
        hub = hubmod.Hub()
        hub.broadcast("board-1", {"n": 1})
        self.assertEqual(hub.open("board-2").drain(), [])

    def test_fresh_pixels_are_addressed_by_element(self):
        hub = hubmod.Hub()
        sub = hub.open("board-1")
        hub.artifacts("board-1", "fb_1", [{"name": "sketch-1.glb", "element": "sketch-1",
                                           "sha256": "0" * 64, "bytes": 1}])
        message = sub.drain()[0]
        self.assertEqual(message["kind"], "artifacts")
        self.assertEqual(message["by_element"]["sketch-1"][0]["name"], "sketch-1.glb")
        hub.artifacts("board-1", "fb_2", [
            {"name": "sketch-1#1.png", "element": "sketch-1", "variant": 1},
            {"name": "sketch-1#2.png", "element": "sketch-1", "variant": 2},
        ])
        grouped = sub.drain()[0]
        self.assertEqual(len(grouped["by_element"]["sketch-1"]), 2, "a fan stays one frame")


class Kernel(unittest.TestCase):
    def test_the_script_parses(self):
        result = subprocess.run(["bash", "-n", str(ROOT / "kernel" / "kernel.sh")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_dry_run_lists_the_steps_and_installs_nothing(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        plan_file = directory / "plan.json"
        plan_file.write_text(json.dumps(compiler.preset_plan("sketch-to-mesh")))
        result = subprocess.run(
            ["bash", str(ROOT / "kernel" / "kernel.sh"), "--dry-run", str(plan_file)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 steps", result.stdout)
        self.assertIn("mesh.triposr", result.stdout)
        self.assertIn("would install: opencv-python-headless", result.stdout)

    def test_every_op_a_preset_declares_is_an_op_the_worker_knows(self):
        """a preset whose op the worker refuses is a preset that can never run.

        this was true of nineteen ops after the catalogue landed: the graphs wired, the compiler
        planned, and the far end said "not an op this worker knows" for sixteen of them. the worker
        keeps its table explicit rather than deriving it from the registry, because a typo'd op
        should be refused rather than accepted, so what is needed is this test.
        """
        source = (ROOT / "kernel" / "worker.py").read_text()
        known = set(re.findall(r'^    "([a-z]+\.[a-z.]+)":', source, re.M))
        for name, preset in presets.PRESETS.items():
            for step in preset.steps.values():
                self.assertIn(step.op, known,
                              f"{name} declares {step.op}, which the worker cannot run")

    def test_the_worker_writes_a_manifest_a_job_will_accept(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        plan = compiler.preset_plan("sketch-to-mesh")
        plan_file = directory / "plan.json"
        plan_file.write_text(json.dumps(plan))
        out = directory / "out"
        result = subprocess.run(
            [sys.executable, str(ROOT / "kernel" / "worker.py"),
             "--plan", str(plan_file), "--outdir", str(out), "--simulate"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "manifest.json").read_text())
        self.assertEqual(manifest["plan_digest"], plan["job_id"])
        self.assertTrue(manifest["simulated"])
        for artifact in manifest["artifacts"]:
            body = (out / artifact["name"]).read_bytes()
            import hashlib

            self.assertEqual(hashlib.sha256(body).hexdigest(), artifact["sha256"])
            self.assertEqual(len(body), artifact["bytes"])

    def test_the_worker_refuses_a_model_it_does_not_have(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        plan_file = directory / "plan.json"
        plan_file.write_text(json.dumps(compiler.preset_plan("sketch-to-mesh")))
        result = subprocess.run(
            [sys.executable, str(ROOT / "kernel" / "worker.py"),
             "--plan", str(plan_file), "--outdir", str(directory / "out")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("depth estimator", result.stderr)
        self.assertIn("--simulate", result.stderr)


class Alignment(unittest.TestCase):
    def test_the_two_canvases_agree(self):
        if not (ROOT / "web" / "tests" / "align.test.mjs").exists():
            self.skipTest("no web tests")
        try:
            result = subprocess.run(
                ["node", "--test", str(ROOT / "web" / "tests" / "align.test.mjs")],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            self.skipTest("node is not installed here")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("fail 1", result.stdout)


class Prose(unittest.TestCase):
    """the readme is checked against the registry, because drift is the one bug prose cannot catch."""

    def test_each_doc_page_is_still_the_page_it_claims_to_be(self):
        """a doc that silently becomes another doc is worse than a missing one.

        docs/research.md was once overwritten with directory.md contents and nothing failed,
        because every prose test only asked whether a word appeared somewhere in the tree. so:
        each page states its own subject in the first line, and those are checked here.
        """
        expected = {
            "docs/research.md": ("# research", ["vectary canvas", "fuser", "studio.base44.com"]),
            "directory.md": ("# directory", ["src/flowby/", "tests/selftest.py"]),
            "readme.md": ("# flowby", ["presets", "wires"]),
            "docs/presets.md": ("#", ["preset"]),
            "docs/compute.md": ("#", ["colab"]),
            "docs/frontend.md": ("#", ["camera"]),
        }
        for path, (first_line, subjects) in expected.items():
            page = (ROOT / path).read_text()
            self.assertTrue(page.splitlines()[0].lower().startswith(first_line),
                            f"{path} starts with {page.splitlines()[0]!r}")
            for subject in subjects:
                self.assertIn(subject, page.lower(), f"{path} does not mention {subject}")

    def test_the_readme_names_the_three_doors(self):
        readme = (ROOT / "readme.md").read_text().lower()
        for mode in modes.MODES:
            self.assertIn(mode, readme, f"the readme does not mention the {mode} door")
        self.assertIn("every door reaches every other", readme)

    def test_the_readme_names_every_preset(self):
        text = (ROOT / "readme.md").read_text()
        for name in presets.names():
            self.assertIn(name, text, f"readme does not mention {name}")

    def test_the_directory_lists_every_path(self):
        text = (ROOT / "directory.md").read_text()
        for entry in ("src/", "kernel/", "app/", "web/", "tests/", "docs/", "theidea/",
                      "journal/", "bin/"):
            self.assertIn(entry, text, f"directory.md does not mention {entry}")

    def test_the_idea_keeps_the_owner_s_brief(self):
        text = (ROOT / "theidea" / "main.md").read_text()
        for phrase in ("spatial layout layer", "node pipeline layer", "kernel.sh"):
            self.assertIn(phrase, text)

    def test_every_module_is_named_in_the_directory(self):
        text = (ROOT / "directory.md").read_text()
        for module in sorted(p.stem for p in (ROOT / "src" / "flowby").glob("*.py")):
            if module == "__init__":
                continue
            self.assertIn(module, text, f"directory.md does not mention {module}.py")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
