#!/usr/bin/env bash
# Manual regression: run API against a local checkout (server must already be up).
# Usage: BASE_URL=http://127.0.0.1:8000 REPO=/path/to/repo ./scripts/archaeology_smoke.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
REPO="${REPO:?Set REPO to a local directory path}"

echo "== analyze (persist + archaeology)"
ANALYZE_JSON="$(curl -fsS -X POST "${BASE_URL}/api/analysis/analyze" \
  -H 'Content-Type: application/json' \
  -d "{\"source\": \"${REPO}\", \"persist\": true, \"run_archaeology\": true}")"
AID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["analysis_id"])' "${ANALYZE_JSON}")"
RID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["repo_id"])' "${ANALYZE_JSON}")"
SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["commit_hash"])' "${ANALYZE_JSON}")"
echo "analysis_id=${AID} repo_id=${RID} commit=${SHA}"

SEARCH="${SEARCH:-bootstrap_env_keys}"
echo "== entities/search (by analysis_id, SEARCH=${SEARCH})"
curl -fsS "${BASE_URL}/api/analysis/entities/search?q=${SEARCH}&analysis_id=${AID}" | python3 -m json.tool | head -n 40

echo "== resolve (adjust FILE and LINE for your repo)"
FILE="${FILE:-README.md}"
LINE="${LINE:-1}"
RESOLVE_JSON="$(curl -fsS -X POST "${BASE_URL}/api/analysis/resolve" \
  -H 'Content-Type: application/json' \
  -d "{\"repo_id\": \"${RID}\", \"commit_sha\": \"${SHA}\", \"file_path\": \"${FILE}\", \"line\": ${LINE}}")"
EID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("resolved_entity_id") or "")' "${RESOLVE_JSON}")"
echo "${RESOLVE_JSON}" | python3 -m json.tool
if [[ -z "${EID}" ]]; then
  echo "No entity at ${FILE}:${LINE}; set FILE/LINE to a Python definition line and re-run."
  exit 0
fi

echo "== identify / trace / interpret"
curl -fsS "${BASE_URL}/api/analysis/entity/${EID}/identify" | python3 -m json.tool | head -n 30
curl -fsS "${BASE_URL}/api/analysis/entity/${EID}/trace" | python3 -m json.tool | head -n 40
curl -fsS "${BASE_URL}/api/analysis/entity/${EID}/interpret?repo_path=${REPO}" | python3 -m json.tool | head -n 40

REL="$(curl -fsS "${BASE_URL}/api/analysis/entity/${EID}/trace" | python3 -c \
  'import json,sys; j=json.load(sys.stdin); c=j.get("callees") or j.get("contains") or []; print(c[0]["relation_id"] if c else "")')"
if [[ -n "${REL}" ]]; then
  echo "== relation ${REL}"
  curl -fsS "${BASE_URL}/api/analysis/relation/${REL}?analysis_id=${AID}" | python3 -m json.tool | head -n 35
fi

echo "OK"
