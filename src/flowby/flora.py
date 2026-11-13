"""flora webhooks: proving a callback came from flora before anything acts on it.

flora finishes a generation or a technique run asynchronously and can send one signed POST to a
callback url instead of being polled (docs.flora.ai/api/platform/webhooks). every delivery carries a
`Flora-Signature` header and is signed with the workspace's signing secret, which starts `whsec_` — the
same secret flora shows in its "new webhook signing secret" dialog and in the API-key-created dialog.

two things this module refuses to be sloppy about, because a webhook endpoint is a door:

    - the bytes. the signed message is the timestamp, a literal dot, then the EXACT raw body. parsing
      the json and serialising it again reorders keys and changes spacing, and the signature stops
      matching. so `verify` takes bytes and never a dict, and a str is refused rather than encoded.
    - the window. the timestamp is inside the signature so a captured delivery cannot be replayed
      later. a delivery older than REPLAY_WINDOW is refused, and so is one from the future, which is
      what a forged clock looks like.

what this module does NOT do: it does not fetch the run, and it does not mark anything done in flowby.
the payload carries the run's identity and its final status, not its outputs, so a caller that wants the
picture has to ask flora for it by `data.run_id`. that dispatch half is not built yet.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

# how far a delivery's timestamp may be from now, in seconds. five minutes each way: wide enough for a
# retry that spent a while in a queue, narrow enough that a captured delivery is stale by the time it
# could be replayed.
REPLAY_WINDOW = 300

# the events flora sends today. a terminal run sends exactly one.
EVENTS = ("run.completed", "run.failed")

# the header a delivery is signed in.
SIGNATURE_HEADER = "Flora-Signature"

# where the secret is read from by the server route, in order. `FLORA_WEBHOOK_SECRET` is what flora's
# own docs name it; `FLORA_API_KEY` is accepted because that is the name the secret was saved under
# here, and a working door beats a tidy one.
SECRET_VARS = ("FLORA_WEBHOOK_SECRET", "FLORA_API_KEY")


class Refused(Exception):
    """a delivery that cannot be vouched for is refused, and the sentence says why."""


class NoSecret(Refused):
    """nothing is configured to verify against, which is a server fault and not the sender's."""


def secret_from(env: dict[str, str]) -> str:
    """the signing secret, or NoSecret naming the variables that were looked in."""
    for name in SECRET_VARS:
        value = (env.get(name) or "").strip()
        if value:
            return value
    raise NoSecret(f"no signing secret is set: export one of {', '.join(SECRET_VARS)}")


def signed_message(stamp: int, body: bytes) -> bytes:
    """what is actually hashed: the unix-seconds timestamp, a dot, then the raw body."""
    return str(stamp).encode() + b"." + body


def signature_for(stamp: int, body: bytes, secret: str) -> str:
    """the v1 signature a delivery would carry. here so tests and tools sign the same way flora does."""
    if not secret:
        raise NoSecret("a signature needs a secret, and that one is empty")
    return hmac.new(secret.encode(), signed_message(stamp, body), hashlib.sha256).hexdigest()


def verify(body: bytes, header: str | None, secret: str, *, now: float | None = None,
           tolerance: int = REPLAY_WINDOW) -> dict:
    """the parsed event, or Refused. `body` must be the raw bytes exactly as they arrived."""
    if not secret:
        # an empty key is not a weak key, it is a forgeable one: anybody can sign with nothing
        raise NoSecret("no signing secret is configured, so nothing sent here can be vouched for")
    if isinstance(body, (bytearray, memoryview)):
        body = bytes(body)
    if not isinstance(body, bytes):
        raise Refused("verify needs the raw body bytes: a str or a dict has already lost what was signed")

    stamp, given = _parse_header(header)
    when = time.time() if now is None else now
    age = when - stamp
    if age > tolerance:
        raise Refused(f"that delivery is {int(age)}s old, past the {tolerance}s replay window: ask flora to resend it")
    if age < -tolerance:
        raise Refused(f"that delivery is stamped {int(-age)}s in the future, which no honest clock is: refused")

    expected = signature_for(stamp, body, secret)
    # compare every candidate without short-circuiting, so the time taken says nothing about how much
    # of a wrong signature was right
    matched = False
    for candidate in given:
        matched |= hmac.compare_digest(candidate, expected)
    if not matched:
        raise Refused("the signature does not match this body and secret: refused rather than half-believed")

    try:
        event = json.loads(body or b"null")
    except ValueError:
        raise Refused("the body is signed but is not json") from None
    if not isinstance(event, dict):
        raise Refused("the body is signed but is not a json object")
    if not event.get("type"):
        raise Refused("the event does not say what it is: no `type`")
    if event["type"] not in EVENTS:
        # not a refusal of the sender's honesty, only of our understanding of it
        raise Refused(f"{event['type']!r} is not an event this flowby knows ({', '.join(EVENTS)})")
    return event


def delivery_id(event: dict) -> str:
    """the id to dedupe on: flora retries a delivery and the body is identical on every retry."""
    got = event.get("id")
    if not isinstance(got, str) or not got:
        raise Refused("this event has no delivery id, so a retry could not be told from a first arrival")
    return got


def _parse_header(header: str | None) -> tuple[int, list[str]]:
    """`t=1733952000,v1=9f86…` into the stamp and every v1 offered."""
    if not header:
        raise Refused(f"no {SIGNATURE_HEADER} header: an unsigned delivery is not a delivery")
    stamp: int | None = None
    candidates: list[str] = []
    for part in header.split(","):
        name, _, value = part.strip().partition("=")
        value = value.strip()
        if name == "t":
            if not value.isdigit():
                raise Refused(f"{SIGNATURE_HEADER} has a timestamp that is not a whole number of seconds")
            stamp = int(value)
        elif name == "v1":
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise Refused(f"{SIGNATURE_HEADER} has a v1 that is not a sha256 in lowercase hex")
            candidates.append(value)
        # any other name is from a scheme we do not speak yet, and ignoring it is how a v2 can be added
    if stamp is None:
        raise Refused(f"{SIGNATURE_HEADER} has no timestamp, so a replay cannot be ruled out")
    if not candidates:
        raise Refused(f"{SIGNATURE_HEADER} has no v1 signature: there is nothing to check")
    return stamp, candidates
