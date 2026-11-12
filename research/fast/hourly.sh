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

# 3. websocket lifetime study, window level, two ask caps, one hour of data per process (memory), the hour that just finished
#    first, then back-fill older hours (last 30 h) while the hook has run < 14 min.
#    Lines carry "feed": the model only uses Chainlink prints already RECEIVED (rx, ~1.45 s after their timestamp) - lines
#    from before 11-12 13:00 UTC without it looked ~1.5 s ahead of the book and are superseded - or, with "feed": "bn", also
#    a nowcast from the Binance prices on the same socket (arrive ~1 s before the Chainlink prints they anticipate).
#    Up to 11-11 12h: K the bot could know then (K_EST=bot) -> lifetimes.jsonl. From 11-11 13h (bot K = official ptb, so ptb
#    is no hindsight): the live rule lock_m (margin >= 1 bp, >= 6 s left) at the R latency grid -> lockm.jsonl, rx both caps,
#    bn at cap 0.97.
has() { grep -q "\"hour\": \"$1\", \"k_est\": \"$2\", \"feed\": \"$3\".*\"ask_max\": $4" "data/fast/hourly/$5" 2>/dev/null; }
run_lt() {  # hour k_est feed cap file [extra env...]
  local H=$1 K=$2 F=$3 C=$4 O=$5; shift 5
  ( ulimit -v 650000; env "$@" K_EST="$K" FEED_TIME="$F" HOUR="$H" ASK_MAX="$C" R_LO=0 R_HI=60 OUT="data/fast/hourly/$O" timeout 300 "$PY" research/fast/lifetimes.py ) 2>&1 | grep -E "MemoryError|Traceback" | sed "s/^/  $H $F cap $C: /"
}
for back in $(seq 1 30); do
  [ "$back" -gt 1 ] && [ "$SECONDS" -gt 840 ] && break
  H=$(date -u -d "$back hour ago" +%FT%H)
  for cap in 0.97 0.92; do
    if [[ "$H" > "2026-11-11T12" ]]; then
      has "$H" ptb rx "$cap" lockm.jsonl || run_lt "$H" ptb rx "$cap" lockm.jsonl MARGIN_MIN=1 REM_MIN=6
      [ "$cap" = 0.97 ] && { has "$H" ptb bn "$cap" lockm.jsonl || run_lt "$H" ptb bn "$cap" lockm.jsonl MARGIN_MIN=1 REM_MIN=6; }
    else
      has "$H" bot rx "$cap" lifetimes.jsonl || run_lt "$H" bot rx "$cap" lifetimes.jsonl
    fi
  done
done
echo "  lifetimes done at ${SECONDS}s"
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
  # the server has 927 MiB of RAM: cap each job's address space so a greedy job fails alone instead of taking the runner down
  ( ulimit -v 650000; timeout 420 "$PY" -u "$j" ) > "data/fast/hourly/job_$n.jsonl" 2>&1 || echo "[exit $?]" >> "data/fast/hourly/job_$n.jsonl"
done
echo "hourly $(date -u +%FT%H:%M) done; store $(du -sh "$STORE" 2>/dev/null | cut -f1)"
