"""plug_test.py: connecting a gpu, against a real server that behaves (and misbehaves) like vllm.

the module's claim is that "up" can only come from an answer. so the tests stand up an actual
http server on loopback with vllm's documented endpoints (/health, /v1/models, /version) and a set
of ways for it to go wrong: a redirect, a 500, a huge body, the wrong shape, a token it wants, a
silence. nothing here mocks the network except dns, which is injected so a name can be made to
resolve to a private address without touching the machine's resolver.
"""

import json
import pathlib
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from flowby import plug as pl  # noqa: E402
from flowby.plug import Plug, PlugRefused, Plugs  # noqa: E402

PUBLIC = "45.32.10.20"       # a vultr-style address: genuinely global, unlike the RFC 5737 ranges
INTERNAL = "169.254.169.254"


class FakeVllm:
    """a model server on loopback. `mode` picks how it behaves; `seen` records what it was sent."""

    def __init__(self, mode="ok", token=None, models=("llama-3.1-8b",)):
        self.mode, self.token, self.models, self.seen = mode, token, list(models), []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", kind="application/json", extra=None):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                outer.seen.append({"path": self.path, "auth": self.headers.get("Authorization")})
                if outer.mode == "slow":
                    time.sleep(2.5)
                if outer.mode == "redirect":
                    return self._send(302, b"", extra={"Location": "http://169.254.169.254/latest/meta-data/"})
                if outer.token and self.headers.get("Authorization") != f"Bearer {outer.token}":
                    return self._send(401, b'{"error":"unauthorized"}')
                if outer.mode == "500":
                    return self._send(500, b'{"error":"engine dead"}')
                if outer.mode == "404":
                    return self._send(404, b"not found")
                if outer.mode == "huge":
                    return self._send(200, b"x" * (pl.MAX_BODY + 5000))
                if self.path == "/health":
                    return self._send(200, b"" if outer.mode != "html" else b"<html>hi</html>")
                if self.path == "/v1/models":
                    if outer.mode == "nomodels":
                        return self._send(200, json.dumps({"object": "list", "data": []}).encode())
                    if outer.mode == "badmodels":
                        return self._send(200, b'{"data": "not a list"}')
                    if outer.mode == "modelsdown":
                        return self._send(503, b"loading")
                    return self._send(200, json.dumps({"object": "list", "data": [{"id": m} for m in outer.models]}).encode())
                if self.path == "/version":
                    return self._send(200, b'{"version": "0.11.2"}')
                return self._send(404, b"")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.httpd.daemon_threads = True
        threading.Thread(target=lambda: self.httpd.serve_forever(poll_interval=0.02), daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown(); self.httpd.server_close()


def served(**kwargs):
    fake = FakeVllm(**kwargs)
    return fake


class Addresses(unittest.TestCase):
    def ok(self, url, **kw):
        return pl.parse_endpoint(url, **kw)

    def refused(self, url, fragment, **kw):
        with self.assertRaises(PlugRefused) as cm:
            pl.parse_endpoint(url, **kw)
        self.assertIn(fragment, str(cm.exception), url)

    def test_real_public_addresses_and_names_pass(self):
        self.assertEqual(self.ok(f"https://{PUBLIC}:8000"), f"https://{PUBLIC}:8000")
        self.assertEqual(self.ok("https://gpu.example.com"), "https://gpu.example.com")
        self.assertEqual(self.ok("https://gpu.example.com/"), "https://gpu.example.com")

    def test_an_ssh_tunnel_to_localhost_may_be_plain_http(self):
        for url in ("http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"):
            self.assertTrue(self.ok(url))

    def test_plain_http_over_the_internet_is_refused_because_it_sends_the_token_in_the_clear(self):
        self.refused(f"http://{PUBLIC}", "in the clear")
        self.refused("http://gpu.example.com", "in the clear")

    def test_the_cloud_metadata_address_and_private_ranges_are_refused(self):
        for bad in (INTERNAL, "10.0.0.5", "192.168.1.9", "172.16.0.4", "0.0.0.0", "100.64.0.1", "[fe80::1]", "224.0.0.1", "239.255.255.250"):
            self.refused(f"https://{bad}", "private network address")

    def test_a_private_address_is_allowed_only_when_the_owner_says_it_is_a_tunnel(self):
        self.assertEqual(self.ok("https://10.0.0.5:8000", tunnel=True), "https://10.0.0.5:8000")

    def test_the_documentation_ranges_are_not_public_and_are_refused(self):
        for bad in ("203.0.113.5", "198.51.100.7", "192.0.2.1"):
            self.refused(f"https://{bad}", "private network address")

    def test_credentials_in_the_address_are_refused(self):
        self.refused("https://user:secret@gpu.example.com", "do not put a password in the address")
        self.refused("https://token@gpu.example.com", "do not put a password in the address")

    def test_a_path_or_query_is_refused_and_flowby_adds_its_own(self):
        for url in ("https://gpu.example.com/v1", "https://gpu.example.com/health", "https://gpu.example.com/?a=1", "https://gpu.example.com/#x"):
            self.refused(url, "base address only")

    def test_other_schemes_and_missing_schemes_are_refused(self):
        self.refused("ftp://gpu.example.com", "ftp://")
        self.refused("file:///etc/passwd", "file://")
        self.refused("gpu.example.com:8000", "start the address with https://")
        self.refused("javascript://x", "javascript://")

    def test_empty_and_hostless_addresses_are_refused(self):
        self.refused("", "give the address")
        self.refused("   ", "give the address")
        self.refused("https://", "no host")

    def test_a_bad_port_is_refused(self):
        self.refused("https://gpu.example.com:99999", "not a number between 1 and 65535")
        self.refused("https://gpu.example.com:abc", "not a number")


class Names(unittest.TestCase):
    def test_a_name_that_resolves_to_a_private_address_is_refused_at_check_time(self):
        p = pl.make("p", "x", "other", "https://innocent.example")
        pl.check(p, resolver=lambda h, port: [(2, 1, 6, "", ("10.0.0.5", 0))], opener=_Boom())
        self.assertEqual(p.state, "down")
        self.assertIn("resolves to a private address (10.0.0.5)", p.detail)

    def test_a_name_that_resolves_to_the_metadata_address_is_refused_and_nothing_is_sent(self):
        boom = _Boom()
        p = pl.make("p", "x", "other", "https://rebind.example", token="s3cret")
        pl.check(p, resolver=lambda h, port: [(2, 1, 6, "", (INTERNAL, 0))], opener=boom)
        self.assertEqual(p.state, "down")
        self.assertEqual(boom.calls, 0, "a request, and the token with it, went out to the metadata address")

    def test_one_bad_answer_among_good_ones_refuses_the_name(self):
        both = [(2, 1, 6, "", (PUBLIC, 0)), (2, 1, 6, "", (INTERNAL, 0))]
        self.assertIn("resolves to a private", pl.resolves_public("rebind.example", False, lambda h, p: both))

    def test_a_tunnelled_name_may_resolve_privately(self):
        self.assertIsNone(pl.resolves_public("inside.example", True, lambda h, p: [(2, 1, 6, "", ("10.0.0.5", 0))]))

    def test_a_name_that_points_at_this_machine_is_treated_as_a_tunnel(self):
        self.assertIsNone(pl.resolves_public("me.example", False, lambda h, p: [(2, 1, 6, "", ("127.0.0.1", 0))]))

    def test_a_name_that_does_not_resolve_says_so(self):
        import socket
        def nope(h, p):
            raise socket.gaierror("Name or service not known")
        self.assertIn("does not resolve", pl.resolves_public("typo.example", False, nope))

    def test_a_public_name_passes(self):
        self.assertIsNone(pl.resolves_public("good.example", False, lambda h, p: [(2, 1, 6, "", (PUBLIC, 0))]))


class _Boom:
    """an opener that must never be called."""
    calls = 0

    def open(self, *a, **k):
        _Boom.calls += 1
        self.calls = _Boom.calls
        raise AssertionError("the network was touched")

    def __init__(self):
        _Boom.calls = 0
        self.calls = 0


class Checking(unittest.TestCase):
    def check_against(self, fake, token="", **kw):
        self.addCleanup(fake.close)
        p = pl.make("p", "my gpu", "vultr", fake.url, token=token)
        return pl.check(p, **kw), fake

    def test_a_healthy_server_is_up_and_lists_what_it_serves(self):
        p, fake = self.check_against(served(models=("llama-3.1-8b", "flux-dev")))
        self.assertEqual(p.state, "up")
        self.assertEqual(p.models, ["llama-3.1-8b", "flux-dev"])
        self.assertEqual(p.version, "0.11.2")
        self.assertIsNotNone(p.latency_ms)
        self.assertIn("serving llama-3.1-8b, flux-dev", p.detail)

    def test_it_asks_for_exactly_the_documented_endpoints_and_nothing_else(self):
        p, fake = self.check_against(served())
        self.assertEqual([s["path"] for s in fake.seen], ["/health", "/v1/models", "/version"])

    def test_a_plug_that_was_never_checked_is_not_up(self):
        self.assertEqual(pl.make("p", "x", "other", "https://gpu.example.com").state, "unchecked")

    def test_up_with_no_model_yet_says_so_instead_of_claiming_one(self):
        p, _ = self.check_against(served(mode="nomodels"))
        self.assertEqual((p.state, p.models), ("up", []))
        self.assertIn("not serving a model yet", p.detail)

    def test_a_models_list_of_the_wrong_shape_is_ignored_and_the_plug_stays_up_with_none(self):
        p, _ = self.check_against(served(mode="badmodels"))
        self.assertEqual((p.state, p.models), ("up", []))

    def test_a_model_list_that_errors_does_not_take_a_healthy_server_down(self):
        p, _ = self.check_against(served(mode="modelsdown"))
        self.assertEqual((p.state, p.models), ("up", []))

    def test_a_server_that_wants_a_token_and_gets_none_says_exactly_that(self):
        p, _ = self.check_against(served(token="s3cret"))
        self.assertEqual(p.state, "down")
        self.assertEqual(p.detail, "the server wants a token and none was given")

    def test_a_wrong_token_is_refused_with_its_own_sentence(self):
        p, _ = self.check_against(served(token="s3cret"), token="wrong")
        self.assertEqual(p.detail, "the server refused the token")

    def test_the_right_token_is_sent_as_a_bearer_and_works(self):
        p, fake = self.check_against(served(token="s3cret"), token="s3cret")
        self.assertEqual(p.state, "up")
        self.assertTrue(all(s["auth"] == "Bearer s3cret" for s in fake.seen))

    def test_no_token_means_no_authorization_header_at_all(self):
        p, fake = self.check_against(served())
        self.assertTrue(all(s["auth"] is None for s in fake.seen))

    def test_a_redirect_is_not_followed_and_the_token_never_reaches_the_other_host(self):
        p, fake = self.check_against(served(mode="redirect"), token="s3cret")
        self.assertEqual(p.state, "down")
        self.assertIn("redirected", p.detail)
        self.assertEqual(len(fake.seen), 1, "it followed the redirect")

    def test_a_500_is_down_and_says_it_may_be_loading(self):
        p, _ = self.check_against(served(mode="500"))
        self.assertEqual(p.state, "down")
        self.assertIn("may still be loading the model", p.detail)

    def test_a_404_says_it_is_not_a_model_server(self):
        p, _ = self.check_against(served(mode="404"))
        self.assertIn("there is no /health", p.detail)

    def test_a_huge_answer_is_refused_and_not_read_to_the_end(self):
        p, _ = self.check_against(served(mode="huge"))
        self.assertEqual(p.state, "down")
        self.assertIn("far more than a health check", p.detail)

    def test_silence_times_out_with_the_likely_causes(self):
        p, _ = self.check_against(served(mode="slow"), timeout=0.4)
        self.assertEqual(p.state, "down")
        self.assertIn("nothing answered in time", p.detail)

    def test_nothing_listening_says_the_model_server_is_not_running(self):
        import socket
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        p = pl.make("p", "x", "other", f"http://127.0.0.1:{port}")
        pl.check(p)
        self.assertEqual(p.state, "down")
        self.assertIn("nothing is listening on that port", p.detail)

    def test_a_server_that_goes_away_after_being_up_is_down_the_next_time_it_is_asked(self):
        fake = served(); p = pl.make("p", "x", "other", fake.url)
        self.assertEqual(pl.check(p).state, "up")
        fake.close()
        self.assertEqual(pl.check(p).state, "down")
        self.assertEqual((p.models, p.version), ([], None), "stale models survived a failed check")

    def test_checking_again_after_a_recovery_is_up_again(self):
        fake = served(mode="500"); self.addCleanup(fake.close)
        p = pl.make("p", "x", "other", fake.url)
        self.assertEqual(pl.check(p).state, "down")
        fake.mode = "ok"
        self.assertEqual(pl.check(p).state, "up")

    def test_a_check_records_when_it_ran(self):
        p, _ = self.check_against(served(), clock=lambda: 1234.5)
        self.assertEqual(p.checked_at, 1234.5)


class Bounds(unittest.TestCase):
    def test_a_hostile_answer_is_cut_off_at_the_cap_and_not_read_to_the_end(self):
        # the point is memory: a server that streams without end must cost us MAX_BODY, not all of it.
        # a stub response records how many bytes were asked for, which is the thing that matters.
        asked = []

        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n=-1):
                asked.append(n)
                return b"x" * (pl.MAX_BODY + 1 if n is None or n < 0 or n > pl.MAX_BODY else n)

        class Opener:
            def open(self, request, timeout=None): return Response()

        p = pl.make("p", "x", "other", "https://gpu.example.com")
        pl.check(p, opener=Opener(), resolver=lambda h, port: [(2, 1, 6, "", (PUBLIC, 0))])
        self.assertEqual(p.state, "down")
        self.assertTrue(asked and all(0 < n <= pl.MAX_BODY + 1 for n in asked), f"read was asked for {asked}: unbounded")


