"""runs_test: per-node history, and the two claims it has to earn.

claim one: a node does not run its upstream. claim two, which is the harder one: a node's history is
keyed on the runs it was fed, not on the parameters of the nodes feeding it, so a re-run upstream is
never silently skipped below. a test suite that only did the first would pass on a stale cache.
"""

import json
import os
import unittest

from flowby import cli, graph, runs


def board():
    return cli.demo_board().graph


def line(count=3):
    """a straight line of nodes with one input each: a, b, c."""
    g = graph.Graph()
    g.add(graph.Node(id="a", op="image.make", outputs={"out": graph.Port("image")}))
    for i in range(1, count):
        name = chr(ord("a") + i)
        prev = chr(ord("a") + i - 1)
        g.add(graph.Node(id=name, op="image.pass", inputs={"in": graph.Port("image")},
                         outputs={"out": graph.Port("image")}))
        g.add_edge(prev, "out", name, "in")
    return g


def fake_clock(start=100.0):
    ticks = {"now": start}

    def tick():
        ticks["now"] += 1.0
        return ticks["now"]
    return tick


class Signature(unittest.TestCase):
    def test_the_same_ask_has_the_same_signature_however_the_dict_is_ordered(self):
        node = graph.Node(id="n", op="image.make", params={"a": 1, "b": 2})
        self.assertEqual(runs.signature(node, {}), runs.signature(node, {}))

    def test_a_different_param_is_a_different_signature(self):
        one = graph.Node(id="n", op="image.make", params={"seed": 1})
        two = graph.Node(id="n", op="image.make", params={"seed": 2})
        self.assertNotEqual(runs.signature(one, {}), runs.signature(two, {}))

    def test_a_different_upstream_run_is_a_different_signature(self):
        # this is the whole design: the same params, fed by a different run, is not the same ask
        node = graph.Node(id="b", op="image.pass", inputs={"in": graph.Port("image")})
        self.assertNotEqual(runs.signature(node, {"in": "a#1"}), runs.signature(node, {"in": "a#2"}))

    def test_an_input_that_is_not_fed_is_part_of_the_key(self):
        node = graph.Node(id="b", op="image.pass", inputs={"in": graph.Port("image")})
        self.assertNotEqual(runs.signature(node, {"in": None}), runs.signature(node, {"in": "a#1"}))

    def test_a_port_the_node_does_not_have_is_refused(self):
        node = graph.Node(id="b", op="image.pass", inputs={"in": graph.Port("image")})
        with self.assertRaises(runs.RunsRefused):
            runs.signature(node, {"sideways": "a#1"})


class Book(unittest.TestCase):
    def setUp(self):
        self.book = runs.Book(clock=fake_clock())

    def test_a_history_keeps_the_newest_and_drops_the_oldest(self):
        for i in range(5):
            self.book.record("a", f"sig{i}")
        capped = runs.Book(clock=fake_clock(), keep=3)
        for i in range(5):
            capped.record("a", f"sig{i}")
        self.assertEqual(len(capped.runs_for("a")), 3)
        self.assertEqual(capped.runs_for("a")[-1].signature, "sig4")
        self.assertEqual(capped.runs_for("a")[0].signature, "sig2")

    def test_two_runs_of_the_same_ask_at_the_same_instant_are_still_two_runs(self):
        first = self.book.record("a", "sig", at=5.0)
        second = self.book.record("a", "sig", at=5.0)
        self.assertNotEqual(first.id, second.id)

    def test_a_failed_run_cannot_be_reused(self):
        self.book.record("a", "sig", state=runs.FAILED)
        self.assertIsNone(self.book.reuse("a", "sig"))

    def test_a_failed_run_does_not_hide_the_success_before_it(self):
        ok = self.book.record("a", "sig")
        self.book.record("a", "sig", state=runs.FAILED)
        self.assertEqual(self.book.last_ok("a").id, ok.id)
        self.assertEqual(self.book.reuse("a", "sig").id, ok.id)
        self.assertEqual(self.book.latest("a").state, runs.FAILED)

    def test_a_reused_run_is_the_newest_match(self):
        self.book.record("a", "sig")
        newest = self.book.record("a", "sig")
        self.assertEqual(self.book.reuse("a", "sig").id, newest.id)

    def test_forgetting_a_node_takes_its_history_with_it(self):
        self.book.record("a", "sig")
        self.book.forget("a")
        self.assertIsNone(self.book.latest("a"))

    def test_a_state_that_is_not_a_state_is_refused(self):
        with self.assertRaises(runs.RunsRefused):
            self.book.record("a", "sig", state="probably")


