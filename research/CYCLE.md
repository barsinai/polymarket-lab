# Research cycle (run by the scheduled task every 4 h; one cycle <= ~60 min of work)

Goal: keep finding, testing and killing ideas on our own recorded data without being asked. Paper only.

## Hard rules
- NO live trading, no real orders, no change to live bots' money settings. Paper and read-only only.
- Keys stay in GitHub Actions secrets; never print them, never put them in git or messages.
- Do not route around geoblocks. The combo sampler never accepts quotes.
- Server (pilot-helsinki, 927 MiB RAM): heavy scripts run under `ulimit -v 650000`, only inside existing hooks or a
  dispatched `run_script.yml` job; never start a second long job next to the fast paper bot.
- Commit messages end with the two attribution lines from the session's instructions.

## Steps
1. **Read** research/LESSONS.md, research/IDEAS.md, the tail of research/QUEUE.md, and research/CYCLE_LOG.md (last 3).
2. **Read-outs** (15 min max): for every TESTING row whose read-out data has grown, recompute its number from the repo
   data (data/fast/hourly/*.jsonl, data/research/*_report.json, weather/converge/young/sharp/options paper files).
   Promote, keep, or kill with the number. Killed -> DEAD with the number, and a LESSONS entry if the reason is new.
3. **New ideas** (always 2): one "adjacent" (a variant of something that half-worked) and one "outside the box"
   (a market type, data source or mechanism we have never touched). Each must state: why the crowd/bots would be wrong,
   which LESSONS it is exposed to, and the cheapest decisive test. Brainstorm prompts: resolution-rule fine print;
   markets that resolve on a source we can read earlier; who is forced to trade (deadlines, rewards, rebalancing);
   new market launches; cross-venue (Kalshi, options, sportsbooks); time-of-day/weekend liquidity; markets with a
   running count; what our 30 GB of recordings can answer that nobody else has.
4. **Test** at least one idea (new or READY) on recorded data now: write research/<area>/<name>.py, run it locally or via
   `gh api -X POST repos/barsinai/polymarket-lab/actions/workflows/run_script.yml/dispatches -f ref=main -f "inputs[script]=<path>"`,
   executable prices + fees, receive-time ordering, count independent events. If promising -> add a paper tracker
   (TESTING row). Keep 3+ ideas in TESTING.
5. **Health**: last fast/slow paper publishes, Tracebacks/MemoryErrors in logs/*.txt. Fix small breakages; note big ones.
   Also the hosted chained trackers: boosts.yml and follow.yml (COPY-1: data/follow/report.json 'updated' within ~70 min, logs/follow-log.txt);
   re-dispatch with `gh workflow run <file> --ref main` if the chain stopped.
6. **Write** a CYCLE_LOG.md entry (date, read-outs, ideas, test result, next), update IDEAS/QUEUE, commit, push.
7. **Report** to the user in Hebrew, short and plain: what was tested, the number, what died, what's next. Say clearly
   when nothing works. Never ask for live trading; if something survives paper for a week with 30+ independent events,
   propose it with the numbers and wait for an explicit OK.
