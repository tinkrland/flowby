"""actions_test: a file that describes itself, and the four ways that description can lie.

the parser is the part a page trusts, so most of these are refusals: an unknown header key, a wire
flowby does not have, a default outside its own range, a visibility rule pointing at nothing. a
description that is wrong in any of those ways looks fine in a list and breaks at run time, which is
why none of them are warnings here.
"""

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from flowby import actions


def header(**over):
    """a minimal valid action file, with pieces replaced."""
    parts = {
        "name": '"Halftone"',
        "description": '"Dots."',
        "runtime": "python",
        "inputs": '[{"name": "source", "type": "image"}]',
        "outputs": '[{"name": "dotted", "type": "image"}]',
        "params": '[]',
    }
    parts.update(over)
    lines = [f"# @flowby-{key}: {value}" for key, value in parts.items() if value is not None]
    return "\n".join(lines) + "\n\n\ndef run(inputs, values, out_dir):\n    return {}\n"


TWO_PARAM = '''# @flowby-name: "Risograph"
# @flowby-description: "Two inks."
# @flowby-inputs: [{"name": "source", "type": "image"}]
# @flowby-outputs: [{"name": "printed", "type": "image"}]
# @flowby-params: [
#   {"key": "inks", "label": "Inks", "type": "select", "default": "two",
#    "options": [{"label": "One", "value": "one"}, {"label": "Two", "value": "two"}]},
#   {"key": "shift", "label": "Shift", "type": "number", "default": 2, "min": 0, "max": 12,
#    "visibleIf": [{"key": "inks", "equals": "two"}]}
# ]
'''


class TheHeader(unittest.TestCase):
    def test_a_valid_header_becomes_an_action(self):
        got = actions.parse(header())
        self.assertEqual(got.name, "Halftone")
        self.assertEqual(got.inputs[0].dtype, "image")
        self.assertEqual(got.minutes, actions.MINUTES["python"])

    def test_floras_own_spelling_parses_unchanged(self):
        # a file written for flora carries @flora- and camelCase visibleIf; it should not need editing
        source = TWO_PARAM.replace("@flowby-", "@flora-")
        got = actions.parse(source)
        self.assertEqual([p.key for p in got.params], ["inks", "shift"])
        self.assertEqual(got.params[1].when, (("inks", "two"),))

    def test_a_params_list_may_run_over_several_comment_lines(self):
        got = actions.parse(TWO_PARAM)
        self.assertEqual(len(got.params), 2)

    def test_a_bare_word_is_a_value_and_does_not_swallow_the_next_line(self):
        # `@flowby-runtime: python` followed by another key: a collector that appended until it parsed
        # would take the next header with it, and the runtime would read as "python @flowby-inputs: …"
        got = actions.parse(header(runtime="python"))
        self.assertEqual(got.runtime, "python")

    def test_a_quoted_and_a_bare_name_agree(self):
        self.assertEqual(actions.parse(header(name="Halftone")).name, "Halftone")
        self.assertEqual(actions.parse(header(name='"Halftone"')).name, "Halftone")


