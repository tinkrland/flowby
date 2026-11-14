"""looks_test: the direction layer has to be a catalogue a picker can trust.

every rule here came from reading nodetool's `packages/presets` on 2026-11-13 (their `stack.ts` and
`compile.ts`), which is the most complete answer anyone has published to "how does a style actually
reach a model". the rules are re-checked here because a catalogue that only *usually* refuses is worse
than no catalogue: the user sees a card that looks available and a run that fails.

the tests are in three groups: the catalogue refuses rows that would lie to a panel, the compiler
refuses briefs that ask for two directions down one slot, and the ejection puts the wording in the graph
where a person can edit it rather than in a hidden suffix.
"""

import json
import tempfile
import unittest
from pathlib import Path

from flowby import kits, looks, presets


def row(**overrides) -> dict:
    """a minimal valid catalogue row, so each test changes exactly the thing it is testing."""
    base = {
        "id": "look.test", "kind": "look", "version": 1, "name": "test",
        "description": "a direction, for a test", "slot": "mark",
        "modes": ["image"], "inputs": ["text"], "stackable": True, "conflicts": [],
        "prompt": {"default": "a test direction"},
    }
    base.update(overrides)
    return base


class TheCatalogue(unittest.TestCase):
    def setUp(self):
        self.shelf = looks.catalogue("looks")

    def test_a_kit_with_wording_words_all_of_it_and_the_others_say_they_do_not(self):
        # handdrawn and paint are worded end to end; analog and textile are not worded at all. a kit that
        # worded half its members would be the confusing case, so the rule is all or none.
        menu = kits.menu(presets=presets.PRESETS, looks=self.shelf)
        for kit in menu["kits"]:
            worded = [row for row in kit["members"] if row["worded"]]
            if kit["id"] in ("handdrawn", "paint"):
                self.assertEqual(len(worded), kit["total"], f"every {kit['id']} member should have its wording")
            else:
                self.assertEqual(worded, [], f"{kit['id']} has no looks yet and should say so")
        # and no kit claims a look that is not in the catalogue: that is the same lie as a dead preset
        for kit in menu["kits"]:
            for member in kit["members"]:
                if member["look"]:
                    self.assertIn(member["look"], self.shelf, f"{kit['id']}/{member['id']}")

    def test_every_look_belongs_to_a_kit_that_exists(self):
        for look in self.shelf.values():
            self.assertIn(look.kit, kits.KITS, f"{look.id} says it is in {look.kit!r}")

    def test_a_row_without_a_default_fragment_is_refused(self):
        # an unknown model has to fall back to *something*; a row with no default and no matching family
        # would compile to an empty prompt and charge for it
        with self.assertRaises(looks.LookRefused) as caught:
            looks.look_from_dict(row(prompt={"flux": "a flux direction"}))
        self.assertIn("default", str(caught.exception))

    def test_a_fragment_for_an_unknown_family_is_refused(self):
        with self.assertRaises(looks.LookRefused):
            looks.look_from_dict(row(prompt={"default": "x", "midjourney": "a mj direction"}))

    def test_a_fragment_key_that_is_not_prefix_suffix_or_replace_is_refused(self):
        with self.assertRaises(looks.LookRefused):
            looks.look_from_dict(row(prompt={"default": {"prefix": "x", "prologue": "y"}}))

    def test_a_setting_no_mode_forwards_is_refused_at_load_not_at_run(self):
        with self.assertRaises(looks.LookRefused) as caught:
            looks.look_from_dict(row(params={"cfg_scale": 7}))
        self.assertIn("cfg_scale", str(caught.exception))

    def test_a_setting_for_a_family_that_does_not_exist_is_refused(self):
        with self.assertRaises(looks.LookRefused):
            looks.look_from_dict(row(family_params={"midjourney": {"steps": 20}}))

    def test_an_id_that_is_not_a_look_id_is_refused(self):
        for bad in ("pencil", "studio.pencil", "look.Pencil Sketch"):
            with self.assertRaises(looks.LookRefused, msg=bad):
                looks.look_from_dict(row(id=bad))

    def test_a_look_with_no_slot_or_no_mode_is_refused(self):
        with self.assertRaises(looks.LookRefused):
            looks.look_from_dict(row(slot="vibe"))
        with self.assertRaises(looks.LookRefused):
            looks.look_from_dict(row(modes=[]))

    def test_a_conflict_naming_a_look_that_does_not_exist_is_refused_as_a_set(self):
        # checked against the whole catalogue, not the row: this is the failure a single row cannot see
        room = Path(tempfile.mkdtemp())
        (room / "a.json").write_text(json.dumps(row(id="look.a", conflicts=["look.ghost"])))
        with self.assertRaises(looks.LookRefused) as caught:
            looks.catalogue(room)
        self.assertIn("look.ghost", str(caught.exception))

    def test_two_files_for_one_look_are_refused(self):
        room = Path(tempfile.mkdtemp())
        body = json.dumps(row(id="look.a"))
        (room / "a.json").write_text(body)
        (room / "b.json").write_text(body)
        with self.assertRaises(looks.LookRefused):
            looks.catalogue(room)

    def test_a_look_conflicting_with_itself_is_refused(self):
        room = Path(tempfile.mkdtemp())
        (room / "a.json").write_text(json.dumps(row(id="look.a", conflicts=["look.a"])))
        with self.assertRaises(looks.LookRefused):
            looks.catalogue(room)