class Work(unittest.TestCase):
    def setUp(self):
        self.book = runs.Book(clock=fake_clock())

    def run_all(self, g):
        """perform the board the way an executor would, upstream first."""
        for node_id in g.topo():
            fed = {}
            from flowby import runs as r
            for port, source in r.upstream_of(g, node_id).items():
                run = self.book.last_ok(source)
                fed[port] = run.id if run else None
            self.book.record(node_id, r.signature(g.nodes[node_id], fed))

    def test_a_board_that_has_never_run_executes_every_node(self):
        g = line()
        work = runs.work(g, self.book)
        self.assertEqual(work["run"], ["a", "b", "c"])
        self.assertEqual(work["reuse"], [])

    def test_a_board_that_has_run_executes_nothing(self):
        g = line()
        self.run_all(g)
        work = runs.work(g, self.book)
        self.assertEqual(work["run"], [])
        self.assertEqual(work["reuse"], ["a", "b", "c"])
        self.assertEqual(work["minutes"], 0)

    def test_a_changed_parameter_reruns_that_node_and_the_ones_below_it(self):
        g = line()
        self.run_all(g)
        g.nodes["b"].params["amount"] = 0.9
        work = runs.work(g, self.book)
        self.assertEqual(work["run"], ["b", "c"])
        self.assertEqual(work["reuse"], ["a"])

    def test_a_new_upstream_run_reruns_the_node_below_even_with_identical_params(self):
        # the failure a params-only key would hide: a is asked for the same thing, hands back a
        # different sample, and b stands on the old one
        g = line()
        self.run_all(g)
        a_sig = runs.signature(g.nodes["a"], {})
        self.book.record("a", a_sig)  # a second run of the same ask
        work = runs.work(g, self.book)
        # a stands on its newest run, which is a real run of exactly this ask; everything below it
        # was fed the previous one and cannot stand on it
        self.assertEqual(work["reuse"], ["a"])
        self.assertEqual(work["run"], ["b", "c"])

    def test_the_signature_reported_for_a_pending_node_is_not_the_one_it_wore_before(self):
        # a signature is what a node was asked for. while an input is pending there is no real run
        # behind it, and a key that pretended otherwise would read as "same ask, already done"
        g = line()
        self.run_all(g)
        worn = runs.signature(g.nodes["b"], {"in": self.book.last_ok("a").id})
        g.nodes["a"].params["gain"] = 0.5
        work = runs.work(g, self.book, targets=["b"])
        self.assertNotEqual(work["detail"]["b"]["signature"], worn)

    def test_running_one_node_does_not_run_its_siblings(self):
        g = line()
        g.add(graph.Node(id="twin", op="image.make", outputs={"out": graph.Port("image")}))
        self.run_all(g)
        g.nodes["twin"].params["seed"] = 7
        work = runs.work(g, self.book, targets=["a"])
        self.assertEqual(work["run"], [])
        self.assertNotIn("twin", work["order"])

    def test_running_the_last_node_reuses_what_came_before_it(self):
        g = line()
        self.run_all(g)
        work = runs.work(g, self.book, targets=["c"])
        self.assertEqual(work["run"], [])
        self.assertEqual(work["reuse"], ["a", "b", "c"])

    def test_a_target_that_is_not_on_the_board_is_refused(self):
        with self.assertRaises(runs.RunsRefused):
            runs.work(line(), self.book, targets=["nowhere"])

    def test_a_node_whose_upstream_never_ran_says_why_it_must_run(self):
        g = line()
        self.book.record("b", runs.signature(g.nodes["b"], {"in": None}))
        work = runs.work(g, self.book, targets=["b"])
        self.assertEqual(work["run"][0] if work["run"] else None, "a")
        self.assertIn("b", work["detail"])

    def test_the_estimate_counts_only_what_would_run(self):
        g = line()
        self.run_all(g)
        g.nodes["b"].params["amount"] = 0.5
        work = runs.work(g, self.book)
        self.assertAlmostEqual(work["minutes"], round(g.nodes["b"].minutes() + g.nodes["c"].minutes(), 2))