class WhatIsRefused(unittest.TestCase):
    def refused(self, source, *words):
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.parse(source)
        for word in words:
            self.assertIn(word, str(caught.exception))

    def test_no_name(self):
        self.refused(header(name=None), "no @flowby-name")

    def test_an_unknown_header_key_is_named_rather_than_ignored(self):
        # a typo in `@flowby-descriptio` would otherwise leave an action with a blank blurb forever
        self.refused(header() + "# @flowby-descriptio: \"typo\"\n", "descriptio")

    def test_an_unknown_runtime(self):
        self.refused(header(runtime="ruby"), "ruby")

    def test_a_wire_flowby_does_not_have_is_named(self):
        self.refused(header(inputs='[{"name": "voice", "type": "audio"}]'), "audio", "wires")

    def test_a_wire_that_is_not_a_wire(self):
        self.refused(header(inputs='[{"name": "source", "type": "pdf"}]'), "pdf")

    def test_the_same_port_twice(self):
        self.refused(header(inputs='[{"name": "a", "type": "image"}, {"name": "a", "type": "image"}]'), "twice")

    def test_no_inputs_or_no_outputs(self):
        self.refused(header(inputs="[]"), "takes no inputs")
        self.refused(header(outputs="[]"), "returns nothing")

    def test_the_same_param_key_twice(self):
        self.refused(header(params='[{"key": "a"}, {"key": "a"}]'), "twice")

    def test_a_param_with_no_key(self):
        self.refused(header(params='[{"label": "Nameless"}]'), "no key")

    def test_a_default_outside_its_own_range(self):
        self.refused(header(params='[{"key": "a", "type": "number", "default": 40, "min": 0, "max": 10}]'),
                     "above its own")

    def test_a_select_with_nothing_to_choose(self):
        self.refused(header(params='[{"key": "a", "type": "select", "options": []}]'), "nothing to choose")

    def test_a_select_whose_default_is_not_offered(self):
        self.refused(header(params='[{"key": "a", "type": "select", "default": "x", '
                                   '"options": [{"value": "y"}]}]'), "does not offer")

    def test_visibility_pointing_at_a_param_that_does_not_exist(self):
        self.refused(header(params='[{"key": "a", "type": "number", "visibleIf": [{"key": "ghost", "equals": "x"}]}]'),
                     "ghost", "not a param")

    def test_visibility_pointing_at_a_value_that_never_happens(self):
        self.refused(header(params='[{"key": "a", "type": "select", "options": [{"value": "one"}]}, '
                                   '{"key": "b", "type": "number", "visibleIf": [{"key": "a", "equals": "two"}]}]'),
                     "never is")

    def test_visibility_controlled_by_a_number_is_refused(self):
        # "show this when that equals 3" is meaningless for a continuous slider, and a page would have
        # to reimplement the comparison to draw it
        self.refused(header(params='[{"key": "a", "type": "number", "min": 0, "max": 9}, '
                                   '{"key": "b", "type": "number", "visibleIf": [{"key": "a", "equals": "3"}]}]'),
                     "not a choice")

    def test_a_param_type_flowby_does_not_draw(self):
        self.refused(header(params='[{"key": "a", "type": "colourwheel"}]'), "colourwheel")


class TheControls(unittest.TestCase):
    def setUp(self):
        self.action = actions.parse(TWO_PARAM)

    def test_a_conditional_control_is_returned_but_marked_hidden(self):
        # returning only the visible ones would leave a page unable to draw the control when the choice
        # changes, and would make the page learn a rule that belongs to the action
        by_key = {c["name"]: c for c in self.action.controls({"inks": "one"})}
        self.assertFalse(by_key["shift"]["shown"])
        self.assertTrue({c["name"]: c for c in self.action.controls({"inks": "two"})}["shift"]["shown"])

    def test_every_control_says_what_it_would_be_saying(self):
        shift = {c["name"]: c for c in self.action.controls()}["shift"]
        self.assertEqual(shift["because"], {"inks": "two"})
        self.assertEqual((shift["low"], shift["high"]), (0.0, 12.0))
        self.assertEqual(shift["kind"], "number")

    def test_a_number_control_knows_its_position(self):
        shift = {c["name"]: c for c in self.action.controls()}["shift"]
        self.assertAlmostEqual(shift["where"], 2 / 12)
        self.assertAlmostEqual({c["name"]: c for c in self.action.controls({"shift": 6})}["shift"]["where"], 0.5)

    def test_a_choice_control_carries_labels_and_values(self):
        inks = {c["name"]: c for c in self.action.controls()}["inks"]
        self.assertEqual(inks["choices"], ["one", "two"])
        self.assertEqual(inks["choice_labels"], ["One", "Two"])
        self.assertEqual(inks["where"], 1.0)

    def test_an_override_that_is_out_of_range_is_refused_at_the_panel(self):
        for bad in ({"shift": 40}, {"shift": -1}, {"inks": "three"}, {"nonsense": 1}):
            with self.assertRaises(actions.ActionRefused, msg=str(bad)):
                self.action.controls(bad)

    def test_a_code_action_costs_nothing_and_says_why(self):
        estimate = self.action.estimate()
        self.assertEqual(estimate["cost_usd"], 0.0)
        self.assertEqual(estimate["gpu_minutes"], 0.0)
        self.assertIn("not a model", estimate["free_because"])


