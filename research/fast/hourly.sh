#!/usr/bin/env bash
# Runs on the Finnish server between two hourly parts of the paper bot (fast_paper.yml), with the bot stopped.
# Raw recordings stay on the server ($BOOKWS_DIR, $RTDS_DIR, 7-day retention); this produces the small per-hour
# summaries that go to git instead:  data/fast/hourly/lifetimes.jsonl  (one JSON line per hour and ask cap).
# Everything here is read-only against Polymarket (Gamma results) and must never take more than ~10 minutes.
set -u
PY="${PYTHON:-python3}"
STORE="${STORE:-/home/runner/pilot-data}"
export BOOKWS_DIR="${BOOKWS_DIR:-$STORE/bookws}" RTDS_DIR="${RTDS_DIR:-$STORE/rtds}"
export RESULTS_META="$STORE/results_meta.json"     # official results, kept on the server (not in git)
mkdir -p data/fast/hourly
echo "hourly $(date -u +%FT%H:%M) start"

# 1. archives: repair any hour whose gzip was damaged by an interrupted compress (checks files touched in the last 3 h)
"$PY" research/fast/repair_gz.py "$RTDS_DIR" "$BOOKWS_DIR" 2>&1 | tail -5

# 2. official results for the windows of the last 2 days (Gamma, ~1 request per unsettled window)
SETTLE_DAYS=2 timeout 360 "$PY" research/fast/settle.py 2>&1 | tail -2

# 3. websocket lifetime study for the hour that just finished, window level, two ask caps
H=$(date -u -d '1 hour ago' +%FT%H)
for cap in 0.97 0.92; do
  if ! grep -q "\"hour\": \"$H\".*\"ask_max\": $cap" data/fast/hourly/lifetimes.jsonl 2>/dev/null; then
    HOUR="$H" ASK_MAX="$cap" R_LO=0 R_HI=60 OUT=data/fast/hourly/lifetimes.jsonl timeout 300 "$PY" research/fast/lifetimes.py 2>&1 | grep -E "windows with|R  2.00" | sed "s/^/  $H cap $cap: /"
  fi
done
echo "hourly $(date -u +%FT%H:%M) done; store $(du -sh "$STORE" 2>/dev/null | cut -f1)"
