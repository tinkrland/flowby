/**
 * panel.mjs: the state of the "new node" panel, as a reducer with no DOM.
 *
 * the panel has two doors, upload and figma, and one outcome: elements the board can hold. what the
 * user sees at any moment is a function of this state, and what can go wrong is decided here, so
 * `tests/panel.test.mjs` can drive a whole import from node and `Panel.tsx` is only a skin.
 *
 * the figma token is the one thing in here that must not leak, so its rules are structural:
 *
 *   - it lives in this state, in memory, and nowhere else. there is no localStorage, no cookie, no
 *     url parameter and no log line anywhere in the panel's code, and a test reads the source to
 *     keep it that way.
 *   - `view()` is what the interface renders, and it never contains the token, only whether one is
 *     set and its last four characters so the user can tell which one it is.
 *   - the only function that reads it is `figmaClient`, and that function only ever talks to
 *     api.figma.com. a url that points anywhere else is refused before the token is attached.
 *   - closing the panel clears it.
 */

import * as intake from "./intake.mjs";

export const FIGMA_API = "https://api.figma.com";
const MAX_QUEUE = 40;

export const initial = () => ({
  open: false,
  door: "upload",               // "upload" | "figma"
  queue: [],                    // files accepted but not yet placed: { id, name, status, ... }
  placed: [],                   // elements handed to the board, newest last
  refused: [],                  // { name, reason }: never silently lost
  figma: { link: "", token: "", seat: "view", frames: [], missing: [], picked: [], step: "link", error: null, cost: null },
  seq: 0,
});

// --- reducer --------------------------------------------------------------------------------

export function reduce(state, action) {
  switch (action.type) {
    case "open": return { ...state, open: true, door: action.door ?? state.door };
    case "close":
      // closing forgets the token. a panel left open overnight is not a place to leave a credential.
      return { ...initial(), placed: state.placed, refused: [] };
    case "door": return { ...state, door: action.door };

    case "files": {
      let seq = state.seq;
      const accepted = [], refused = [];
      for (const f of action.files) {
        if (state.queue.length + accepted.length >= MAX_QUEUE) {
          refused.push({ name: f.name, reason: `the queue holds ${MAX_QUEUE} files. place some first` });
          continue;
        }
        try {
          const plan = intake.classify({ name: f.name, bytes: f.bytes });
          accepted.push({
            id: `q${++seq}`, name: f.name, bytes: f.bytes, type: plan.type, kind: plan.kind,
            via: plan.via, warning: plan.warning, note: plan.note, status: "ready",
          });
        } catch (e) {
          refused.push({ name: f.name, reason: e.message });
        }
      }
      return { ...state, seq, queue: [...state.queue, ...accepted], refused: [...state.refused, ...refused] };
    }

    case "unpacked": {
      // a zip was opened: its images replace it in the queue, and anything inside that is not an
      // image is refused by name instead of vanishing.
      const rest = state.queue.filter((q) => q.id !== action.id);
      let seq = state.seq;
      const accepted = [], refused = [];
      for (const f of action.files) {
        try {
          const plan = intake.classify({ name: f.name, bytes: f.bytes });
          if (plan.via === "unpack") throw new intake.IntakeRefused("a zip inside a zip is not opened");
          accepted.push({ id: `q${++seq}`, name: f.name, bytes: f.bytes, type: plan.type, kind: plan.kind, via: plan.via, warning: plan.warning, note: plan.note, status: "ready" });
        } catch (e) { refused.push({ name: f.name, reason: e.message }); }
      }
      return { ...state, seq, queue: [...rest, ...accepted], refused: [...state.refused, ...refused] };
    }

    case "unqueue": return { ...state, queue: state.queue.filter((q) => q.id !== action.id) };
    case "dismiss": return { ...state, refused: state.refused.filter((_, i) => i !== action.index) };

    case "placed":
      return {
        ...state,
        queue: state.queue.filter((q) => !action.ids.includes(q.id)),
        placed: [...state.placed, ...action.elements],
        refused: [...state.refused, ...(action.failed ?? []).map((f) => ({ name: f.name ?? f.id, reason: f.reason }))],
      };

    // --- figma ---
    case "figma-link": return patchFigma(state, { link: action.link, error: null });
    case "figma-token": return patchFigma(state, { token: action.token });
    case "figma-seat": return patchFigma(state, { seat: action.seat });

    case "figma-parsed": return patchFigma(state, { step: "token", error: null, parsed: action.parsed });
    case "figma-frames": {
      let cost = null, error = null;
      try { cost = intake.planImport(Math.max(1, action.frames.length), { seat: state.figma.seat }); } catch (e) { error = e.message; }
      return patchFigma(state, { step: "pick", frames: action.frames, missing: action.missing ?? [], picked: [], cost, error });
    }
    case "figma-pick": {
      const picked = state.figma.picked.includes(action.id)
        ? state.figma.picked.filter((x) => x !== action.id)
        : [...state.figma.picked, action.id];
      return patchFigma(state, { picked, ...recost(state.figma, picked) });
    }
    case "figma-pick-all": {
      const picked = action.ids ?? state.figma.frames.map((f) => f.id);
      return patchFigma(state, { picked, ...recost(state.figma, picked) });
    }
    case "figma-error": return patchFigma(state, { error: action.error });
    case "figma-reset": return patchFigma(state, { step: "link", frames: [], missing: [], picked: [], error: null, cost: null, parsed: undefined });

    default: throw new Error(`panel: ${action.type} is not an action`);
  }
}

function patchFigma(state, patch) { return { ...state, figma: { ...state.figma, ...patch } }; }

function recost(figma, picked) {
  if (!picked.length) return { cost: null, error: null };
  try { return { cost: intake.planImport(picked.length, { seat: figma.seat }), error: null }; }
  catch (e) { return { cost: null, error: e.message }; }
}

