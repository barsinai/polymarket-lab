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

# 3. (removed 11-13) the hourly websocket lock replay (lifetimes.py -> lockm.jsonl). Its +8..+11%/$ came only from the
#    windows that ended while THIS hook ran: 4.8 cheap-lock trades per end-time at +14..+20%/$ vs 1.4 and ~0%/$ while the
#    bot was running (41 h, 11-11 13h..11-13 15h). The heavy replay (650 MB on a 927 MiB box) made the recorder fall
#    behind, so its book records were stamped late and the replay bought asks that were already gone. It also kept the
#    bot stopped ~7 min an hour. lifetimes.py stays for offline use; exclude hook minutes (job_lag_check) when replaying.
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
