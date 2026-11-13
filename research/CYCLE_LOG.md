# Cycle log (newest at the bottom)

- 11-12 16:00 UTC (setup): LESSONS.md + CYCLE.md written. State: lock_m server rx +7..8% / bn same (8 h, ~50 trades,
  lumpy, pooled with local ~0); options paper 16 positions (~2 independent bets); weather 270 open, 0 settled;
  converge first settlements 11-13. Next: first scheduled cycle.

## 11-12 17:10 UTC cycle 1 (scheduled)
- Read-outs: paper lock_m 114 trades 93% -0.5%/$; lock_early 32 trades 93.8% +0.9%/$ (one -$19 day; kill at 50 if <= 0);
  lock_x 8 trades 7 won +8.1%/$ (n small); lock_mv 8/8 +5.2%; lock_b 1 trade. Server websocket study (lockm.jsonl, 21 h,
  deduped by window): rx 191 trades 88.5% +9.1%/$ at 0.1 s, bn +9.8% -> the Binance nowcast adds ~0.7 pts; the edge
  is at <= 0.1 s, where the 2-s bot is never first (LESSONS 1). Weather W1 day 1: 31 positions / 15 Asian events +$139,
  $78 of it one 6c YES. Converge 1/1 +$0.78 (91 open). Young NO 0/9 -$90 (early-settlement bias, see below).
  Sharp: no position (lines tight). Options: 21 open, none settled.
- Test (adjacent): young NO at executable prices on history (research/slow/young_exec_history.py): real NO ask = mid +
  10.5c; path questions +16%/$ (138 events), fixed-date -31% (32); completed 2026H2 path markets -6.6% (34 events) vs
  +29..31% earlier halves. Not dead, not good: decision at the end dates (11-30). New lesson 11 (early settlements biased).
- New ideas: N1 young NO path-only + spread cap (adjacent); N2 box-office opening weekend vs Thursday previews (outside).
- Health: fast paper 16:32, slow 16:41 OK. combos/sample.py crashed every hour (outcomes is a dict) -> fixed. pilot STOP
  mode, no orders. smoke.py UnboundLocalError when the feed is unreachable (GitHub runner, 14:37) - cosmetic, noted.
- Next: N2 census of closed box-office markets; read young at 11-13 end dates; lock_early at 50 trades; weather day 2-3.

## 11-12 20:10 UTC check-in (main session)
- Weather W1 scored at settlement (research/slow/weather_score.py, first snapshot ~1 day ahead, 17 events / 187 buckets,
  all Asia 11-12): Brier model 0.0741 vs market 0.0685 - the market is better; winning bucket model 0.195 vs market 0.302
  (model too spread). Paper +$140 is mostly one 6c YES (luck, not skill). Same as the 11-01 prior (LESSONS 9). Keep
  scoring 3 more days (independent weather days, not cities); kill W1 if Brier still worse on 60+ events.
- Dead buckets (W2): London 7C bid 6.5c at obs max 8, NYC 54-55F bid 2.1c at 55.9 - not settled yet (resolve with the
  official source next day); if they lose, a same-day dead-bucket NO is near-riskless but size is a few $.
- Server websocket lock study, 30 h common hours: rx +4.6% (0.1 s) .. +6.6% (1 s), bn +4.7 .. +7.6%; 7 of 30 hours negative.
  The REST paper lock_m at the same time: -0.5% on 114 trades -> the gap between websocket-speed and our 2-s loop is the edge.

## 11-12 21:00 UTC cycle 2 (scheduled)
- Read-outs: server websocket lock_m (lockm.jsonl, 29-30 h, unique windows, flat $10 no fee): rx 250 trades +7.5%/$ at 0.1 s,
  bn 227 +7.5% (1 s: rx +8.1, bn +9.6) - the nowcast still adds ~nothing at 0.1 s; paper (2-s bot) lock_m 117 93.2% -0.4%/$,
  lock_x 10 9 won +6.9%, lock_mv 10/10 +4.9%, lock_b 3/3, lock_early unchanged 32 +0.9%. Young NO 12 settled 0 won -$120 (early
  path touches, LESSONS 11; decide at end dates). Weather 35 settled +$140 (one 6c YES); Brier model .074 vs market .069 unchanged.
  Converge 1/1, 91 open. Options 26 open, 0 settled. Sharp 0 positions.
