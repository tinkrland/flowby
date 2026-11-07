#!/usr/bin/env bash
# kernel.sh: what runs inside the disposable container, after the plan has been handed over.
#
# the contract is narrow on purpose. this script does not know what a node is. it reads a flattened
# plan, builds the python environment the plan asked for, keeps the heartbeat alive so the runtime
# is not reclaimed mid-job, walks the steps, bundles the results and posts them home.
#
#   kernel.sh --dry-run plan.json          print exactly what would happen, touch nothing
#   kernel.sh --plan plan.json             do it
#   FLOWBY_CALLBACK=https://host/hook/job kernel.sh --plan plan.json
#
# the heartbeat exists because the cheapest route here reclaims a runtime after 90 seconds of
# silence, which is faster than some model loads.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN=""
DRY_RUN=0
OUTDIR="${FLOWBY_OUTDIR:-out}"
CALLBACK="${FLOWBY_CALLBACK:-}"
BEAT_SECONDS="${FLOWBY_BEAT_SECONDS:-30}"

while [ $# -gt 0 ]; do
  case "$1" in
    --plan) PLAN="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --outdir) OUTDIR="${2:-}"; shift 2 ;;
    --callback) CALLBACK="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) echo "kernel.sh: unknown argument $1" >&2; exit 2 ;;
    *) PLAN="$1"; shift ;;
  esac
done

if [ -z "${PLAN}" ]; then
  echo "kernel.sh: --plan is required" >&2
  exit 2
fi
if [ ! -f "${PLAN}" ]; then
  echo "kernel.sh: no plan at ${PLAN}" >&2
  exit 2
fi

# one reader for the plan, so the rest of the script can stay about processes and not json
read_plan() {
  python3 - "$PLAN" "$1" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1]))
what = sys.argv[2]
if what == "env":
    for key, value in {
        "FLOWBY_JOB": plan["job_id"],
        "FLOWBY_CONTRACT": plan["contract"],
        "FLOWBY_ROUTE": plan["route"],
        "FLOWBY_GPU": "1" if plan["env"]["gpu"] else "0",
        "FLOWBY_PIP": " ".join(plan["env"]["pip"]),
        "FLOWBY_MODELS": " ".join(plan["env"]["models"]),
    }.items():
        print(f"{key}={value}")
elif what == "steps":
    for index, step in enumerate(plan["steps"], start=1):
        wires = ", ".join(f"{k}<-{v}" for k, v in step["inputs"].items()) or "no inputs"
        print(f"  {index:>2}/{len(plan['steps'])} {step['id']}  {step['op']}  [{wires}]")
elif what == "pip":
    print("\n".join(plan["env"]["pip"]))
elif what == "counts":
    print(f"{len(plan['steps'])} {len(plan['artifacts'])}")
PY
}

EVAL="$(read_plan env)"
# shellcheck disable=SC2086
export $(echo "${EVAL}" | tr '\n' ' ')
read -r STEP_COUNT ARTIFACT_COUNT <<<"$(read_plan counts)"

echo "flowby kernel: job ${FLOWBY_JOB} on ${FLOWBY_ROUTE}, ${STEP_COUNT} steps, ${ARTIFACT_COUNT} artifacts"
echo "  contract ${FLOWBY_CONTRACT}, gpu ${FLOWBY_GPU}"
read_plan steps

if [ "${DRY_RUN}" -eq 1 ]; then
  if [ -n "${FLOWBY_PIP}" ]; then
    echo "  would install: ${FLOWBY_PIP}"
  fi
  if [ -n "${FLOWBY_MODELS}" ]; then
    echo "  would resolve: ${FLOWBY_MODELS}"
  fi
  echo "  would write:   ${OUTDIR}/ and post the manifest back"
  exit 0
fi

# the heartbeat. a runtime that goes quiet is a runtime that gets reclaimed, and the failure looks
# like a network error rather than a timeout, so it is worth the four lines.
BEAT_PID=""
cleanup() {
  if [ -n "${BEAT_PID}" ]; then kill "${BEAT_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
if [ -n "${CALLBACK}" ]; then
  (
    while true; do
      curl -fsS -X POST "${CALLBACK}/beat" -d "{\"job\":\"${FLOWBY_JOB}\"}" \
        -H 'content-type: application/json' >/dev/null 2>&1 || true
      sleep "${BEAT_SECONDS}"
    done
  ) &
  BEAT_PID=$!
fi

if [ -n "${FLOWBY_PIP}" ]; then
  echo "installing: ${FLOWBY_PIP}"
  # shellcheck disable=SC2086
  read_plan pip | while read -r requirement; do
    [ -n "${requirement}" ] || continue
    python3 -m pip install --quiet --no-input "${requirement}"
  done
fi

mkdir -p "${OUTDIR}"
SIMULATE_FLAG=""
if [ "${FLOWBY_REAL:-0}" != "1" ]; then
  # no model is installed, so the plumbing runs and the pixels do not. see kernel/worker.py.
  SIMULATE_FLAG="--simulate"
fi

PYTHONPATH="${HERE}/../src${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 "${HERE}/worker.py" --plan "${PLAN}" --outdir "${OUTDIR}" ${SIMULATE_FLAG} --tar

if [ -n "${CALLBACK}" ]; then
  echo "posting $(wc -c <"${OUTDIR}/manifest.json") bytes of manifest and ${OUTDIR}/scene.tar back"
  curl -fsS -X POST "${CALLBACK}/complete" \
    -H 'content-type: application/json' \
    --data-binary @"${OUTDIR}/manifest.json" || {
      echo "kernel.sh: the plan ran and the post failed. the tar is at ${OUTDIR}/scene.tar" >&2
      exit 1
    }
fi

echo "flowby kernel: done"
