"""server_test.py: the http surface, over a real socket.

the session and the store carry the rules; the server's job is to be strict about who is asking and
how. so these tests use a real ThreadingHTTPServer on a free port and real http requests, because a
claim like "a page in another tab cannot post to the board" is only true if a request that looks
like one is actually refused.
"""

import http.client
import json
import pathlib
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from flowby import server as srv  # noqa: E402
from flowby.session import Session  # noqa: E402
from flowby.store import Store, MAX_BYTES, digest_of  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010100c9fe92ef0000000049454e44ae426082")


class Live:
    """a board served on a free loopback port, torn down after the test."""

    def __init__(self, **kwargs):
        self.store = Store(tempfile.mkdtemp())
        self.session = Session(self.store)
        self.server, self.url = srv.serve_in_thread(self.session, **kwargs)
        self.host, self.port = self.server.server_address[:2]

    def call(self, method, path, body=None, headers=None, raw=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=10)
        h = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        if data is not None:
            h.setdefault("Content-Length", str(len(data)))
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        payload = r.read()
        conn.close()
        try:
            parsed = json.loads(payload)
        except ValueError:
            parsed = payload
        return r.status, parsed, dict(r.getheaders())

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Base(unittest.TestCase):
    def setUp(self):
        self.live = Live()
        self.addCleanup(self.live.close)

    def upload(self, data=PNG, **headers):
        return self.live.call("POST", "/api/assets", raw=data, headers={"Content-Type": "application/octet-stream", **headers})


