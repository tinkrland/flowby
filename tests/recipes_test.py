"""recipes_test: a chain that somebody else can use, and the three ways that goes wrong.

read off Fuser's recipe pages: a recipe has a name for the result, a one-line brief, exposed inputs with
starting values, outputs, an author and a version, and a placement is pinned to a version so improving
the recipe cannot silently change finished work. the tests here are mostly about the pin, because it is
the only part that cannot be seen by looking at the recipe.
"""

import unittest

from flowby import presets, recipes


def record(name="the owl chain", steps=None, kind="image"):
    """a chain as `Scene.record` reads one back."""
    return {
        "name": name,
        "kind": kind,
        "steps": [
            {"preset": "sketch-to-mesh", "values": {"detail": 90000, "fidelity": 0.85, "smooth": 2},
             "slots": {}},
            {"preset": "frosted-glass", "values": {"frost": 0.42}, "slots": {}},
        ] if steps is None else steps,
        "estimate": {"minutes": 5.4, "gpu_minutes": 3.2},
    }


def exposure(**over):
    base = {"label": "Surface detail", "preset": "sketch-to-mesh", "param": "detail", "start": 90000}
    base.update(over)
    return recipes.Exposed(**base)


class TheVersion(unittest.TestCase):
    def test_a_param_change_is_a_new_version(self):
        before = recipes.of(record())
        after = recipes.of(record(steps=[
            {"preset": "sketch-to-mesh", "values": {"detail": 40000}, "slots": {}},
            {"preset": "frosted-glass", "values": {"frost": 0.42}, "slots": {}},
        ]))
        self.assertNotEqual(before.version, after.version)

    def test_prose_is_not_a_new_version(self):
        # a rename or a better brief must not look like a change of behaviour, or the pin becomes noise
        # and people learn to click through it
        one = recipes.of(record(), brief="bring a sketch, get a mesh")
        two = recipes.of(record(name="the owl"), brief="a sketch becomes a mesh", author="liat")
        self.assertEqual(one.version, two.version)

    def test_renaming_the_output_is_not_a_new_version(self):
        # the output's name is a label like the recipe's own, and Fuser share names across versions;
        # what a placement pins is behaviour, not wording
        one = recipes.of(record(), output="mesh")
        two = recipes.of(record(), output="the printed thing")
        self.assertEqual(one.version, two.version)

    def test_wiring_is_part_of_the_version(self):
        # the same two steps and the same values, wired to a different element: that is a different
        # recipe to run, so the version has to move. (the first draft of this test changed the step
        # count as well, which is why dropping slots from the hash survived it.)
        loose = record()
        wired = record()
        wired["steps"][0]["slots"] = {"reference": "sketch-2"}
        self.assertNotEqual(recipes.of(loose).version, recipes.of(wired).version)

    def test_a_new_exposed_input_is_a_new_version(self):
        # adding an input changes what somebody is offered, so it is a different recipe to use
        self.assertNotEqual(recipes.of(record()).version, recipes.of(record(), inputs=[exposure()]).version)

    def test_the_version_is_short_enough_to_say_out_loud(self):
        version = recipes.of(record()).version
        self.assertEqual(len(version), 6)
        self.assertTrue(version.isalnum())


class ThePin(unittest.TestCase):
    def test_a_matching_pin_runs(self):
        made = recipes.of(record())
        self.assertIs(made.placed(made.version).holds(), made)

    def test_a_moved_recipe_refuses_instead_of_running_the_new_one(self):
        # this is the whole point: work already on a board does not change because the recipe improved
        old = recipes.of(record())
        placement = old.placed(old.version)
        new = recipes.of(record(steps=[{"preset": "sketch-to-mesh", "values": {"detail": 1}, "slots": {}}]))
        placement.recipe = new
        with self.assertRaises(recipes.RecipeRefused) as caught:
            placement.holds()
        message = str(caught.exception)
        self.assertIn(f"v{old.version}", message)
        self.assertIn(f"v{new.version}", message)
        self.assertIn("adopt", message)

    def test_adopting_is_the_one_way_finished_work_changes(self):
        made = recipes.of(record())
        placement = made.placed(made.version)
        moved = recipes.of(record(steps=[{"preset": "sketch-to-mesh", "values": {"detail": 2}, "slots": {}}]))
        placement.recipe = moved
        self.assertFalse(placement.current)
        placed = placement.adopt()
        self.assertTrue(placed.current)
        self.assertIs(placed.holds(), moved)

    def test_a_placement_must_say_which_version_it_holds(self):
        made = recipes.of(record())
        with self.assertRaises(recipes.RecipeRefused):
            made.placed("")

    def test_the_view_says_what_is_offered_without_running_anything(self):
        made = recipes.of(record())
        view = made.placed(made.version).view()
        self.assertTrue(view["current"])
        self.assertIsNone(view["offer"])


