"""kohya_test: the plan becomes a dataset, a config and a command, and nothing is assumed.

the flags under test are the ones illustrace's first live run on a free colab T4 needed, and each was
learned from a failure: --lowram from a silent OOM-kill, --fp8_base from a 16GB card and a 12B unet,
--save_state from a session that dies mid-run. a test that only counted flags would pass on a command
that cannot finish, so these check the reason each flag is there.
"""

import contextlib
import io
import json
import os
import tomllib
import unittest

from flowby import kohya, styles


def corpus(n=12, trigger="mzqtlv"):
    subjects = ("a harbour", "a bridge", "a garden", "a market")
    return tuple(
        styles.Item(name=f"img_{i:02d}.png",
                    caption=f"{trigger}, a view of {subjects[i % len(subjects)]} number {i}",
                    subject=subjects[i % len(subjects)])
        for i in range(n)
    )


def a_style(**over):
    base = dict(id="s1", label="harbour wash", trigger="mzqtlv", base="flux-dev", items=corpus())
    base.update(over)
    return styles.Style(**base)


def gated(**over):
    return styles.advance(a_style(**over), "gated")


class Captions(unittest.TestCase):
    def test_a_caption_that_does_not_start_with_the_trigger_gets_it(self):
        items = list(corpus())
        items[3] = styles.Item(name=items[3].name, caption="a view of a harbour")
        rows = kohya.captions(a_style(items=tuple(items)))
        self.assertTrue(rows[3]["caption"].startswith("mzqtlv, "))

    def test_a_caption_that_already_starts_with_it_is_not_doubled(self):
        rows = kohya.captions(a_style())
        self.assertFalse(rows[0]["caption"].startswith("mzqtlv, mzqtlv"))

    def test_an_empty_corpus_is_refused_rather_than_trained_on(self):
        with self.assertRaises(kohya.KohyaRefused):
            kohya.captions(a_style(items=()))

    def test_an_image_with_no_caption_is_named(self):
        items = list(corpus())
        items[5] = styles.Item(name=items[5].name, caption="   ")
        with self.assertRaises(kohya.KohyaRefused) as caught:
            kohya.captions(a_style(items=tuple(items)))
        self.assertIn(items[5].name, str(caught.exception))


class Config(unittest.TestCase):
    def test_the_toml_parses_and_points_at_this_layout(self):
        layout = kohya.Layout(root="/content/drive/MyDrive/x")
        cfg = tomllib.loads(kohya.dataset_toml(a_style(), layout, repeats=3))
        self.assertTrue(cfg["general"]["shuffle_caption"])
        subset = cfg["datasets"][0]["subsets"][0]
        self.assertEqual(subset["image_dir"], "/content/drive/MyDrive/x/dataset")
        self.assertEqual(subset["metadata_file"], "/content/drive/MyDrive/x/dataset/metadata.jsonl")
        self.assertEqual(subset["num_repeats"], 3)

    def test_buckets_are_on_because_a_corpus_is_not_one_shape(self):
        cfg = tomllib.loads(kohya.dataset_toml(a_style(), kohya.Layout()))
        self.assertTrue(cfg["datasets"][0]["enable_bucket"])
        self.assertLessEqual(cfg["datasets"][0]["max_bucket_reso"], 1024)

    def test_caption_dropout_is_on_so_the_trigger_is_not_the_only_thing_learned(self):
        cfg = tomllib.loads(kohya.dataset_toml(a_style(), kohya.Layout()))
        self.assertGreater(cfg["datasets"][0]["caption_dropout_rate"], 0)


class Command(unittest.TestCase):
    def setUp(self):
        self.style = gated()
        self.plan = styles.training_plan(self.style)
        self.layout = kohya.Layout()
        self.argv = kohya.argv(self.style, self.plan, self.layout)

    def flag(self, name):
        at = self.argv.index(name)
        return self.argv[at + 1]

    def test_the_numbers_come_from_the_plan_and_not_from_a_default(self):
        params = self.plan["steps"][0]["params"]
        self.assertEqual(self.flag("--network_dim"), str(params["dim"]))
        self.assertEqual(self.flag("--network_alpha"), str(params["alpha"]))
        self.assertEqual(self.flag("--learning_rate"), str(params["lr"]))
        self.assertEqual(self.flag("--max_train_epochs"), str(params["epochs"]))

    def test_a_free_t4_needs_lowram_or_flux_dies_without_a_traceback(self):
        self.assertIn("--lowram", self.argv)
        self.assertEqual(self.flag("--blocks_to_swap"), "8")

    def test_a_16gb_card_needs_fp8_weights_and_fp16_state(self):
        self.assertIn("--fp8_base", self.argv)
        self.assertEqual(self.flag("--mixed_precision"), "fp16")

    def test_the_run_can_resume_because_a_free_session_will_be_cut(self):
        self.assertIn("--save_state", self.argv)
        resumed = kohya.argv(self.style, self.plan, self.layout, resume="/out/s1-000002-state")
        self.assertEqual(resumed[-2:], ["--resume", "/out/s1-000002-state"])

    def test_the_flux_flow_shift_matches_the_one_that_was_run(self):
        self.assertEqual(self.flag("--timestep_sampling"), "shift")
        self.assertEqual(self.flag("--discrete_flow_shift"), "3.1582")
        self.assertEqual(self.flag("--model_prediction_type"), "raw")

    def test_a_plan_that_asks_for_a_different_rank_gets_it(self):
        # every plan flowby builds today says dim 16, so "reads the plan" and "hardcodes 16" look
        # identical unless a plan asks for something else
        odd = {"kind": "style.train", "style": "s1",
               "steps": [{"params": {"dim": 32, "alpha": 16, "lr": 2e-4, "epochs": 4, "save_every_epochs": 1}}]}
        argv = kohya.argv(self.style, odd, self.layout)
        at = lambda name: argv[argv.index(name) + 1]
        self.assertEqual(at("--network_dim"), "32")
        self.assertEqual(at("--learning_rate"), "0.0002")
        self.assertEqual(at("--max_train_epochs"), "4")
        self.assertEqual(at("--save_every_n_epochs"), "1")

    def test_a_base_with_no_proven_argv_is_refused_rather_than_guessed(self):
        with self.assertRaises(kohya.KohyaRefused):
            kohya.argv(self.style, self.plan, self.layout, base="sdxl")

    def test_a_plan_that_is_not_a_training_plan_is_refused(self):
        with self.assertRaises(kohya.KohyaRefused):
            kohya.argv(self.style, {"kind": "style.probe"}, self.layout)


