/**
 * gpuplug.mjs: what the plug in the corner shows, decided without a DOM.
 *
 * python owns whether a gpu is reachable (plug.py: a real health check, and nothing else makes a
 * plug `up`). this file owns how that is SAID, and its one rule is the same one: a colour or a
 * word that means "connected" is only ever produced from a state python reported as `up`. there is
 * no path from "the form was filled in" or "the request was sent" to a green dot.
 *
 * the token is the other rule. a form holds it while it is typed, `body()` sends it once, and
 * `clear()` empties it. nothing here stores one, and nothing python sends back has one to store.
 */

export const STATES = Object.freeze(["unchecked", "up", "down"]);

/** the dot for a state. only `up` is green; an unchecked plug is grey, not amber, because it is not a warning. */
export const DOT = Object.freeze({
  up: { hex: "#4ade80", word: "connected" },
  down: { hex: "#f87171", word: "not reachable" },
  unchecked: { hex: "#71717a", word: "not checked yet" },
});

export function dotFor(state) {
  // an unknown state is treated as unchecked and never as up
  return DOT[state] ?? DOT.unchecked;
}

/**
 * the button in the corner. it says what is true of the whole set, from the plugs python listed.
 * `reachable` is false when the page could not talk to python at all, which is not the same as
 * "no gpu", and the button says so.
 */
export function buttonState(plugs, { reachable = true } = {}) {
  if (!reachable) return { label: "plug a gpu", tone: "off", title: "flowby's server is not running, so a gpu cannot be plugged in from this page" };
  const list = plugs ?? [];
  const up = list.filter((p) => p.state === "up");
  if (list.length === 0) return { label: "plug a gpu", tone: "idle", title: "connect a gpu you rent to run models on it" };
  if (up.length > 0) {
    const models = new Set(up.flatMap((p) => p.models ?? []));
    return {
      label: up.length === 1 ? "1 gpu up" : `${up.length} gpus up`,
      tone: "up",
      title: models.size ? `serving ${[...models].slice(0, 4).join(", ")}${models.size > 4 ? ` and ${models.size - 4} more` : ""}` : "connected, and not serving a model yet",
    };
  }
  const down = list.filter((p) => p.state === "down").length;
  if (!down && list.every((p) => p.kind === "hosted")) {
    return { label: "hosted, not checked", tone: "idle", title: "this vendor has no free check. the first real run is the proof" };
  }
  return {
    label: down ? "no gpu up" : "gpu not checked",
    tone: down ? "down" : "idle",
    title: down ? "every plug failed its last check" : "check a plug to find out if it answers",
  };
}

// --- the form ---------------------------------------------------------------------------------

export const EMPTY_FORM = Object.freeze({ label: "", provider: "other", endpoint: "", token: "", tunnel: false });

/** is this address a loopback one, which is what an ssh tunnel looks like and may be plain http */
export function isLoopback(endpoint) {
  try {
    const host = new URL(endpoint).hostname.replace(/^\[|\]$/g, "");
    // the whole host must be a dotted quad in 127.0.0.0/8. matching only the start let
    // 127.0.0.1.evil.com through, which is an attacker's name that merely begins like a loopback address
    const quad = host.match(/^127\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    return host === "localhost" || host === "::1" || Boolean(quad && quad.slice(1).every((n) => Number(n) <= 255));
  } catch {
    return false;
  }
}

/**
 * hints before a request is made. these are a courtesy so a typo is caught at the field; python
 * checks everything again and has the last word, so nothing here can make a bad address pass.
 * @returns {{field: string, say: string}[]}
 */
export function hints(form, providers) {
  const out = [];
  const hosted = kindOf(form.provider, providers) === "hosted";
  const endpoint = (form.endpoint ?? "").trim();
  if (!(form.label ?? "").trim()) out.push({ field: "label", say: "give it a name, so you can tell it from the next one" });
  if (!endpoint) {
    out.push({ field: "endpoint", say: "the address your model server answers at" });
  } else if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(endpoint)) {
    out.push({ field: "endpoint", say: "start with https://" });
  } else {
    let url;
    try { url = new URL(endpoint); } catch { out.push({ field: "endpoint", say: "that is not an address" }); }
    if (url) {
      if (url.username || url.password) out.push({ field: "endpoint", say: "put the token in its own field, not in the address" });
      else if (!hosted && url.protocol === "http:" && !isLoopback(endpoint)) out.push({ field: "endpoint", say: "http sends your token in the clear. use https, or tunnel to localhost over ssh" });
      else if (url.protocol !== "http:" && url.protocol !== "https:") out.push({ field: "endpoint", say: `${url.protocol}// is not something flowby speaks` });
      else if (hosted) {
        if (url.protocol !== "https:") out.push({ field: "endpoint", say: "https only, because your key goes with it" });
        else if (url.search || url.hash) out.push({ field: "endpoint", say: "the endpoint without a query" });
        else if (url.pathname.split("/").filter(Boolean).length < 2) out.push({ field: "endpoint", say: "add the owner and app, like /fal-ai/flux/schnell" });
      }
      else if (url.pathname !== "/" || url.search || url.hash) out.push({ field: "endpoint", say: "the base address only. flowby adds /health itself" });
    }
  }
  if (/[\r\n]/.test(form.token ?? "")) out.push({ field: "token", say: "a token is one line" });
  return out;
}

