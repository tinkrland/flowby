"""flora_test: refusing a callback that cannot be vouched for, and accepting the one that can.

the rules worth a test are the ones that fail open. a verifier that accepts everything passes every
happy-path test; a verifier that signs the parsed dict instead of the raw bytes accepts its own tests
and nothing that flora ever sends.
"""

import json
import unittest

from flowby import flora


SECRET = "whsec_test_only_not_a_real_secret"


def delivery(**over):
    event = {"id": "whd_abc123", "type": "run.completed", "api_version": "2026-06-11",
             "created_at": 1733952000000,
             "data": {"run_id": "run_abc123", "run_type": "generation", "workspace_id": "ws_abc123",
                      "status": "completed"}}
    event.update(over)
    return json.dumps(event).encode()


def header_for(body, stamp=1733952000, secret=SECRET):
    return f"t={stamp},v1={flora.signature_for(stamp, body, secret)}"


def verify(body, header, secret=SECRET, now=None):
    return flora.verify(body, header, secret, now=1733952000 if now is None else now)


class TheHappyPath(unittest.TestCase):
    def test_a_signed_delivery_comes_back_as_the_event(self):
        body = delivery()
        event = verify(body, header_for(body))
        self.assertEqual(event["type"], "run.completed")
        self.assertEqual(flora.delivery_id(event), "whd_abc123")

    def test_the_signature_covers_the_bytes_that_arrived_not_the_ones_we_would_write(self):
        # the same json, spaced differently: a verifier that re-serialises would refuse this, and a
        # verifier that hashes what it received accepts it, because flora's bytes are the message
        body = b'{"id": "whd_1",  "type": "run.failed",\n "data": {"run_id": "run_1"}}'
        event = verify(body, header_for(body))
        self.assertEqual(event["type"], "run.failed")

    def test_both_terminal_events_are_known(self):
        for kind in flora.EVENTS:
            body = delivery(type=kind)
            self.assertEqual(verify(body, header_for(body))["type"], kind)


class WhatIsRefused(unittest.TestCase):
    def test_a_body_changed_after_signing_is_refused(self):
        body = delivery()
        header = header_for(body)
        tampered = body.replace(b"run_abc123", b"run_xyz123")
        self.assertEqual(len(tampered), len(body))  # same length, so nothing about the size gives it away
        with self.assertRaises(flora.Refused) as caught:
            verify(tampered, header)
        self.assertIn("does not match", str(caught.exception))

    def test_a_signature_made_with_another_secret_is_refused(self):
        body = delivery()
        with self.assertRaises(flora.Refused):
            verify(body, header_for(body, secret="whsec_somebody_elses"))

    def test_a_missing_header_is_refused(self):
        with self.assertRaises(flora.Refused) as caught:
            verify(delivery(), None)
        self.assertIn("unsigned", str(caught.exception))

    def test_a_header_with_no_signature_is_refused(self):
        with self.assertRaises(flora.Refused) as caught:
            verify(delivery(), "t=1733952000")
        self.assertIn("no v1", str(caught.exception))

    def test_a_header_with_no_timestamp_is_refused_because_a_replay_could_not_be_ruled_out(self):
        body = delivery()
        sig = flora.signature_for(1733952000, body, SECRET)
        with self.assertRaises(flora.Refused) as caught:
            verify(body, f"v1={sig}")
        self.assertIn("replay", str(caught.exception))

    def test_a_signature_that_is_not_a_full_sha256_is_refused_before_it_is_compared(self):
        body = delivery()
        sig = flora.signature_for(1733952000, body, SECRET)
        for wrong in (sig[:-1], sig.upper(), "z" * 64, sig + "0"):
            with self.assertRaises(flora.Refused, msg=wrong):
                verify(body, f"t=1733952000,v1={wrong}")

    def test_an_old_delivery_is_refused_as_a_replay(self):
        body = delivery()
        header = header_for(body, stamp=1733952000)
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header, now=1733952000 + 301)
        self.assertIn("replay window", str(caught.exception))

    def test_a_delivery_from_the_future_is_refused(self):
        body = delivery()
        header = header_for(body, stamp=1733952000)
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header, now=1733952000 - 301)
        self.assertIn("future", str(caught.exception))

    def test_a_retry_that_spent_a_while_in_a_queue_is_still_accepted(self):
        body = delivery()
        header = header_for(body, stamp=1733952000)
        # 299 seconds late is late, not forged
        self.assertEqual(verify(body, header, now=1733952000 + 299)["type"], "run.completed")


