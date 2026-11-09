"""store_test.py: bytes by digest.

the store's promises are the module's docstring, and each one is attacked here: a name that lies
about its contents, a path that climbs out, a file that rots on disk, two writers of one file, and a
crash halfway through a write. none of these are exotic. a content-addressed store is only worth
having if every one of them is refused.
"""

import os
import pathlib
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from flowby import store as storemod  # noqa: E402
from flowby.store import Store, StoreRefused, digest_of  # noqa: E402


def fresh():
    return Store(tempfile.mkdtemp())


class Putting(unittest.TestCase):
    def test_a_stored_file_comes_back_byte_for_byte_under_its_own_digest(self):
        s = fresh()
        d = s.put(b"an owl")
        self.assertEqual(d, digest_of(b"an owl"))
        self.assertEqual(s.get(d), b"an owl")

    def test_the_digest_is_a_real_sha256_of_the_bytes(self):
        import hashlib
        self.assertEqual(fresh().put(b"abc"), "sha256:" + hashlib.sha256(b"abc").hexdigest())

    def test_the_same_file_twice_is_one_file(self):
        s = fresh()
        a, b = s.put(b"same"), s.put(b"same")
        self.assertEqual(a, b)
        self.assertEqual(s.count(), 1)

    def test_different_files_are_different_files(self):
        s = fresh()
        self.assertNotEqual(s.put(b"one"), s.put(b"two"))
        self.assertEqual(s.count(), 2)

    def test_bytes_sent_under_the_wrong_digest_are_refused_and_nothing_is_written(self):
        s = fresh()
        with self.assertRaises(StoreRefused) as cm:
            s.put(b"real", expect=digest_of(b"something else"))
        self.assertIn("hash to", str(cm.exception))
        self.assertEqual(s.count(), 0)

    def test_the_right_expected_digest_is_accepted(self):
        s = fresh()
        self.assertEqual(s.put(b"real", expect=digest_of(b"real")), digest_of(b"real"))

    def test_an_empty_file_is_not_an_asset(self):
        with self.assertRaises(StoreRefused):
            fresh().put(b"")

    def test_a_file_over_the_limit_is_refused_with_its_size(self):
        with self.assertRaises(StoreRefused) as cm:
            fresh().put(b"\0" * (storemod.MAX_BYTES + 1))
        self.assertIn("25 MB limit", str(cm.exception))

    def test_a_file_exactly_at_the_limit_is_taken(self):
        s = fresh()
        self.assertTrue(s.has(s.put(os.urandom(1024) * (storemod.MAX_BYTES // 1024))))

    def test_only_bytes_can_be_stored(self):
        for bad in ("text", 5, None, ["a"]):
            with self.assertRaises(StoreRefused):
                fresh().put(bad)

    def test_the_limit_matches_the_one_the_browser_enforces(self):
        src = (pathlib.Path(__file__).resolve().parents[1] / "web" / "src" / "intake.mjs").read_text()
        self.assertIn(f"MAX_BYTES = {storemod.MAX_BYTES // 1048576} * 1024 * 1024", src)


class Names(unittest.TestCase):
    def test_only_a_sha256_digest_names_a_file(self):
        s = fresh()
        for bad in ["", "sha256:", "sha256:abc", "md5:" + "a" * 32, "a" * 64, "sha256:" + "A" * 64,
                    "sha256:" + "g" * 64, "sha256:" + "a" * 63, "sha256:" + "a" * 65]:
            with self.assertRaises(StoreRefused, msg=repr(bad)):
                s.get(bad)

    def test_a_path_that_climbs_out_never_reaches_the_disk(self):
        s = fresh()
        outside = pathlib.Path(tempfile.mkdtemp()) / "secret"
        outside.write_bytes(b"do not serve")
        for bad in ["../" * 6 + str(outside), "sha256:../../etc/passwd", "sha256:" + "a" * 60 + "/..", str(outside),
                    "sha256:" + "a" * 64 + "/../../x", "sha256:" + "a" * 64 + "\0"]:
            with self.assertRaises(StoreRefused, msg=repr(bad)):
                s.get(bad)

    def test_has_never_raises_it_just_says_no(self):
        s = fresh()
        for bad in ["", None, "../x", 5, "sha256:zz"]:
            self.assertFalse(s.has(bad))
        self.assertFalse(s.has("sha256:" + "a" * 64))

    def test_an_absent_digest_is_refused_by_name_and_not_a_traceback(self):
        with self.assertRaises(StoreRefused) as cm:
            fresh().get("sha256:" + "a" * 64)
        self.assertIn("is not in the store", str(cm.exception))

    def test_files_are_spread_across_directories_by_their_digest(self):
        s = fresh()
        d = s.put(b"fan out")
        hexed = d.split(":")[1]
        self.assertTrue((s.root / hexed[:2] / hexed[2:4] / hexed).is_file())


class Trust(unittest.TestCase):
    def test_a_file_edited_on_disk_is_refused_and_not_served(self):
        s = fresh()
        d = s.put(b"original")
        hexed = d.split(":")[1]
        (s.root / hexed[:2] / hexed[2:4] / hexed).write_bytes(b"tampered")
        with self.assertRaises(StoreRefused) as cm:
            s.get(d)
        self.assertIn("no longer hash to it", str(cm.exception))

    def test_a_truncated_file_is_refused(self):
        s = fresh()
        d = s.put(b"a long enough body to cut short")
        hexed = d.split(":")[1]
        p = s.root / hexed[:2] / hexed[2:4] / hexed
        p.write_bytes(p.read_bytes()[:5])
        with self.assertRaises(StoreRefused):
            s.get(d)

    def test_verify_names_exactly_the_rotten_files(self):
        s = fresh()
        good, bad = s.put(b"good"), s.put(b"bad")
        hexed = bad.split(":")[1]
        (s.root / hexed[:2] / hexed[2:4] / hexed).write_bytes(b"rot")
        self.assertEqual(s.verify(), [bad])
        self.assertNotIn(good, s.verify())

    def test_a_healthy_store_verifies_clean(self):
        s = fresh()
        for i in range(5):
            s.put(f"file {i}".encode())
        self.assertEqual(s.verify(), [])


class Writing(unittest.TestCase):
    def test_a_crash_mid_write_leaves_no_file_under_the_final_name(self):
        s = fresh()
        real = os.replace
        def boom(*a, **k):
            raise OSError("disk went away")
        os.replace = boom
        try:
            with self.assertRaises(OSError):
                s.put(b"half written")
        finally:
            os.replace = real
        self.assertFalse(s.has(digest_of(b"half written")))
        self.assertEqual([p for p in s.root.rglob(".part-*")], [], "the temp file is cleaned up")

    def test_a_second_put_after_a_crash_succeeds(self):
        s = fresh()
        real = os.replace
        os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
        try:
            with self.assertRaises(OSError):
                s.put(b"retry me")
        finally:
            os.replace = real
        self.assertEqual(s.get(s.put(b"retry me")), b"retry me")

    def test_two_threads_writing_the_same_bytes_leave_one_intact_file(self):
        s = fresh()
        body = os.urandom(200_000)
        results = []
        def go():
            results.append(s.put(body))
        threads = [threading.Thread(target=go) for _ in range(12)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(s.get(results[0]), body)
        self.assertEqual(s.count(), 1)
        self.assertEqual(s.verify(), [])

    def test_a_partial_file_left_by_a_dead_writer_is_not_counted_or_served(self):
        s = fresh()
        d = s.put(b"real one")
        hexed = d.split(":")[1]
        (s.root / hexed[:2] / hexed[2:4] / ".part-dead").write_bytes(b"junk")
        self.assertEqual(s.count(), 1)
        self.assertEqual(s.verify(), [])

    def test_size_reports_the_bytes_on_disk(self):
        s = fresh()
        self.assertEqual(s.size(s.put(b"12345")), 5)
        with self.assertRaises(StoreRefused):
            s.size("sha256:" + "b" * 64)

    def test_a_store_can_be_reopened_and_still_has_its_files(self):
        root = tempfile.mkdtemp()
        d = Store(root).put(b"persists")
        self.assertEqual(Store(root).get(d), b"persists")


if __name__ == "__main__":
    unittest.main()