class Reading(Base):
    def test_an_empty_board_reads_as_a_whole_board(self):
        status, body, _ = self.live.call("GET", "/api/board")
        self.assertEqual(status, 200)
        self.assertEqual(set(body) >= {"version", "pipeline", "board", "assets", "can_undo"}, True)
        self.assertEqual(body["pipeline"]["nodes"], [])

    def test_the_preset_menu_is_the_cli_menu_exactly(self):
        status, body, _ = self.live.call("GET", "/api/presets")
        self.assertEqual((status, body), (200, srv.menu()))
        self.assertGreater(len(body["presets"]), 20)

    def test_the_kits_are_served_with_every_member_listed_and_none_runnable(self):
        status, body, _ = self.live.call("GET", "/api/kits")
        self.assertEqual(status, 200)
        self.assertEqual([k["id"] for k in body["kits"]], ["analog", "handdrawn", "textile"])
        members = [m for k in body["kits"] for m in k["members"]]
        # counted from the declaration rather than pinned, so adding a member to a kit does not fail a
        # server test for a server reason; a member that goes missing on the wire still fails here
        from flowby import kits
        self.assertEqual(len(members), sum(len(kit.members) for kit in kits.KITS.values()))
        self.assertTrue(all(m["state"] == "listed" and m["runnable"] is False for m in members))

    def test_the_flora_door_believes_a_signed_delivery_and_nothing_else(self):
        """the route in one place: signed in, tampered out, unsigned out, and a 202 rather than a 200.

        the secret comes from the environment at request time, so this sets it for the test and puts
        back whatever was there. a delivery older than the replay window is refused by the module, and
        the module's own tests cover the arithmetic; what is checked here is that the route reads the
        RAW bytes and hands the right answers back.
        """
        import os
        import time
        from flowby import flora

        secret = "whsec_for_this_test_only"
        before = os.environ.get("FLORA_WEBHOOK_SECRET")
        os.environ["FLORA_WEBHOOK_SECRET"] = secret
        try:
            body = json.dumps({"id": "whd_1", "type": "run.completed", "data": {"run_id": "run_1"}}).encode()
            stamp = int(time.time())
            good = f"t={stamp},v1={flora.signature_for(stamp, body, secret)}"

            status, answer, _ = self.live.call("POST", "/api/flora/webhook", raw=body,
                                               headers={"Content-Type": "application/json", "Flora-Signature": good})
            self.assertEqual(status, 202)
            self.assertEqual(answer["accepted"], "whd_1")
            self.assertEqual(answer["event"]["data"]["run_id"], "run_1")

            # the bytes the signature covers, not the json they mean: re-spacing changes the bytes and
            # must be refused, because otherwise the signature would be checking a document nobody sent
            respaced = body.replace(b'"id": "whd_1",', b'"id":   "whd_1",')
            status, answer, _ = self.live.call("POST", "/api/flora/webhook", raw=respaced,
                                               headers={"Content-Type": "application/json", "Flora-Signature": good})
            self.assertEqual(status, 400)
            self.assertIn("does not match", answer["refused"])

            status, answer, _ = self.live.call("POST", "/api/flora/webhook", raw=body,
                                               headers={"Content-Type": "application/json"})
            self.assertEqual(status, 400)
            self.assertIn("unsigned", answer["refused"])
        finally:
            if before is None:
                os.environ.pop("FLORA_WEBHOOK_SECRET", None)
            else:
                os.environ["FLORA_WEBHOOK_SECRET"] = before

    def test_the_flora_door_says_so_when_it_has_no_secret_instead_of_opening(self):
        import os
        from flowby import flora

        before = {name: os.environ.get(name) for name in flora.SECRET_VARS}
        for name in flora.SECRET_VARS:
            os.environ.pop(name, None)
        try:
            body = b'{"id": "whd_2", "type": "run.completed", "data": {"run_id": "run_2"}}'
            status, answer, _ = self.live.call("POST", "/api/flora/webhook", raw=body,
                                               headers={"Content-Type": "application/json", "Flora-Signature": "t=1,v1=" + "0" * 64})
            self.assertEqual(status, 503)
            self.assertIn("no signing secret", answer["refused"])
        finally:
            for name, value in before.items():
                if value is not None:
                    os.environ[name] = value

    def test_an_unknown_route_is_a_404_with_a_sentence(self):
        for method in ("GET", "POST"):
            status, body, _ = self.live.call(method, "/api/nothing", body={} if method == "POST" else None)
            self.assertEqual(status, 404)
            self.assertIn("no such route", body["refused"])

    def test_there_is_no_generic_call_a_method_route(self):
        for path in ("/api/__class__", "/api/scene", "/api/_do", "/api/store", "/", "/api", "/../etc/passwd"):
            self.assertEqual(self.live.call("GET", path)[0], 404, path)