- Test (N2 box office, research/slow/boxoffice_census.py via run_script, 619 markets / 134 films / 78 weekends 2024-02..2026-03,
  hourly last prices + c cost): Brier Thu22 .103 / Fri18 .077 / Sat18 .042 / Sun18 .015.
  (B) preview momentum DEAD: +4.7%/$ at +2c on 111 films, but placebo (no-news window) +8.4%, entry hour flips the sign -> lesson 12.
  (C) Saturday favourite 0.80-0.97 at Sat 14-02 UTC: 95.5% won at 0.91, +2.9%/$ at +2c, 54/60 weekends >= 0, stable across
  Saturday hours; 2024..2025H1 -2%, later +6..+8%. Real spread unknown -> paper boxoffice_paper.py (hourly, Sat 14-02 UTC, real
  asks, $10) added to spike_paper.yml. First entries Sat 11-14 if box-office markets are listed.
- New ideas: N3 later-weekend brackets (adjacent); N4 music chart markets vs daily charts / projections (outside the box).
- Health: fast paper 20:45, slow 21:05 OK. pilot-log combos AttributeError is the old 16:32 log (fixed in cycle 1; the log is only
  copied when the pilot job saves). Pilot STOP, no orders. No MemoryErrors.
- Next: N3 census (cheap rerun); first Saturday box-office paper; lock_x/xk read 11-13; converge + young first end dates 11-13.

## 11-13 01:15 UTC cycle 3 (scheduled)
- Read-outs: server websocket lock_m (lockm.jsonl 11-11 13h..11-12 23h, unique windows, flat $10): rx 285 trades +7.6%/$ at 0.1 s
  (108 end-times), bn 261 +8.0%; paper (2-s) lock_m 128 93.8% +0.6%/$, lock_x 16 (15 won) +12.3% on 12 end-times / 2 days, lock_mv 19/19
  +7.9% (14 end-times, 1 day), lock_b 13/13 +8.6%, lock_early 36 +1.4%. Converge 2 settled (one is a pre-filter sports position, -$20;
  the real one +$0.78). Young 16 settled 3 won -$115 (path touches 0/13 = ~3 bets). Weather paper 62 settled +$153; scored 31 events
  (one day) Brier model .0732 vs market .0662 - market better. W2: London dead 7C bucket resolved NO (bid was 6.5c). Box office: 0 markets yet.
- Test 1 (outside the box, N6 earnings beat, via run_script): 470 closed markets, D-1 price 0.734 vs 73.7% YES -> calibrated. YES -2.2%/$
  at +2c, mid band -10%, 0.80-0.95 +0.6% (0 after fee). DEAD; lesson 13 (public base rates are priced).
- Test 2 (adjacent, N5 scheduled-data favourites, local history): ~20 releases, +1..+5% vs converge +0.4..+1.1% - not distinguishable; PARKED.
- New ideas queued: N7 lock_x ∩ lock_mv (adjacent), N8 earnings-call mention markets with past transcripts (outside the box).
- Health: fast paper 00:51, slow 01:02, MM v2 00:31, order books every 15 min - OK. pilot-log traceback is the old 11-12 17:03 copy
  (sample.py already fixed). Pilot STOP (since 11-05), no orders. No MemoryErrors. Polymarket APIs are not reachable from the cycle
  sandbox (proxy) -> network tests go through run_script.yml.
- Next: first Saturday box-office paper (11-14 14 UTC); converge/young end dates; N8 census; lock_x/lock_mv at 30 end-times.

## 11-13 05:10 UTC cycle 4 (scheduled)
- Read-outs: server websocket lock_m (lockm.jsonl, 39 h, unique windows, flat $1): rx 301 trades +7.7%/$ at 0.1 s (115 end-times), bn 276
  +8.5% (1 s: rx +8.7, bn +10.7). Paper (2-s) lock_m 133 94% +0.8%/$, lock_mv 21/21 +7.5% (15 end-times), lock_b 18/18 +8.5%, lock_x 16
  unchanged, lock_early 39 +1.9%. Caveat found: since lock_mv started, every lock_m trade won (27/27, the 6 filtered out too) - the
  range filter is untested on a losing day. All 8 lock_m losses are 5m windows; 15m lock_m 13/13 +6.4% (idea 7, small n).
  Young 18 settled 3 won -$135 (more early path touches). Converge 2 settled, 90 open. Weather paper 73 settled +$133 (YES +$131 on 11,
  NO 37/62 +$3); Brier not re-scored since 01:05 (model .073 vs market .066). Options 36 open, 0 settled. Box office: out of window.
