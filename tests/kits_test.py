"""kits_test.py: a kit lists what the owner named, and never offers what is not built.

the one claim that matters is that a name with nothing behind it cannot be run. so most of these
build real Style objects in each of styles.py's seven states and check what the kit says about a
member that points at them, and a couple pin the owner's list word for word, since "list them now"
was the whole instruction for the styles.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from flowby import kits, presets, styles  # noqa: E402
from flowby.kits import Kit, KitRefused, Member  # noqa: E402


def a_style(state):
    return styles.Style(id="cy", label="cyanotype", trigger="mzqtlv", base="flux-dev", state=state)


class TheOwnersLists(unittest.TestCase):
    def test_analog_holds_exactly_what_was_named(self):
        self.assertEqual([m.id for m in kits.ANALOG.members], ["cyanotype", "linocut-stamp", "wax-seal", "blockprint", "screenprint", "risograph", "lithograph", "woodblock", "etching"])
        self.assertEqual([m.label for m in kits.ANALOG.members], ["cyanotype", "linocut stamps", "wax seals", "block printing", "screen print", "risograph", "lithograph", "woodblock", "etching"])

    def test_textile_holds_cross_stitch_and_woven_as_subtypes_of_textile(self):
        by = {m.id: m for m in kits.TEXTILE.members}
        self.assertEqual(set(by), {"textile", "cross-stitch", "woven"})
        self.assertEqual((by["cross-stitch"].kind, by["cross-stitch"].parent), ("subtype", "textile"))
        self.assertEqual((by["woven"].kind, by["woven"].parent), ("subtype", "textile"))
        self.assertIsNone(by["textile"].parent)

    def test_the_kits_are_the_four_that_were_asked_for(self):
        # analog and textile on 2026-11-09, handdrawn on 2026-11-13, paint on 2026-11-14 (the owner's
        # point that the watercolour-style families already exist and can be taken). a fifth would be
        # somebody's idea, not the owner's, so the list is pinned rather than merely counted.
        self.assertEqual(list(kits.KITS), ["analog", "handdrawn", "paint", "textile"])

    def test_handdrawn_holds_the_marks_named_and_nothing_pressed_or_carved(self):
        self.assertEqual([m.id for m in kits.HANDDRAWN.members],
                         ["pencil-sketch", "doodle", "scribble", "ballpoint",
                          "ink-pen", "charcoal", "crayon", "marker"])
        # the split from analog is the mark, not the hand: a linocut was cut by hand and belongs to
        # analog, because the look comes from the block and the press
        self.assertNotIn("linocut-stamp", [m.id for m in kits.HANDDRAWN.members])
        self.assertTrue(all(m.kind == "style" for m in kits.HANDDRAWN.members))
        self.assertTrue(all(m.parent is None for m in kits.HANDDRAWN.members))

    def test_analog_members_are_styles_because_the_owner_said_styles(self):
        self.assertTrue(all(m.kind == "style" for m in kits.ANALOG.members))

    def test_every_listed_member_says_what_it_looks_like(self):
        for kit in kits.KITS.values():
            for m in kit.members:
                self.assertGreater(len(m.blurb), 20, f"{kit.id}/{m.id} has no description")


class NothingUnbuiltRuns(unittest.TestCase):
    def test_every_member_today_is_listed_and_none_is_runnable(self):
        for kit in kits.KITS.values():
            for m in kit.members:
                self.assertEqual(kits.state_of(m), "listed", f"{kit.id}/{m.id}")
                self.assertFalse(kits.runnable(m), f"{kit.id}/{m.id} claims to run with nothing behind it")

    def test_the_menu_agrees_and_counts_zero_ready(self):
        for kit in kits.menu()["kits"]:
            self.assertEqual(kit["ready"], 0)
            self.assertTrue(all(r["state"] == "listed" and not r["runnable"] for r in kit["members"]))

    def test_a_member_naming_a_style_that_does_not_exist_is_still_listed(self):
        m = Member("x", "x", style="never-made")
        self.assertEqual(kits.state_of(m, styles={}), "listed")
        self.assertEqual(kits.state_of(m, styles=None), "listed")

    def test_editing_a_member_to_say_ready_is_impossible_because_there_is_no_such_field(self):
        with self.assertRaises(TypeError):
            Member("x", "x", state="ready")


class FollowsTheStyle(unittest.TestCase):
    def member(self):
        return Member("cyanotype", "cyanotype", style="cy")

    def test_each_of_the_seven_style_states_reads_as_the_right_kit_state(self):
        expected = {"corpus": "corpus", "gated": "corpus", "training": "training", "validating": "training",
                    "ready": "ready", "refused": "listed", "failed": "listed"}
        self.assertEqual(set(expected), set(styles.STATES), "a state was added to styles.py and the kit does not know it")
        for state, want in expected.items():
            self.assertEqual(kits.state_of(self.member(), styles={"cy": a_style(state)}), want, state)

    def test_only_a_ready_style_is_runnable(self):
        for state in styles.STATES:
            self.assertEqual(kits.runnable(self.member(), styles={"cy": a_style(state)}), state == "ready", state)

    def test_a_style_that_fails_after_being_ready_stops_being_offered(self):
        s = a_style("ready")
        self.assertTrue(kits.runnable(self.member(), styles={"cy": s}))
        s.state = "failed"
        self.assertFalse(kits.runnable(self.member(), styles={"cy": s}))

    def test_the_menu_counts_a_ready_member_and_shows_the_rest_as_listed(self):
        kit = Kit("k", "k", "a test kit long enough", (Member("a", "a", style="cy"), Member("b", "b")))
        self.assertEqual(kits.state_of(kit.member("a"), styles={"cy": a_style("ready")}), "ready")
        self.assertEqual(kits.state_of(kit.member("b"), styles={"cy": a_style("ready")}), "listed")


class PresetMembers(unittest.TestCase):
    def test_a_preset_member_is_ready_only_when_that_preset_exists(self):
        m = Member("t", "t", kind="preset", preset="text-to-image")
        self.assertEqual(kits.state_of(m, presets=presets.PRESETS), "ready")
        self.assertEqual(kits.state_of(Member("t", "t", kind="preset", preset="no-such"), presets=presets.PRESETS), "listed")
        self.assertEqual(kits.state_of(m, presets=None), "listed")

    def test_a_preset_member_must_name_its_preset_and_no_one_else_may(self):
        with self.assertRaises(KitRefused):
            Member("t", "t", kind="preset")
        with self.assertRaises(KitRefused):
            Member("t", "t", kind="style", preset="text-to-image")


class RefusedWhenBuilt(unittest.TestCase):
    def test_two_members_with_one_id_are_refused(self):
        with self.assertRaises(KitRefused) as cm:
            Kit("k", "k", "b", (Member("a", "a"), Member("a", "again")))
        self.assertIn("two members are called 'a'", str(cm.exception))

    def test_a_subtype_under_a_parent_that_is_not_in_the_kit_is_refused(self):
        with self.assertRaises(KitRefused) as cm:
            Kit("k", "k", "b", (Member("a", "a", kind="subtype", parent="ghost"),))
        self.assertIn("'ghost', which is not in this kit", str(cm.exception))

    def test_a_member_cannot_be_its_own_parent(self):
        with self.assertRaises(KitRefused):
            Kit("k", "k", "b", (Member("a", "a", kind="subtype", parent="a"),))

    def test_a_kind_that_is_not_a_kind_is_refused(self):
        with self.assertRaises(KitRefused):
            Member("a", "a", kind="vibe")

    def test_an_id_that_cannot_go_in_a_url_is_refused(self):
        for bad in ["", "Has Space", "UPPER", "two words"]:
            with self.assertRaises(KitRefused, msg=bad):
                Member(bad, "x")

    def test_asking_for_a_kit_that_does_not_exist_names_the_ones_that_do(self):
        with self.assertRaises(KitRefused) as cm:
            kits.get("pottery")
        self.assertIn("analog, handdrawn, paint, textile", str(cm.exception))


class Shape(unittest.TestCase):
    def test_children_and_roots(self):
        self.assertEqual([m.id for m in kits.TEXTILE.roots()], ["textile"])
        self.assertEqual([m.id for m in kits.TEXTILE.children("textile")], ["cross-stitch", "woven"])
        self.assertEqual(kits.TEXTILE.children("woven"), ())
        self.assertEqual([m.id for m in kits.ANALOG.roots()], ["cyanotype", "linocut-stamp", "wax-seal", "blockprint", "screenprint", "risograph", "lithograph", "woodblock", "etching"])

    def test_the_menu_is_plain_json(self):
        import json
        out = json.loads(json.dumps(kits.menu()))
        self.assertEqual([k["id"] for k in out["kits"]], ["analog", "handdrawn", "paint", "textile"])
        by = {k["id"]: k for k in out["kits"]}
        self.assertEqual(by["handdrawn"]["total"], len(kits.HANDDRAWN.members))
        self.assertEqual(by["textile"]["total"], 3)

    def test_adding_a_member_is_one_line(self):
        grown = Kit("analog", "analog", "b", kits.ANALOG.members + (Member("mezzotint", "mezzotint", blurb="a rocked plate burnished back from black, velvet darks"),))
        self.assertEqual(len(grown.members), len(kits.ANALOG.members) + 1)
        self.assertEqual(kits.state_of(grown.member("mezzotint")), "listed")


class Terminal(unittest.TestCase):
    def test_the_cli_prints_the_same_kits_the_menu_returns(self):
        import json, subprocess
        root = pathlib.Path(__file__).resolve().parents[1]
        out = subprocess.run([str(root / "bin" / "flowby"), "--json", "kits", "--looks", str(root / "looks")],
                             capture_output=True, text=True, check=True).stdout
        from flowby import looks as looksmod
        self.assertEqual(json.loads(out),
                         kits.menu(presets=presets.PRESETS, looks=looksmod.catalogue(root / "looks")))

    def test_the_plain_view_indents_a_subtype_under_its_parent(self):
        import subprocess
        root = pathlib.Path(__file__).resolve().parents[1]
        lines = subprocess.run([str(root / "bin" / "flowby"), "kits"], capture_output=True, text=True, check=True).stdout.splitlines()
        stitch = next(l for l in lines if "cross stitch" in l)
        parent = next(l for l in lines if l.lstrip().startswith("textile ") and "style" in l)
        self.assertGreater(len(stitch) - len(stitch.lstrip()), len(parent) - len(parent.lstrip()))


if __name__ == "__main__":
    unittest.main()
