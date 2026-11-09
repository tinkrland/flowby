"""session_test.py: the board a page talks to.

the claim the session makes is that the live scene is always a scene that passed every check. so
these tests attack exactly that: a refusal must leave the board byte-for-byte as it was, an action
that fails halfway must not leave half of itself behind, undo must restore, and two requests at
once must not interleave. each is checked by comparing whole scenes, not by spot-checking a field.
"""

import json
import pathlib
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from flowby import presets  # noqa: E402
from flowby.session import Session, SessionRefused, UNDO_DEPTH  # noqa: E402
from flowby.store import Store, digest_of  # noqa: E402


def board():
    store = Store(tempfile.mkdtemp())
    return Session(store), store


def snapshot(session):
    """the whole scene as data, so two boards can be compared exactly."""
    return json.dumps(session.scene.as_dict(), sort_keys=True, default=str) + json.dumps(session.scene.pipeline(), sort_keys=True, default=str)


def with_sketch():
    s, store = board()
    d = store.put(b"a drawing of an owl")
    out = s.add_file("sketch", "the owl", d)
    return s, store, d, out["receipt"]["ids"][0]


class AddingFiles(unittest.TestCase):
    def test_a_stored_file_becomes_an_element_with_its_digest(self):
        s, store, d, el = with_sketch()
        self.assertEqual(s.scene.elements[el].asset, d)
        self.assertEqual(s.scene.elements[el].kind, "sketch")
        self.assertEqual(s.scene.elements[el].label, "the owl")

    def test_a_file_that_is_not_in_the_store_cannot_reach_the_board(self):
        s, _ = board()
        before = snapshot(s)
        with self.assertRaises(SessionRefused) as cm:
            s.add_file("image", "ghost", digest_of(b"never stored"))
        self.assertIn("is not in the store", str(cm.exception))
        self.assertEqual(snapshot(s), before)

    def test_a_kind_a_file_cannot_become_is_refused(self):
        s, store = board()
        d = store.put(b"x")
        with self.assertRaises(SessionRefused) as cm:
            s.add_file("text", "nope", d)
        self.assertIn("is not something a file becomes", str(cm.exception))
        self.assertEqual(len(s.scene.elements), 0)

    def test_every_kind_a_file_can_become_is_accepted(self):
        s, store = board()
        for i, kind in enumerate(("frame", "sketch", "image", "video", "model")):
            s.add_file(kind, kind, store.put(f"file {i}".encode()))
        self.assertEqual(len(s.scene.elements), 5)

    def test_a_garbage_digest_is_refused_and_not_a_traceback(self):
        s, _ = board()
        for bad in ["", "../x", None, "sha256:zz", 5]:
            with self.assertRaises(SessionRefused):
                s.add_file("image", "x", bad)

    def test_text_needs_words(self):
        s, _ = board()
        for blank in ["", "   ", "\n"]:
            with self.assertRaises(SessionRefused):
                s.add_text(blank)
        s.add_text("a small brass owl")
        self.assertEqual(len(s.scene.elements), 1)

    def test_an_unnamed_file_takes_a_label_from_its_name(self):
        s, store = board()
        out = s.add_file("image", "", store.put(b"y"), name="owl.png")
        self.assertEqual(s.scene.elements[out["receipt"]["ids"][0]].label, "owl.png")


class Refusals(unittest.TestCase):
    def test_a_refused_preset_changes_nothing(self):
        s, store, d, el = with_sketch()
        before, version = snapshot(s), s.version
        with self.assertRaises(SessionRefused):
            s.apply_preset(el, "frosted-glass")          # takes a mesh, a sketch is not one
        self.assertEqual(snapshot(s), before)
        self.assertEqual(s.version, version, "a refusal is not a change")

    def test_a_preset_that_does_not_exist_is_refused_by_name(self):
        s, store, d, el = with_sketch()
        with self.assertRaises(SessionRefused) as cm:
            s.apply_preset(el, "no-such-preset")
        self.assertIn("no-such-preset", str(cm.exception))

    def test_an_element_that_is_not_on_the_board_is_refused_for_every_action(self):
        s, _ = board()
        for call in (lambda: s.apply_preset("ghost-1", "sketch-to-mesh"), lambda: s.remove("ghost-1"),
                     lambda: s.rename("ghost-1", "x"), lambda: s.set_value("ghost/inst", "weight", 1)):
            with self.assertRaises(SessionRefused):
                call()

    def test_a_failure_halfway_through_an_action_leaves_nothing_behind(self):
        # the real property: scene.add succeeds, then something later in the same action raises.
        # without the copy, the added element would stay. with it, the board is untouched.
        s, store = board()
        d = store.put(b"z")
        before = snapshot(s)
        def half(scene):
            scene.add("image", "half", asset=d)
            raise SessionRefused("died after adding")
        with self.assertRaises(SessionRefused):
            s._do("half", half)
        self.assertEqual(snapshot(s), before)
        self.assertEqual(len(s.scene.elements), 0)

    def test_an_unexpected_exception_is_not_swallowed_and_changes_nothing(self):
        s, _ = board()
        before = snapshot(s)
        def bug(scene):
            scene.add("text", "x", text="hi")
            raise RuntimeError("a real bug")
        with self.assertRaises(RuntimeError):
            s._do("bug", bug)
        self.assertEqual(snapshot(s), before)

    def test_an_empty_rename_is_refused(self):
        s, store, d, el = with_sketch()
        with self.assertRaises(SessionRefused):
            s.rename(el, "   ")
        self.assertEqual(s.scene.elements[el].label, "the owl")