class Element_view(unittest.TestCase):
    def test_a_panel_gets_newest_first_and_knows_what_is_stale(self):
        g = line()
        book = runs.Book(clock=fake_clock())
        for node_id in g.topo():
            book.record(node_id, runs.signature(g.nodes[node_id], {"in": None} if node_id != "a" else {}))
        view = runs.element_runs(g, book, ["a", "b"])
        self.assertEqual(view["a"]["count"], 1)
        self.assertEqual(view["a"]["runs"][0]["node"], "a")
        self.assertFalse(view["a"]["stale"])
        # b was recorded against an unfed input, so what it is now asked for has never run
        self.assertTrue(view["b"]["stale"])

    def test_a_node_that_left_the_board_is_skipped_rather_than_crashing_the_panel(self):
        g = line()
        view = runs.element_runs(g, runs.Book(), ["a", "gone"])
        self.assertNotIn("gone", view)


class Through_the_session(unittest.TestCase):
    """the history as the page and the cli reach it: through the one door that copies the board."""

    def setUp(self):
        import tempfile
        from flowby import session, store
        self.session = session.Session(store.Store(tempfile.mkdtemp()), cli.demo_board())
        self.element = next(iter(self.session.scene.elements))

    def test_a_run_is_filed_against_what_the_node_is_asked_for_now(self):
        node = self.session.scene.graph.topo()[0]
        filed = self.session.record_run(node, minutes=1.5)
        self.assertEqual(filed["run"]["node"], node)
        self.assertEqual(self.session.history()["stale"].count(node), 0)

    def test_changing_a_param_makes_the_nodes_below_it_stale_again(self):
        before = self.session.work()
        node = before["run"][0]
        self.session.record_run(node)
        # the node itself now stands on a run, but nothing below it does
        after = self.session.work()
        self.assertIn(node, after["reuse"])
        self.assertNotIn(node, after["run"])

    def test_a_run_against_a_node_that_is_not_on_the_board_is_refused(self):
        from flowby.scene import SceneRefused
        with self.assertRaises(Exception):
            self.session.record_run("not-a-node")

    def test_an_element_history_names_the_nodes_it_was_built_from(self):
        held = self.session.history(self.element)
        self.assertTrue(held["nodes"])
        for entry in held["nodes"].values():
            self.assertEqual(entry["count"], 0)
            self.assertTrue(entry["stale"])

    def test_the_panel_carries_the_history_even_when_it_is_empty(self):
        panel = self.session.sidebar(self.element)
        self.assertIn("runs", panel)
        self.assertTrue(all(entry["count"] == 0 for entry in panel["runs"].values()))

    def test_a_panel_built_with_no_book_says_so_by_being_empty(self):
        # the field is present and empty rather than missing, so a page never has to guess
        payload = self.session.scene.sidebar(self.element)
        self.assertEqual(payload["runs"], {})

    def test_undo_does_not_un_happen_a_run(self):
        # undo reverts the board. a run that happened is a fact about the past, and the history keeps
        # it, which is why the book lives beside the scene and not inside it.
        node = self.session.scene.graph.topo()[0]
        self.session.record_run(node, minutes=2.0)
        before = len(self.session.scene.graph.nodes)
        self.session.apply_preset(self.element, "sketch-to-mesh", {})
        self.session.undo()
        self.assertEqual(len(self.session.scene.graph.nodes), before)
        self.assertEqual(self.session.history()["nodes"][node][0]["minutes"], 2.0)