class TheBrief(unittest.TestCase):
    def setUp(self):
        self.shelf = looks.catalogue("looks")

    def compile(self, ids, model="flux-dev", mode="image", prompt="a fox"):
        return looks.compile_looks(ids, model=model, mode=mode, prompt=prompt, looks=self.shelf)

    def test_a_look_reads_a_fragment_for_the_model_and_falls_back_otherwise(self):
        flux = self.compile(("look.pencil-sketch",), model="flux-dev")
        self.assertIn("graphite", flux.prompt.lower())
        self.assertEqual(flux.warnings, ())
        other = self.compile(("look.pencil-sketch",), model="a-model-from-next-year")
        # the default wording is used *and said out loud*, because "we fell back" is the thing a person
        # needs to know before blaming the look for a bad render
        self.assertIn("pencil on paper", other.prompt.lower())
        self.assertTrue(any("default" in warning for warning in other.warnings), other.warnings)

    def test_the_family_settings_override_the_shared_ones(self):
        flux = self.compile(("look.photocopy",), model="flux-dev")
        sdxl = self.compile(("look.photocopy",), model="sdxl-turbo")
        self.assertEqual(flux.params["guidance"], 4.5)
        self.assertEqual(sdxl.params["guidance"], 7.5)

    def test_a_setting_the_mode_does_not_forward_is_dropped_with_a_warning(self):
        still = self.compile(("look.photocopy",), mode="image")
        edit = self.compile(("look.photocopy",), mode="image_edit")
        self.assertNotIn("strength", still.params)
        self.assertEqual(edit.params["strength"], 0.7)
        self.assertTrue(any("strength" in warning for warning in still.warnings))

    def test_three_directions_stack_one_per_slot_and_the_subject_comes_last(self):
        # one mark, one surface, one finish: the three axes are what make a stack of three possible,
        # and photocopy is not used here because it is the finish that conflicts with pencil
        made = self.compile(("look.pencil-sketch", "look.paper-tooth", "look.flat-scan"))
        self.assertEqual(made.applied, ("look.pencil-sketch", "look.paper-tooth", "look.flat-scan"))
        for fragment in ("graphite", "watercolour paper", "flatbed scan"):
            self.assertIn(fragment, made.prompt.lower())
        self.assertTrue(made.prompt.endswith("a fox"), made.prompt[-40:])

    def test_two_directions_down_one_slot_are_refused_naming_both(self):
        with self.assertRaises(looks.LookRefused) as caught:
            self.compile(("look.pencil-sketch", "look.charcoal"))
        message = str(caught.exception)
        self.assertIn("pencil sketch", message)
        self.assertIn("charcoal", message)

    def test_a_declared_conflict_is_refused_even_across_slots(self):
        # the pair rule that a slot cannot express: photocopy is a finish and pencil sketch is a mark,
        # so only the explicit conflict list can stop them, which is why it exists
        with self.assertRaises(looks.LookRefused):
            self.compile(("look.pencil-sketch", "look.photocopy"))

    def test_four_directions_are_refused_even_across_four_filled_slots(self):
        # built here because the catalogue fills only three of the four slots, so a four-look brief
        # would be refused by the slot rule first and the count rule would never be the one that bit
        shelf = {slot: looks.look_from_dict(row(id=f"look.{slot}", slot=slot, name=slot))
                 for slot in ("mark", "surface", "finish", "medium")}
        with self.assertRaises(looks.LookRefused) as caught:
            looks.compile_looks(tuple(shelf), model="flux-dev", mode="image", prompt="x", looks=shelf)
        self.assertIn("at most 3", str(caught.exception))

    def test_a_look_missing_the_fragments_family_says_so_even_when_the_model_is_known(self):
        # a known family with no fragment for it is the common case as a catalogue grows, and it is a
        # different warning from an unknown model: the model is fine, this one look is generic
        bare = looks.look_from_dict(row(id="look.bare", prompt={"default": "a generic direction"}))
        made = looks.compile_looks(("look.bare",), model="flux-dev", mode="image", prompt="x",
                                   looks={"look.bare": bare})
        self.assertTrue(any("no flux fragment" in warning for warning in made.warnings), made.warnings)

    def test_the_same_look_twice_is_refused(self):
        with self.assertRaises(looks.LookRefused):
            self.compile(("look.marker", "look.marker"))

    def test_a_look_that_does_not_run_in_this_mode_is_refused(self):
        with self.assertRaises(looks.LookRefused) as caught:
            self.compile(("look.marker",), mode="video")
        self.assertIn("marker", str(caught.exception))

    def test_two_looks_disagreeing_about_one_setting_are_refused_naming_both(self):
        # built here rather than added to the catalogue: two directions that genuinely want different
        # guidance is a real collision, and the point is that the compiler refuses rather than letting
        # whichever came second win silently
        first = looks.look_from_dict(row(id="look.a", slot="mark", params={"guidance": 3.0}))
        second = looks.look_from_dict(row(id="look.b", slot="surface", params={"guidance": 8.0}))
        shelf = {"look.a": first, "look.b": second}
        with self.assertRaises(looks.LookRefused) as caught:
            looks.compile_looks(("look.a", "look.b"), model="flux-dev", mode="image",
                                prompt="x", looks=shelf)
        self.assertIn("guidance", str(caught.exception))

    def test_two_looks_agreeing_about_one_setting_are_fine(self):
        first = looks.look_from_dict(row(id="look.a", slot="mark", params={"guidance": 5.0}))
        second = looks.look_from_dict(row(id="look.b", slot="surface", params={"guidance": 5.0}))
        made = looks.compile_looks(("look.a", "look.b"), model="flux-dev", mode="image", prompt="x",
                                   looks={"look.a": first, "look.b": second})
        self.assertEqual(made.params["guidance"], 5.0)

    def test_compiling_twice_gives_the_same_words(self):
        one = self.compile(("look.doodle", "look.paper-tooth"))
        two = self.compile(("look.doodle", "look.paper-tooth"))
        self.assertEqual(one.as_dict(), two.as_dict())

    def test_the_picker_and_the_compiler_agree_about_every_pair(self):
        ids = sorted(self.shelf)
        for a in ids:
            for b in ids:
                picked = looks.can_add((a,), b, self.shelf)
                try:
                    looks.compile_looks((a, b), model="flux-dev", mode="image", prompt="x",
                                        looks=self.shelf)
                    compiled = None
                except looks.LookRefused as exc:
                    compiled = str(exc)
                self.assertEqual(picked is None, compiled is None,
                                 f"{a} + {b}: picker said {picked!r}, compiler said {compiled!r}")