class Secrecy(unittest.TestCase):
    TOKEN = "tok_live_AbCdEf0123456789"

    def plug(self):
        return pl.make("p", "my gpu", "vultr", "https://gpu.example.com", token=self.TOKEN)

    def test_the_token_is_in_nothing_a_page_can_see(self):
        p = self.plug()
        for text in (json.dumps(p.as_dict()), repr(p), str(p.as_dict())):
            self.assertNotIn(self.TOKEN, text)
            self.assertNotIn("tok_live", text)
            self.assertNotIn("AbCdEf", text)

    def test_the_view_says_whether_a_token_is_held_and_nothing_about_its_shape(self):
        d = self.plug().as_dict()
        self.assertTrue(d["has_token"])
        self.assertFalse(pl.make("p", "x", "other", "https://gpu.example.com").as_dict()["has_token"])
        self.assertFalse(any("token" in k and k != "has_token" for k in d))

    def test_the_token_survives_a_failed_check_without_appearing_in_the_reason(self):
        p = self.plug()
        pl.check(p, resolver=lambda h, port: [(2, 1, 6, "", (PUBLIC, 0))], opener=_Failing())
        self.assertNotIn(self.TOKEN, p.detail)
        self.assertNotIn(self.TOKEN, json.dumps(p.as_dict()))

    def test_a_token_with_a_line_break_is_refused_because_it_could_inject_a_header(self):
        for bad in ("abc\r\nX-Evil: 1", "abc\ndef", "abc\x00def"):
            with self.assertRaises(PlugRefused):
                pl.make("p", "x", "other", "https://gpu.example.com", token=bad)

    def test_the_collection_listing_never_contains_a_token(self):
        plugs = Plugs(); plugs.add("a", "vultr", "https://gpu.example.com", token=self.TOKEN)
        self.assertNotIn("tok_live", json.dumps(plugs.all()))