class Running(unittest.TestCase):
    def setUp(self):
        self.room = Path(tempfile.mkdtemp())
        self.source = self.room / "source.png"
        image = Image.new("L", (64, 64))
        pen = image.load()
        for y in range(64):
            for x in range(64):
                pen[x, y] = x * 4 % 256
        image.save(self.source)

    def write(self, source: str) -> str:
        path = self.room / "action.py"
        path.write_text(source)
        return str(path)

    def test_the_shipped_halftone_runs_and_keeps_its_geometry(self):
        action = actions.from_file("actions/halftone.py")
        got = action.run({"source": str(self.source)}, str(self.room / "out"), {"cell": 6})
        made = Image.open(got["dotted"])
        self.assertEqual(made.size, (64, 64))
        # a screen is not a copy: the picture must actually change
        self.assertNotEqual(made.convert("L").tobytes(), Image.open(self.source).tobytes())

    def test_the_shipped_risograph_runs_and_two_inks_differ_from_one(self):
        action = actions.from_file("actions/risograph.py")
        one = Image.open(action.run({"source": str(self.source)}, str(self.room / "one"),
                                    {"inks": "one"})["printed"]).convert("RGB")
        two = Image.open(action.run({"source": str(self.source)}, str(self.room / "two"),
                                    {"inks": "two", "misregistration": 4})["printed"]).convert("RGB")
        self.assertNotEqual(one.tobytes(), two.tobytes())
        # paper plus two inks and their overlap, not a photograph
        self.assertLessEqual(len(set(two.getcolors(4096) or [])), 8)

    def test_a_missing_input_is_refused_before_anything_runs(self):
        action = actions.from_file("actions/halftone.py")
        with self.assertRaises(actions.ActionRefused) as caught:
            action.run({}, str(self.room))
        self.assertIn("needs 'source'", str(caught.exception))

    def test_a_module_with_no_run_is_refused(self):
        path = self.write("# @flowby-name: \"Still\"\n# @flowby-inputs: [{\"name\": \"s\", \"type\": \"image\"}]\n"
                          "# @flowby-outputs: [{\"name\": \"o\", \"type\": \"image\"}]\nx = 1\n")
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.from_file(path).run({"s": str(self.source)}, str(self.room))
        self.assertIn("no run(", str(caught.exception))

    def test_an_undeclared_output_is_refused(self):
        # a page cannot wire a port the action never declared, so returning one is a bug in the action
        path = self.write("# @flowby-name: \"Extra\"\n# @flowby-inputs: [{\"name\": \"s\", \"type\": \"image\"}]\n"
                          "# @flowby-outputs: [{\"name\": \"o\", \"type\": \"image\"}]\n"
                          "def run(inputs, values, out_dir):\n    return {'o': inputs['s'], 'surprise': inputs['s']}\n")
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.from_file(path).run({"s": str(self.source)}, str(self.room))
        self.assertIn("surprise", str(caught.exception))

    def test_a_declared_output_that_was_never_written_is_refused(self):
        path = self.write("# @flowby-name: \"Liar\"\n# @flowby-inputs: [{\"name\": \"s\", \"type\": \"image\"}]\n"
                          "# @flowby-outputs: [{\"name\": \"o\", \"type\": \"image\"}]\n"
                          "def run(inputs, values, out_dir):\n    return {'o': '/nowhere/at/all.png'}\n")
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.from_file(path).run({"s": str(self.source)}, str(self.room))
        self.assertIn("nothing is there", str(caught.exception))

    def test_text_that_was_never_a_file_cannot_be_run(self):
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.parse(header()).run({"source": str(self.source)}, str(self.room))
        self.assertIn("not a file", str(caught.exception))


class TheShelf(unittest.TestCase):
    def test_the_repo_ships_a_shelf_of_runnable_actions(self):
        shelf = actions.shelf("actions")
        self.assertIn("Halftone", shelf)
        self.assertIn("Risograph", shelf)
        for name, action in shelf.items():
            self.assertTrue(action.means, f"{name} has no description to show in a list")
            self.assertEqual(action.estimate()["cost_usd"], 0.0)

    def test_two_files_claiming_one_name_are_refused_as_a_set(self):
        room = Path(tempfile.mkdtemp())
        for suffix in ("a", "b"):
            (room / f"{suffix}.py").write_text(header())
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.shelf(str(room))
        self.assertIn("declared twice", str(caught.exception))

    def test_a_missing_directory_is_not_an_empty_shelf_pretending_to_be_one(self):
        # Path.glob over a missing directory simply yields nothing, which would report "no actions"
        # for a typo in the path
        with self.assertRaises(actions.ActionRefused) as caught:
            actions.shelf(str(Path(tempfile.mkdtemp()) / "not-here"))
        self.assertIn("not a directory", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