class TheEjection(unittest.TestCase):
    def setUp(self):
        self.shelf = looks.catalogue("looks")
        self.ops = {step.op for preset in presets.PRESETS.values() for step in preset.steps.values()}

    def test_a_look_ejects_into_two_steps_the_graph_already_has(self):
        made = looks.eject("look.charcoal", model="flux-dev", looks=self.shelf)
        self.assertEqual([step["op"] for step in made["steps"]], [looks.TEMPLATE_OP, looks.GENERATE_OP])
        # the ops have to be real: an ejection naming an op no preset has is a graph that cannot build
        for step in made["steps"]:
            self.assertIn(step["op"], self.ops, f"{step['op']} is not an op any preset has")

    def test_the_wording_lands_in_the_template_step_where_a_person_can_edit_it(self):
        made = looks.eject("look.ink-pen", model="flux-dev", looks=self.shelf)
        template = made["steps"][0]
        self.assertIn("nib pen", template["params"]["prefix"].lower())
        # and the subject is not baked in: it arrives on the compose step's own input
        self.assertNotIn("{{", template["params"]["prefix"])

    def test_the_settings_land_on_the_generator_step(self):
        made = looks.eject("look.photocopy", model="sdxl-turbo", mode="image_edit", looks=self.shelf)
        self.assertEqual(made["steps"][1]["params"], {"guidance": 7.5, "strength": 0.7})


