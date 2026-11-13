# the flora door: proving a callback before believing it

FLORA finishes a generation or a Technique run asynchronously. Its docs let you pass a `callback_url`
per run instead of polling (`docs.flora.ai/api/platform/webhooks`), and every delivery is signed.
`src/flowby/flora.py` holds the checking half and `POST /api/flora/webhook` is the endpoint.

## the secret

One signing secret per FLORA workspace, starting `whsec_`. It is *not* an API key: FLORA's MCP and REST
accept `ak_` keys (older `flora_sk_`), and its MCP rejects a `whsec_` value with `invalid_token` /
`Invalid token format`. The same `whsec_` string is what a headless MCP client would use as a *bearer*
only in docs where the two are conflated; here they are separate doors.

`flora.secret_from` reads `FLORA_WEBHOOK_SECRET` first, then `FLORA_API_KEY`, because that is the name
this secret happens to be saved under. A blank value is not a value.

## what is checked, in order

1. a secret exists. Empty is refused as `NoSecret`, because anybody can compute an HMAC with an empty
   key, and "no key" must never mean "no check".
2. the body is `bytes`. A `str` is refused rather than encoded: the signed message is the timestamp, a
   literal dot, then the exact bytes that arrived, and re-serialising JSON changes them.
3. the header parses: an integer `t`, one or more `v1` values that are 64 lowercase hex characters.
   Other names (`v0`, a future `v2`) are ignored so a scheme can be added without a rewrite.
4. the timestamp is inside `REPLAY_WINDOW` (300s) in both directions. Old is a replay, future is a
   forged clock.
5. one offered `v1` matches, compared with `hmac.compare_digest` and without short-circuiting, so a
   rotation can offer the old and the new signature at once and timing says nothing.
6. the body is a JSON object with a `type` this flowby knows (`run.completed`, `run.failed`) and an
   `id` to dedupe on, because FLORA retries and the body is identical on every retry.

Answers: `202` accepted (with the event and its delivery id), `400` refused with one sentence, `503`
when no secret is configured. `202` rather than `200` on purpose: the delivery is believed, and nothing
has been fetched or marked done.

## what is not built

The dispatch half. The payload carries a run's identity and final status, not its outputs, so acting on
it means fetching the run by `data.run_id` and then recording it against a node. flowby has no FLORA
runner yet, so there is nothing to record into; the door is ready for the day there is.