class Assets(Base):
    def test_an_upload_returns_the_digest_of_exactly_those_bytes(self):
        status, body, _ = self.upload()
        self.assertEqual((status, body["digest"], body["bytes"]), (200, digest_of(PNG), len(PNG)))

    def test_the_same_upload_twice_is_one_file(self):
        self.upload(); self.upload()
        self.assertEqual(self.live.store.count(), 1)

    def test_an_upload_under_a_lying_digest_is_refused_and_not_stored(self):
        status, body, _ = self.upload(**{"X-Digest": digest_of(b"something else")})
        self.assertEqual(status, 422)
        self.assertIn("hash to", body["refused"])
        self.assertEqual(self.live.store.count(), 0)

    def test_an_upload_under_its_true_digest_is_accepted(self):
        self.assertEqual(self.upload(**{"X-Digest": digest_of(PNG)})[0], 200)

    def test_an_empty_upload_is_refused(self):
        self.assertEqual(self.upload(b"")[0], 422)

    def test_an_oversize_upload_is_refused_before_a_byte_is_read(self):
        # claim a huge body and send none: if the server believed the length and waited to read it
        # this would hang to the timeout. it must answer 413 from the header alone.
        conn = http.client.HTTPConnection(self.live.host, self.live.port, timeout=5)
        conn.putrequest("POST", "/api/assets")
        conn.putheader("Content-Length", str(MAX_BYTES + 1))
        conn.putheader("Content-Type", "application/octet-stream")
        conn.endheaders()
        r = conn.getresponse()
        self.assertEqual(r.status, 413)
        self.assertIn("MB", json.loads(r.read())["refused"])

    def test_a_missing_content_length_is_refused(self):
        conn = http.client.HTTPConnection(self.live.host, self.live.port, timeout=5)
        conn.putrequest("POST", "/api/assets")
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 411)

    def test_a_body_shorter_than_its_length_is_refused(self):
        conn = http.client.HTTPConnection(self.live.host, self.live.port, timeout=3)
        conn.putrequest("POST", "/api/assets")
        conn.putheader("Content-Length", "100")
        conn.endheaders()
        conn.send(b"only ten b")
        conn.sock.shutdown(1)
        self.assertEqual(conn.getresponse().status, 400)
        self.assertEqual(self.live.store.count(), 0)

    def test_the_bytes_come_back_the_same_with_a_type_read_from_the_bytes(self):
        d = self.upload()[1]["digest"]
        status, body, headers = self.live.call("GET", f"/api/assets/{d}")
        self.assertEqual((status, body), (200, PNG))
        self.assertEqual(headers["Content-Type"], "image/png")

    def test_the_type_comes_from_the_bytes_and_never_from_a_name(self):
        # an html file uploaded as if it were a picture must be served as an opaque download, never as html
        page = b"<html><script>alert(1)</script></html>"
        d = self.upload(page, **{"Content-Type": "image/png"})[1]["digest"]
        status, body, headers = self.live.call("GET", f"/api/assets/{d}")
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertEqual(headers["Content-Disposition"], "attachment")

    def test_every_asset_is_served_sandboxed_and_unsniffable(self):
        d = self.upload()[1]["digest"]
        _, _, headers = self.live.call("GET", f"/api/assets/{d}")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", headers["Content-Security-Policy"])

    def test_an_svg_is_never_served_as_an_image_a_browser_would_run(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        d = self.upload(svg)[1]["digest"]
        _, _, headers = self.live.call("GET", f"/api/assets/{d}")
        self.assertNotIn("svg", headers["Content-Type"])

    def test_a_missing_asset_is_a_404_by_name(self):
        status, body, _ = self.live.call("GET", "/api/assets/sha256:" + "a" * 64)
        self.assertEqual(status, 404)
        self.assertIn("not in the store", body["refused"])

    def test_a_path_that_is_not_a_digest_never_reaches_the_store(self):
        for bad in ("/api/assets/../../etc/passwd", "/api/assets/sha256:" + "A" * 64, "/api/assets/sha256:abc",
                    "/api/assets/%2e%2e%2f%2e%2e%2fetc%2fpasswd", "/api/assets/sha256:" + "a" * 64 + "/x"):
            status, body, _ = self.live.call("GET", bad)
            self.assertEqual(status, 404, bad)
            # the route refuses these itself, before the store is asked. the store would refuse them
            # too, with a different sentence, and that second wall is what a loosened route would hit,
            # so the first wall is pinned by which sentence comes back.
            self.assertIn("no such route", body["refused"], f"{bad} reached the store")

    def test_a_corrupted_file_is_not_served(self):
        d = self.upload()[1]["digest"]
        hexed = d.split(":")[1]
        (self.live.store.root / hexed[:2] / hexed[2:4] / hexed).write_bytes(b"rot")
        status, body, _ = self.live.call("GET", f"/api/assets/{d}")
        self.assertEqual(status, 404)
        self.assertIn("no longer hash", body["refused"])


class Acting(Base):
    def add_sketch(self):
        d = self.upload()[1]["digest"]
        return self.live.call("POST", "/api/add_file", {"kind": "sketch", "label": "the owl", "digest": d})[1]["receipt"]["ids"][0]

    def test_the_whole_flow_over_the_wire(self):
        el = self.add_sketch()
        status, body, _ = self.live.call("POST", "/api/apply", {"element": el, "preset": "sketch-to-mesh"})
        self.assertEqual(status, 200)
        self.assertGreater(len(body["pipeline"]["nodes"]), 2)
        self.assertEqual(body["board"][0]["presets"], ["sketch-to-mesh"])
        self.assertEqual(self.live.call("GET", "/api/board")[1]["version"], body["version"])

    def test_an_added_image_has_a_preview_pointing_at_bytes_that_are_really_served(self):
        d = self.upload()[1]["digest"]
        el = self.live.call("POST", "/api/add_file", {"kind": "image", "label": "pic", "digest": d})[1]["receipt"]["ids"][0]
        assets = self.live.call("GET", "/api/board")[1]["assets"]
        self.assertEqual(assets[el], d)
        self.assertEqual(self.live.call("GET", f"/api/assets/{assets[el]}")[2]["Content-Type"], "image/png")

    def test_a_refusal_is_422_with_the_sentence_and_the_board_is_as_it_was(self):
        el = self.add_sketch()
        before = self.live.call("GET", "/api/board")[1]
        status, body, _ = self.live.call("POST", "/api/apply", {"element": el, "preset": "frosted-glass"})
        self.assertEqual(status, 422)
        self.assertTrue(body["refused"])
        self.assertEqual(self.live.call("GET", "/api/board")[1], before)

    def test_a_file_that_was_never_uploaded_cannot_be_added(self):
        status, body, _ = self.live.call("POST", "/api/add_file", {"kind": "image", "digest": digest_of(b"never")})
        self.assertEqual(status, 422)
        self.assertIn("not in the store", body["refused"])

    def test_a_missing_field_is_a_400_that_names_it(self):
        status, body, _ = self.live.call("POST", "/api/apply", {"element": "x"})
        self.assertEqual(status, 400)
        self.assertIn("send preset", body["refused"])

    def test_undo_and_redo_over_the_wire(self):
        el = self.add_sketch()
        self.live.call("POST", "/api/apply", {"element": el, "preset": "sketch-to-mesh"})
        after = self.live.call("GET", "/api/board")[1]["pipeline"]
        undone = self.live.call("POST", "/api/undo", {})[1]
        self.assertLess(len(undone["pipeline"]["nodes"]), len(after["nodes"]))
        self.assertEqual(self.live.call("POST", "/api/redo", {})[1]["pipeline"], after)

    def test_undo_with_nothing_to_undo_is_422(self):
        self.assertEqual(self.live.call("POST", "/api/undo", {})[0], 422)

    def test_text_remove_and_rename(self):
        t = self.live.call("POST", "/api/add_text", {"text": "a small brass owl"})[1]["receipt"]["ids"][0]
        self.assertEqual(self.live.call("POST", "/api/rename", {"element": t, "label": "caption"})[1]["board"][0]["label"], "caption")
        self.assertEqual(self.live.call("POST", "/api/remove", {"element": t})[1]["board"], [])

    def test_the_board_survives_a_burst_of_parallel_requests(self):
        d = self.upload()[1]["digest"]
        codes = []
        def go():
            codes.append(self.live.call("POST", "/api/add_file", {"kind": "image", "label": "x", "digest": d})[0])
        threads = [threading.Thread(target=go) for _ in range(25)]
        [t.start() for t in threads]; [t.join() for t in threads]
        self.assertEqual(set(codes), {200})
        board = self.live.call("GET", "/api/board")[1]
        self.assertEqual(len(board["board"]), 25)
        self.assertEqual(board["version"], 25)


class Strictness(Base):
    def test_a_form_post_is_refused_because_a_form_cannot_send_json(self):
        # the shape of a request an attacker's page in another tab can make without any permission
        for kind in ("application/x-www-form-urlencoded", "text/plain", "multipart/form-data; boundary=x"):
            status, body, _ = self.live.call("POST", "/api/add_text", raw=b"text=hello", headers={"Content-Type": kind})
            self.assertEqual(status, 415, kind)
        self.assertEqual(self.live.call("GET", "/api/board")[1]["board"], [])

    def test_a_request_from_another_origin_is_refused(self):
        status, body, _ = self.live.call("POST", "/api/add_text", {"text": "hello"}, headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.live.call("GET", "/api/board")[1]["board"], [])

    def test_a_read_from_another_origin_is_refused_too(self):
        self.assertEqual(self.live.call("GET", "/api/board", headers={"Origin": "https://evil.example"})[0], 403)

    def test_an_upload_from_another_origin_is_refused_and_not_stored(self):
        self.assertEqual(self.upload(**{"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.live.store.count(), 0)

    def test_the_servers_own_origin_is_allowed(self):
        own = f"http://{self.live.host}:{self.live.port}"
        self.assertEqual(self.live.call("GET", "/api/board", headers={"Origin": own})[0], 200)

    def test_a_listed_origin_is_allowed_and_nothing_else_is(self):
        live = Live(allow_origins=("http://localhost:5173",))
        self.addCleanup(live.close)
        ok = live.call("GET", "/api/board", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(ok[0], 200)
        self.assertEqual(ok[2]["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertEqual(live.call("GET", "/api/board", headers={"Origin": "http://localhost:5174"})[0], 403)
        self.assertEqual(live.call("GET", "/api/board", headers={"Origin": "http://localhost:5173.evil.example"})[0], 403)

    def test_a_refused_origin_is_never_echoed_back_as_allowed(self):
        _, _, headers = self.live.call("GET", "/api/board", headers={"Origin": "https://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_preflight_from_an_unlisted_origin_is_refused(self):
        self.assertEqual(self.live.call("OPTIONS", "/api/add_text", headers={"Origin": "https://evil.example"})[0], 403)

    def test_preflight_from_a_listed_origin_allows_json_and_only_what_is_used(self):
        live = Live(allow_origins=("http://localhost:5173",))
        self.addCleanup(live.close)
        status, _, h = live.call("OPTIONS", "/api/add_text", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(status, 204)
        self.assertEqual(h["Access-Control-Allow-Methods"], "GET, POST, OPTIONS")
        self.assertEqual(h["Access-Control-Allow-Headers"], "Content-Type")

    def test_malformed_json_is_a_400_and_not_a_traceback(self):
        status, body, _ = self.live.call("POST", "/api/add_text", raw=b"{not json", headers={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(self.live.call("POST", "/api/add_text", raw=b"[1,2]", headers={"Content-Type": "application/json"})[0], 400)

    def test_a_huge_json_body_is_refused_from_its_length(self):
        conn = http.client.HTTPConnection(self.live.host, self.live.port, timeout=5)
        conn.putrequest("POST", "/api/add_text")
        conn.putheader("Content-Length", str(srv.JSON_LIMIT + 1))
        conn.putheader("Content-Type", "application/json")
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 413)

    def test_every_response_says_not_to_cache_and_not_to_sniff(self):
        for path in ("/api/board", "/api/presets", "/api/nothing"):
            _, _, h = self.live.call("GET", path)
            self.assertEqual(h["Cache-Control"], "no-store")
            self.assertEqual(h["X-Content-Type-Options"], "nosniff")

    def test_the_server_does_not_announce_its_python_version(self):
        _, _, h = self.live.call("GET", "/api/board")
        self.assertNotIn("Python", h.get("Server", ""))

    def test_the_default_is_loopback_only(self):
        self.assertTrue(self.live.server.flowby_loopback)
        self.assertEqual(self.live.host, "127.0.0.1")

    def test_an_unexpected_error_in_a_route_does_not_corrupt_the_board(self):
        before = self.live.call("GET", "/api/board")[1]
        self.live.call("POST", "/api/value", {"instance": "ghost", "slider": "x", "value": 1})
        self.assertEqual(self.live.call("GET", "/api/board")[1]["version"], before["version"])


class Gpus(Base):
    """the plug, over the wire, against a real model server on loopback (which is what an ssh
    tunnel to a rented gpu looks like from here)."""

    TOKEN = "tok_live_ZzYyXx9876543210"

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import plug_test
        self.fake = plug_test.FakeVllm(token=self.TOKEN, models=("flux-dev", "llama-3.1-8b"))
        self.addCleanup(self.fake.close)

    def add(self, **over):
        body = {"label": "vultr a100", "provider": "vultr", "endpoint": self.fake.url, "token": self.TOKEN, **over}
        return self.live.call("POST", "/api/plugs/add", body)

    def test_a_new_plug_is_unchecked_and_the_reply_has_no_token(self):
        status, body, _ = self.add()
        self.assertEqual(status, 200)
        self.assertEqual(body["plug"]["state"], "unchecked")
        self.assertTrue(body["plug"]["has_token"])
        self.assertNotIn("tok_live", json.dumps(body))

    def test_checking_really_asks_the_server_and_only_then_is_it_up(self):
        pid = self.add()[1]["plug"]["id"]
        self.assertEqual(self.fake.seen, [], "adding a plug must not touch the network")
        status, body, _ = self.live.call("POST", "/api/plugs/check", {"id": pid})
        self.assertEqual((status, body["plug"]["state"]), (200, "up"))
        self.assertEqual(body["plug"]["models"], ["flux-dev", "llama-3.1-8b"])
        self.assertEqual([s["path"] for s in self.fake.seen], ["/health", "/v1/models", "/version"])

    def test_the_token_the_page_sent_is_what_the_server_received_and_never_comes_back(self):
        pid = self.add()[1]["plug"]["id"]
        _, checked, _ = self.live.call("POST", "/api/plugs/check", {"id": pid})
        self.assertTrue(all(s["auth"] == f"Bearer {self.TOKEN}" for s in self.fake.seen))
        listing = self.live.call("GET", "/api/plugs")
        for blob in (json.dumps(checked), json.dumps(listing[1])):
            self.assertNotIn("tok_live", blob)
            self.assertNotIn("ZzYyXx", blob)

    def test_a_wrong_token_shows_as_down_with_a_sentence_and_not_a_server_error(self):
        pid = self.add(token="nope")[1]["plug"]["id"]
        status, body, _ = self.live.call("POST", "/api/plugs/check", {"id": pid})
        self.assertEqual(status, 200)
        self.assertEqual((body["plug"]["state"], body["plug"]["detail"]), ("down", "the server refused the token"))

    def test_a_plug_store_handed_to_the_server_is_the_one_it_uses(self):
        # a server restarted with its plugs (loaded from somewhere) must show them, not an empty set
        from flowby.plug import Plugs
        kept = Plugs(); kept.add("already here", "gcp", "https://gpu.example.com")
        live = Live(plugs=kept)
        self.addCleanup(live.close)
        listed = live.call("GET", "/api/plugs")[1]["plugs"]
        self.assertEqual([p["label"] for p in listed], ["already here"])

    def test_the_listing_names_the_providers_and_says_how_auth_is_sent(self):
        status, body, _ = self.live.call("GET", "/api/plugs")
        self.assertEqual(set(body["providers"]), {"vultr", "gcp", "azure", "aws", "amd", "nvidia", "fal", "other"})
        self.assertIn("Bearer", body["auth"])
        self.assertIn("not confirmed", body["auth"])

    def test_a_hosted_plug_is_added_and_stays_unchecked_when_asked_to_check(self):
        status, body, _ = self.add(provider="fal", label="flux on fal", endpoint="https://queue.fal.run/fal-ai/flux/schnell", token="FALKEY-9")
        self.assertEqual(status, 200)
        self.assertEqual(body["plug"]["kind"], "hosted")
        self.assertNotIn("FALKEY-9", json.dumps(body))
        pid = body["plug"]["id"]
        status, checked, _ = self.live.call("POST", "/api/plugs/check", {"id": pid})
        self.assertEqual(status, 200)
        self.assertEqual(checked["plug"]["state"], "unchecked")
        self.assertIn("no free ping", checked["plug"]["detail"])
        self.assertNotIn("FALKEY-9", json.dumps(checked))

    def test_a_hosted_plug_on_the_wrong_host_is_refused_over_http(self):
        status, body, _ = self.add(provider="fal", endpoint="https://evil.example.com/a/b", token="FALKEY-9")
        self.assertEqual(status, 422)
        self.assertNotIn("FALKEY-9", json.dumps(body))
        self.assertEqual(self.live.call("GET", "/api/plugs")[1]["plugs"], [])

    def test_a_public_http_address_is_refused_with_the_reason(self):
        status, body, _ = self.add(endpoint="http://45.32.10.20:8000")
        self.assertEqual(status, 422)
        self.assertIn("in the clear", body["refused"])
        self.assertEqual(self.live.call("GET", "/api/plugs")[1]["plugs"], [])

    def test_the_metadata_address_is_refused_over_the_wire_too(self):
        status, body, _ = self.add(endpoint="https://169.254.169.254")
        self.assertEqual(status, 422)
        self.assertIn("private network address", body["refused"])

    def test_the_same_address_twice_is_a_422_that_names_the_first(self):
        self.add()
        status, body, _ = self.add(label="again")
        self.assertEqual(status, 422)
        self.assertIn("'vultr a100' is already plugged in", body["refused"])

    def test_removing_forgets_it_and_checking_it_after_is_a_422(self):
        pid = self.add()[1]["plug"]["id"]
        self.assertEqual(self.live.call("POST", "/api/plugs/remove", {"id": pid})[1]["plugs"], [])
        self.assertEqual(self.live.call("POST", "/api/plugs/check", {"id": pid})[0], 422)

    def test_a_plug_survives_undo_because_a_gpu_is_not_board_state(self):
        pid = self.add()[1]["plug"]["id"]
        self.live.call("POST", "/api/add_text", {"text": "hello there"})
        self.live.call("POST", "/api/undo", {})
        self.assertEqual([p["id"] for p in self.live.call("GET", "/api/plugs")[1]["plugs"]], [pid])

    def test_missing_fields_are_a_400_that_names_them(self):
        status, body, _ = self.live.call("POST", "/api/plugs/add", {"label": "x"})
        self.assertEqual(status, 400)
        self.assertIn("send provider", body["refused"])

    def test_every_plug_route_refuses_another_origin_and_a_form_post(self):
        for path in ("/api/plugs/add", "/api/plugs/check", "/api/plugs/remove"):
            self.assertEqual(self.live.call("POST", path, {"id": "x"}, headers={"Origin": "https://evil.example"})[0], 403, path)
            self.assertEqual(self.live.call("POST", path, raw=b"id=x", headers={"Content-Type": "application/x-www-form-urlencoded"})[0], 415, path)
        self.assertEqual(self.live.call("GET", "/api/plugs", headers={"Origin": "https://evil.example"})[0], 403)

    def test_a_server_that_dies_is_down_on_the_next_check_and_comes_back_up(self):
        pid = self.add()[1]["plug"]["id"]
        self.assertEqual(self.live.call("POST", "/api/plugs/check", {"id": pid})[1]["plug"]["state"], "up")
        self.fake.mode = "500"
        down = self.live.call("POST", "/api/plugs/check", {"id": pid})[1]["plug"]
        self.assertEqual(down["state"], "down")
        self.assertEqual(down["models"], [])
        self.fake.mode = "ok"
        self.assertEqual(self.live.call("POST", "/api/plugs/check", {"id": pid})[1]["plug"]["state"], "up")


class Weather(Base):
    def test_a_client_that_vanishes_mid_request_prints_nothing(self):
        import io, contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(5):
                conn = http.client.HTTPConnection(self.live.host, self.live.port, timeout=3)
                conn.putrequest("POST", "/api/assets")
                conn.putheader("Content-Length", "5000")
                conn.endheaders()
                conn.send(b"half")
                conn.sock.close()           # a closed tab: no shutdown, just gone
            import time; time.sleep(0.3)
        self.assertEqual(err.getvalue(), "", "a client leaving is not an error worth a traceback")
        self.assertEqual(self.live.call("GET", "/api/board")[0], 200, "and the server is still up")

    def test_a_real_error_in_a_handler_is_still_reported(self):
        import io, contextlib
        err = io.StringIO()
        class Boom(Exception):
            pass
        real = self.live.session.view
        self.live.session.view = lambda *a, **k: (_ for _ in ()).throw(Boom("a genuine bug"))
        with contextlib.redirect_stderr(err):
            try:
                self.live.call("GET", "/api/board")
            except Exception:
                pass
            import time; time.sleep(0.2)
        self.live.session.view = real
        self.assertIn("Boom", err.getvalue(), "only disconnects are quiet; a real fault must still show")


class Content(unittest.TestCase):
    def test_the_sniffer_knows_each_type_by_its_bytes(self):
        self.assertEqual(srv.content_type(PNG), "image/png")
        self.assertEqual(srv.content_type(b"\xff\xd8\xff\xe0abc"), "image/jpeg")
        self.assertEqual(srv.content_type(b"GIF89a"), "image/gif")
        self.assertEqual(srv.content_type(b"RIFF\0\0\0\0WEBPVP8 "), "image/webp")
        self.assertEqual(srv.content_type(b"\0\0\0\x18ftypmp42"), "video/mp4")
        self.assertEqual(srv.content_type(b"glTF\x02\0\0\0"), "model/gltf-binary")
        self.assertEqual(srv.content_type(b"<svg></svg>"), "application/octet-stream")
        self.assertEqual(srv.content_type(b""), "application/octet-stream")


class TheRecipeCards(unittest.TestCase):
    """`GET /api/recipes`: the board's own chains, drawn as the card a stranger reads.

    the route exists so the page cannot describe a board differently from the terminal: both call
    `recipes.card`, and both take the recipe from `Session.record`, not from a second copy of the steps.
    """

    def setUp(self):
        self.live = Live()
        png = PNG
        added = self.live.call("POST", "/api/assets", raw=png)
        self.digest = added[1]["digest"]
        self.element = self.live.call("POST", "/api/add_file",
                                      {"kind": "image", "label": "heron",
                                       "digest": self.digest})[1]["receipt"]["ids"][0]
        self.live.call("POST", "/api/apply", {"element": self.element, "preset": "sketch-to-render"})

    def tearDown(self):
        self.live.close()

    def test_a_chain_on_the_board_comes_back_as_a_card(self):
        status, body, _ = self.live.call("GET", "/api/recipes")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["recipes"]), 1)
        card = body["recipes"][0]
        self.assertEqual(card["element"], self.element)
        for key in ("name", "brief", "version", "inputs", "advanced", "hidden", "needs", "run"):
            self.assertIn(key, card)

    def test_the_card_names_the_step_that_cannot_be_changed_rather_than_hiding_it(self):
        card = self.live.call("GET", "/api/recipes")[1]["recipes"][0]
        self.assertTrue(card["hidden"], "a chain sets settings the card has no control for; they must be named")
        self.assertTrue(all("no control" in row["means"] for row in card["hidden"]))

    def test_an_element_with_nothing_applied_has_no_card(self):
        self.live.call("POST", "/api/add_text", {"text": "a heron on a jetty", "label": "caption"})
        names = [card["name"] for card in self.live.call("GET", "/api/recipes")[1]["recipes"]]
        self.assertNotIn("caption", names)


if __name__ == "__main__":
    unittest.main()