class TheShelf(unittest.TestCase):
    def test_every_look_appears_once_under_its_own_slot(self):
        shelf = looks.catalogue("looks")
        panel = looks.shelf(shelf)
        seen = [look["id"] for group in panel["groups"] for look in group["looks"]]
        self.assertEqual(sorted(seen), sorted(shelf))
        for group in panel["groups"]:
            for look in group["looks"]:
                self.assertEqual(shelf[look["id"]].slot, group["slot"])

    def test_an_empty_slot_is_not_drawn(self):
        # the whole catalogue fills every slot now, so the rule is checked on a shelf that really has a
        # gap: a slot with no looks must not appear as an empty heading
        shelf = {k: v for k, v in looks.catalogue("looks").items() if v.slot != "medium"}
        panel = looks.shelf(shelf)
        self.assertNotIn("medium", [group["slot"] for group in panel["groups"]])
        self.assertEqual(len(panel["groups"]), len({v.slot for v in shelf.values()}))


class ThePaintMedium(unittest.TestCase):
    """paint: the kit that fills the `medium` slot, added from the owner's point (2026-11-14) that the
    watercolour-style families already exist in the products he sent and can be taken rather than invented.

    the rule these tests hold is the line that makes the kit more than a list: paint is the slot whose job
    is what the *medium* does once the hand has gone, so every paint member must sit in `medium` and no
    two of them can share a brief. if one drifted into `mark` it would stack with crayon and the kit would
    stop meaning anything.
    """

    def setUp(self):
        self.shelf = looks.catalogue("looks")
        self.paint = {i: l for i, l in self.shelf.items() if l.kit == "paint"}

    def test_the_four_paint_members_exist_and_all_are_wording(self):
        self.assertEqual(sorted(self.paint), ["look.gouache", "look.ink-wash", "look.oil-paint",
                                              "look.watercolour"])

    def test_every_paint_member_occupies_the_medium_slot(self):
        self.assertEqual({l.slot for l in self.paint.values()}, {"medium"},
                         "a paint look in another slot would stack beside a medium instead of replacing one")

    def test_every_paint_member_words_every_family_and_a_default(self):
        for look in self.paint.values():
            self.assertIn("default", look.prompt, f"{look.id} must work for a model nobody anticipated")
            for family in looks.FAMILIES:
                self.assertIn(family, look.prompt, f"{look.id} says nothing to {family}")

    def test_two_paints_in_one_brief_are_refused_naming_both(self):
        with self.assertRaises(looks.LookRefused) as caught:
            looks.compile_looks(("look.watercolour", "look.gouache"), model="flux-dev", mode="image",
                                prompt="", looks=self.shelf)
        self.assertIn("watercolour", str(caught.exception))
        self.assertIn("gouache", str(caught.exception))

    def test_a_paint_medium_composes_with_a_surface_and_a_finish(self):
        done = looks.compile_looks(("look.watercolour", "look.paper-tooth", "look.flat-scan"),
                                   model="flux-dev", mode="image", prompt="a heron on a jetty",
                                   looks=self.shelf)
        words = done.prompt.lower()
        self.assertIn("watercolour", words)
        self.assertIn("heron on a jetty", words, "the subject still comes last")
        self.assertEqual(len({self.shelf[i].slot for i in done.applied}), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
