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

## 11-13 13:15 UTC cycle 6 (scheduled)
- HEALTH BUG (LESSONS 10): slow paper ran every hour but did not push since 09:14 - cycle 5's mention_paper writes data/slow/mention_*.json,
  which the Save step did not `git add`, so `git pull --rebase` refused ("unstaged changes") 10:06, 11:07, 12:08 (13:10 run too). Converge /
  young / weather / options / charts / mention state from 10-13h is lost (trackers resume from the 09:14 files). Fixed: mention files added,
  `--autostash`. All slow read-outs below are therefore the 09:14 numbers.
- Read-outs (fast paper, data/fast/trades.jsonl): lock_m 142 trades 133 won +0.1%/$ (106 end-times, 5 days); lock_b 26 / 25 won +2.4%;
  lock_mv 26 / 25 won +1.8% (19 end-times) - FIRST LOSS: sol-updown-5m 13:00, Down at 0.97, margin 7.6 bp, 57 s left (lock_m/lock_b also);
  the 'never tested on a losing day' caveat is now answered once: one loss at 0.97 wipes ~32 wins of +3c. lock_x 16 / 15 +12.3% (no new
  signal since 11-12 22:24); lock_early 40 / 38 +2.0% (29 end-times); lock_m 15m (2-s paper) 14/14 +6.5% (11 end-times).
  Server websocket lockm.jsonl (ask_max 0.97, unique windows, 11-11 13h..11-13 12h): rx 0.1 s 355 trades 88.5% +9.1%/$ (134 end-times),
  bn 322 +10.4%; 15m rx 73 trades +14.0% on 25 end-times - no new 15m signal since cycle 5; 5m rx 282 +7.8% (115).
- Test (adjacent, N15, research/slow/tod_asks.py on 1,261 order-book snapshots 10-31..11-13, 192 slow favourite tokens 0.92-0.985 / 189
  events, best ask with >= $10 depth): hour-of-day effect is real but cents - asks are lowest 04-05 UTC (-0.13c vs the same-day median) and
  highest 22-23 UTC (+0.04..+0.09c); max-min 0.22c vs shuffled-hour placebo p95 0.08c (placebo ignores within-token clustering, so
  overstated). Weekend no cheaper (-0.02c vs weekday -0.04c). Dips >= 1c under the trailing 24-h median (177 on 70 events): 24 h later the
  ask is +0.97c higher (median +1.0c), the bid +0.21c over the dip ask; 34/70 back at the old median within 24 h. -> As a strategy DEAD
  (cents, LESSONS 8); as an entry rule for converge it could save ~1c of a ~2c edge -> READY N15b (converge 'dip entry', needs outcomes).