export function canSubmit(form, providers) {
  return hints(form, providers).length === 0;
}

/** server (a machine you rent, asked at /health) or hosted (a vendor's api, which flowby cannot ask for free).
 * an unknown or missing provider is a server: the stricter of the two, and the one that can be checked. */
export function kindOf(provider, providers) {
  return providers?.[provider]?.kind === "hosted" ? "hosted" : "server";
}

/** the words on the form for a kind. a hosted vendor has a key, an endpoint with a path, and no tunnel. */
export function formWords(provider, providers) {
  if (kindOf(provider, providers) === "hosted") {
    return {
      endpoint: "https://queue.fal.run/owner/app",
      tokenLabel: "key",
      tokenHint: "your vendor key. sent only to the vendor's own host",
      tunnel: false,
      submit: "plug in",
      after: "plugging in does not connect it, and this vendor has no free check. the first real run is the proof.",
    };
  }
  return {
    endpoint: "https://gpu.example.com:8000",
    tokenLabel: "token (optional)",
    tokenHint: "only if your server asks for one",
    tunnel: true,
    submit: "plug in",
    after: "plugging in does not connect it. press check on the plug to ask the server.",
  };
}

/** the request body. the token is included only when one was typed, and is the only place it travels. */
export function body(form, providers) {
  const out = { label: form.label.trim(), provider: form.provider, endpoint: form.endpoint.trim(), tunnel: kindOf(form.provider, providers) === "hosted" ? false : Boolean(form.tunnel) };
  if ((form.token ?? "").trim()) out.token = form.token.trim();
  return out;
}

/** after a submit the form is empty again, token included, whether it worked or not */
export function clear() {
  return { ...EMPTY_FORM };
}

// --- one plug, as a row -------------------------------------------------------------------------

export function rowOf(plug) {
  const dot = dotFor(plug.state);
  const hosted = plug.kind === "hosted";
  return {
    id: plug.id,
    title: plug.label,
    sub: `${plug.provider_label ?? plug.provider} · ${plug.endpoint}`,
    dot,
    detail: plug.detail,
    models: plug.models ?? [],
    version: plug.version ?? null,
    latency: plug.latency_ms == null ? null : `${plug.latency_ms} ms`,
    hasToken: Boolean(plug.has_token),
    checked: plug.checked_at ? new Date(plug.checked_at * 1000) : null,
    // "check" is always offered. what it is called depends on whether it has ever been asked
    // a hosted plug has nothing free to ask, so it offers no check that would only repeat "not checked"
    action: hosted ? null : plug.state === "unchecked" ? "check" : "check again",
    hosted,
  };
}

/** a short line for the age of a check, so a stale green is visible as stale */
export function ago(checkedAt, now = Date.now()) {
  if (!checkedAt) return "never";
  const s = Math.max(0, Math.round((now - checkedAt.getTime()) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  return `${Math.round(s / 3600)} h ago`;
}

/** how long an `up` may sit unrefreshed before the page calls it stale. a gpu can be switched off. */
export const STALE_AFTER_S = 120;

export function isStale(plug, now = Date.now()) {
  if (plug.state !== "up" || !plug.checked_at) return false;
  return now / 1000 - plug.checked_at > STALE_AFTER_S;
}
