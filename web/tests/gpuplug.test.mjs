/**
 * gpuplug.test.mjs: what the corner plug says, and the one thing it must never say.
 *
 * the rule from the owner is that "connected" is shown only after a health check succeeded. python
 * enforces that; these tests enforce that the page cannot fake it on its own: no state, form or
 * half-built plug produces a green dot or the word "connected" unless python said `up`.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import * as g from "../src/gpuplug.mjs";

const plug = (over = {}) => ({ id: "plug-1", label: "vultr a100", provider: "vultr", provider_label: "Vultr Cloud GPU", endpoint: "https://gpu.example.com", state: "unchecked", detail: "not checked yet", models: [], version: null, checked_at: null, latency_ms: null, has_token: false, ...over });

// --- the rule ---------------------------------------------------------------------------------

test("only the state `up` is ever green or called connected", () => {
  for (const state of ["unchecked", "down", "", null, undefined, "UP", "connected", "ok", "true", 1, {}, "up "]) {
    const d = g.dotFor(state);
    assert.notEqual(d.hex, g.DOT.up.hex, `${JSON.stringify(state)} produced the green dot`);
    assert.notEqual(d.word, "connected", `${JSON.stringify(state)} was called connected`);
  }
  assert.equal(g.dotFor("up").word, "connected");
});

test("an unknown state reads as unchecked, never as a guess in either direction", () => {
  assert.deepEqual(g.dotFor("who knows"), g.DOT.unchecked);
});

test("a row for a plug that was never checked is grey and offers to check, not to check again", () => {
  const r = g.rowOf(plug());
  assert.equal(r.dot.hex, g.DOT.unchecked.hex);
  assert.equal(r.action, "check");
});

test("a row for a plug with models listed but state down is red: models alone do not make it connected", () => {
  const r = g.rowOf(plug({ state: "down", models: ["flux-dev"], detail: "the server refused the token" }));
  assert.equal(r.dot.hex, g.DOT.down.hex);
  assert.equal(r.action, "check again");
});

test("a plug that is up but whose last check is old is stale and the page can say so", () => {
  const now = 1_000_000_000_000;
  assert.equal(g.isStale(plug({ state: "up", checked_at: now / 1000 - 10 }), now), false);
  assert.equal(g.isStale(plug({ state: "up", checked_at: now / 1000 - 600 }), now), true);
  assert.equal(g.isStale(plug({ state: "down", checked_at: now / 1000 - 600 }), now), false, "only a green can go stale");
  assert.equal(g.isStale(plug({ state: "up", checked_at: null }), now), false);
});

// --- the button -------------------------------------------------------------------------------

test("with no plugs the button invites one and is not green", () => {
  const b = g.buttonState([]);
  assert.deepEqual([b.label, b.tone], ["plug a gpu", "idle"]);
});

test("the button turns green only when at least one plug is up", () => {
  assert.equal(g.buttonState([plug({ state: "up", models: ["flux-dev"] })]).tone, "up");
  for (const states of [["unchecked"], ["down"], ["down", "unchecked"], []]) {
    assert.notEqual(g.buttonState(states.map((s) => plug({ state: s }))).tone, "up", states.join());
  }
});

test("a plug that lists models but is not up never turns the button green or counts as a gpu up", () => {
  // the models list can be stale: it was filled by an earlier successful check, and the server may
  // since have gone. the models are evidence of the PAST; only the state says anything about now.
  for (const state of ["down", "unchecked"]) {
    const b = g.buttonState([plug({ state, models: ["flux-dev", "llama"] })]);
    assert.notEqual(b.tone, "up", state);
    // "no gpu up" is the honest negative and contains the word, so the test looks for the claims:
    // "1 gpu up", "3 gpus up", "connected". a label that starts with a count is a claim.
    assert.doesNotMatch(b.label, /^\d+ gpus? up$/, `${state}: ${b.label}`);
    assert.doesNotMatch(b.label, /connected/, `${state}: ${b.label}`);
    assert.doesNotMatch(b.title, /serving/, `${state} claimed to be serving ${b.title}`);
  }
});

test("the button counts the plugs that are up, not the plugs there are", () => {
  const b = g.buttonState([plug({ state: "up" }), plug({ id: "2", state: "down" }), plug({ id: "3", state: "up" })]);
  assert.equal(b.label, "2 gpus up");
  assert.equal(g.buttonState([plug({ state: "up" }), plug({ id: "2", state: "down" })]).label, "1 gpu up");
});

test("the button lists what the up plugs serve, once each, and says when it is nothing yet", () => {
  const b = g.buttonState([plug({ state: "up", models: ["flux-dev", "llama"] }), plug({ id: "2", state: "up", models: ["flux-dev"] })]);
  assert.match(b.title, /serving flux-dev, llama$/);
  assert.match(g.buttonState([plug({ state: "up", models: [] })]).title, /not serving a model yet/);
});

test("when every plug failed the button says no gpu is up, which is not the same as none plugged", () => {
  assert.equal(g.buttonState([plug({ state: "down" })]).label, "no gpu up");
  assert.equal(g.buttonState([plug({ state: "unchecked" })]).label, "gpu not checked");
});

test("when the page cannot reach python the button says so, and is never green or idle", () => {
  const b = g.buttonState([plug({ state: "up" })], { reachable: false });
  assert.equal(b.tone, "off");
  assert.match(b.title, /server is not running/);
});

// --- the form ---------------------------------------------------------------------------------

const form = (over = {}) => ({ ...g.EMPTY_FORM, label: "my gpu", endpoint: "https://gpu.example.com", ...over });

test("a complete form with a public https address has no hints and can be submitted", () => {
  assert.deepEqual(g.hints(form()), []);
  assert.equal(g.canSubmit(form()), true);
});

test("an empty form says what is missing, field by field", () => {
  const fields = g.hints(g.EMPTY_FORM).map((h) => h.field);
  assert.deepEqual(fields.sort(), ["endpoint", "label"]);
  assert.equal(g.canSubmit(g.EMPTY_FORM), false);
});

test("http over the internet is caught at the field, and http to localhost (an ssh tunnel) is not", () => {
  assert.match(g.hints(form({ endpoint: "http://45.32.10.20:8000" }))[0].say, /in the clear/);
  for (const ok of ["http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"]) assert.deepEqual(g.hints(form({ endpoint: ok })), [], ok);
});

test("credentials, paths, queries and other schemes in the address are caught", () => {
  assert.match(g.hints(form({ endpoint: "https://u:p@gpu.example.com" }))[0].say, /token in its own field/);
  for (const bad of ["https://gpu.example.com/v1", "https://gpu.example.com/?a=1", "https://gpu.example.com/#x"]) assert.match(g.hints(form({ endpoint: bad }))[0].say, /base address only/, bad);
  assert.match(g.hints(form({ endpoint: "ftp://gpu.example.com" }))[0].say, /not something flowby speaks/);
  assert.match(g.hints(form({ endpoint: "gpu.example.com" }))[0].say, /start with https/);
});

test("a token with a line break is caught", () => {
  assert.equal(g.hints(form({ token: "abc\ndef" })).some((h) => h.field === "token"), true);
});

test("the hints are only a courtesy: a private address passes them, because python has the last word", () => {
  // the page cannot know what a name resolves to, and must not pretend a clean form is a safe one
  assert.deepEqual(g.hints(form({ endpoint: "https://10.0.0.5" })), []);
});

test("isLoopback is true for the three loopback forms and false for lookalikes", () => {
  // 127.1 is here on purpose: the url parser normalises it to 127.0.0.1, which is loopback to the os too
  for (const yes of ["http://localhost", "http://127.0.0.1:1", "http://127.9.9.9", "http://[::1]:8000", "http://127.1"]) assert.equal(g.isLoopback(yes), true, yes);
  for (const no of ["http://localhost.evil.com", "http://127.0.0.1.evil.com", "http://127.0.0.1.nip.io", "http://127.0.0.300", "http://10.0.0.1", "not a url", ""]) assert.equal(g.isLoopback(no), false, no);
});

test("the request body carries the token once and omits the field when none was typed", () => {
  assert.equal(g.body(form({ token: "  tok_abc  " })).token, "tok_abc");
  assert.equal("token" in g.body(form({ token: "   " })), false);
  assert.equal("token" in g.body(form()), false);
});

test("the body is trimmed and carries the tunnel flag as a boolean", () => {
  const b = g.body(form({ label: "  my gpu ", endpoint: " https://gpu.example.com ", tunnel: 1 }));
  assert.deepEqual([b.label, b.endpoint, b.tunnel], ["my gpu", "https://gpu.example.com", true]);
});

test("clearing the form leaves no token behind and does not share the frozen original", () => {
  const typed = form({ token: "tok_secret" });
  const cleared = g.clear();
  assert.equal(cleared.token, "");
  assert.equal(JSON.stringify(cleared).includes("tok_secret"), false);
  cleared.label = "changed";
  assert.equal(g.EMPTY_FORM.label, "", "the shared empty form was mutated");
  assert.equal(typed.token, "tok_secret", "clear must not reach into the old form");
});

// --- the row ----------------------------------------------------------------------------------

test("a row never carries a token, only whether one is held", () => {
  const r = g.rowOf(plug({ has_token: true }));
  assert.equal(r.hasToken, true);
  assert.equal(JSON.stringify(r).includes("tok_"), false);
  assert.equal(Object.keys(r).some((k) => /^token$/i.test(k)), false);
});

test("a row shows provider, address, latency and models exactly as python gave them", () => {
  const r = g.rowOf(plug({ state: "up", models: ["flux-dev"], version: "0.11.2", latency_ms: 84, detail: "answered in 84 ms, serving flux-dev" }));
  assert.equal(r.sub, "Vultr Cloud GPU · https://gpu.example.com");
  assert.deepEqual([r.latency, r.version, r.models], ["84 ms", "0.11.2", ["flux-dev"]]);
  assert.equal(g.rowOf(plug()).latency, null);
});

test("the age of a check reads naturally and never says a future time", () => {
  const now = new Date("2026-11-09T12:00:00Z").getTime();
  const at = (s) => new Date(now - s * 1000);
  assert.equal(g.ago(null, now), "never");
  assert.equal(g.ago(at(2), now), "just now");
  assert.equal(g.ago(at(30), now), "30s ago");
  assert.equal(g.ago(at(300), now), "5 min ago");
  assert.equal(g.ago(at(7200), now), "2 h ago");
  assert.equal(g.ago(new Date(now + 5000), now), "just now", "a clock skew must not print a negative");
});

// --- hosted vendors (fal.ai) vs machines you rent ---------------------------------------------

const PROVIDERS = {
  vultr: { kind: "server", label: "Vultr Cloud GPU" },
  azure: { kind: "server", label: "Microsoft Azure" },
  fal: { kind: "hosted", label: "fal.ai" },
};
const hostedPlug = (over = {}) => plug({ id: "plug-9", label: "flux on fal", provider: "fal", provider_label: "fal.ai", kind: "hosted", endpoint: "https://queue.fal.run/fal-ai/flux/schnell", has_token: true, ...over });
const fform = (over = {}) => ({ ...g.EMPTY_FORM, label: "flux", provider: "fal", endpoint: "https://queue.fal.run/fal-ai/flux/schnell", token: "k", ...over });

test("a provider the page was not told about is a server, the stricter kind", () => {
  assert.equal(g.kindOf("nope", PROVIDERS), "server");
  assert.equal(g.kindOf("fal", undefined), "server");
  assert.equal(g.kindOf("fal", PROVIDERS), "hosted");
  assert.equal(g.kindOf("azure", PROVIDERS), "server");
});

test("a hosted endpoint needs an owner and an app, and a server address must not have a path", () => {
  assert.equal(g.canSubmit(fform(), PROVIDERS), true);
  assert.equal(g.canSubmit(fform({ endpoint: "https://queue.fal.run" }), PROVIDERS), false);
  assert.equal(g.canSubmit(fform({ endpoint: "https://queue.fal.run/only" }), PROVIDERS), false);
  const server = { ...g.EMPTY_FORM, label: "a", provider: "azure", endpoint: "https://gpu.example.com:8000/fal-ai/x" };
  assert.equal(g.canSubmit(server, PROVIDERS), false, "a path on a server address still says the base only");
});

test("a hosted endpoint is https only, with no query, and credentials are still refused", () => {
  assert.equal(g.canSubmit(fform({ endpoint: "http://queue.fal.run/a/b" }), PROVIDERS), false);
  assert.equal(g.canSubmit(fform({ endpoint: "https://queue.fal.run/a/b?x=1" }), PROVIDERS), false);
  assert.equal(g.canSubmit(fform({ endpoint: "https://u:p@queue.fal.run/a/b" }), PROVIDERS), false);
});

test("http to localhost is no excuse for a hosted vendor", () => {
  assert.equal(g.canSubmit(fform({ endpoint: "http://127.0.0.1:8000/a/b" }), PROVIDERS), false);
});

test("the form speaks of a key and hides the tunnel for a hosted vendor, and the reverse for a server", () => {
  const hosted = g.formWords("fal", PROVIDERS);
  assert.equal(hosted.tunnel, false);
  assert.match(hosted.tokenLabel, /key/);
  assert.match(hosted.after, /no free check/);
  const server = g.formWords("azure", PROVIDERS);
  assert.equal(server.tunnel, true);
  assert.match(server.after, /press check/);
});

test("a hosted plug never sends tunnel=true, even if the box was ticked before the provider changed", () => {
  assert.equal(g.body(fform({ tunnel: true }), PROVIDERS).tunnel, false);
  assert.equal(g.body({ ...fform({ tunnel: true }), provider: "azure" }, PROVIDERS).tunnel, true);
});

test("a hosted row offers no check, because there is nothing free to ask, and it is never green", () => {
  const row = g.rowOf(hostedPlug());
  assert.equal(row.action, null);
  assert.equal(row.hosted, true);
  assert.equal(row.dot.hex, g.DOT.unchecked.hex);
  assert.notEqual(row.dot.word, "connected");
});

test("a server row still offers check, and check again once it has been asked", () => {
  assert.equal(g.rowOf(plug()).action, "check");
  assert.equal(g.rowOf(plug({ state: "up" })).action, "check again");
});

test("the corner button for only hosted plugs says they are not checked, never that a gpu is up", () => {
  const b = g.buttonState([hostedPlug()]);
  assert.equal(b.label, "hosted, not checked");
  assert.equal(b.tone, "idle");
  assert.doesNotMatch(b.label, /up/);
});

test("a hosted plug beside a server that is up still reports only the server as up", () => {
  const b = g.buttonState([hostedPlug(), plug({ state: "up", models: ["flux-dev"] })]);
  assert.equal(b.label, "1 gpu up");
});

test("a hosted plug beside an unchecked server still tells you to check the server", () => {
  assert.equal(g.buttonState([hostedPlug(), plug()]).label, "gpu not checked");
});