class TheSecretItself(unittest.TestCase):
    def test_an_empty_secret_refuses_rather_than_forging(self):
        # anybody can compute an hmac with an empty key. a verifier that treats "no secret" as "no
        # check" is the classic way a webhook door is left open, so this must refuse, not pass
        body = delivery()
        forged = f"t=1733952000,v1={flora.signature_for(1733952000, body, 'x')}"
        with self.assertRaises(flora.NoSecret):
            flora.verify(body, forged, "")

    def test_signing_with_an_empty_secret_is_refused_too(self):
        with self.assertRaises(flora.NoSecret):
            flora.signature_for(1733952000, b"{}", "")

    def test_the_secret_is_read_from_the_environment_by_name(self):
        self.assertEqual(flora.secret_from({"FLORA_WEBHOOK_SECRET": SECRET}), SECRET)
        # the name it is saved under here, accepted so a configured door is not left unopened
        self.assertEqual(flora.secret_from({"FLORA_API_KEY": SECRET}), SECRET)
        # the documented name wins when both are set
        self.assertEqual(flora.secret_from({"FLORA_WEBHOOK_SECRET": "a", "FLORA_API_KEY": "b"}), "a")
        # a blank value is not a value
        self.assertEqual(flora.secret_from({"FLORA_API_KEY": "  ", "FLORA_WEBHOOK_SECRET": SECRET}), SECRET)

    def test_no_secret_configured_names_the_variables_that_were_looked_in(self):
        with self.assertRaises(flora.NoSecret) as caught:
            flora.secret_from({})
        for name in flora.SECRET_VARS:
            self.assertIn(name, str(caught.exception))


class TheBodyItself(unittest.TestCase):
    def test_a_str_body_is_refused_rather_than_encoded(self):
        body = delivery()
        with self.assertRaises(flora.Refused) as caught:
            verify(body.decode(), header_for(body))
        self.assertIn("raw body bytes", str(caught.exception))

    def test_a_signed_body_that_is_not_json_is_refused(self):
        body = b"not json at all"
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header_for(body))
        self.assertIn("not json", str(caught.exception))

    def test_a_signed_body_that_is_not_an_object_is_refused(self):
        body = b'["run.completed"]'
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header_for(body))
        self.assertIn("json object", str(caught.exception))

    def test_an_event_without_a_type_is_refused(self):
        body = json.dumps({"id": "whd_1"}).encode()
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header_for(body))
        self.assertIn("no `type`", str(caught.exception))

    def test_an_event_this_flowby_does_not_know_is_refused_by_name(self):
        body = delivery(type="run.paused")
        with self.assertRaises(flora.Refused) as caught:
            verify(body, header_for(body))
        self.assertIn("run.paused", str(caught.exception))

    def test_an_event_with_no_delivery_id_cannot_be_deduped(self):
        with self.assertRaises(flora.Refused):
            flora.delivery_id({"type": "run.completed"})


class Rotation(unittest.TestCase):
    def test_a_header_offering_two_signatures_is_accepted_when_one_matches(self):
        # during a rotation a sender may sign with both the old and the new secret; refusing the
        # header outright would turn a supported rotation into an outage
        body = delivery()
        old = flora.signature_for(1733952000, body, "whsec_previous")
        new = flora.signature_for(1733952000, body, SECRET)
        self.assertEqual(verify(body, f"t=1733952000,v1={old},v1={new}")["type"], "run.completed")

    def test_two_wrong_signatures_are_still_refused(self):
        body = delivery()
        a = flora.signature_for(1733952000, body, "whsec_a")
        b = flora.signature_for(1733952000, body, "whsec_b")
        with self.assertRaises(flora.Refused):
            verify(body, f"t=1733952000,v1={a},v1={b}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