class The_book_on_disk(unittest.TestCase):
    """a history that outlives the process, and refuses to be read when it does not hold up."""

    def setUp(self):
        import tempfile
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "runs.json")
        self.graph = cli.demo_board().graph

    def _filed(self):
        from flowby import runs
        book = runs.Book(clock=lambda: 10.0)
        for node_id in self.graph.topo():
            fed = {port: (book.last_ok(source).id if book.last_ok(source) else None)
                   for port, source in runs.upstream_of(self.graph, node_id).items()}
            book.record(node_id, runs.signature(self.graph.nodes[node_id], fed),
                        minutes=self.graph.nodes[node_id].minutes())
        return book

    def test_a_saved_book_answers_the_next_process_the_same(self):
        from flowby import runs
        filed = self._filed()
        filed.save(self.path)
        back = runs.Book.load(self.path)
        self.assertEqual(runs.stale(self.graph, back), runs.stale(self.graph, filed))
        self.assertEqual(runs.work(self.graph, back)["minutes"], runs.work(self.graph, filed)["minutes"])
        self.assertEqual(sum(len(v) for v in back.runs.values()), len(self.graph.nodes))

    def test_a_run_kept_across_processes_is_not_run_again(self):
        from flowby import runs
        filed = self._filed()
        filed.save(self.path)
        again = runs.work(self.graph, runs.Book.load(self.path))
        self.assertEqual(again["run"], [])

    def test_a_half_written_file_is_refused_rather_than_trusted(self):
        from flowby import runs
        with open(self.path, "w", encoding="utf-8") as out:
            out.write('{"kind": "flowby.runs", "version": 1, "runs": {"a": [')
        with self.assertRaises(runs.RunsRefused):
            runs.Book.load(self.path)

    def test_a_file_that_is_not_a_book_is_refused(self):
        from flowby import runs
        with open(self.path, "w", encoding="utf-8") as out:
            out.write('{"nodes": []}')
        with self.assertRaises(runs.RunsRefused) as caught:
            runs.Book.load(self.path)
        # refused for the right reason: a file that never said it was a run history, not one with a
        # version this flowby happens not to read
        self.assertIn("not a run history", str(caught.exception))

    def test_a_signature_that_is_not_a_sha256_is_refused(self):
        from flowby import runs
        with open(self.path, "w", encoding="utf-8") as out:
            out.write(json.dumps({"kind": "flowby.runs", "version": 1,
                                  "runs": {"a": [{"id": "a#1", "signature": "nope"}]}}))
        with self.assertRaises(runs.RunsRefused) as caught:
            runs.Book.load(self.path)
        self.assertIn("sha256", str(caught.exception))

    def test_a_book_from_a_future_version_is_refused_in_one_sentence(self):
        from flowby import runs
        with open(self.path, "w", encoding="utf-8") as out:
            out.write(json.dumps({"kind": "flowby.runs", "version": 99, "runs": {}}))
        with self.assertRaises(runs.RunsRefused) as caught:
            runs.Book.load(self.path)
        self.assertIn("99", str(caught.exception))

    def test_saving_leaves_no_temporary_file_behind(self):
        self._filed().save(self.path)
        self.assertEqual(sorted(os.listdir(self.folder)), ["runs.json"])

    def test_the_cap_survives_a_round_trip(self):
        from flowby import runs
        book = runs.Book(clock=lambda: 1.0, keep=2)
        for _ in range(5):
            book.record("a", "0" * 64)
        book.save(self.path)
        self.assertEqual(len(runs.Book.load(self.path).runs["a"]), 2)


if __name__ == "__main__":
    unittest.main()