// --- what the interface sees ----------------------------------------------------------------

/** the token, reduced to what a person needs to recognise it by. */
export function mask(token) {
  if (!token) return null;
  return token.length <= 8 ? "••••" : `••••${token.slice(-4)}`;
}

/** everything the panel renders, with the token replaced by `mask`. nothing else reaches the dom. */
export function view(state) {
  const { token, ...figma } = state.figma;
  return {
    open: state.open, door: state.door,
    queue: state.queue.map(({ bytes, ...q }) => ({ ...q, size: bytes.length })),
    placed: state.placed.length, refused: state.refused,
    figma: { ...figma, hasToken: Boolean(token), token: mask(token) },
    canPlace: state.queue.some((q) => q.status === "ready" && q.via !== "unpack" && q.via !== "refuse"),
    canImport: state.figma.step === "pick" && state.figma.picked.length > 0 && !state.figma.error,
  };
}

// --- the figma client -----------------------------------------------------------------------

/**
 * a client that holds the token in a closure and can only reach api.figma.com. `fetchFn` is
 * injected, so a test can prove which urls it would call and that it attached the token to none
 * other than figma's.
 */
export function figmaClient({ token, fetchFn = globalThis.fetch }) {
  if (!token) throw new intake.IntakeRefused("a figma token is needed to read a file");
  const get = async (path) => {
    const url = new URL(path, FIGMA_API);
    // a backstop, not a tested feature: the key, id and scale checks below make every path this
    // client builds safe, so no public input reaches this line (deleting it fails no test, and
    // that was checked). it stays so the next method someone adds, if it builds a path
    // without validating, still cannot aim the token anywhere but figma.
    if (url.origin !== FIGMA_API) throw new intake.IntakeRefused(`${url.origin} is not figma's api, so the token is not sent there`);
    const res = await fetchFn(url.toString(), { headers: { "X-Figma-Token": token } });
    if (res.status === 403) throw new intake.IntakeRefused("figma rejected the token, or it cannot see this file");
    if (res.status === 404) throw new intake.IntakeRefused("figma could not find that file or node");
    if (res.status === 429) {
      const wait = res.headers?.get?.("retry-after");
      throw new intake.IntakeRefused(`figma says slow down${wait ? `: retry in ${wait}s` : ""}. this seat's budget may be spent`);
    }
    if (!res.ok) throw new intake.IntakeRefused(`figma answered ${res.status}`);
    return res.json();
  };
  // the origin check keeps the token on figma. these keep it on the endpoint that was meant: a file
  // key spliced into a path could otherwise climb it ("a/../../x" fetches /v1/x), and the key comes
  // from a link a person pasted. a real key is 10 to 40 letters and digits, a real node id is
  // digits with colons, and anything else is refused before a request exists.
  const key = (k) => {
    if (!/^[A-Za-z0-9]{10,40}$/.test(String(k))) throw new intake.IntakeRefused(`${JSON.stringify(String(k)).slice(0, 40)} is not a figma file key`);
    return k;
  };
  const nodeIds = (ids) => {
    const bad = ids.find((id) => !/^\d+:\d+(;\d+:\d+)*$/.test(String(id)));
    if (bad !== undefined) throw new intake.IntakeRefused(`${JSON.stringify(String(bad)).slice(0, 40)} is not a figma node id`);
    return encodeURIComponent(ids.join(","));
  };
  const scaleOf = (n) => {
    if (!(n >= 0.01 && n <= 4)) throw new intake.IntakeRefused(`scale ${n} is outside figma's 0.01 to 4`);
    return n;
  };
  return {
    // async, so a refusal is always a rejection. a caller should not have to handle a throw from
    // building the path and a rejection from the request as two different things.
    nodes: async (fileKey, ids) => get(`/v1/files/${key(fileKey)}/nodes?ids=${nodeIds(ids)}&depth=2`),
    file: async (fileKey) => get(`/v1/files/${key(fileKey)}?depth=2`),
    images: async (fileKey, ids, scale = 2) =>
      get(`/v1/images/${key(fileKey)}?ids=${nodeIds(ids)}&format=png&scale=${scaleOf(scale)}`),
  };
}

/** read a nodes or file response into the frame list the picker shows. */
export function framesFromResponse(response, wanted = null) {
  if (response?.nodes) return intake.framesOf(response, wanted);
  if (response?.document) return intake.framesOf({ nodes: { root: { document: response.document } } });
  throw new intake.IntakeRefused("figma returned neither a file nor a nodes map");
}

/**
 * place what is picked: one images call per batch (never per frame), then copy the bytes in.
 * `download` fetches an exported image and must not carry the figma token, since the exported
 * urls are signed storage links and not figma's api.
 */
export async function importPicked({ client, parsed, frames, picked, download, seat, subtle }) {
  const cost = intake.planImport(picked.length, { seat });
  const chosen = frames.filter((f) => picked.includes(f.id));
  const out = { elements: [], failed: [], requests: 0, cost };
  for (let i = 0; i < chosen.length; i += intake.IMAGE_BATCH) {
    const batch = chosen.slice(i, i + intake.IMAGE_BATCH);
    // one scale per batch, chosen from its largest frame, so none is quietly shrunk by figma
    const scale = Math.min(...batch.map((f) => intake.exportScale(f).scale));
    const response = await client.images(parsed.fileKey, batch.map((f) => f.id), scale);
    out.requests += 1;
    const urls = intake.imageUrls(response, batch.map((f) => f.id));
    const got = await intake.importFrames({ frames: batch, urls, fetchBytes: download, file: parsed, subtle });
    out.elements.push(...got.elements);
    out.failed.push(...got.failed);
  }
  return out;
}