- Idea 2 (outside the box, N16 Elon tweet-count markets, running public tally): looked at the recorded books - the Nov 6-13 event in its
  last hours: dead buckets at 0.001, sum of YES asks 1.037 / bids 1.004 (tight, bots read the tracker). Any edge would be mid-week rate
  modelling (LESSONS 1, 9). READY with a low prior; test = census of closed weekly tweet events, bucket price at day 3-5 vs a rate model
  from the tally at that time (needs the tracker's history - check reachability first).
- Health: fast paper 13:10, live snapshot 13:04, order books every 15 min, boosts hourly - OK. Slow paper: see bug above. Pilot STOP, no orders.
  spike_monitor (DEAD idea, -20..-25% at 24 h) still uses 8 of the 13 min of the slow job - candidate to drop next cycle.
- Next: confirm the 14:23 slow paper push lands; mention paper candidates (scan coverage); box-office Saturday 11-14 14 UTC; lock_mv after
  its first loss; N15b dip-entry on converge.

## 11-13 16:40-19:30 UTC deep session (main, user asked for a hard look at how to make money)
- KILLED the websocket lock edge (LESSONS 14): split of server lockm.jsonl by whether the paper bot was running in the window's last
  minute - running: 1.4 trades/end-time, -0.3%/$ (0.1 s), -0.9% (1 s), -6.4% (2 s); our hook running: 4.8 trades/end-time, +14..+20%/$,
  count flat from R 0.1 s to 2 s (frozen recording). Hook replay step removed (also gave the bot back ~7 min/h); lag_check server job.
- Fixed: options_probe never settled (/markets?slug= hides closed markets -> closed=true); mention_paper scan (tags first).
- W2 same-day dead buckets DEAD: after the obsTime fix 719 dead rows, 0 with a YES bid >= 1c.
- Executable census on the 15-min books (10-31..11-13, 9,620 markets, 7,814 with outcomes, exact fee per market, books_outcomes.py):
  * non-sports favourites in the last 1-12 h: 0.98-0.99 +1.0..+1.1%/$ with 0 losses in ~100 families per horizon; 0.90-0.95 +7..+9%
    but the sample is election night (11-03 races), month-end markets and Elon tweet buckets (where the losses are) - not repeatable as is.
  * sports pre-game full-game moneylines: favourite at the ask won above its price at every band 0.60-0.90 (3-6 h before: +2..+10%/$,
    ~340 markets); NBA 15/15 at 0.835. No pre-game drift (buy 24/12/6 h before, sell before the start: -1.4..-6.8% = costs), so any
    edge is in outcomes, i.e. a closing-price favourite-longshot bias - or luck. Polymarket already prices heavy favourites ABOVE
    Pinnacle's proportional fair (0.851 vs 0.832, n 10). Big-history test running (hist_prices.py, 6.5k moneylines Jun-Nov) and a
    forward paper tracker (sports_fav_paper.py in the slow job; spike_monitor dropped).
  * crypto price markets vs lognormal at Deribit DVOL (530 markets): model ~= market at < 12 h; touches 12-48 h model better
    (Brier .116 vs .133) but only ~12 independent events and trade results swing with the threshold -> paper options tracker decides.
- Running: kalshi_mentions.py (mention bias at executable Kalshi bid/ask), hist_prices.py.
- 11-13 19:55 UTC deep-session verdicts (decisive tests, all at executable prices or with real costs):
  * Mention NO: DEAD - Kalshi 9,623 settled mention markets / 494 events with hourly bid/ask: YES 0-6 pts rich at the mid, spread 3-9c,
    NO at the ask -0.1..-13.7%/$ (3 h) in every band.
  * Sports favourite-longshot: DEAD - 5 months / 8,871 moneylines: majors calibrated (MLB 60.7% vs 60.5%, NHL 62.9/63.0, NFL 68.2/67.1,
    esports 70.0/70.2); after +0.5c + fee favourites -2.0%/$ (n 629), underdogs -7.2%; other leagues' gap = final-volume selection
    (LESSONS 16). sports_fav_paper removed from the slow job.
  * Last-day favourites 0.95-0.99: 5 months 369 / 11 losses / -0.7%/$ (August war events -11.8%) vs 167/167 in the calm 2 weeks
    (LESSONS 15). converge_day paper kept to measure the calm-period yield only.
  * Net: every large category we can test systematically is efficient at the prices we can trade. Remaining small candidates: crypto
    touches vs options (model Brier better at 12 h+, few events; options paper settling now), converge 3-30 d, perps carry, charts/box office.

## 11-13 17:00-18:10 UTC cycle 7 (scheduled)
- Read-outs (fast paper trades.jsonl, settled): lock_x 17 / 16 +12.0%/$ (13 end-times, 3 days); lock_mv 30 / 29 +2.2% (22); lock_early
  41 / 39 +2.1% (30); lock_m 147 / 138 +0.2%; lock_p 36 / 33 +8.2% (31 end-times, 4 days). N7: lock_x ∩ lock_mv 12/12 +13.6% on 8 end-times,
  mv-only 18 / 17 -3.2% (its one loss, sol 0.97) -> lock_mv adds nothing outside lock_x. Slow: converge 4 settled (rule-conforming 3/3
  +3.5%), 88 open mark -$27; young 28 settled 3 won -$235 (36 'Week of 11-09' touch rungs marked -$168, NO ask = NO mid + 13c median);
  weather paper 143 settled +$106 / $715 (YES longshots +$94 on 26); charts 2 open; box office out of window; mention 1 event seen at 16:24
  (scan fix landed 16:55). weather_score.py cannot run here (gamma 403 from the cycle sandbox, not a workaround case) -> via Actions next.
- Test (adjacent, N17 touch ladders, hit_census.py via run_script, 1,228 'hit' events found via hit-price series; 4,592 rungs with
  history, stocks/commodities only - crypto not reached in the 42-min budget): touch YES is RICH, not cheap - start + 24 h YES 0.27 ->
  0.17, 0.43 -> 0.35 (LOW/dip touches worst). NO on YES 0.30-0.50: +9.4%/$ at +2c + fee (283 events, 19/28 weeks +), +4.3% at +5c, mid-life
  +0.7%. Hourly last prices; the real NO ask on these rungs early in the week is mid + 13c -> DEAD as a taker (same story as the mention
  census). Maker variant N17b queued (fills likely adverse, LESSONS 2).
- New ideas: N17b maker NO on touch ladders (adjacent), N18 Rotten Tomatoes score markets vs the review tally (outside the box).
- Health: fast paper 16:15, slow 16:27 (pushes OK again), MM v2 17:01, books 17:00, live snapshot 17:04. Old smoke Traceback in
  logs/script-log.txt (11:34 copy, cosmetic). Pilot STOP, no orders. A parallel deep session was editing IDEAS; merged by hand.
- Next: weather_score via Actions (Brier with 2+ days); lock_x / lock_p to 30 end-times; young at the 11-16..11-30 end dates; box office Sat
  11-14 14 UTC; N18 census with real spreads first.
- 11-13 20:30 UTC liquidity review (user asked): contested reward markets lose (paper MM fills -5.4..-6.7% of notional in every
  category; at the pilot's 1/5 reward haircut all 6 variants -$90..-730/day). NEW: uncontested pools - lp_screen.py over 11,507
  reward markets ($121k/day): 837 of the 1,487 largest have no quote in the band (>= $10/day, $22k/day), persistent (94% still
  empty 2 h later, median 6.4 days at the current pool), paid in USDC. Never tested: the paper MM and the pilot skipped wide books.
  Docs: no liquidity minimum or per-maker cap; per-market pools, daily payout. Next: user OK for a 48 h, <= $200 live test (LP-1). -> 11-13 21:50 the user chose SIMULATION ONLY: no live LP-1 test is approved.

## 11-13 21:00-21:40 UTC cycle 8 (scheduled)
- Read-outs (fast trades.jsonl): lock_x 17 / 16 +11.9%/$ (13 end-times, no signal since 13:29); lock_p 37 / 34 +8.1% (32 end-times, 4 days;
  contains all of lock_x: p∩x +11.9%, p-only 20 / 18 +3.9%); lock_early 41 / 39 +2.1% (unchanged); lock_m 154 / 143 -0.8%; lock_b 31 / 30
  +3.0%. lock_mv 34 / 32 -0.6%, mv-only 22 / 20 -6.4% -> DEAD. Slow: converge 4 settled (non-sports 3/3 +3.5%), 88 open mark -$31; young 29
  settled 3 won -$245; charts 2/2 +$3; LP-1 3 runs: formula reward $145 (upper bound) vs pessimistic fills -$59, 26 of 59 markets saw a
  competitor - too early. converge_day: 0 positions (1 candidate) - check its filter next cycle.
- Weather W1 DEAD: weather_score.py via Actions, 66 events / 726 buckets (2 days): Brier model .0732 vs market .0635; NO bets: model
  expected 103.5 wins, market 81.0, actual 82; paper +$89 is one 6c Taipei bucket (+$78). Paper keeps logging to 11-22.
  Side note: the same run lists 22 same-day 'dead bucket' snapshots still bid >= 1c (SF 62-63F bid 0.46 at obs max 64.0) although W2 was
  declared dead at 0 rows - the two scripts disagree (clock or F/C rounding? LESSONS 10). The 2 with outcomes resolved NO. Recount next cycle.
- Test (N18 Rotten Tomatoes, rt_census.py via Actions, 264 markets / 64 events, hourly CLOB last prices, +c + fee): near-certain 0.90-0.97
  won 39/39 at end-72h (26 films) +3.9%/$ at +2c, 26/26 at end-24h (19 films) +3.5%; the 0.60-0.90 'anchoring' band flips sign with
  the entry clock (-18% / +8.6% / +15%) = noise. ~5 RT events a month -> PARKED, folded into N19.
- New ideas: N19 (adjacent) running-tally near-certainties 0.90-0.97 inside converge; N20 (outside the box) the UMA proposal window.
- Health: fast paper 20:20, slow 20:27, books 21:00, boosts 20:55, MM v2 20:32 - OK. Pilot STOP, no orders, equity $224.06 unchanged.
  pilot-log Traceback is the old combo sampler crash (fixed at 17:53, isinstance guard). No MemoryErrors.
- Next: lock_p week mark 11-17 (40+ end-times at >= +5% -> write up for the user); W2 dead-bucket recount; converge_day filter; N19 tag in
  converge_paper; box office Sat 11-14 14 UTC; LP-1 first daily read 11-14.
- 11-13 21:50 user: run the experiment as a simulation only. LP-1 stays paper; lp_paper.py report now also has 'budget_slice' = the
  proposed 48 h / $200 test simulated (markets a $200 budget would have entered, entry order + largest pool first). First read on the
  current state: 6 markets, $195, pools $1,331/day, formula reward $41, fills +$6.5 (pessimistic -$8.7). Read it at 48 h (11-15 ~19 UTC).

## 11-14 00:55-01:40 UTC cycle 9 (scheduled)
- Read-outs (fast trades.jsonl, settled): lock_x 18 / 16 +9.2%/$ (14 end-times; new loss hype 5m Down 0.92, margin 14.6 bp, -$7.3); lock_p
  39 / 35 +6.8% (34 end-times, 4 days); lock_early 44 / 41 -0.6% (31 end-times; its kill rule is 50 trades <= 0); lock_m 159 / 147 -1.5%
  (118 end-times); lock_b 35 / 33 -0.4%. Slow: converge 4 settled, 88 open mark -$37; converge_day 0 positions (1 candidate at 00:22, night);
  young 48 settled 20 won -$161 / $480 (early YES-heavy, LESSONS 11); options 13 settled 3 won -$89 (~2 independent events: 11-12/13 BTC drop);
  LP-1 8 runs: formula $427 upper bound, pessimistic fills -$145, $200 slice +$7.2 at 100% pay / -$2.9 at 20%; charts 2/2; mention 0 settled.
- Test (N20 UMA proposal window, uma_window.py, local, 1,308 snapshots / 7,814 closed markets): non-sports winners in the last 2 h before
  resolution trade at 0.999 (17/19 seen); the 2 cheaper were Binance candle markets pre-close. Recorder sees only 19 of 1,829 non-sports
  markets after their end date (thin), but nothing there -> DEAD. First pass had all 'winners' at 0.05 - sports endDate = game start, so the
  window was the live game (LESSONS 10); fixed by excluding gameStartTime / sportsMarketType markets.
- Side test (-> N21 adjacent): first lock signal per window, all lock_* rules: BTC/ETH 179 windows +3.5%/$ (6/8 days >= 0) vs alts 265
  windows -3.2% (1/8 days > 0). Chosen after looking -> forward-only read-out (lock_be_readout.py, from 11-14 01:00 UTC).
- New ideas: N21 lock_be (adjacent, TESTING), N22 Argentina CPI buckets vs Buenos Aires City CPI released days earlier (outside the box, READY).
- Health: fast paper 00:22, slow 00:29, MM v2 00:32, books 01:00 - OK. Tracebacks only the old combo sampler crash in pilot-log (fixed 11-13
  17:53) and the old script-log smoke. No MemoryErrors. Pilot STOP, no orders.
- Next: lock_early 50-trade kill check; lock_p week mark 11-17; LP-1 48-h read 11-15 ~19 UTC; box office Sat 11-14 14 UTC; N22 census via
  Actions; N19 tally tag in converge_paper; W2 dead-bucket recount (still open).

## 11-14 04:55-05:35 UTC cycle 10 (scheduled)
- Read-outs (fast trades.jsonl, settled): lock_x 18 / 16 +9.2%/$ (14 end-times, no new signal); lock_p 39 / 35 +6.8% (34 end-times, 4 days);
  lock_p_majors 13/13 +14.1%; lock_early 45 / 41 -3.2% (32 end-times, 5 trades from its kill rule); lock_m 164 / 151 -1.5%; N21 forward:
  5 alt windows 5/5 +4.9%, 0 BTC/ETH yet. Slow: converge 4 settled (non-sports 3/3 +3.5%), 89 open mark -$40; young 50 settled 20 won -$181
  / $500; options 13 settled 3 won -$89 (~2 events), 52 open; charts 2/2 +$3; LP-1 12 runs (0.4 d): formula $663 upper bound, pessimistic
  fills -$199, $200 slice +$7.2 at 100% pay / -$2.9 at 20%; box office out of window (Sat 14 UTC); mention 1 open.
- Test (adjacent N23, converge_geo_split.py, local, 5-month hourly history): last-day favourites 0.95-0.99, 755 markets / 750 events,
  +0.5c + fee: 24 losses (3.2%) -1.3%/$; geopolitics filter 280 / 6 -0.4%, the rest 475 / 18 -1.9%. The tail is not war-only -> N23 DEAD
  and converge_day DEAD; removed from the slow job (its 0 candidates were also a scan problem, not worth fixing now).
- Test (outside the box N24, quake_census.py via Actions): only 13 earthquake markets found (yearly M7 count buckets + one 2021 market) ->
  PARKED, too few events. (The script's 'resolved against catalog' rows are count buckets my by-date logic misreads - not a finding.)
- Health: fast paper 04:23, slow 04:28, MM v2 05:01, books 05:00, live snapshot 05:05 - OK. Tracebacks only the old combo sampler crash in
  pilot-log and the old script-log smoke. No MemoryErrors. Pilot STOP, no orders.
- Next: lock_early kill at 50 trades; lock_p week mark 11-17; LP-1 48-h read 11-15 ~19 UTC; box office Sat 11-14 14 UTC; N22 Argentina CPI
  census via Actions; N19 tally tag in converge_paper; W2 dead-bucket recount (still open).

## 11-14 09:00-09:40 UTC cycle 11 (scheduled)
- Health FIRST: the fast paper bot was DOWN 06:58-09:03 (run 39: 'runner has received a shutdown signal' on pilot-helsinki; the self-chain
  only re-dispatches after a clean part, so nothing restarted it) and with it the hourly slow-paper kick (last slow 06:45). Re-dispatched
  fast_paper.yml (run 40 running) and spike_paper.yml (slow, 09:07 OK). ~2 h of lock signals missing. No orders anywhere; pilot STOP.
- Read-outs (fast trades.jsonl, settled): lock_x 18 / 16 +9.2%, lock_p 39 / 35 +6.8% (34 end-times) - unchanged, no signal since 11-13 20h;
  lock_early 46 / 42 -3.0% (4 trades from its kill rule); lock_m 166 / 153 -1.4%; N21 forward BTC/ETH 1 window, alts 11 / 10 -1.2%.
  NEW SPLIT (lock_price_split.py): lock_p's whole profit is 7 trades bought at 0.52-0.74 (+$34.7); its 32 trades at >= 0.80 are +1.0%/$;
  lock_x >= 0.80 -3.9%. The 11-17 write-up must show this; it is not a '0.9x lock' edge. Slow (06:43 reports): converge 4 settled, 89 open
  mark -$37; young 50 settled 20 won -$181; charts 2/2; LP-1 15 runs (0.5 d): formula $763 (upper bound), pessimistic fills -$249, $200
  slice +$7.2 / -$2.9; box office out of window until 14 UTC.
- W2 recount (open since c8): after the 11-13 fix 2 of 3,537 dead-bucket rows bid >= 1c; the 22 'bid >= 1c' rows are pre-fix, local hours
  00-10 (previous-day obs). W2 stays DEAD; item closed.
- Test (outside the box N26, tsa_census.py via Actions, 488 markets / 70 TSA-passenger events Nov 2025 - Mar 2026): YES rich on 0.10-0.50
  buckets; favourite side 0.80-0.90 +7..+11%/$ at +2c + fee at all three clocks (27-35 days); 0.60-0.80 flips sign = noise. Last prices,
  one 4-month period, and no TSA market is live now -> PARKED (relaunch watch; tsa.gov is reachable from Actions for a YoY model).
- New ideas: N25 lock_cheap (adjacent, forward read-out from 11-14 09:00), N26 TSA (outside the box, PARKED). Gas-price markets checked
  first: 13 events ever -> not worth a test.
- Parallel session active (tape_census.py, maker-vs-taker); did not touch its files.
- Next: confirm fast run 40 publishes at ~10:05; lock_early kill at 50; lock_p week mark 11-17 with the price split; box office 14 UTC today;
  LP-1 48-h read 11-15 ~19 UTC; N22 Argentina CPI census.

## 11-14 08:50-11:00 UTC deep session (user: 'bring me an idea that works')
- Built the largest test so far from the public trade tape (data-api /v2/trades, real fills): 12 weeks, 48,933 closed markets, 5.46M taker
  trades, wallets, fees, outcomes (research/slow/tape_entries.py via 3 Actions jobs -> data/research/entries_{a,b,c}*, orders_{a,b,c}*).
- KILLED on it (numbers in IDEAS/DEAD 'TAPE STUDIES 11-14'): passive maker, combo maker, follow big orders (my morning candidate: +6.4 on 61
  sampled events -> -1.7 on 968), copy sharp wallets a minute later, bonds as a taker, resting bids on the cheap side, mention blanket NO.
- What the tape does show: small takers lose 1.3 pts/share, takers of $200-1,000 win 1.2, wallets with a record keep +1.6 (out of sample)
  - skill is paid, flow-following is not. Information is paid most visibly in mention, movies, ai/tech leaderboards, youtube.
- NEW TESTING: COPY-1 (research/slow/follow_paper.py, workflow follow.yml, data/follow/): real-time copy of 148 two-half winners at the real ask,
  control group, fixed decision rule (300 settled primaries / 100 events / 10 days). First run 10:47 UTC. Health check it each cycle
  (logs/follow-log.txt, data/follow/report.json 'updated'); it chains itself and has a 6-h cron fallback.
- LP-1: v1 numbers void (re-fill artifact + my manual fair values), restarted as v2. Told the user the 'unclaimed pools' claim was overstated.
- New READY: N27 mention transcript model (the next thing to test - text is our comparative advantage), N28 bid for favourites.
- Lessons 17-24 added. Next cycle: N27 feasibility (are transcripts reachable from Actions?), COPY-1 health, LP-1 v2.