class _Failing:
    def open(self, request, timeout=None):
        raise OSError(f"connection broke while sending {request.get_header('Authorization')}")


class Collection(unittest.TestCase):
    def test_add_get_remove(self):
        plugs = Plugs()
        p = plugs.add("vultr a100", "vultr", "https://gpu.example.com")
        self.assertEqual(plugs.get(p.id).label, "vultr a100")
        plugs.remove(p.id)
        with self.assertRaises(PlugRefused):
            plugs.get(p.id)
        with self.assertRaises(PlugRefused):
            plugs.remove(p.id)

    def test_the_same_address_twice_is_refused_by_name(self):
        plugs = Plugs(); plugs.add("first", "vultr", "https://gpu.example.com")
        with self.assertRaises(PlugRefused) as cm:
            plugs.add("second", "gcp", "https://gpu.example.com")
        self.assertIn("'first' is already plugged in", str(cm.exception))

    def test_an_unknown_provider_is_refused_and_the_choices_are_named(self):
        with self.assertRaises(PlugRefused) as cm:
            Plugs().add("x", "aws-ish", "https://gpu.example.com")
        for key in pl.PROVIDERS:
            self.assertIn(key, str(cm.exception))

    def test_a_blank_name_is_refused(self):
        with self.assertRaises(PlugRefused):
            Plugs().add("   ", "vultr", "https://gpu.example.com")

    def test_only_an_up_plug_that_lists_the_model_counts_as_serving_it(self):
        plugs = Plugs()
        a = plugs.add("a", "vultr", "https://a.example.com"); a.state, a.models = "up", ["flux-dev"]
        b = plugs.add("b", "gcp", "https://b.example.com"); b.state, b.models = "down", ["flux-dev"]
        c = plugs.add("c", "amd", "https://c.example.com"); c.state, c.models = "up", ["llama"]
        d = plugs.add("d", "other", "https://d.example.com")      # never checked
        self.assertEqual([p.id for p in plugs.serving("flux-dev")], [a.id])
        self.assertEqual(plugs.serving("nothing-serves-this"), [])

    def test_every_provider_has_a_label_and_a_note_that_says_something(self):
        self.assertEqual(set(pl.PROVIDERS), {"vultr", "gcp", "azure", "aws", "amd", "nvidia", "fal", "other"})
        for key, info in pl.PROVIDERS.items():
            self.assertGreater(len(info["note"]), 40, key)
        self.assertIn("ssh tunnel", pl.PROVIDERS["amd"]["note"])


