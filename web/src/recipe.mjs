/**
 * recipe.mjs: the card a recipe gets, decided without a DOM.
 *
 * python owns the card (recipes.card) and this file only arranges it for reading, so there is exactly
 * one place that decides *what the card claims*. the three claims worth a test:
 *
 *   a required mark appears only where required is true, because a mark that decorates a control with a
 *   saved example teaches people to ignore marks;
 *   a setting the chain fixes is drawn as FIXED and never as a control, so nobody hunts for a slider the
 *   recipe does not have;
 *   a run that cannot go says what is blocking it. "disabled" with no reason is the same as "broken".
 */

/** the string a value is drawn as, without lying about a missing one */
function show(value) {
  if (value === null || value === undefined) return "nothing saved";
  if (typeof value === "string") return value === "" ? "empty" : value;
  return String(value);
}

/** one card, arranged into the blocks the panel draws, in reading order. */
export function cardView(card) {
  if (!card || typeof card !== "object" || !card.name) return null;

  const inputs = (card.inputs ?? []).map((input) => ({
    label: input.label,
    // the mark is a fact about the card, not a style: required means nothing to fall back on
    mark: input.required ? "*" : "",
    required: input.required === true,
    example: input.example ? show(input.example.value) : "nothing saved",
    means: input.means ?? "",
    where: input.target ? `${input.target.preset}.${input.target.param}` : "",
  }));

  const slots = (card.slots ?? []).map((slot) => ({
    label: `${slot.slot} slot on ${slot.preset}`,
    mark: slot.required ? "*" : "",
    required: slot.required === true,
    filled: slot.filled === true,
    means: slot.filled ? "wired" : "nothing in it",
  }));

  const advanced = (card.advanced ?? []).map((row) => ({
    label: row.name,
    value: show(row.value),
    means: row.means ?? "",
  }));

  // `fixed` is the honest name: the chain sets this and the card cannot change it
  const fixed = (card.hidden ?? []).map((row) => ({
    label: row.name,
    where: row.preset,
    value: show(row.value),
    means: row.means ?? "runs at its saved value",
  }));

  const needs = card.needs ?? {};
  const needRows = [];
  if (needs.runtime) needRows.push({ key: "runtime", says: `${needs.runtime}${needs.gpu ? ", on a gpu" : ""}` });
  if (needs.weights?.length) needRows.push({ key: "weights", says: needs.weights.join(", ") });
  if (needs.files?.length) needRows.push({ key: "files", says: needs.files.join("; ") });
  // cost is stated whether it is free or not: silence about money reads as free. a route can be free to
  // run while the weights it names are not, so those two are not allowed to collapse into "free".
  const routeFree = !needs.cost || String(needs.cost).toLowerCase() === "free";
  needRows.push({
    key: "cost",
    says: !needs.paid ? "free" : routeFree ? "free to run here, paid weights" : `costs (${needs.cost})`,
  });

  const blocked = card.run?.blocked_by ?? [];
  const enabled = card.run?.enabled !== false;
  const run = {
    label: card.run?.label || "run",
    enabled,
    // an unexplained disabled button is a bug the person cannot report
    why: enabled ? "" : blocked.length ? `blocked by ${blocked.join(" and ")}` : "this card cannot run",
  };

  return {
    name: card.name,
    stamp: card.version ? `v${card.version}${card.author ? ` · ${card.author}` : ""}` : "unsigned",
    brief: card.brief ?? "",
    output: card.output ?? "",
    category: card.category ?? "",
    inputs,
    slots,
    advanced,
    fixed,
    needs: needRows,
    run,
    // anything required at all, for a one-line summary at the top of the panel
    wanted: [...inputs, ...slots].filter((row) => row.required).length,
  };
}

/** the shelf: what is on this board, newest first is python's order and is kept. */
export function shelfView(recipes, { reachable = true } = {}) {
  if (!reachable) {
    return { rows: [], empty: "flowby's server is not running, so this board's recipes cannot be read", reachable };
  }
  const rows = (recipes ?? []).map((card) => ({
    element: card.element ?? "",
    name: card.name,
    version: card.version ? `v${card.version}` : "unsigned",
    brief: card.brief ?? "",
    output: card.output ?? "",
    // a chain with nothing required and nothing blocked is ready to run as it stands
    ready: card.run?.enabled !== false,
  }));
  return {
    rows,
    empty: rows.length ? "" : "no chains on this board yet: apply a preset to something and it becomes a recipe",
    reachable,
  };
}