class TheExposedInputs(unittest.TestCase):
    def setUp(self):
        self.made = recipes.of(record(), inputs=[exposure()])

    def test_the_chain_carries_the_exposed_value(self):
        got = self.made.values_for({"Surface detail": 12000})
        self.assertEqual(got["steps"][0]["values"]["detail"], 12000.0)

    def test_an_unset_input_keeps_its_starting_value(self):
        got = self.made.values_for()
        self.assertEqual(got["steps"][0]["values"]["detail"], 90000)

    def test_a_value_that_is_not_an_input_is_refused_by_name(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            self.made.values_for({"Prompt": "a fox"})
        self.assertIn("Surface detail", str(caught.exception))

    def test_an_input_out_of_its_own_range_is_refused_at_the_border(self):
        with self.assertRaises(presets.PresetRefused):
            self.made.values_for({"Surface detail": 10 ** 9})
        with self.assertRaises(presets.PresetRefused):
            recipes.of(record(), inputs=[exposure(start=-5)])

    def test_an_input_that_feeds_a_step_not_in_the_chain_is_refused(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(), inputs=[exposure(preset="relight")])
        self.assertIn("not one of its steps", str(caught.exception))

    def test_an_input_onto_a_control_that_does_not_exist_names_the_real_ones(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(), inputs=[exposure(param="nonexistent")])
        message = str(caught.exception)
        self.assertIn("nonexistent", message)
        self.assertIn("detail", message)

    def test_two_inputs_on_one_value_are_refused(self):
        # otherwise the second silently wins, and the first looks broken to whoever changed it
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(), inputs=[exposure(label="Detail"),
                                         exposure(label="Detail again", start=20000)])
        self.assertIn("two places", str(caught.exception))

    def test_an_input_with_no_label_is_refused(self):
        with self.assertRaises(recipes.RecipeRefused):
            recipes.of(record(), inputs=[exposure(label="  ")])

    def test_the_default_input_is_the_one_the_chain_was_saved_with(self):
        # not the control's default: a recipe that opens on the default would quietly change the board
        got = recipes.default_inputs(record())
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].start, 90000)
        self.assertNotEqual(got[0].start, presets.get("sketch-to-mesh").sliders["detail"].default)


class WhatIsRefused(unittest.TestCase):
    def test_a_chain_with_no_steps(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(steps=[]))
        self.assertIn("nothing to run", str(caught.exception))

    def test_a_recipe_with_no_name(self):
        with self.assertRaises(recipes.RecipeRefused):
            recipes.of(record(name="  "))

    def test_a_preset_that_does_not_exist(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(steps=[{"preset": "nope", "values": {}, "slots": {}}]))
        self.assertIn("nope", str(caught.exception))

    def test_an_empty_brief(self):
        with self.assertRaises(recipes.RecipeRefused):
            recipes.of(record(), brief="   ")

    def test_a_brief_that_is_really_a_page(self):
        with self.assertRaises(recipes.RecipeRefused) as caught:
            recipes.of(record(), brief="x" * 201)
        self.assertIn("one line", str(caught.exception))


class ThePanel(unittest.TestCase):
    def setUp(self):
        self.panel = recipes.of(record(), inputs=[exposure()], author="liat",
                                category="image", output="mesh").panel()

    def test_it_carries_the_blocks_a_recipe_page_shows(self):
        for key in ("recipe", "brief", "version", "author", "inputs", "outputs", "models", "estimate"):
            self.assertIn(key, self.panel)

    def test_the_output_is_named_and_typed(self):
        self.assertEqual(self.panel["outputs"], [{"name": "mesh", "dtype": "mesh"}])

    def test_the_estimate_is_the_sum_of_its_steps(self):
        # read from the same presets that will run, so the number shown is the number spent
        self.assertAlmostEqual(self.panel["estimate"]["minutes"],
                               round(presets.get("sketch-to-mesh").minutes()
                                     + presets.get("frosted-glass").minutes(), 1))

    def test_the_models_are_named_without_duplicates(self):
        self.assertEqual(self.panel["models"], sorted(set(self.panel["models"])))


class TheShelf(unittest.TestCase):
    def setUp(self):
        self.one = recipes.of(record(name="one"), category="image")
        self.two = recipes.of(record(name="two", steps=[{"preset": "relight", "values": {}, "slots": {}}]
                                     ), category="photography")
        self.shelf = [self.one, self.two]

    def test_the_two_facets_filter_by_what_comes_out_and_what_job_it_is_for(self):
        self.assertEqual([r.name for r in recipes.shelf(self.shelf, output="mesh")], ["one"])
        self.assertEqual([r.name for r in recipes.shelf(self.shelf, category="photography")], ["two"])
        self.assertEqual(len(recipes.shelf(self.shelf, category="image", output="image")), 0)

    def test_the_facets_are_counted_for_a_menu(self):
        got = recipes.facets(self.shelf)
        self.assertEqual(got["categories"], {"image": 1, "photography": 1})
        self.assertEqual(got["outputs"]["mesh"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