class Presets(unittest.TestCase):
    def test_applying_a_preset_adds_its_nodes_and_says_which(self):
        s, store, d, el = with_sketch()
        out = s.apply_preset(el, "sketch-to-mesh")
        self.assertGreater(len(out["pipeline"]["nodes"]), 1)
        self.assertTrue(out["receipt"]["ids"], "the receipt names the nodes that were made")
        self.assertTrue(all(i in {n["id"] for n in out["pipeline"]["nodes"]} for i in out["receipt"]["ids"]))
        self.assertIn("on the owl", out["receipt"]["said"])

    def test_presets_chain_on_what_the_element_shows(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        out = s.apply_preset(el, "frosted-glass")
        self.assertEqual(out["board"][0]["presets"], ["sketch-to-mesh", "frosted-glass"])

    def test_every_preset_in_the_menu_can_be_applied_to_an_element_it_names_or_is_refused_cleanly(self):
        # nothing in the menu may crash the session: each is either applied or refused with a sentence
        s, store = board()
        kinds = {"text": ("text", {"text": "a small brass owl"}), "image": ("image", {}), "mesh": ("model", {})}
        for name, preset in presets.PRESETS.items():
            fresh, st = board()
            kind, extra = kinds[preset.input_dtype]
            if kind == "text":
                el = fresh.add_text("a small brass owl")["receipt"]["ids"][0]
            else:
                el = fresh.add_file(kind, "src", st.put(name.encode()))["receipt"]["ids"][0]
            before = snapshot(fresh)
            try:
                out = fresh.apply_preset(el, name)
                self.assertGreaterEqual(len(out["pipeline"]["nodes"]), 2, name)
            except SessionRefused as problem:
                self.assertTrue(str(problem), name)
                self.assertEqual(snapshot(fresh), before, f"{name} refused but changed the board")

    def test_moving_a_control_changes_the_param_it_targets(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        inst = next(iter(s.scene.instances.values()))
        slider = next(iter(presets.get("sketch-to-mesh").sliders.values()))
        mid = (slider.low + slider.high) / 2
        out = s.set_value(inst.id, slider.name, mid)
        self.assertEqual(s.scene.instances[inst.id].values[slider.name], mid)
        self.assertEqual(out["receipt"]["action"], "set_value")

    def test_a_control_outside_its_range_is_refused_and_the_value_stays(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        inst = next(iter(s.scene.instances.values()))
        slider = next(iter(presets.get("sketch-to-mesh").sliders.values()))
        was = s.scene.instances[inst.id].values[slider.name]
        before = snapshot(s)
        with self.assertRaises(SessionRefused):
            s.set_value(inst.id, slider.name, slider.high + 1000)
        self.assertEqual(snapshot(s), before)
        self.assertEqual(s.scene.instances[inst.id].values[slider.name], was)


class Removing(unittest.TestCase):
    def test_removing_an_element_takes_its_nodes_with_it(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        out = s.remove(el)
        self.assertEqual(out["pipeline"]["nodes"], [])
        self.assertEqual(out["board"], [])

    def test_removing_one_element_leaves_another_alone(self):
        s, store = board()
        a = s.add_file("sketch", "a", store.put(b"a"))["receipt"]["ids"][0]
        b = s.add_file("sketch", "b", store.put(b"b"))["receipt"]["ids"][0]
        s.apply_preset(a, "sketch-to-mesh")
        s.apply_preset(b, "sketch-to-mesh")
        out = s.remove(a)
        self.assertEqual([e["id"] for e in out["board"]], [b])
        self.assertTrue(all(n["id"].startswith(b) for n in out["pipeline"]["nodes"]))


class Undo(unittest.TestCase):
    def test_undo_puts_the_board_back_exactly(self):
        s, store, d, el = with_sketch()
        before = snapshot(s)
        s.apply_preset(el, "sketch-to-mesh")
        self.assertNotEqual(snapshot(s), before)
        s.undo()
        self.assertEqual(snapshot(s), before)

    def test_redo_puts_it_forward_again(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        after = snapshot(s)
        s.undo(); s.redo()
        self.assertEqual(snapshot(s), after)

    def test_a_new_action_after_undo_discards_the_redo_branch(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        s.undo()
        self.assertTrue(s.view()["can_redo"])
        s.add_text("something else")
        self.assertFalse(s.view()["can_redo"])
        with self.assertRaises(SessionRefused):
            s.redo()

    def test_undo_with_nothing_to_undo_is_refused(self):
        s, _ = board()
        with self.assertRaises(SessionRefused):
            s.undo()
        with self.assertRaises(SessionRefused):
            s.redo()

    def test_a_refused_action_leaves_nothing_to_undo(self):
        s, _ = board()
        with self.assertRaises(SessionRefused):
            s.remove("ghost")
        self.assertFalse(s.view()["can_undo"])

    def test_undo_walks_all_the_way_back_step_by_step(self):
        s, store = board()
        states = [snapshot(s)]
        for i in range(5):
            s.add_file("image", f"i{i}", store.put(f"img {i}".encode()))
            states.append(snapshot(s))
        for expected in reversed(states[:-1]):
            s.undo()
            self.assertEqual(snapshot(s), expected)
        self.assertFalse(s.view()["can_undo"])

    def test_the_undo_stack_is_bounded(self):
        s, store = board()
        for i in range(UNDO_DEPTH + 20):
            s.add_text(f"t{i}")
        n = 0
        while s.view()["can_undo"]:
            s.undo(); n += 1
        self.assertEqual(n, UNDO_DEPTH)


class Views(unittest.TestCase):
    def test_the_version_moves_on_every_change_and_only_then(self):
        s, store = board()
        v = s.version
        s.add_text("a")
        self.assertEqual(s.version, v + 1)
        with self.assertRaises(SessionRefused):
            s.remove("ghost")
        self.assertEqual(s.version, v + 1)
        s.undo()
        self.assertEqual(s.version, v + 2, "undo is a change a page must see")
        s.view()
        self.assertEqual(s.version, v + 2, "reading is not")

    def test_the_view_carries_the_receipt_of_the_action_that_made_it(self):
        s, _ = board()
        out = s.add_text("hello there")
        self.assertEqual(out["receipt"]["action"], "add_text")
        self.assertIsNone(s.view()["receipt"], "a plain read has no receipt")

    def test_only_images_whose_bytes_exist_are_offered_as_previews(self):
        s, store = board()
        keep = s.add_file("image", "kept", store.put(b"kept"))["receipt"]["ids"][0]
        vid = s.add_file("video", "clip", store.put(b"clip"))["receipt"]["ids"][0]
        assets = s.view()["assets"]
        self.assertEqual(set(assets), {keep}, "a video is not drawn as a picture")

    def test_a_preview_whose_file_has_gone_is_dropped_not_linked(self):
        s, store = board()
        d = store.put(b"will vanish")
        el = s.add_file("image", "x", d)["receipt"]["ids"][0]
        hexed = d.split(":")[1]
        (store.root / hexed[:2] / hexed[2:4] / hexed).unlink()
        self.assertNotIn(el, s.view()["assets"])

    def test_the_view_is_json(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        json.dumps(s.view())

    def test_the_pipeline_in_the_view_is_the_shape_the_renderer_checks(self):
        s, store, d, el = with_sketch()
        s.apply_preset(el, "sketch-to-mesh")
        p = s.view()["pipeline"]
        self.assertEqual(set(p), {"scene", "nodes", "wires"})
        ids = {n["id"] for n in p["nodes"]}
        for w in p["wires"]:
            self.assertIn(w["from"]["node"], ids)
            self.assertIn(w["to"]["node"], ids)


class Concurrency(unittest.TestCase):
    def test_many_threads_adding_at_once_lose_nothing_and_collide_on_nothing(self):
        s, store = board()
        errors = []
        def go(i):
            try:
                s.add_file("image", f"i{i}", store.put(f"image number {i}".encode()))
            except Exception as problem:   # noqa: BLE001
                errors.append(problem)
        threads = [threading.Thread(target=go, args=(i,)) for i in range(40)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(errors, [])
        self.assertEqual(len(s.scene.elements), 40)
        self.assertEqual(len({e for e in s.scene.elements}), 40, "every id is distinct")
        self.assertEqual(s.version, 40, "one version per change, none skipped or doubled")

    def test_reads_during_writes_always_see_a_whole_board(self):
        s, store = board()
        seen = []
        stop = threading.Event()
        def reader():
            while not stop.is_set():
                v = s.view()
                ids = {n["id"] for n in v["pipeline"]["nodes"]}
                seen.append(all(w["from"]["node"] in ids and w["to"]["node"] in ids for w in v["pipeline"]["wires"]))
        r = threading.Thread(target=reader); r.start()
        for i in range(15):
            el = s.add_file("sketch", f"s{i}", store.put(f"s{i}".encode()))["receipt"]["ids"][0]
            s.apply_preset(el, "sketch-to-mesh")
        stop.set(); r.join()
        self.assertTrue(seen and all(seen), "a reader saw a wire to a node that was not there")


if __name__ == "__main__":
    unittest.main()
