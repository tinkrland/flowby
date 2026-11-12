import { test } from "node:test";
import assert from "node:assert/strict";
import { client, baseUrl, Unreachable, Refused } from "../src/api.mjs";

const reply = (status, body, text) => async () => ({ ok: status >= 200 && status < 300, status, text: async () => text ?? (body === undefined ? "" : JSON.stringify(body)) });

test("a fetch that throws is Unreachable, which is not the same as the server saying no", async () => {
  const c = client({ base: "http://x", fetcher: async () => { throw new TypeError("fetch failed"); } });
  await assert.rejects(c.plugs(), (e) => e instanceof Unreachable && /not answering at http:\/\/x/.test(e.message));
});

test("a refusal from python becomes a thrown sentence with its status", async () => {
  const c = client({ fetcher: reply(422, { refused: "http over the internet sends your token in the clear" }) });
  await assert.rejects(c.addPlug({}), (e) => e instanceof Refused && e.status === 422 && /in the clear/.test(e.message));
});

test("a 404 with an html body is the dev server saying it has no such route, so the server is not there", async () => {
  const c = client({ fetcher: reply(404, undefined, "<!doctype html><html>not found</html>") });
  await assert.rejects(c.plugs(), (e) => e instanceof Unreachable);
});

test("a 404 from python with its own sentence is a refusal, not an absence", async () => {
  const c = client({ fetcher: reply(404, { refused: "there is no such route" }) });
  await assert.rejects(c.get("/api/x"), (e) => e instanceof Refused && e.status === 404);
});

test("a 200 that is not json is treated as no server rather than as an empty list", async () => {
  const c = client({ fetcher: reply(200, undefined, "<html>spa fallback</html>") });
  await assert.rejects(c.plugs(), (e) => e instanceof Unreachable);
});

test("a 500 with no sentence still says what happened", async () => {
  const c = client({ fetcher: reply(500, undefined, "boom") });
  await assert.rejects(c.plugs(), (e) => e instanceof Refused && /answered 500/.test(e.message));
});

test("requests carry no credentials, no cache, and json only when there is a body", async () => {
  const seen = [];
  const c = client({ base: "http://h", fetcher: async (url, init) => { seen.push({ url, init }); return reply(200, { plugs: [] })(); } });
  await c.plugs();
  await c.checkPlug("plug-1");
  assert.equal(seen[0].url, "http://h/api/plugs");
  assert.deepEqual(seen[0].init.headers, {});
  assert.equal(seen[0].init.body, undefined);
  assert.equal(seen[1].init.headers["Content-Type"], "application/json");
  assert.equal(seen[1].init.body, JSON.stringify({ id: "plug-1" }));
  for (const s of seen) assert.deepEqual([s.init.credentials, s.init.cache], ["omit", "no-store"]);
});

test("the token is in the request body and nowhere in the url", async () => {
  let seen;
  const c = client({ base: "http://h", fetcher: async (url, init) => { seen = { url, init }; return reply(200, { plug: {}, plugs: [] })(); } });
  await c.addPlug({ label: "x", provider: "vultr", endpoint: "https://a.b", token: "tok_secret_123" });
  assert.equal(seen.url.includes("tok_secret"), false);
  assert.equal(JSON.parse(seen.init.body).token, "tok_secret_123");
});

test("the base url loses a trailing slash and defaults to same origin", () => {
  assert.equal(baseUrl({}), "");
  assert.equal(baseUrl({ VITE_FLOWBY_API: "http://127.0.0.1:8765///" }), "http://127.0.0.1:8765");
  assert.equal(baseUrl({ VITE_FLOWBY_API: "   " }), "");
});

test("a successful answer is returned as parsed", async () => {
  const c = client({ fetcher: reply(200, { plugs: [{ id: "a" }], providers: {}, auth: "x" }) });
  assert.deepEqual((await c.plugs()).plugs, [{ id: "a" }]);
});