class Run(unittest.TestCase):
    def test_a_run_writes_the_three_files_and_counts_its_images(self):
        style = gated(items=corpus(16))
        payload = kohya.run(style)
        self.assertEqual(payload["files"], ["dataset.toml", "metadata.jsonl", "run.sh"])
        self.assertEqual(payload["images"], 16)
        lines = payload["writes"]["metadata.jsonl"].strip().splitlines()
        self.assertEqual(len(lines), 16)
        for line in lines:
            row = json.loads(line)
            self.assertTrue(row["caption"].startswith(style.trigger), row)

    def test_the_session_script_downloads_the_weights_once_and_checks_the_dataset(self):
        script = kohya.run(gated())["writes"]["run.sh"]
        self.assertIn("huggingface-cli download black-forest-labs/FLUX.1-dev", script)
        self.assertIn("--local-dir /content/drive/MyDrive/flowby/weights", script)
        self.assertIn("test -f /content/drive/MyDrive/flowby/dataset/metadata.jsonl", script)
        # the weights are skipped when they are already on the drive, because a free session is short
        self.assertIn("[ ! -f /content/drive/MyDrive/flowby/weights/flux1-dev.safetensors ]", script)

    def test_the_gates_are_named_in_the_script_and_never_read_by_it(self):
        payload = kohya.run(gated())
        script = payload["writes"]["run.sh"]
        for gate in ("GOOGLE_SESSION_COOKIES", "COLAB_NOTEBOOK_ID"):
            self.assertIn(gate, script)
        self.assertNotIn("COOKIES=", script, "the script must not try to set a credential")

    def test_a_style_that_is_not_gated_has_no_plan_and_so_no_run(self):
        with self.assertRaises(styles.StyleRefused):
            kohya.run(a_style())


class Command_line(unittest.TestCase):
    """the crossing as the owner reaches it: `flowby kohya style.json --write dir`."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.style_path = os.path.join(self.dir, "style.json")
        with open(self.style_path, "w", encoding="utf-8") as handle:
            json.dump({"id": "s1", "label": "harbour wash", "trigger": "mzqtlv", "base": "flux-dev",
                       "items": [{"name": item.name, "caption": item.caption, "subject": item.subject}
                                 for item in corpus()]}, handle)

    def run_cli(self, *extra, as_json=False):
        from flowby import cli
        parser = cli.build_parser()
        # --json is the program's flag, not the subcommand's, which is why it goes first
        args = parser.parse_args([*(["--json"] if as_json else []), "kohya", self.style_path, *extra])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = args.func(args)
        return code, buffer.getvalue()

    def test_it_writes_the_three_files_a_colab_run_needs(self):
        out = os.path.join(self.dir, "run")
        code, text = self.run_cli("--write", out)
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(os.listdir(out)), ["dataset.toml", "metadata.jsonl", "run.sh"])
        with open(os.path.join(out, "run.sh"), encoding="utf-8") as handle:
            self.assertIn("--lowram", handle.read())

    def test_the_json_payload_carries_the_command_and_the_files(self):
        code, text = self.run_cli(as_json=True)
        self.assertEqual(code, 0, text)
        payload = json.loads(text)
        self.assertEqual(payload["kind"], "style.kohya")
        self.assertEqual(payload["files"], ["dataset.toml", "metadata.jsonl", "run.sh"])
        self.assertTrue(any(a.endswith("flux_train_network.py") for a in payload["argv"]), payload["argv"])

    def test_a_thin_corpus_is_refused_with_the_gates_own_reason(self):
        with open(self.style_path, "w", encoding="utf-8") as handle:
            json.dump({"id": "s2", "trigger": "mzqtlv", "base": "flux-dev",
                       "items": [{"name": f"x{i}.png", "caption": "mzqtlv, a photo"} for i in range(5)]}, handle)
        code, text = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("below 10", text)


if __name__ == "__main__":
    unittest.main()