- Test 1 (adjacent, N9 lock_m cool-down after a loss, local paper trades): no clustering (30 min after a loss 3/4, 60 min 11/12 +9%) -> DEAD.
- Test 2 (outside the box, N10 ranking-chart markets, charts_census.py via run_script, 208 closed events / 1,128 markets with history,
  2025-10..2026-02, hourly last prices, fees disabled): favourites 0.70-0.85 won 87-90% vs priced 0.78; fav 0.60-0.85 +5.6%/$ at +2c
  (49 events, end-24h), +13.6% (26, end-2h); Netflix fav +6.7% (72 events), App Store -6.2% (37); halves -5.4% / +6.2% at 24 h.
  Hint, not proof (last prices not asks, LESSONS 3/5) -> paper charts_paper.py (hourly in spike_paper.yml, real asks, $10, rules fav + tail).
- New ideas: N9 (adjacent, dead same cycle), N10 (outside the box, TESTING), N11 Netflix FlixPatrol nowcast (follow-up to N10).
- Health: fast paper 04:57, slow 04:06, MM v2 05:01, order books every 15 min - OK. No new Tracebacks/MemoryErrors (pilot-log and
  script-log are the old 11-12 copies; smoke.py UnboundLocalError when the feed is unreachable still cosmetic). Pilot STOP, no orders.
- Charts paper first run (05:21): 12 live events, fees now ON, favourite spreads wide (bid 0.41 / ask 0.76) -> spread cap 10c + fee; 2 kept.
- Next: charts paper spreads + first settlements; box-office Saturday 11-14 14 UTC; lock_mv on its first losing day; young/converge end dates.

## 11-13 09:10 UTC cycle 5 (scheduled)
- Read-outs: server websocket lock_m (lockm.jsonl 41 h, unique windows, scored won/ask - 1 - 0.07(1-ask)): rx 329 trades 88% +8.4%/$ at 0.1 s
  (123 end-times), bn 300 +8.9%; 1 s rx +9.2 / bn +11.1. Paper (2-s): no new lock signals 05-09h - lock_m 133 +0.8%/$, lock_b 20/20 +8.0%,
  lock_x 16 +12.3%, lock_mv 21/21, lock_early 39 +1.9%. Converge 2 settled / 90 open, young 18 settled -$135 (unchanged), weather paper
  89 settled +$123 (YES +$121 on 13), options 47 open 0 settled, charts 2 open, box office out of window.
- BUG (W2): weather_paper.observed_max dated METARs by reportTime (nominal hour) -> the previous day's 23:51 report counted for today;
  'dead' buckets at local midnight (NYC 00:05, Munich 5C bid 15-27c all night) were artifacts, the market was right. Fixed (obsTime).
- Test 1 (adjacent, N12 = idea 7, server lockm.jsonl): 15m windows +14.0%/$ on 25 end-times (bootstrap +2.8..+23.5) vs 5m +6.8% on 104
  (-4.5..+17). Promising, small -> TESTING read-out at 40 15m end-times.
- Test 2 (outside the box, N8 mention markets, mention_census.py via run_script, 2,277 markets sampled, 1,689 with history): YES is rich
  everywhere (earnings avg price 0.60 vs said 0.53; other 0.45 vs 0.38). Earnings calls (36 calls): NO when YES 0.10-0.40 +14.6%/$ at
  24 h / +17.3% at 2 h (+2c + fee), 22-23 of 27-29 calls positive, both halves positive. Hourly last prices, not asks (LESSONS 3) ->
  paper mention_paper.py (hourly in spike_paper.yml, real NO asks, spread <= 6c, $10 per word, count by call).
- New ideas: N13 index/gold daily markets vs futures (outside the box), N14 mention NO for single-event speeches (adjacent).
- Health: fast paper 09:04, slow 09:14, MM v2 09:01, books every 15 min - OK. Tracebacks only in the old 11-12 pilot-log/script-log copies.
  score_locks.py's results_meta.json is stale (shows settled lock trades as open) - cosmetic, trades.jsonl results are current.
  Pilot STOP, no orders.
- Next: first mention paper positions + spreads (earnings season: NVDA etc.); W2 recount after the fix; box-office Saturday 11-14; lock 15m.
- 09:28 mention_paper smoke run (run_script): works, but only 1 live mention event found ending within 21 d, 0 candidates -> next cycle check
  whether the gamma events scan misses them (tag/series listing) before reading the tracker as 'no markets'.
