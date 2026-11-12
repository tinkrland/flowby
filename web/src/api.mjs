/**
 * api.mjs: the page's one way to talk to flowby's python server.
 *
 * two things it does that a bare fetch does not. it tells "the server is not there" apart from "the
 * server said no", because the page must never show an empty healthy list when it simply could not
 * reach python. and it turns python's `{refused: "..."}` into a thrown sentence the panel can print,
 * so a refusal reads as a sentence and not as a status code.
 *
 * nothing here stores a token or logs a body. a request body is built by the caller, sent, and gone.
 */

export class Unreachable extends Error {
  constructor(base) {
    super(`flowby's server is not answering at ${base || "this page's address"}`);
    this.name = "Unreachable";
  }
}

export class Refused extends Error {
  constructor(message, status) {
    super(message);
    this.name = "Refused";
    this.status = status;
  }
}

/** the server's address. same origin unless the page was told otherwise at build time. */
export function baseUrl(env = {}) {
  const given = (env.VITE_FLOWBY_API ?? "").trim().replace(/\/+$/, "");
  return given;
}

export function client({ base = "", fetcher = globalThis.fetch } = {}) {
  async function call(method, path, payload) {
    let response;
    try {
      response = await fetcher(`${base}${path}`, {
        method,
        headers: payload === undefined ? {} : { "Content-Type": "application/json" },
        body: payload === undefined ? undefined : JSON.stringify(payload),
        // the server is the page's own backend. no cookies, no ambient credentials, and no cache
        credentials: "omit",
        cache: "no-store",
      });
    } catch {
      throw new Unreachable(base);
    }
    let data = null;
    const text = await response.text();
    try { data = text ? JSON.parse(text) : null; } catch { /* a non-json answer is handled below */ }
    if (!response.ok) {
      if (data && typeof data.refused === "string") throw new Refused(data.refused, response.status);
      // a vite dev server answers 404 html for a route it does not have: that is "no server", not "refused"
      if (response.status === 404 && data === null) throw new Unreachable(base);
      throw new Refused(`the server answered ${response.status}`, response.status);
    }
    if (data === null) throw new Unreachable(base);
    return data;
  }
  return {
    get: (path) => call("GET", path),
    post: (path, payload = {}) => call("POST", path, payload),
    plugs: () => call("GET", "/api/plugs"),
    addPlug: (form) => call("POST", "/api/plugs/add", form),
    checkPlug: (id) => call("POST", "/api/plugs/check", { id }),
    removePlug: (id) => call("POST", "/api/plugs/remove", { id }),
    kits: () => call("GET", "/api/kits"),
  };
}
