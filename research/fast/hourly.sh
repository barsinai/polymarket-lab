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

# 3. websocket lifetime study, window level, two ask caps, with the K the bot can know (K_EST=bot; before 11-11 the
#    summaries used the official price to beat, which is published only late in the window = hindsight).
#    The hour that just finished first, then back-fill up to 4 older hour-cap runs (last 30 h) that have no K_EST=bot line yet.
done_line() { grep -q "\"hour\": \"$1\", \"k_est\": \"bot\".*\"ask_max\": $2" data/fast/hourly/lifetimes.jsonl 2>/dev/null && { [[ ! "$1" > "2026-11-11T12" ]] || grep -q "\"hour\": \"$1\", \"k_est\": \"ptb\".*\"ask_max\": $2" data/fast/hourly/lockm.jsonl 2>/dev/null; }; }
n_back=0
for back in $(seq 1 30); do
  H=$(date -u -d "$back hour ago" +%FT%H)
  for cap in 0.97 0.92; do
    if ! done_line "$H" "$cap"; then
      [ "$back" -gt 1 ] && { [ "$n_back" -ge 4 ] && break 2; n_back=$((n_back + 1)); }
      K_EST=bot HOUR="$H" ASK_MAX="$cap" R_LO=0 R_HI=60 OUT=data/fast/hourly/lifetimes.jsonl timeout 300 "$PY" research/fast/lifetimes.py 2>&1 | grep -E "windows with" | sed "s/^/  $H cap $cap: /"
      # the live rule: exact K (= official ptb since 11-11 13:00 UTC, so ptb is no hindsight from then on), margin >= 1 bp,
      # >= 6 s left -> per-hour lock_m at the websocket's decision latencies (R grid), one hour of data per process (memory)
      if [[ "$H" > "2026-11-11T12" ]]; then
        K_EST=ptb MARGIN_MIN=1 REM_MIN=6 HOUR="$H" ASK_MAX="$cap" R_LO=0 R_HI=60 OUT=data/fast/hourly/lockm.jsonl timeout 300 "$PY" research/fast/lifetimes.py > /dev/null 2>&1 || true
      fi
    fi
  done
done
# 4. one-off research jobs on the raw recordings: research/fast/server_jobs/<name>.py runs ONCE (marker in
#    $STORE/jobs_done/<name>), at most 420 s, stdout -> data/fast/hourly/job_<name>.jsonl (plain text; the .jsonl name makes the
#    running job's publish step pick it up without a workflow change).
#    To re-run a job, give it a new name (<name>_v2.py). Env for jobs: STORE, BOOKWS_DIR, RTDS_DIR, RESULTS_META.
mkdir -p "$STORE/jobs_done"
for j in research/fast/server_jobs/*.py; do
  [ -e "$j" ] || continue
  n=$(basename "$j" .py)
  [ -e "$STORE/jobs_done/$n" ] && continue
  touch "$STORE/jobs_done/$n"
  echo "  server job $n"
  timeout 420 "$PY" -u "$j" > "data/fast/hourly/job_$n.jsonl" 2>&1 || echo "[exit $?]" >> "data/fast/hourly/job_$n.jsonl"
done
echo "hourly $(date -u +%FT%H:%M) done; store $(du -sh "$STORE" 2>/dev/null | cut -f1)"