class Vendors(unittest.TestCase):
    """the cloud gpus and the hosted vendor added after the first three."""

    def test_every_provider_declares_a_kind_and_only_two_kinds_exist(self):
        for key, info in pl.PROVIDERS.items():
            self.assertIn(info["kind"], (pl.SERVER, pl.HOSTED), key)

    def test_the_raw_gpu_clouds_are_servers_and_fal_is_hosted(self):
        for key in ("vultr", "gcp", "azure", "aws", "amd", "nvidia", "other"):
            self.assertEqual(pl.PROVIDERS[key]["kind"], pl.SERVER, key)
        self.assertEqual(pl.PROVIDERS["fal"]["kind"], pl.HOSTED)

    def test_a_new_cloud_is_added_like_the_old_ones_with_a_plain_address(self):
        for key in ("azure", "aws", "nvidia"):
            plug = Plugs().add("box", key, "https://gpu.example.com:8000")
            self.assertEqual(plug.endpoint, "https://gpu.example.com:8000", key)
            self.assertEqual(plug.as_dict()["kind"], "server")

    def test_a_hosted_endpoint_keeps_its_owner_and_app_path(self):
        plug = Plugs().add("flux", "fal", "https://queue.fal.run/fal-ai/flux/schnell/", "k")
        self.assertEqual(plug.endpoint, "https://queue.fal.run/fal-ai/flux/schnell")

    def test_a_hosted_endpoint_on_any_other_host_is_refused_so_the_key_goes_nowhere_else(self):
        for bad in ("https://queue.fal.run.evil.com/a/b", "https://evil.com/a/b", "https://fal.run/a/b",
                    "https://queue.fal.run@evil.com/a/b", "https://127.0.0.1/a/b"):
            with self.assertRaises(PlugRefused, msg=bad):
                Plugs().add("x", "fal", bad, "k")

    def test_a_hosted_endpoint_must_be_https_with_no_credentials_query_or_odd_port(self):
        for bad in ("http://queue.fal.run/a/b", "https://u:p@queue.fal.run/a/b", "https://queue.fal.run/a/b?x=1",
                    "https://queue.fal.run:8443/a/b", "https://queue.fal.run/a/b#frag"):
            with self.assertRaises(PlugRefused, msg=bad):
                Plugs().add("x", "fal", bad, "k")

    def test_a_hosted_endpoint_needs_an_owner_and_an_app_and_no_dot_segments(self):
        for bad in ("https://queue.fal.run", "https://queue.fal.run/", "https://queue.fal.run/only", "https://queue.fal.run/a/../b"):
            with self.assertRaises(PlugRefused, msg=bad):
                Plugs().add("x", "fal", bad, "k")

    def test_a_hosted_vendor_cannot_be_a_tunnel(self):
        with self.assertRaises(PlugRefused):
            Plugs().add("x", "fal", "https://queue.fal.run/a/b", "k", tunnel=True)

    def test_checking_a_hosted_plug_sends_nothing_and_never_says_up(self):
        plug = Plugs().add("flux", "fal", "https://queue.fal.run/fal-ai/flux/schnell", "SECRET")
        opener = _Boom()
        resolved = []
        pl.check(plug, opener=opener, resolver=lambda *a, **k: resolved.append(a) or [])
        self.assertEqual(plug.state, "unchecked")
        self.assertEqual(resolved, [], "no dns lookup either: nothing is asked")
        self.assertIn("no free ping", plug.detail)

    def test_a_hosted_plug_is_unchecked_from_the_moment_it_is_made_and_says_why(self):
        plug = Plugs().add("flux", "fal", "https://queue.fal.run/fal-ai/flux/schnell", "k")
        self.assertEqual(plug.state, "unchecked")
        self.assertIn("no free ping", plug.detail)

    def test_a_hosted_plug_never_counts_as_serving_a_model_it_was_not_shown_to_serve(self):
        plugs = Plugs()
        plug = plugs.add("flux", "fal", "https://queue.fal.run/fal-ai/flux/schnell", "k")
        pl.check(plug)
        self.assertEqual(plugs.serving("flux-dev"), [])

    def test_the_hosted_key_is_in_nothing_a_page_can_see(self):
        plugs = Plugs()
        plugs.add("flux", "fal", "https://queue.fal.run/fal-ai/flux/schnell", "FALKEY-123")
        self.assertNotIn("FALKEY-123", json.dumps(plugs.all()))
        self.assertNotIn("FALKEY-123", repr(plugs.get("plug-1")))

    def test_the_hosted_note_says_there_is_no_check(self):
        self.assertIn("no free ping", pl.PROVIDERS["fal"]["note"])
        self.assertIn("queue.fal.run", pl.PROVIDERS["fal"]["note"])


if __name__ == "__main__":
    unittest.main()
