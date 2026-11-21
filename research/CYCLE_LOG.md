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

## 11-14 13:00-13:45 UTC cycle 12 (scheduled)
- Read-outs (fast trades.jsonl, settled, last trade 12:03): lock_x 18 / 16 +9.2%, lock_p 39 / 35 +6.8% (34 end-times), lock_p_majors 13/13
  +14.1%, lock_early 46 / 42 -3.0% (still 4 from its kill rule), lock_m 168 / 155 -1.4%, lock_b 36 / 33 -2.0% - no new lock signals since c11.
  N21 forward: BTC/ETH 4 / 4 +7.8%, alts 12 / 11 -1.0% (1 day). N25 forward (price split): 4 trades >= 0.80, 4/4 +7.6%, 0 below 0.80.
  Slow (12:04-12:09): converge 5 settled 4 won -$18 (non-sports 4/4 +2.8%), 88 open mark -$38; young 50 settled 20 won -$181 (end dates
  11-16..30); options 19 settled 6 won -$114 / $190 (still ~2-3 BTC-move events); charts 2/2 +$3, 0 live; mention 2 open; box office out of
  window. LP-1 v2 3 runs (0.08 d): formula $93 (upper bound), pessimistic fills -$44, 22 of 60 markets saw a competitor already.
  COPY-1 (1.9 h): sharp 5 positions / 1 primary, control 7; sharp ask is +10.9c over the wallet's price (median, 217 s lag), only 20% pass
  the +3c cap - the WEAK POINT shows from the first hours (price runs before we copy). Too early to judge; decision rule unchanged.
- Test (N28 favourite bid, tape_favbid.py, local, raw mention + awards tapes): live-pegged bid on the 0.94-0.985 side, filled by the next
  selling print: 140 fills / 63 events, +2.27 pts/share [-0.0, +3.7], 2 losses (both on a falling price, -97 pts each); Oct-Nov 125 fills
  +3.65 / 0 losses, Aug-Sep 15 fills; >= 7 d before end -0.2. Same sign as the 6-week number but a tail bet on a calm sample (LESSONS 15)
  -> not killed, not a result: N29 forward paper with the cancel-on-down rule pre-registered. Limits: only 2 of 6 raw tapes are in the repo.
- New ideas: N29 (adjacent) favourite-bid forward paper; N30 (outside the box) Google Year in Search markets vs Google Trends (TRENDING rule
  fine print; ~1 release a year, so census first and park if < 10 events).
- Health: fast paper 12:03, slow 12:09, follow 12:47 (COPY-1 report 12:39, < 70 min), boosts 12:13, MM v2 13:00, books 13:00 - OK. Tracebacks only
  the old combo-sampler crash in pilot-log and the old script-log smoke; no MemoryErrors. Pilot STOP, no orders.
- Next: N29 needs every print, not the >= $FILTER feed follow_paper.py reads -> a small separate poller of /trades for live mention/awards
  markets (next cycle); N27 transcript feasibility via Actions; box office window 14-02 UTC tonight; lock_early kill at 50; lock_p week 11-17;
  LP-1 v2 48 h 11-16 ~10 UTC.

## 11-14 17:00-17:40 UTC cycle 13 (scheduled)
- Read-outs (fast trades.jsonl, last settled 16:58): lock_x 18 / 16 +9.2%, lock_p 39 / 35 +6.8% (34 end-times) - no signal since 11-13 20:09;
  checked it is not a bug: lock_p_z2 fired 21 times since, max z 2.59 (17 before), none of the 3 z >= 2.5 held 2 s. lock_early 47 / 43 -2.7%
  (3 from its kill rule); lock_m 177 / 164 -1.0%. N21 forward: BTC/ETH 12 / 12 +5.9%, alts 18 / 17 +2.5%. N25 forward: >= 0.80 17/17 +5.7%,
  < 0.80 1/1. Slow (16:05-16:08): converge 5 settled 4 won -$18, 88 open mark -$38; young 50 / 20 -$181 (end dates 11-16..30); options 19 / 6
  -$114, 53 open; charts 2/2; LP-1 v2 0.25 d: formula $290 (upper bound), pessimistic fills -$138, 78/97 markets saw a competitor (worst:
  same-day weather buckets). COPY-1 6.1 h: sharp 10 primaries, 0 settled; ask minus their price median +4.7c, 31% pass the cap.
- BUG (LESSONS 10): boxoffice_paper saw 0 box-office markets in its first live window (14-16 UTC) while LP-1 was quoting 'Ebenezer' Opening
  Weekend - the capped 4-day end-date scan. Fixed (search + tag first, paged fallback to 20,000), pushed 17:04; the 17:06 run saw 33 markets and opened 1 position.
- Tests: N31 (adjacent) favourite bid on movies/music/tweets/youtube tapes (never looked at): -0.3 pts [-2.2, +1.3] on 180 events, the
  pre-registered N29 rule +0.3 [-1.9, +2.1] -> N28/N29 DEAD, poller not built. N32 (outside the box) maker P&L by the taker's clock, 1.51M
  entries: US night +0.8% [-1.1, +2.8], weekend -0.3%, US day -2.0% [-4.2, -0.3] -> no slot pays a maker; DEAD, kept as N33 question for LP-1.
- New READY: N33 LP-1 off-US-hours (split LP-1 fills by hour at the 48-h read), N34 Polymarket copies of Kalshi series (Kalshi as prior/fair).
- Health: fast paper 16:04, slow 16:10, follow 16:59 (report 16:50), boosts 16:37, MM v2 17:01, books 17:00 - OK. Tracebacks only the old
  combo-sampler crash in pilot-log and the old script-log smoke; no MemoryErrors. Pilot STOP, no orders.
- Next: confirm boxoffice_paper sees markets (tonight to 02 UTC); lock_early kill at 50; LP-1 v2 48 h 11-16 with the N33 hour split;
  lock_p week mark 11-17; N27 transcript feasibility; N22 Argentina CPI census.

## 11-14 21:00-21:35 UTC cycle 14 (scheduled)
- Read-outs (fast trades.jsonl, last 20:04): lock_x 19 / 17 +8.8% (15 end-times), lock_p 40 / 36 +6.6% (35), lock_p_majors 14/14 +13.2%,
  lock_early 47 / 43 -2.7% (unchanged, 3 from kill), lock_m 181 / 168 -0.8%, lock_b 41 / 38 -1.2%. N21 forward BTC/ETH 19/19 +5.3%, alts 21 / 20
  +2.7% (1 day). N25 forward >= 0.80 27/27 +5.2%. Slow (20:06-20:10): converge 5 settled -$18, 88 open mark -$40; young 50 / 20 -$181; options
  25 / 7 -$156, 58 open; charts 2/2, 0 live; box office FIX WORKS (27 markets, 6 open, spread 7c). LP-1 v2 0.42 d: formula $502 (upper bound),
  pessimistic -$204, 100/121 saw a competitor. COPY-1 10.1 h: sharp 20 primaries, 0 settled; ask +4.6c over theirs, 36% pass the cap.
- Test (adjacent N35, lp_fill_split.py, LP-1 v2 state): weather same-day buckets carry all the loss - formula $100 vs pessimistic -$167 (fills
  -11.5% of notional, 30 markets); the rest formula $401 vs pessimistic -$37 (fills +0.3%, 33 markets). In-sample, one Saturday -> lp_paper.py
  now reports by_kind with a forward block (markets opened >= 21:00). N33 clock split: all fills Saturday, not readable yet.
- Test (outside the box N37, approval_census.py via Actions, 382 markets / 101 Trump approval events, RCP average): favourite 0.60-0.97 at +2c
  -5.3%/$ end-72h (78 events, both halves negative), -4.6% end-24h, -0.7% end-6h on last prices (which flatter). DEAD. RCP 403 from Actions.
- New ideas: N35 (adjacent, TESTING split), N36 (adjacent, low prior: be the METAR taker), N37 (outside the box, DEAD).
- Health: fast paper 20:06, slow 20:11, follow 21:00 (report 20:54), boosts 21:01, MM v2 20:31, books 21:00 - OK. Tracebacks only the old
  combo-sampler crash in pilot-log and the old script-log smoke; no MemoryErrors. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 (by_kind forward + N33 hour split on weekday fills); lock_early kill at 50; lock_p week mark 11-17 with the price
  split; box office settlements Monday; N27 transcript feasibility; N22 Argentina CPI census.

## 11-15 01:00-01:30 UTC cycle 15 (scheduled)
- Read-outs (fast trades.jsonl, last 00:04): lock_x 19 / 17 +8.8% (15 end-times), lock_p 40 / 36 +6.6% (35), lock_p_majors 14/14 +13.2%,
  lock_early 49 / 45 -2.4% (1 from its kill rule at 50), lock_m 182 / 169 -0.8%, lock_b 41 / 38 -1.2% - no new lock_x/lock_p signal.
  N21 forward BTC/ETH 22/22 +5.5%, alts 24 / 22 +1.8% (1 day). N25 forward >= 0.80 32/32 +5.3% (24 end-times), < 0.80 2 / 1.
  Slow (00:07-00:10): converge 5 settled -$18, 88 open mark -$40; young 50 / 20 -$181 (39 open); options 25 / 7 -$156, 67 open; charts 2/2,
  0 live; box office 8 open, 0 settled (Monday). LP-1 v2 0.59 d: formula $689 (upper bound), realistic trading -$139, pessimistic -$262;
  'other' pessimistic fell from -$37 to -$94 since c14, almost all one stream market (Caedrel 'Crab / Scuttle 10+ times' -$79 realistic).
  COPY-1 13.3 h: sharp 24 primaries, 0 settled; ask +4.4c over theirs (median), 37% pass the cap; control 9 settled +5.7 pts (noise).
- Test (outside the box N39, cb_decision_census.py, local, 12-week tape): central-bank decision favourites 0.60-0.97, 24-168 h out: -0.2 pts
  [-29.8, +17.6] on 22 meetings, -9.9 per meeting equal-weight, halves +16 / -12.5, 7-30 d out -21.7 [-39.8, -5.2]. DEAD (LESSONS 13).
- Test (adjacent N38, LP-1 v2 state, in-sample): live-count / mention / views markets 11: formula $65 vs pessimistic -$56; core 92: formula
  $523 vs pessimistic -$39, realistic +$30. -> lp_paper.py now reports by_kind.core / forward_core (markets opened after 01:00 UTC).
- Health: fast paper 00:07, slow 00:10, follow 00:12 (report 00:04, < 70 min), boosts 00:20, MM v2 01:01, books 01:00 - OK. Tracebacks only
  the old combo-sampler crash in pilot-log and the old script-log smoke; no MemoryErrors. Pilot STOP, no orders.
- Next: lock_early kill at 50 (next signal); LP-1 v2 48 h 11-16 ~10 UTC with N33 hour split + N35/N38 forward; box office settlements Monday;
  lock_p week mark 11-17; N27 transcript feasibility; N34 Kalshi-first census.

## 11-15 05:00-05:30 UTC cycle 16 (scheduled)
- Read-outs (fast trades.jsonl, last 04:08): lock_x 19 / 17 +8.8% (15 end-times), lock_p 40 / 36 +6.6% (35), lock_p_majors 14/14 +13.2% - no new
  lock_x/lock_p signal; lock_m 184 / 171 -0.7%, lock_b 43 / 40 -0.9%. lock_early 51 / 47 -2.1% (37 end-times) -> KILL RULE FIRED, DEAD.
  N21 forward BTC/ETH 24/24 +5.6%, alts 28 / 26 +2.4% (2 days). N25 forward >= 0.80 38/38 +5.5% (28 end-times), < 0.80 2 / 1.
  Slow (04:08-04:16): converge 9 settled 8 won -$13, 85 open mark -$29; young 52 / 20 -$201; options 25 / 7 -$156, 71 open; charts 0 live;
  box office 9 open (Monday); mention 2 open. LP-1 v2 22 runs / 0.75 d: formula $857 (upper bound), trading -$114, pessimistic -$285, 130 of 147
  markets saw a competitor; core 96 markets formula $618 vs pessimistic -$42; forward_other 14 markets $65 vs -$16 (too early).
  COPY-1 17.5 h: sharp 29 primaries, 0 settled; ask +4.8c over theirs, 34% pass the cap, lag 159 s; control 18 primaries settled -0.5 pts.
- Test (adjacent N40, lock_early autopsy): BTC/ETH 21 / 19 -4.6%, alts 30 / 28 -0.1% -> the N21 asset split does not rescue it; N40 DEAD.
- Test (outside the box N41, tally_source_census.py, local, 12-week tape): markets resolving on slow public counts. Ship transits (Hormuz /
  Bab el-Mandeb, 34 events): favourite 0.60-0.97 6-24 h out +11.1 pts [-0.8, +18.8] (29 events, 24 positive), follower +11.0 [-3.0, +20.7];
  24-168 h +3.4 [-2.1, +8.3]; halves +3.7 / +4.7; equal weight per event +4.9. Drought (5 events) and CDC counts (2) too few. Not a result
  (interval through 0, windows looked at) -> READY: live-market check + is the transit source readable early, then forward paper.
- Health: fast paper 04:08, slow 04:13, follow 04:24 (report 04:16, < 70 min), boosts 04:41, MM v2 04:01, books 04:45 - OK. Tracebacks only the
  old combo-sampler crash in pilot-log and the old script-log smoke; no MemoryErrors. Pilot STOP, no orders.
- Next: N41 (a) live 'ships transit' markets, (b) source reachability via Actions; LP-1 v2 48 h 11-16 ~10 UTC (N33/N35/N38 splits); box office
  settlements Monday; lock_p week mark 11-17 with the price split; N27 transcript feasibility; N34 Kalshi-first census.
## 11-15 09:00-09:40 UTC cycle 17 (scheduled)
- Read-outs (fast trades.jsonl, last 08:04): lock_x 19 / 17 +8.8% (15 end-times), lock_p 40 / 36 +6.6% (35), lock_p_majors 14/14 +13.2% - no new
  lock_x/lock_p signal since 11-14; lock_m 189 / 176 -0.5%, lock_b 45 / 42 -0.6%. N21 forward BTC/ETH 30/30 +5.4%, alts 35 / 31 -2.1% (2 days) -
  the split shows forward for the first time. N25 forward >= 0.80 50 / 49 +2.9% (37 end-times, first loss), < 0.80 3 / 1 -36.7%.
  Slow (08:10-08:13): converge 9 settled 8 won -$13, 85 open mark -$35; young 52 / 20 -$201 (37 open); options 31 / 11 +$13 (see N42); charts
  0 live; box office 9 open (Monday); mention 1 / 0 -$10. LP-1 v2 26 runs / 0.92 d: formula $1,009 (upper bound), trading -$262, pessimistic
  -$425; forward_other (N35) 15 markets formula $120 vs pessimistic -$145 (MrBeast views buckets) - failing so far; forward_core 2 markets.
  COPY-1 21.6 h: sharp 37 primaries, 1 settled; ask +4.7c over theirs, 38% pass the cap, lag 165 s; control 21 / 9 events -0.3 pts.
- Test N41 checks (transit_check.py via Actions): 153 live transit markets (Bab el-Mandeb / Hormuz weekly buckets, Panama Canal weekly, 'any
  day' thresholds); PortWatch reachable, but its last day on 11-15 is 11-08 (~7-day lag) -> the weekly buckets resolve a week after they 'end',
  the source cannot lead the price. DEAD as a source edge (LESSONS 25); the tape favourite effect gets one replication on the next tape refresh.
- Test (outside the box N43, gas_census.py, local, 12-week tape): AAA daily gas 1-cent buckets, 26 days: favourite -4.7 pts [-16.4, +6.4],
  trend nowcast hits 46% of days, its trades -0.9 pts. DEAD.
- New (adjacent N42, options_tail_readout.py): options paper tails < 0.20 5 / 2 +28.7 pts (3 coin-dates, two BTC dip long shots), rest 26 / 9
  -33.0 pts on 6 coin-dates, 0 positive. Open: 24 of 25 tails are crash bets, 0 of 48 rest -> one directional bet. TESTING (forward read-out).
- Health: fast paper 08:09, slow 08:13, follow 08:37 (report 08:27, < 70 min), boosts 07:59, MM v2 08:31, books 09:00 - OK. Tracebacks only the
  old pilot-log / script-log ones; no MemoryErrors. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 ~10 UTC (N33/N35/N38 splits); box office settlements Monday; lock_p week mark 11-17 with the price split;
  options N42 forward 11-19; N27 transcript feasibility; N34 Kalshi-first census.


## 11-15 13:00-13:40 UTC cycle 18 (scheduled)
- Read-outs (fast trades.jsonl, last settled 12:04): lock_x 19 / 17 +8.8% (no signal since 11-14 16:14), lock_p 41 / 37 +6.7% (36 end-times),
  lock_p_majors 15/15 +13.3% (one new win); lock_m 196 / 180 -1.9%, lock_b 48 / 44 -0.9%. N21 forward BTC/ETH 36 / 35 +2.1% (first loss),
  alts 41 / 35 -4.7% (2 days). N25 forward >= 0.80 60 / 58 +1.5% (43 end-times; +5.5 -> +2.9 -> +1.5 over three cycles, decaying),
  < 0.80 5 / 1 -75%. lock_x >= 0.80 16 / 14 -3.4% vs < 0.80 3/3 +60% -> lock_x's edge is 3 cheap fills.
  Slow (12:11-12:16): converge 9 / 8 -$13, 85 open mark -$31; young 52 / 20 -$201 (37 open); options 31 / 11 +$13, 75 open, N42 forward 0
  settled (26 open tails, 25 crash bets); box office 9 open (Monday); charts 2/2; mention 1 / 0 -$10. LP-1 v2 30 runs / 1.09 d: formula
  $1,156 (upper bound), trading -$238, pessimistic -$421; core 99 markets formula $727 vs pessimistic -$50, forward_core 4 markets; count/
  mention 14 markets pessimistic -$178. COPY-1 26 h: sharp 44 primaries, 1 settled (+49 pts, n=1).
- Test (adjacent N44, leaderboard_census.py, local, 12-week tape): N41's favourite rule on tweet / post count buckets, 6-24 h: -3.1 pts
  [-10.5, +3.2] on 105 events, newer half -7.5. DEAD - the transit result does not generalise.
- Test (outside the box N45, same script): AI-leaderboard markets (LMArena / LiveBench / AI agent, best / 2nd / 3rd end of week/month):
  favourite 24-168 h +3.7 pts [-1.0, +7.1] (46 events, 40 positive), 6-24 h +5.6 [4.7, 6.3] (15), halves +3.3 / +4.1; clustered by end-day
  +3.7 [-0.5, +6.2] on 16 days. OpenRouter share weekly -5.9 (30 events). Not a result (16 independent days, interval through 0) -> READY:
  forward paper on the 11-30 month-end markets.
- Health: fast paper 12:11, slow 12:16, follow 12:49 (report 12:49, < 70 min), boosts 12:23, MM v2 13:01, books 13:00 - OK. Tracebacks only
  the old pilot-log (2) / script-log (1) ones; no MemoryErrors. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 ~10 UTC (N33 hour split + N35/N38 forward); box office settlements Monday; lock_p week mark 11-17 with the price
  split (lock_x/lock_p look like a few cheap fills); N45 tracker for the 11-30 month-end; options N42 forward 11-19; N34 Kalshi-first census.

## 11-15 17:00-17:55 UTC cycle 19 (scheduled)
- Read-outs (fast trades.jsonl, last settled 16:09): lock_x 19 / 17 +8.8% (no signal since 11-14 16:14), lock_p 41 / 37 +6.7% (36 end-times,
  no new trade since 11:09), lock_p_majors 15/15 +13.3%; lock_m 201 / 184 -2.1%, lock_b 49 / 45 -0.7%, lock_p_z2 234 / 215 +0.2%.
  N21 forward BTC/ETH 39 / 38 +2.3% (2 days), alts 45 / 38 -5.7%. N25 forward >= 0.80 67 / 64 +0.8% (48 end-times; +5.5 -> +2.9 -> +1.5
  -> +0.8, decaying to zero), < 0.80 (the N25 rule itself) 5 / 1 -75% on 4 end-times - against it so far.
  Slow (16:12-16:16): converge 9 / 8 -$13, 85 open mark -$32; young 52 / 20 -$201 (38 open); options 31 / 11 +$13, 77 open, N42 forward 0
  settled (26 tails, 25 crash bets); box office 9 open (Monday); charts 2/2 +$3; mention 1 / 0 -$10. LP-1 v2 34 runs / 1.26 d: formula
  $1,273 (upper bound), trading -$155, pessimistic -$493; only 11 markets still quoted (150 of 170 saw a competitor); core 101 markets
  formula $740 vs pessimistic -$50, forward_core 6 markets $12 vs -$7, forward_other 20 markets $263 vs -$197 (N35 failing).
  COPY-1 29.9 h: sharp 52 primaries, 3 settled 3/3 +34.7 pts (n=3, means nothing yet); control 21 / 9 events -0.3 pts.
- Test (adjacent N46, riskday_census.py, local, 12-week tape, N45 rule): month-end rank markets beyond LMArena - largest company favourite
  24-168 h -40.1 pts [-47.4, -0.2] (6 events), Chinese AI company +0.5 [-9.0, +7.1] (9). DEAD.
- Test (outside the box N47, riskday_census.py + riskday_clock.py local, riskday_check.py via Actions): rain / tornado-risk city binaries.
  Rules read: rain = NWS CLI next morning, ends 19 UTC next day; tornado = SPC 01 UTC Day 1 polygon, ends 12 UTC; SPC GeoJSON reachable.
  Rain favourite at hb 6-13 (day over, CLI pending) +6.3 pts [3.6, 10.0] on 7 dates (7/7), long shots -7.5; all 6-24 h +3.3 [-2.2, +7.4]
  (20 dates). Tornado NO favourite +3.0 [1.7, 3.7] on 9 dates at 0.96 (tail, series looks stopped). Books very thin. Not a result -> READY:
  METAR nowcast check, then forward paper.
- Health: fast paper 16:12, slow 16:16, follow 16:49 (report 16:43, < 70 min), boosts 16:47, MM v2 16:32, books 17:00 - OK. Tracebacks only the
  old pilot-log (2) / script-log (1) ones; no MemoryErrors. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 ~10 UTC; box office settlements Monday; lock_p week mark 11-17 (it is a few cheap fills; N25 forward says no);
  N47 METAR check (Iowa Mesonet ASOS) for the hb 6-13 rain fills; N45 tracker for 11-30; options N42 forward 11-19.

## 11-15 21:00-21:40 UTC cycle 20 (scheduled)
- Read-outs (fast trades.jsonl, last settled 20:09): lock_x 19 / 17 +8.8% (no signal since 11-14), lock_p 42 / 37 +5.1% (37 end-times, one new
  loss), lock_p_majors 15/15 +13.3%; lock_m 204 / 186 -2.2%, lock_b 51 / 47 -0.5%, lock_p_z2 238 / 217 -0.2%. N21 forward BTC/ETH 43 / 41
  +1.7%, alts 48 / 40 -6.2% (2 days). N25 forward < 0.80 6 / 2 -65.5% (5 end-times) -> DEAD; >= 0.80 73 / 68 -0.1% (52 end-times).
  Slow (20:13-20:16): converge 9 / 8 -$13, 85 open mark -$34; young 52 / 20 -$201 (38 open); options 40 / 12 -$52, 68 open, N42 forward 0
  settled; box office 9 open (Monday); charts 2/2 +$3; mention 1 / 0 -$10. LP-1 v2 39 runs / 1.42 d: formula $1,386 (upper bound), trading
  -$221, pessimistic -$529; 12 markets still quoted, 157 of 178 saw a competitor; forward_other 23 markets $322 vs -$196, forward_core 9
  markets $31 vs -$7. COPY-1 33 h: sharp 60 primaries, 4 settled 4/4 (n=4); control 25 settled +0.1 pts.
- Test (N47 READY + adjacent N48, riskday_metar.py via Actions, IEM METARs + archived CLI, 361 rain markets / 26 dates): METAR day sum agrees with
  the resolution on 357/361 (CLI 359/361) - the answer is public - but the CLI is out 1-2 h after the climate day and only 23 fills traded
  after it: 7 on the METAR side +9.4 pts [-23, +34] (5 dates), 16 against, all lost. N48 (YES after METARs already show rain): 9/9 won +8.5 pts
  on 4 dates. Right but crumbs -> both DEAD (capacity), LESSONS 26. Tornado part parked (series stopped).
- New (outside the box N49, election_late_census.py, local): midterm races after election night. 133 races in the tape; pre-election favourite
  +5.3 [-0.2, +9.7] (one night), election night +2.4 [-6, +9], after-night only 5 resolved races (-9.5) -> not testable here, PARKED.
- Health: fast paper 20:13, slow 20:17, follow 21:02 (report 20:55, < 70 min), boosts 20:03, MM v2 20:31, books 21:00 - OK. Tracebacks only the
  old pilot-log (2) / script-log (1) ones; no MemoryErrors. IEM rate-limits (429) but retries passed. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 ~10 UTC (forward_other failing, forward_core still tiny); box office settlements Monday; lock_p week mark 11-17
  (+5.1% on 37 end-times, but the profit is a few cheap fills and N25 forward says those lose); N45 tracker for 11-30; options N42 11-19.

## 11-16 01:00-01:35 UTC cycle 21 (scheduled)
- Read-outs (fast trades.jsonl, last settled 00:10): lock_x 19 / 17 +8.9% (no signal since 11-14), lock_p 43 / 38 +5.1% (38 end-times),
  lock_p_majors 15/15 +13.4%; lock_m 206 / 187 -2.8%, lock_b 52 / 48 -0.5%, lock_p_z2 240 / 218 -0.7%. N21 forward BTC/ETH 45 / 42 -0.8%
  (3 days; was +5.4 -> +1.7 -> -0.8, under its +2% bar), alts 50 / 42 -5.5%. N25 forward >= 0.80 77 / 71 -1.3% (56 end-times).
  Slow (00:15-00:17): converge 9 / 8 -$13, 85 open mark -$25; young 52 / 20 -$201 (38 open); options 40 / 12 -$52, 68 open, N42 forward 0
  settled; box office 9 open (settle Monday); charts 2/2 +$3; mention 1 / 0 -$10. LP-1 v2 44 runs / 1.59 d: formula $1,450 (upper bound),
  trading -$220, pessimistic -$557; 168 of 190 saw a competitor, 10 still quoted; forward_other 33 markets $379 vs -$196 (N35 failing),
  forward_core 18 markets $73 vs -$12. N33 clock split not readable (all fills so far weekend). COPY-1 37 h: sharp 72 primaries, 4 settled
  4/4 (n=4); control 25 settled / 12 events +0.1 pts.
- Test (outside the box N50, tv_awards_census.py, local, 12-week tape): reality-TV eliminations / evictions (DWTS, Big Brother, AGT; 16
  events): favourite 6-168 h +1.2 pts [-4.4, +7.5], halves -4.0 / +8.2, big takers +1.4 [-7, +9] -> DEAD.
- Test (adjacent N51, same script): pre-decided awards (Ballon d'Or, Nobel, VMAs, Emmys; 43 events / 9 ceremonies): favourite 6-168 h
  +3.7 [-1.7, +7.9] per event, by ceremony [-4.9, +5.2] -> DEAD. Big takers >= $200 +4.3 [0.9, 7.5] and small -2.0 (lesson 17 again), but
  by ceremony [-2.4, +8.0] - nothing to build.
- Health: fast paper 00:14, slow 00:17, follow 00:14 (report 00:05, < 70 min), boosts 00:28, MM v2 01:01, books 01:00 - OK. Tracebacks only
  the old pilot-log (2) / script-log (1) ones; no MemoryErrors. Pilot STOP, no orders.
- Next: LP-1 v2 48 h 11-16 ~10 UTC (forward_core is the only LP piece still alive; N33 clock split needs weekday fills); box office
  settlements today; lock_p week mark 11-17 (+5.1% on 38 end-times; profit is a few cheap fills); N21 11-21 (now below bar); N45 11-30.

## 11-16 05:00-05:40 UTC cycle 22 (scheduled)
- Read-outs (fast trades.jsonl, last trade 04:03): lock_x 21 / 18 +7.2% (17 end-times), lock_p 46 / 39 +1.5% (40 end-times; was +5.1, three
  new losses), lock_p_majors 17 / 16 +5.4%; lock_m 209 / 189 -3.0%, lock_b 55 / 50 -1.2%, lock_p_z2 244 / 220 -1.2%. N21 forward BTC/ETH 50 / 47
  -0.2% (3 days, below its +2% bar), alts 51 / 42 -6.7%.
  Slow (04:16-04:19): converge 11 / 10 -$12, 83 open mark -$30; young 52 / 20 -$201 (38 open); options 40 / 12 -$52, 69 open, N42 forward 0
  settled (24 tails, 23 crash bets); box office 9 open (settle today); charts 2/2 +$3 BUT 0 events seen for days (bug, fixed below); mention
  1 / 0 -$10. LP-1 v2 49 runs / 1.76 d: formula $1,483 (upper bound), trading -$225, pessimistic -$564; 175 of 194 saw a competitor, 5 still
  quoted; forward_other 36 markets $402 vs -$196 (N35 failing), forward_core 21 markets $96 vs -$13 (pessimistic -13% of formula, passing so
  far, tiny). COPY-1 41.6 h: sharp 85 primaries, 8 settled / 5 events 7 won +24.6 pts (n tiny); control 25 / 12 events +0.1 pts.
- Test (outside the box N52, statuspage_census.py, local, 12-week tape): status-page / running-count markets (Claude 'go down', ChatGPT
  outages, GitHub incident, Codex resets, SpaceX launches; 28 events): favourite 6-168 h +6.2 pts [-4.7, +13.9], by end day [-10.8, +15.4]
  (25 days) -> DEAD by the pre-registered rule; positive everywhere but too few events per family; re-check on the next tape refresh.
- Test (adjacent N53, same script): Ornn GPU rental index month-end buckets: favourite -0.2 [-9.5, +8.9] on 5 month-ends -> DEAD; big takers
  +5.7 [1.4, 9.7] and small -2.3 (lesson 17 again).
- Health: fast paper 04:16, slow 04:19, follow 04:26 (report 04:26, < 70 min), boosts 04:53, MM v2 04:32, books 05:00 - OK. Tracebacks only the
  old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders. FIX: charts_paper.py saw 0 chart events in every run (same
  capped end-date scan bug as box office / converge_day) -> text search + scan to 20,000. Check (charts_probe.py via Actions, 05:08): the
  search finds 50 chart events, but none ends in the 2-24 h window right now (next: Netflix weekly 11-18 04:59, so first entries 11-17
  ~05 UTC); the fixed tracker ran clean (0 seen is true at this hour). Check again next cycle that it enters.
- Next: LP-1 v2 48 h read ~10 UTC (forward_core only live piece); box office settlements today; lock_p week mark 11-17 (now +1.5%, fading);
  N21 11-21 (below bar); N45 11-30; check charts tracker sees events.

## 11-16 09:00-09:40 UTC cycle 23 (scheduled)
- Read-outs (fast trades.jsonl, last settled 09:01): lock_x 21 / 18 +7.2% (no signal since 04:34), lock_p 46 / 39 +1.5% (40 end-times),
  lock_p_majors 17 / 16 +5.4%; lock_m 214 / 194 -2.8%, lock_b 59 / 54 -0.9%, lock_p_z2 250 / 226 -1.1%. N21 forward BTC/ETH 57 / 52 -3.2%
  (3 days; failing, formal decision 11-21), alts 56 / 46 -8.2%.
  Slow (08:17-08:22): converge 13 / 12 -$11 (non-sports 12/12 +3.8%), 81 open mark -$29; young 55 / 23 -$187 (38 open); options 59 / 21
  +$169 / $559 (two long shots), 56 open; N42 forward tails 1 / 0, rest 2 / 2 +20.5 pts (n tiny); box office 9 open, 0 settled yet; charts
  0 events seen (expected: next chart event enters 11-17 ~05 UTC); mention 1 / 0 -$10.
  LP-1 v2 48-h read (53 runs / 1.93 d): formula $1,513 (upper bound), trading -$224, pessimistic 158 fills -$566; 179 of 202 markets saw a
  competitor, 7 still quoted. forward_other 38 markets $425 vs -$197 (-46% of formula: N35 failing), forward_core 23 markets $119 vs -$13
  (-11%: passing, but 23 markets / 2 days; rule needs 40+ markets, 3+ days). COPY-1 45.5 h: sharp 98 primaries, 12 settled / 7 events 10 won
  +12.3 pts (n tiny); control 39 / 16 events +1.9 pts.
- Test (outside the box N54, macro_census.py, local, 12-week tape): US macro release buckets (CPI, core CPI, PPI, ISM, unemployment, UMich,
  eggs; 27 releases): favourite 6-168 h -10.0 pts [-21.5, +2.7], halves +2.2 / -18.1; after the release +3.9 on 17 releases (crumbs) -> DEAD.
- Test (adjacent N55, same script): Treasury-yield touch ladders: only 2 finished months -> DEAD by rule; favourite -9.0, YES long shots +8.9
  (two moving months, not a market property).
- Health: fast paper 08:17, slow 08:20, follow 08:27 (report 08:22, < 70 min), boosts 08:09, MM v2 09:00, books 09:00 - OK. Tracebacks only the
  old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: box office settlements (today/tomorrow); lock_p week mark 11-17 (+1.5% on 40 end-times, below the +5% bar -> expect to close it);
  charts tracker first entries 11-17 ~05 UTC; LP-1 forward_core to 40 markets (11-17..19); N21 11-21; options N42 11-19; N45 11-30.

## 11-16 13:00-13:30 UTC cycle 24 (scheduled)
- Read-outs (fast trades.jsonl, last settled 12:13): lock_x 23 / 20 +7.3% (19 end-times), lock_p 48 / 41 +1.8% (42 end-times), lock_p_majors
  18 / 17 +5.3%; lock_m 221 / 201 -2.4%, lock_b 65 / 60 -0.0%, lock_p_z2 259 / 235 -0.7%. N21 forward BTC/ETH 67 / 62 -1.7% (3 days, below
  its +2% bar), alts 63 / 53 -6.0%.
  Slow (12:19-12:20): converge 13 / 12 -$11 (non-sports 12/12 +3.8%), 81 open mark -$28; young 55 / 23 -$187 (39 open); options unchanged
  (N42 forward tails 1 / 0, rest 2 / 2 +20.5 pts, 61 open); box office 9 open, 0 settled (Monday resolution not in yet); charts 0 events
  (expected until 11-17 ~05 UTC); mention 1 / 0 -$10. LP-1 v2 58 runs / 2.09 d: formula $1,563 (upper bound), trading -$247, pessimistic
  -$605; 185 markets saw a competitor, 3 still quoted. forward_core 25 markets $148 vs +$6 trading / -$22 pessimistic (-15% of formula,
  passing, still < 40 markets); forward_other 42 markets $471 vs -$236 (N35 failing). COPY-1 46.4 h: sharp 100 primaries, 14 settled /
  9 events 11 won +4.7 pts (n tiny); control 39 / 16 events +1.9 pts.
- Test (outside the box N56, fresh_wallet_census.py, local, 12-week tape): the insider footprint - follow a wallet's first-ever entry
  (politics, geopolitics, ai/tech, economy): follower 60 s later -0.93 pts [-2.8, +0.4] on 949 events, halves +4.95 / -1.65, the >= $500
  lookahead upper bound -1.05 [-3.8, +1.6] -> DEAD. New lesson 27 (the famous cases are the visible tail).
- Test (adjacent N57, same script): fresh wallets in culture / mention: -3.19 [-4.5, -1.9] on 585 events (mention -7.6) -> DEAD.
- Health: fast paper 12:19, slow 12:21, follow 12:40 (report 12:32, < 70 min), boosts 12:32, MM v2 13:01, books 13:00 - OK. Tracebacks only
  the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: box office settlements (check next cycle that they settle; if still 0 settled on 11-17, it is a bug until shown otherwise);
  lock_p week mark 11-17 (+1.8%, below the +5% bar -> expect to close); charts first entries 11-17 ~05 UTC; LP-1 forward_core to 40
  markets; N21 11-21; options N42 11-19; N45 11-30.

## 11-16 17:00-17:15 UTC cycle 25 (scheduled)
- Read-outs (fast trades.jsonl, last lock settled 14:24): lock_x 23 settled +7.3% (19 end-times, no new signal), lock_p 48 +1.8% (42),
  lock_p_majors 18 +5.3%; lock_m 222 -2.4%, lock_b 65 -0.0%, lock_p_z2 260 -0.6%. N21 forward BTC/ETH 68 / 63 -1.6% (3 days, below its +2%
  bar), alts 66 / 56 -5.3%. Slow (16:20-16:23): converge 13 / 12 -$11 (non-sports 12/12 +3.8%), 81 open mark -$27; young 55 / 23 -$187
  (45 open); options 59 / 21 +$169, 61 open, N42 forward tails 1 / 0 -14 pts, rest 2 / 2 +20.5 (n tiny); box office 9 open, 0 settled at
  16:21 UTC (= 11:21 ET Monday; actuals usually post Monday afternoon US - check next cycle, a bug only if still unsettled 11-17); charts 0
  events (expected until 11-17 ~05 UTC); mention 1 / 0 -$10. LP-1 v2 62 runs / 2.26 d: formula $1,606 (upper bound), trading -$248,
  pessimistic -$610; 188 markets saw a competitor, 4 still quoted. forward_core 32 markets $153 vs +$9 trading / -$22 pessimistic (-14% of
  formula, passing, < 40 markets); forward_other 49 markets $489 vs -$241 (N35 failing). COPY-1 50.5 h: sharp 114 primaries, 19 settled /
  13 events 16 won +6.5 pts (weather -1.4, rest +17; n tiny); control 39 / 16 events +1.9 pts.
- Test (outside the box N59, launch_census.py, local, 12-week tape): new market launches - follower fill in the first hour after a market's
  first trade +0.3 pts [-0.5, +1.0] on 3,379 events, halves +1.06 / -0.58 -> DEAD by its pre-registered rule. First takers' own fills +0.5
  [0.2, 0.9] vs -0.5 at 24-72 h (seed books a little stale, taken in seconds).
- Adjacent N58 (found AFTER looking, lesson 22): culture launch-hour NO, one follower fill per market +7.4 pts [5.5, 9.3] on 614 events /
  112 days, halves +8.7 / +5.6 [2.8, 8.4], non-mention +4.6 (both halves positive); the same NO 24-72 h later +0.7. -> READY with a
  pre-registered forward rule (tracker on new listings next cycle, inside the follow.yml chain).
- Health: fast paper 16:20, slow 16:24, follow 16:51 (report 16:43, < 70 min), boosts 16:58, MM v2 publishing, books 17:00 - OK. Tracebacks
  only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: build the N58 forward tracker (new culture listings, real NO ask, first hour); box office settlements; lock_p week mark 11-17 (+1.8%,
  below the +5% bar -> close); charts first entries 11-17 ~05 UTC; LP-1 forward_core to 40 markets; N21 11-21; options N42 11-19; N45 11-30.

## 11-16 17:00-17:50 UTC LP-1 read-out (scheduled one-shot, deep session)
- BUG found and fixed in lp_paper.py: no market was ever settled (Gamma list drops closed markets) and leftovers were marked at our last
  fair price. The 17:21 run settled 60 resolved markets and re-marked 67 open leftovers at today's price. The LP-1 trading numbers in
  cycles 13-25 (incl. '-$248 / -$610' two entries above) were too rosy; the splits N35 / N38 moved too. LESSONS 28.
- Corrected read (2.3 d, 63 runs, 213 markets): formula reward $1,615 (upper bound); trading -$436 on 648 tape fills, -$760 on 163
  pessimistic fills; break-even payout ratio 27% / 47%. 188 of 213 got a competitor (median 2.3 h to exit), 92 pools removed, 2 still
  quoted; formula accrual $1,047 first 24 h -> $354 last 24 h. Weather $191 vs -$240 / -$302; live count/mention/views $541 vs -$231 /
  -$386; core $884 vs +$35 / -$73 (48 markets with open leftovers); forward_core 32 markets $156 vs +$29 / -$20 (-13%, passing, bar is
  40 markets / 3 days); forward_other 49 markets $492 vs -$62 / -$286 (-58%: N35 fails). $200 slice: $93 vs -$37 / -$69.
- Verdict sent to the user: the proposed 48-h / $200 / 5-market live test is not worth an OK. Proposed instead (waiting for his answer,
  do NOT run without it - it uses the account key): a read-only query of our own reward history for the pilot days
  (CLOB GET /rewards/user/markets?date=, L2 auth; docs.polymarket.com/api-reference/rewards) = the real payout ratio with no orders.
- COPY-1 at 50.5 h: sharp 114 primaries, 19 settled / 13 events +6.5 pts (n tiny). Already clear: only 40% of their orders can be
  followed within 3c (ask after their trade is a median 4.2c above their price) and our lag is ~2 min, not seconds (the public feed);
  the 24-h mark of 34 sharp primaries is -6.3 pts vs the ask paid; control (99) -0.0. Decision rule unchanged (300 settled).
- Next cycle: check the 18:21 LP run keeps settling (report fields settled_markets / open_leftover_markets); read N38 with the corrected
  numbers; if the user OKs the read-only reward query, write it as a one-off script for the pilot workflow's secrets (no orders).
- 17:50 note: the run_script dispatch of lp_settle_probe.py (run 43915402685, 17:09) never left 'queued' and cannot be cancelled ('run is
  completed') - a ghost on GitHub's side, scheduled workflows kept running. The probe is redundant (the fixed lp_paper settled at 17:21 and
  the numbers above were recomputed locally from the committed state). Next cycle: confirm a fresh run_script dispatch starts normally.

## 11-16 21:00-21:45 UTC cycle 26 (scheduled)
- Read-outs (fast trades.jsonl, last settled 20:09): lock_x 24 / 21 +7.1% (20 end-times), lock_p 50 / 43 +1.9% (44), lock_p_majors 19 / 18 +5.2%;
  lock_m 229 -2.1%, lock_b 71 +0.5%, lock_p_z2 268 -0.4%. N21 forward BTC/ETH 76 / 71 -0.9% (3 days, below its +2% bar), alts 75 / 64 -5.9%.
  Slow (20:22-20:24): converge 14 / 13 -$10, 80 open mark -$29; young 55 / 23 -$187 (49 open); options 69 settled +$103, 51 open, N42 forward
  tails 1 / 0 -14 pts, rest 2 / 2 +20.5 (unchanged); box office SETTLES now: 2 / 2 +$2.06, 7 open (the Monday worry is closed); charts 0 events
  (expected until 11-17 ~05 UTC); mention 1 / 0 -$10. LP-1 v2 (fixed settlement) 66 runs / 2.43 d: formula $1,641 (upper bound), trading -$467,
  pessimistic -$714; settled 65 markets, 62 open leftovers (guard OK: it settles); forward_core 35 markets $158 vs +$30 / -$22 (-14%, passing,
  < 40 markets); forward_other 52 markets $494 vs -$69 / -$296 (N35 failing). COPY-1 54.7 h: sharp 26 primaries settled / 18 events 21 won
  +7.2 pts (n tiny); control 42 / 19 events +2.7 pts.
- Test (adjacent N60, launch_latency.py, local, 12-week tape): does N58 survive our latency? One culture NO fill per market in the launch hour:
  follower >= 60 s +8.8 pts [6.5, 11.2] (554 events), >= 300 s +8.4 [6.0, 10.7] (543), halves +10.6 / +5.8, non-mention +5.6 [2.9, 8.1];
  86% of fills in the first 10 min; median NO drift 60 -> 300 s 0c -> PASSED. Still found by looking (lesson 22): only the forward run counts.
- Built: N58 forward paper launch_paper.py (TESTING), running inside the follow.yml chain from its next hand-over (poll 150 s, $10 at the real
  NO ask, pre-registered kill/promote rule, settled / open_past_end guard). Logs to logs/launch-log.txt, data in data/launch/.
- New (outside the box N61): year-end lists from one publisher (words of the year, Wrapped, Year in Search, TIME POY) where the sources publish
  in stages -> READY; needs Gamma history (Actions).
- Health: fast paper 20:21, slow 20:24, follow 21:04 (report 20:54, < 70 min), boosts 20:19, MM v2 21:01, books 21:00 - OK. The 17:09 'ghost'
  run_script did publish 'Script output' at 18:21. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: confirm data/launch/report.json appears after the next follow hand-over (~03:00 UTC) with candidates > 0 (0 candidates for a day = bug,
  lesson 10); N61 history script; lock_p week mark 11-17 (+1.9%, below the +5% bar -> close); charts first entries 11-17 ~05 UTC; LP-1
  forward_core to 40 markets; N21 11-21; options N42 11-19; N45 11-30.
- 21:20 smoke run (run_script launch_smoke.py, 6 min, live API): tracker runs clean, 532 events listed over 4 polls, 0 new listings < 60 min in that window (base rate ~3 an hour, so plausible). Added a '< 24 h old' counter so the next cycle can tell a quiet hour from a discovery bug.

## 11-17 01:00-01:40 UTC cycle 27 (scheduled)
- Read-outs (fast trades.jsonl, last settled 00:20): lock_p WEEK MARK +2.2% on 53 / 46 (47 end-times) < +5% bar -> CLOSED (DEAD); lock_x 27 / 24
  +7.0% (23 end-times, needs 30+, week mark 11-19), lock_p_majors 22 / 21 +5.4%; lock_m 238 -2.6%, lock_p_z2 280 -0.6%. N21 forward BTC/ETH
  87 / 81 -1.4% (3 days, below +2%; read 11-21), alts 84 / 72 -5.4%. Slow (00:23-00:27): converge 14 / 13 -$10, 80 open mark -$29; young 59 / 27
  -$169 (45 open); options 69 settled +$103, 53 open, N42 forward tails 1 / 0 -14 pts, rest 2 / 2 +20.5 (unchanged); box office all 9 settled
  8 won -$0.96 (2 weekends); charts 2 / 2 +$3.35 (app store), 0 chart events seen (first entries expected ~05 UTC); mention 1 / 0 -$10.
  LP-1 v2 71 runs / 2.6 d: formula $1,688 (upper bound), trading -$492, pessimistic -$706; settled 68, 65 open leftovers; forward_core 47
  markets $191 vs +$23 / -$27 (-14% of formula, passing; 40-market bar reached, 3-day mark ~11-17 21 UTC); forward_other 64 markets $527 vs
  -$73 / -$292 (N35 failing). COPY-1 57.8 h: sharp 29 primaries settled / 19 events 22 won +3.5 pts (n tiny; was +7.2); 132 primaries.
- Test (adjacent N62, lateadd_census.py, local, 12-week tape): outcomes added >= 24 h after their event listed, launch-hour NO, follower
  >= 300 s, non-culture: -2.3 pts [-9.0, +3.9] on 131 events, halves +3.4 / -13.5 -> DEAD. Side read: culture late-adds NO +11.0 [5.0, 16.9]
  (118 events) vs culture originals +5.6 - inside N58's scope; split the N58 forward run by event age at listing.
- New (outside the box N63): 'slot-only' events (Congress in recess, no SCOTUS opinion day before a 'by <date>' deadline) -> READY, needs
  the official 2026 calendars.
- Health: fast paper 00:23, slow 00:28, follow 01:04 (report 23:59 -> 01:04 hand-over, OK), boosts 00:41, MM v2 01:01, books 01:00 - OK.
  data/launch not there yet: expected after the next follow hand-over (~03 UTC), not a bug yet. Tracebacks only the old pilot-log (2) /
  script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: data/launch/report.json after ~03 UTC with candidates > 0 (and the '< 24 h old' counter); LP-1 forward_core 3-day mark ~21 UTC;
  lock_x week mark 11-19; charts first entries ~05 UTC; N63 calendars + test; N61 history; N21 11-21; options N42 11-19; N45 11-30.

## 11-17 05:00-05:45 UTC cycle 28 (scheduled)
- Read-outs (fast trades.jsonl, last 04:23): lock_x 28 / 28 settled +6.8% (24 end-times, needs 30+, week mark 11-19), lock_p_majors 23 +5.3%;
  lock_m 249 -3.3%, lock_b 84 -0.2%, lock_p_z2 293 -2.0% (lock_p closed last cycle, now 54 +2.3%). N21 forward BTC/ETH 98 windows / 90 won
  -3.0% (4 days, below +2%; read 11-21), alts 91 / 77 -7.3%. Slow (04:35-04:37): converge 14 / 13 -$10, 81 open mark -$31; young 59 / 27 -$169
  (49 open); options N42 forward tails 1 / 0 -14 pts, rest 2 / 2 +20.5 (unchanged), 54 open; box office 9 / 8 -$0.96 (no new weekend);
  charts 2 / 2 +$3.35, 0 chart events at 04:36 (first entries expected ~05 UTC); mention 1 / 0 -$10, 4 open. LP-1 v2 76 runs / 2.77 d:
  formula $1,723 (upper bound), trading -$514, pessimistic -$729; settled 69, 68 open leftovers (guard OK); only 5 markets still quoted;
  forward_core 47 markets $223 vs +$18 / -$38 (-17% of formula, passing; 3-day mark ~21 UTC); forward_other 64 markets $559 vs -$76 / -$304
  (N35 failing). COPY-1 61.9 h: sharp 29 primaries settled / 19 events +3.5 pts (unchanged), 147 primaries.
- N58 launch tracker: first report is there (data/launch/report.json 04:15): 3 h, 72 polls, 129 new listings, 3 paper positions, 0 settled;
  skips 86 'not accepting orders' (placeholder 'Person A..L' outcomes), 29 no NO ask, 7 spread > 10c, 4 ask outside band. Candidates > 0: no bug.
  (The empty logs/launch-log.txt is expected - the tracker prints only on errors.)
- Test (local, 12-week tape, wide_other_census.py, rules fixed before looking):
  - adjacent N64 wide-event launch-hour NO outside culture: +1.04 pts [-0.2, +2.3] on 362 events; halves +1.9 / +0.2. Passes the letter by
    0.04 pt; lesson 24 -> PARKED, not built. N58 diagnostic: culture edge is in single / narrow events (+16.6 / +7.5), wide +4.2 -> fans, not
    overround.
  - outside the box N65 catch-all 'Other' YES 6-168 h: -1.2 pts [-17.8, +20.6] on 20 events -> DEAD (< 30); the regex mostly catches titles.
- Health: fast paper 04:24, slow 04:39, follow 04:16 (report 04:09, chain job running to ~06:20), boosts 04:00, MM v2 04:31, books 05:00 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: N58 first settlements (positions need >= 24 h); LP-1 forward_core 3-day mark ~21 UTC; lock_x week mark 11-19; charts entries; N63
  calendars + test; N61 history; N21 11-21; options N42 11-19; N45 11-30.

## 11-17 09:00-09:45 UTC cycle 29 (scheduled)
- Read-outs (fast trades.jsonl, last settled 08:19): lock_x 30 trades / 26 end-times +6.6% (needs 30 end-times, week mark 11-19), lock_x50
  +10.0% (same 30), lock_p_majors 24 / 22 +5.3%; lock_m 253 -3.1%, lock_b 89 +0.2%, lock_p_z2 297 -1.7%. N21 forward BTC/ETH 103 windows / 93
  won -4.3% (4 days, below +2%; read 11-21), alts 95 / 81 -6.6%. Slow (08:26-08:28): converge 14 / 13 -$10, 81 open mark -$34; young 60 / 28
  -$162 (48 open); options N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3 (4 events), 53 open; box office 9 / 8 -$0.96; charts 2 / 2
  +$3.35 (8 chart events seen, 0 entries); mention 1 / 0 -$10, 4 open. LP-1 v2 80 runs / 2.93 d: formula $1,770 (upper bound), trading
  -$525, pessimistic -$765; 71 settled, 68 open leftovers; forward_core 50 markets $265 vs +$28 / -$46 (-17% of formula, passing; 3-day mark
  ~21 UTC); forward_other 67 markets $601 vs -$64 / -$310 (N35 failing). COPY-1 66 h: sharp 30 primaries settled / 20 events +2.3 pts
  (n tiny), control 45 / 21 +4.3. N58 launch tracker: 3 open, 0 settled, 161 candidates, 158 skipped.
- Test (adjacent N66, lateadd_culture.py, local, 12-week tape, splits fixed before looking): culture late-add NO launch hour, follower
  >= 300 s: +11.0 pts [5.1, 16.5], 118 events; halves +9.9 / +11.7; ex-mention +9.7 [2.2, 17.4]; top event 11% -> PASS.
  Why it matters now: the tracker looked once and dropped 158 / 161 candidates for transient reasons; 86 were placeholders that later open as
  late-adds. Built in launch_paper.py: 'retry' (re-read transient skips while < 60 min old) and 'activated' (placeholders watched 14 d by
  id, L = when they open); reported separately, the N58 decision stays on the first-look arm. Local run impossible (no Gamma from here):
  smoke run via run_script; live from the next follow hand-over (~13:30 UTC).
- New (outside the box N67): token-launch FDV ladders vs pre-launch perps -> READY (needs Gamma + perp candle history via Actions).
- Health: fast paper 08:26, slow 08:31, follow 08:29 (report 08:21, < 70 min), boosts 08:24, MM v2 09:01, books 09:00 - OK. Tracebacks only
  the old pilot-log / script-log; no MemoryErrors. Pilot STOP, no orders.
- Next: smoke result of the new tracker arms; first N58 settlements; LP-1 forward_core 3-day mark ~21 UTC; lock_x week mark 11-19; N63
  calendars; N61 history; N67 history; N21 11-21; options N42 11-19; N45 11-30.
- 09:40 check: run_script smoke of the new tracker (live API, 6 min) ran clean (540 events listed, 0 errors, no new listing in the window);
  a mocked-API run exercised all three arms (first / retry / activated: 1 position each, watch emptied). (First dispatch failed: run_script
  paths are relative to research/, i.e. 'slow/launch_smoke.py'.)

## 11-17 13:00-13:25 UTC cycle 30 (scheduled)
- Read-outs (fast trades.jsonl, last settled 12:24): lock_x 31 trades / 27 end-times +6.5% (needs 30 end-times, week mark 11-19), lock_x50
  +9.7%, lock_p_majors 25 / 23 +5.2%; lock_m 261 -2.8%, lock_b 94 +0.4%, lock_p_z2 307 -1.5%. N21 forward BTC/ETH 109 windows / 99 won -3.7%
  (4 days, below +2%; read 11-21), alts 104 / 90 -5.7%. Slow (12:27-12:29): converge 14 / 13 -$10, 82 open mark -$37; young 61 / 28 -$172
  (47 open); options N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3 (4 events, unchanged), 54 open; box office 9 / 8 -$0.96; charts
  2 / 2 +$3.35, 1 open; mention 1 / 0 -$10, 4 open. LP-1 v2 84 runs / 3.1 d: formula $1,794 (upper bound), trading -$505, pessimistic -$737;
  73 settled, 69 open leftovers (guard OK), 4 quoted; forward_core 50 markets $289 vs +$34 / -$42 (-15% of formula, passing; 3 days reached,
  40-market bar reached -> read formally with LP-1 5-day mark 11-19); forward_other 68 markets $625 vs -$67 / -$308 (N35 failing).
  COPY-1 70 h: sharp 31 primaries settled / 21 events +2.7 pts (n tiny), control 45 / 21 +4.3. N58 launch tracker (12:39): 3 open, 0 settled,
  open_past_end 0; N66 arms not live yet (next follow hand-over).
- Test (adjacent N68, culture_decay.py, local, 12-week tape, rules fixed before looking): culture NO 1-6 h after listing, follower >= 300 s,
  one fill per market: +4.6 pts [2.6, 6.8] on 515 events; halves +6.7 / +2.5 [-0.3, +5.4]; ex-mention +3.7; top event 4%; markets with no
  launch-hour fill +4.1 [1.0, 7.6] -> PASS. Decay < 1 h +7.1, 1-3 h +5.1, 3-6 h +4.6, 6-24 h +3.5 (24-72 h was +0.7 in c25). Placebo: YES side
  same buckets -4.1 [-6.6, -1.5] -> fans over-price YES. Built: 'late' arm in launch_paper.py (one look at 1-6 h; mocked-API run: < 1 h ->
  first, 2 h -> late, 8 h -> skipped). Live from the next follow hand-over.
- New (outside the box N69): twin markets (same question in two events) -> DEAD by count: 36 groups in 12 weeks, ~20 independent topics,
  mostly overlapping rolling 'by <date>' series; riskless-cents anyway (lesson 8).
- Health: fast paper 12:27, slow 12:32, follow 12:41 (report 12:32, < 70 min), boosts 12:49, MM v2 12:31, books 13:00 - OK. Tracebacks only
  the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders. (Local main had diverged from origin - reset to origin/main.)
- Next: N58 + N66 + N68 arms in the next launch report; lock_x week mark 11-19; LP-1 5-day mark 11-19; N21 11-21; options N42 11-19; N63
  calendars; N61 history; N67 history; N45 11-30.

## 11-17 17:00-17:25 UTC cycle 31 (scheduled)
- Read-outs (fast trades.jsonl, last settled 16:24): lock_x 32 trades / 28 end-times +6.4% (needs 30 end-times, week mark 11-19), lock_x50
  +9.5%, lock_p_majors 26 / 24 +5.2%; lock_m 263 -2.8%, lock_b 96 +0.5%, lock_p_z2 316 -1.3%. N21 forward BTC/ETH 114 windows / 104 won -3.3%
  (4 days, below +2%; read 11-21), alts 112 / 98 -5.0%. Slow (16:29-16:31): converge 14 / 13 -$10, 82 open mark -$39; young 62 / 28 -$182
  (51 open); options N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3 (4 events, unchanged), 57 open; box office 9 / 8 -$0.96; charts 2 / 2
  +$3.35, 1 open; mention 2 / 1 -$8.74, 3 open. LP-1 v2 89 runs / 3.27 d: formula $1,805 (upper bound), trading -$503, pessimistic -$761;
  80 settled, 67 open leftovers (guard OK), 4 quoted; forward_core 54 markets $300 vs +$37 / -$19 (-6% of formula, passing; formal read 11-19);
  forward_other 72 markets $636 vs -$67 / -$293 (N35 failing). COPY-1 74.7 h: sharp 43 primaries settled / 31 events +2.4 pts (-$42: four
  < 0.20 long shots -$84), control 45 / 21 +4.3. N58 launch tracker (16:52): 6 open (3 first, 3 retry), 0 settled, open_past_end 0.
- Infra note: the report had no 'late' arm because follow.yml run #22 started 11:41, before the c30 commit (13:08), and ran on the old code
  to 16:53 (lesson 10; the c30 '13:30 hand-over' estimate was wrong). Run #23 (16:53, head 48318461) carries the late arm. No fix needed.
- Test (adjacent N70, culture_highno.py, local, 12-week tape, rules fixed before looking): culture launch-hour NO at 0.90-0.98, follower
  >= 300 s: -0.5 pts [-2.1, +1.0] on 374 events, halves -1.0 / +0.0 -> DEAD; control band 0.05-0.90 reproduces +8.7 [6.4, 11.1] (540 events).
  The tracker's 0.90 cap stays.
- New (outside the box N71, collectible_ou.py): Pokemon price Over/Under markets: 'Under' +22.6 pts on 21 markets but only 2 end dates
  -> DEAD by count (2 independent bets); revive if the monthly series returns.
- Health: fast paper 16:28, slow 16:34, follow 16:53 (report 16:53, chain #23 running), boosts 16:05, MM v2 16:31, books 17:00 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders. (Local main had diverged again - reset.)
- Next: first 'late' arm positions (run #23); N58 first settlements; lock_x week mark 11-19; LP-1 5-day + forward_core read 11-19; options
  N42 11-19; N21 11-21; N63 calendars; N61 history; N67 history; N45 11-30.

## 11-17 21:00-21:35 UTC cycle 32 (scheduled)
- Read-outs (fast trades.jsonl, last settled 20:25): lock_x 32 trades / 28 end-times +6.4% (unchanged; needs 30 end-times, week mark 11-19),
  lock_x50 +9.5%, lock_p_majors 26 / 24 +5.2%; lock_m 265 -2.7%, lock_b 97 +0.5%, lock_p_z2 320 -1.2%. N21 forward BTC/ETH 115 windows / 105
  won -3.2% (4 days, below +2%; read 11-21), alts 118 / 103 -5.1%. Slow (20:30-20:34): converge 14 / 13 -$10, 82 open mark -$37; young 62 / 28
  -$182 (57 open); options 85 settled +$178, 48 open, N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3 (4 events, unchanged); box office
  9 / 8 -$0.96; charts 2 / 2 +$3.35, 1 open; mention 2 / 1 -$8.74, 3 open. LP-1 v2 93 runs / 3.44 d: formula $1,844 (upper bound), trading
  -$490, pessimistic -$756; 83 settled, 68 open leftovers (guard OK), 4 quoted; forward_core 55 markets $320 vs +$38 / -$11 (-3% of formula,
  passing; formal read 11-19); forward_other 76 markets $667 vs -$69 / -$289 (N35 failing). COPY-1 78.6 h: sharp 56 primaries settled /
  37 events +4.2 pts (+3.5 at 5 min later; n far below the 300 / 100 bar), control 57 / 26 +0.7. N58 launch tracker (20:54, end of run #23):
  6 open (3 first, 3 retry), 0 settled, open_past_end 0; the late arm looked at 20 markets in its first 4 h, 0 bought (16 ask outside
  0.05-0.90, 4 spread > 10c) - not a bug (it saw candidates), just a tight band.
- Test (adjacent N72, culture_endno.py, local, 12-week tape, rules fixed before looking): culture ex-mention NO 1-48 h before the end,
  follower >= 300 s: -0.2 pts [-1.7, +1.4] on 289 events, halves +0.4 / -0.8, YES placebo -0.7 -> DEAD. The fan YES premium is a launch-time
  effect only; the late end of the market is calibrated.
- New (outside the box N73): esports pre-match winners vs sharp esports lines -> READY (one Actions snapshot decides if there is volume).
- Health: fast paper 20:30, slow 20:34, follow 20:54 (< 70 min; run #24 took over), boosts 20:31, MM v2 21:01, books 21:00, rewards 20:48 -
  OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: lock_x week mark 11-19 (needs 30 end-times and >= +5%); LP-1 5-day + forward_core read 11-19; options N42 11-19; N58 first
  settlements (positions from 11-17 01 UTC end >= 11-18); N21 11-21; N73 snapshot; N63 calendars; N61 history; N67 history; N45 11-30.

## 11-18 01:05-01:30 UTC cycle 33 (scheduled)
- Read-outs (fast trades.jsonl, last settled 00:28): lock_x 32 trades / 28 end-times +6.4% (unchanged for a day; needs 30 end-times, week
  mark 11-19), lock_x50 +9.5%, lock_p_majors 26 / 24 +5.2%; lock_m 268 -2.8%, lock_b 99 +0.2%, lock_p_z2 328 -1.1%. N21 forward BTC/ETH
  118 windows / 107 won -3.4% (read 11-21), alts 123 / 108 -4.7%. Slow (00:32-00:35): converge 14 / 13 -$10, 82 open mark -$43; young
  69 / 34 -$163 (53 open); options 85 settled +$178, 48 open, N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3 (unchanged); box office
  9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 2 / 1 -$8.74, 7 open. LP-1 v2 98 runs / 3.6 d: formula $1,889 (upper bound), trading -$477,
  pessimistic -$702; 88 settled, 68 open leftovers (guard OK), 4 quoted; forward_core 60 markets $345 vs +$42 / +$9 (passing; formal read
  11-19); forward_other 82 markets $711 vs -$71 / -$252 (N35 failing). COPY-1 81.7 h: sharp 59 primaries settled / 40 events +5.4 pts
  (+4.8 at 5 min later; bar is 300 / 100), control 62 / 29 +2.3. N58 launch tracker (00:06): 6 open (3 first, 3 retry), 0 settled,
  open_past_end 0.
- Test (adjacent N74, culture_clock.py, local, exact N60 F300 rows, rules fixed before looking): culture launch-hour NO by listing clock:
  US day +9.5 pts [6.5, 12.5] (348 events), US night +8.6 (132), weekend +4.8 (138); off-hours minus day -3.2 (halves -2.0 / -4.1) ->
  'nobody awake' mechanism DEAD; the edge is fans buying YES while the US is awake. No tracker change.
- New (outside the box N75, views_buckets.py): YouTube view-count bucket ladders (MrBeast / GTA VI, 624 markets): FAV -4.1 pts
  [-9.1, +1.3], FADE -0.3 [-2.1, +1.5], ~40 video-date units -> DEAD (live public count is priced, lesson 26).
- Health: fast paper 00:31, slow 00:35, boosts 00:57, books 01:00, live snapshot 01:05, MM v2 23:31. follow.yml run #25 in progress since
  22:06 (last publish 00:06, report 'updated' 23:58 = 74 min at 01:12: slightly past the 70-min mark but the run is alive; not
  re-dispatched to avoid two chains). Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. Pilot STOP, no orders.
- Next: lock_x week mark 11-19 (needs 30 end-times and >= +5%); LP-1 5-day + forward_core read 11-19; options N42 11-19; N58 first
  settlements; check follow chain hand-over (#25 -> #26); N21 11-21; N73 esports snapshot; N63 calendars; N61 history; N67; N45 11-30.

## 11-18 05:00-05:35 UTC cycle 34 (scheduled)
- Read-outs (fast trades.jsonl, last settled 04:30): lock_x 34 trades / 30 end-times 31 won +6.4% (7 days; the 30-end-time bar is reached,
  formal week read 11-19 needs >= +5%), lock_x50 +9.2%, lock_p_majors 28 / 28 +5.3%; lock_m 280 -2.9%, lock_b 106 -0.6%, lock_p_z2 338
  -1.6%. N21 forward BTC/ETH 126 windows / 114 won -3.6% (5 days, below +2%; read 11-21), alts 133 / 116 -5.2%. Slow (04:36-04:37):
  converge 14 / 13 -$10, 84 open mark -$42; young 70 / 35 -$158 (56 open); options N42 forward tails 2 / 0 -9.8 pts, rest 7 / 6 +12.3
  (4 events, unchanged), 48 open; box office 9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 4 / 3 -$6.41, 6 open. LP-1 v2 102 runs / 3.77 d:
  formula $1,917 (upper bound), trading -$441, pessimistic -$681; 91 settled, 66 open leftovers (guard OK), 3 quoted; forward_core 62
  markets $373 vs +$59 / +$46 (passing; formal read 11-19); forward_other 85 markets $740 vs -$41 / -$240 (N35 failing). COPY-1 85.9 h:
  sharp 67 primaries settled / 44 events +5.4 pts (+4.6 at 5 min later; bar 300 / 100), control 62 / 29 +2.3. N58 launch tracker (04:17):
  7 open (3 first, 4 retry), 0 settled, open_past_end 0; 150 'ask outside' skips are all empty seed books (bid 0.01 / ask 0.99).
- Test (adjacent N76, culture_capacity.py, local, 12-week tape, rules fixed before looking): how much money culture launch-hour NO holds.
  11% of 7,825 markets had a NO taker 5-60 min after listing; single-price NO cost per market median $8 / p75 $23 / p90 $57; real takers'
  dollar edge $48/day total, share-weighted +2.3 pts [-5.6, +10.2] (393 events) vs ~+8 per market at one $10 fill -> SMALL-TICKET: N58
  can only ever be $10-20 per market (tens of dollars a day). No tracker change.
- New (outside the box N77): holding-reward carry (266 markets with the 4%/yr reward, median 2 y): two-sided carry = cash yield; long-shot
  NO adds +0.8%/yr median for 2028 tails on 20 events -> DEAD by arithmetic.
- Health: fast paper 04:33, slow 04:39, follow 04:19 (report 04:09, run started 03:18 in progress - chain hand-over #25 -> #26 worked),
  boosts 04:13 (in progress), MM v2 05:02, books 05:00, live snapshot 04:04 - OK. Tracebacks only the old pilot-log (2) / script-log (1);
  no MemoryErrors. No orders.
- Next: lock_x week read 11-19 (30 end-times reached, needs >= +5%); LP-1 5-day + forward_core read 11-19; options N42 11-19; N58 first
  settlements; N21 11-21; N73 esports snapshot; N63 calendars; N61 history; N67; N45 11-30.

## 11-18 09:02-09:35 UTC cycle 35 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 08:29): lock_x 35 trades / 31 end-times 32 won +6.3% (7 days; formal week read 11-19
  needs >= +5%), lock_x50 +9.0%, lock_p_majors 28 / 26 end-times +5.3%; lock_m 287 -2.7%, lock_b 113 -0.3%, lock_p_z2 344 -1.4%. N21 forward
  BTC/ETH 129 windows / 117 won -3.4% (5 days, below +2%; read 11-21), alts 139 / 121 -5.6%. Slow (08:34-08:36): converge 14 / 13 -$10,
  84 open mark -$41; young 71 / 36 -$152 (55 open); options N42 forward tails 4 / 0 -7.9 pts (3 events), rest 12 / 10 +13.1 (6 events);
  box office 9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 4 / 3 -$6.41, 6 open. LP-1 v2 106 runs / 3.94 d: formula $1,933 (upper bound),
  trading -$442, pessimistic -$678; 93 settled, 65 open leftovers (guard OK), 6 quoted; forward_core 66 markets $374 vs +$63 / +$43
  (passing; formal read 11-19); forward_other 91 markets $756 vs -$44 / -$249 (N35 failing). COPY-1 90.3 h: sharp 68 primaries settled /
  45 events +4.1 pts (+3.3 at 5 min later; bar 300 / 100), control 67 / 31 +2.3. N58 launch tracker (08:29): 7 open (3 first, 4 retry),
  0 settled, open_past_end 0.
- Test (adjacent N78, culture_series.py, local, exact N60 F300 rows listed >= 7 d after tape start, rules fixed before looking): culture
  launch-hour NO by series kind: one-off events +11.1 pts [7.7, 15.0] (249 events), recurring series +4.1 [1.2, 7.2] (243), first copy of
  a series +8.6 (55); one-off - recurring +6.3 / +7.3 in the halves, recurring newer half +1.9 [-1.7, +6.0]. Rule needed recurring <= +1
  -> UNCLEAR, no tracker change. Diagnostic (after looking): recurring ex-mention +1.7 [-1.2, +4.5] on 182 events (tweet counts +3.1,
  MrBeast views +0.4, Netflix/box office -4.1) while recurring mention stays +11.2 -> the fan premium is weakest where a public count or
  last week's copy anchors the price (lessons 13 / 26). Launch positions carry 'ev', so the forward book can be split the same way.
- New (outside the box N79, ai_release_ladders.py): AI model release-date ladders (27 events, 203 markets with fills): NO side +0.7 pts
  [-6.8, +7.4] on 20 model lines, halves -7.5 / +8.8; YES mirror -1.9 -> DEAD (count < 30 lines, sign flip).
- Health: fast paper 08:34, slow 08:39, follow 08:31 (report 08:31, < 70 min), boosts 08:38, MM v2 09:01, books 09:00, live snapshot 09:06 -
  OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP file in place, no orders.
- Next: 11-19 reads: lock_x week (31 end-times, needs >= +5%), LP-1 5-day + forward_core, options N42; N58 first settlements (split by
  series kind); N21 11-21; N73 esports snapshot; N63 calendars; N61 history; N67; N45 11-30.

## 11-18 13:01-13:40 UTC cycle 36 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 12:29): lock_x 36 trades / 32 end-times 33 won +6.5% (7 days; formal week read 11-19
  needs >= +5%), lock_x50 +9.1%, lock_p_majors 28 / 26 end-times +5.3%; lock_m 296 -2.4%, lock_b 118 -0.1%, lock_p_z2 354 -1.6%. N21 forward
  BTC/ETH 133 windows / 120 won -3.9% (below +2%; read 11-21), alts 151 / 132 -5.2%. Slow (12:36-12:37): converge 15 / 14 -$9.64, 83 open
  mark -$40; young 71 / 36 -$152 (56 open); options N42 forward rest 12 / 10 +13.1 pts (6 events), 48 open; box office 9 / 8 -$0.96;
  charts 3 / 3 +$3.64; mention 4 / 3 -$6.41, 6 open. LP-1 v2 110 runs / 4.11 d: formula $1,957 (upper bound), trading -$429, pessimistic
  -$668; 95 settled, 66 open leftovers (guard OK), 6 quoted; forward_core 71 markets $390 vs +$47 / +$37 (passing; formal read 11-19);
  forward_other 96 markets $780 vs -$44 / -$244 (N35 failing). COPY-1 94.2 h: sharp 69 primaries settled / 46 events +3.1 pts (+2.3 at 5
  min later; bar 300 / 100), control 67 / 31 +2.3. N58 launch tracker (12:30): 7 open (3 first, 4 retry), 0 settled, open_past_end 0.
- Sports vs Pinnacle (TESTING since 11-11, read-out date 11-18): 882 pairs / 113 games / 19 snapshots, fair - ask p99 +1.6c, max +2.8c,
  1 pair >= 2c, 0 paper positions in a week -> DEAD (main-line books track Pinnacle within a cent).
- Test (adjacent N80, copy_gap.py, local, 12-week tape a + c, walk-forward 'good' wallets, follower >= 300 s, rules fixed before looking):
  copy only when the follower's price is <= the wallet's + 1c: +0.33 pts [-0.1, +0.8] (1,077 events), halves +0.4 / +0.3; COPY-1's own
  <= 3c cap +0.51 [+0.1, +1.0]; placebo wallets -1.0 -> DEAD. Picking wallets beats random by ~1.3 pts, but the follower keeps ~0-0.5,
  below COPY-1's +1.5 bar: expect its paper +3.1 to regress.
- New (outside the box N81, READY, needs Actions): weekend equity up/down markets vs 24/7 equity perps (Hyperliquid HIP-3).
- Health: fast paper 12:35, slow 12:40, follow 12:31 (report 12:27, < 70 min), boosts 11:57, books 13:00, live snapshot 12:05 - OK.
  NEW: external-log 3 Tracebacks = one open-meteo read timeout in research/external/weather.py that killed the remaining cities (job
  still committed 12:18) -> fixed (catch RequestException per city, retry, skip). Old pilot-log (2) / script-log (1). No MemoryErrors.
  charts_paper chart_events_seen = 0 in all 6 runs today: the 09:03 active-market snapshot also has no chart market ending within days
  (13 chart-like markets, all year-end) -> consistent with the weekly series being absent, not yet proven (lesson 10; recheck when a
  Netflix / Spotify weekly event lists). STOP file in place, no orders. This run had no network to Polymarket and no Actions dispatch.
- Next: 11-19 reads: lock_x week (32 end-times, needs >= +5%), LP-1 5-day + forward_core, options N42; N58 first settlements (split by
  series kind); N21 11-21; N73 esports snapshot (reuse sharp_compare); N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-18 17:05-17:45 UTC cycle 37 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 16:34): lock_x 37 trades / 33 end-times 34 won +6.4% (formal week read 11-19 needs
  >= +5%), lock_x50 +8.9%, lock_p_majors 29 / 27 end-times +5.3%; lock_m 299 -2.4%, lock_b 120 0.0%, lock_p_z2 360 -1.9%. N21 forward
  BTC/ETH 138 windows / 125 won -3.5% (below +2%; read 11-21), alts 159 / 138 -6.3%. Slow (16:37-16:38): converge 16 / 15 -$9.55, 84 open
  mark -$35; young 71 / 36 -$152 (57 open); options N42 forward rest 12 / 10 +13.1 pts (6 events), 53 open (13 tails); box office 9 / 8
  -$0.96; charts 3 / 3 +$3.64; mention 5 / 4 -$4.62 (4 events), 5 open. LP-1 v2 115 runs / 4.27 d: formula $1,966 (upper bound), trading
  -$429, pessimistic -$690; 95 settled, 71 open leftovers (guard OK), 3 quoted; forward_core 74 markets $399 vs +$37 / +$15 (passing;
  formal read 11-19); forward_other 99 markets $788 vs -$45 / -$265 (N35 failing). COPY-1 98.4 h: sharp 71 primaries settled / 48 events
  +3.4 pts (+2.6 at 5 min later; bar 300 / 100), control 69 / 33 +2.4. N58 launch tracker (16:42): 26 open (3 first, 22 retry, 1 late),
  0 settled, open_past_end 0 - 19 new positions 15:20-16:00, 18 of 26 in five 'streamer finishes GTA VI by <date>' ladders (one theme,
  lesson 6: ~9 events in the book, read it by event).
- Test (adjacent N82, culture_ladder.py, local, exact N60 F300 rows, rules fixed before looking): launch-hour NO on deadline ladders
  +3.9 pts [-10.9, +20.0] on 14 events / 58 markets (4% of rows), earliest rung +2.0, later +4.5; non-deadline +8.4 [6.1, 10.7] (529
  events) -> UNCLEAR, no cap (too few ladders on the tape to decide).
- New (outside the box N83, quake_gr.py): earthquake ladders / counts vs the Gutenberg-Richter prior: 32 pre-period entries, rule 3 fills
  -10.7 pts, Brier market .115 vs GR .107; after the day ends the winner trades at 0.96-0.999 -> DEAD (lesson 26).
- Health: fast paper 16:37, slow 16:41, follow 16:44 (report 16:37, < 70 min), boosts 16:22, MM v2 16:02, books 17:00, live snapshot
  16:05 - OK. Tracebacks only the old pilot-log (2) / script-log (1); external-log clean after the c36 fix; no MemoryErrors. STOP in
  place, no orders. No network to Polymarket / USGS from this run.
- Next: 11-19 reads: lock_x week (33 end-times, needs >= +5%), LP-1 5-day + forward_core, options N42; N58 first settlements (by event
  and series kind); N21 11-21; N73 esports snapshot; N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-18 21:05-21:40 UTC cycle 38 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 20:34): lock_x 37 trades / 33 end-times 34 won +6.4% (no new signal since c37; formal
  week read 11-19 needs >= +5%), lock_x50 +8.9%, lock_p_majors 29 / 27 end-times +5.3%; lock_m 302 -2.3%, lock_b 121 +0.1%, lock_p_z2 365
  -1.8%. N21 forward BTC/ETH 141 windows / 128 won -3.4% (below +2%; read 11-21), alts 166 / 145 -5.9%. Slow (20:39-20:41): converge 16 / 15
  -$9.55, 86 open mark -$33; young 75 / 40 -$126 (62 open); options N42 forward tails 4 / 0 -7.9 pts (3 events), rest 12 / 10 +13.1 (6
  events), 47 open; box office 9 / 8 -$0.96; charts 3 / 3 +$3.64 (chart_events_seen still 0); mention 5 / 4 -$4.62, 14 open. LP-1 v2 119
  runs / 4.44 d: formula $1,985 (upper bound), trading -$433, pessimistic -$684; 96 settled, 73 open leftovers (guard OK), 2 quoted;
  forward_core 76 markets $418 vs +$49 / +$21 (passing; formal read 11-19); forward_other 101 markets $808 vs -$33 / -$259 (N35 failing).
  COPY-1 102.6 h: sharp 74 primaries settled / 50 events +3.2 pts (+2.4 at 5 min later; bar 300 / 100), control 76 / 37 +4.0. N58 launch
  tracker (20:54): 28 open (3 first, 24 retry, 1 late), 0 settled, open_past_end 0.
- Test (adjacent N84, copy_horizon.py, local, 12-week tape a + c, walk-forward good wallets, follower >= 300 s, 3c cap, rules fixed before
  looking): by horizon at entry: < 24 h -0.1 pts [-1.5, +1.2] (379 events), 1-7 d +0.2 (667), 7-60 d +1.0 [+0.3, +1.7] (730), 24 h-60 d
  +0.57 [+0.1, +1.0] (996 events, halves +0.7 / +0.4), placebo others -1.0 -> UNCLEAR by the rule (> +0.5, < +1.5), no COPY-1 arm. The
  paper's 'ends 1-7 d +17 pts' is noise; the follower's ceiling stays ~+0.5..+1.
- New (outside the box N85, READY, needs Actions): on-chain rule clarifications (UMA adapter bulletin-board updates) vs the book's reaction.
- Health: fast paper 20:39, slow 20:44, follow 20:56 (report 20:49, < 70 min), boosts 20:43, MM v2 20:01, books 21:00, live snapshot
  20:47 - OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders.
- Next: 11-19 reads: lock_x week (33 end-times, needs >= +5%), LP-1 5-day + forward_core, options N42; N58 first settlements (by event
  and series kind); N21 11-21; N73 esports snapshot; N85 / N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-19 01:00-01:40 UTC cycle 39 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 00:33; slow 00:41-00:45). lock_x WEEK READ (lock_x_week.py): 39 trades / 35 end-times /
  8 days, 36 won, +6.5%/$ (+$44) - meets the +5% letter, but 3 fills at 0.52-0.69 made $37 of it; the 36 fills >= 0.80 are +1.2%/$
  (-2.3 pts/share [-12.3, +5.9]); total +0.7 pts [-9.7, +8.6] by end-time; halves +8.8% / +4.4%. BTC/ETH 19/19 +10.1% (>= 0.80: 17/17
  +5.5%) is a post-hoc split and N21's wider BTC/ETH forward is -2.6% (150 windows / 6 days) -> NOT proposable; keep running, new
  pre-registered forward arm 'lock_x BTC/ETH >= 0.80 from 11-19 01:00', read at 30 end-times (>= +3%/$). lock_x50 +8.8%, lock_p_majors
  30 / 28 +5.5%; lock_m 311 -1.9%, lock_b 128 +0.6%, lock_p_z2 376 -1.4%. N21 forward alts 172 / 151 -5.4% (decision 11-21).
  LP-1 v2 124 runs / 4.61 d: formula $1,989 (upper bound), trading -$424, pessimistic -$650; 99 settled, 72 open leftovers (guard OK), 3
  quoted. 5-day reads: N38 forward_core 79 markets $422 vs +$42 / +$26 -> PASSES (still needs Yoav's OK for the read-only reward-history
  query before anything else); N35 forward_other 104 markets $811 vs -$28 / -$222 (-27%) -> DEAD. Options N42 forward rest 12 / 10 +13.1
  pts on 6 coin-dates (needs 8+), tails 4 / 0 -7.9, 49 open -> next read 11-26. converge 16 / 15 -$9.55 (86 open, mark -$43); young 81 / 44
  -$123; box office 9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 9 / 7 -$7.50 (5 events). COPY-1 105.9 h: sharp 76 primaries settled / 52
  events +3.2 pts (+2.4 at 5 min; bar 300 / 100), control 77 / 38 +4.1. N58 launch tracker: 39 open (3 first, 35 retry, 1 late), 0
  settled, open_past_end 0.
- Test (adjacent N86, culture_maker.py, local, tape group a, rules fixed before looking): launch-hour NO as the MAKER the fans' YES hits:
  +1.55 pts [-1.9, +4.9] on 426 events vs the taker +8.2 [5.9, 10.6] (548); same 424 markets maker +8.1 vs taker +9.2 (halves -2.3 /
  +0.1); placebo -9.7; capacity median 1 wallet / ~$17 -> DEAD (lesson 29: resting fills land where YES is right).
- New (outside the box N87): hurricane / tropical-storm markets vs NHC outlooks -> DEAD by count (39 markets / ~30 questions in 5 seasons,
  no price history). Steam / Twitch count markets: 3 events on the tape - too few.
- Health: fast paper 00:40, slow 00:45, follow 00:08 (< 70 min at 01:00), boosts 00:05, MM v2 00:31, books 00:45, live snapshot 00:07 -
  OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No network to Polymarket from
  this run (proxy refuses gamma / clob).
- Next: N21 decision 11-21; lock_x BTC/ETH forward arm (30 end-times); N58 first settlements (by event and series kind); N42 11-26;
  COPY-1 to 300 / 100; N85 / N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-19 05:00-05:40 UTC cycle 40 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 04:38; slow 04:42-04:44): lock_x 41 trades / 37 end-times 38 won +6.4%/$ (>= 0.80 core
  38 / 35 +1.3%/$, -1.8 pts/share [-11.5, +5.7]; the cheap 3 fills still carry it); new forward arm BTC/ETH >= 0.80 since 01:00: 1 / 1
  won (needs 30 end-times). lock_x50 +8.7%, lock_p_majors 31 / 29 +5.4%; lock_m 318 -1.8%, lock_b 133 +0.7%, lock_p_z2 380 -1.3%. N21
  forward BTC/ETH 152 windows / 139 won -2.5%, alts 179 / 157 -5.9% (decision 11-21). LP-1 v2 128 runs / 4.78 d: formula $1,999 (upper
  bound), trading -$426, pessimistic -$664; 101 settled, 71 open leftovers (guard OK), 2 quoted; forward_core 81 markets $432 vs +$40 /
  +$29 (passed c39; waits for Yoav's OK on the read-only reward-history query). Options N42 forward rest 12 / 10 +13.1 pts (6 coin-dates),
  54 open (11 tails) -> 11-26. converge 19 / 18 -$6.60 (84 open, mark -$34); young 81 / 44 -$123 (56 open); box office 9 / 8 -$0.96;
  charts 3 / 3 +$3.64 (chart_events_seen 0); mention 9 / 7 -$7.50, 15 open. COPY-1 109.8 h: sharp 79 primaries settled / 54 events +4.4
  pts (+3.6 at 5 min; bar 300 / 100), control 77 / 38 +4.1 (control ~ sharp -> no wallet skill visible yet). N58 launch tracker (04:06):
  39 open, 0 settled, open_past_end 0.
- Test (outside the box N89, wording_side.py, local, tape a ex-mention + c, mid-life entries, rules fixed before looking): negated /
  'stay-remain' questions are 1.2% of markets (66 / 33 events): YES -7.7 pts [-19.3, +6.1], NO +5.7 [-6.1, +17.0]; mid-life baseline YES
  -0.5, NO +0.5 -> DEAD (drama story wrong in sign, too rare). Caught a bug before reading: the tape's win bit is per direction.
- Test (adjacent N88, culture_width.py, exact N78 rows): 96% of launch-hour NO rows are in 5+ market events (wide +8.0 [5.6, 10.3],
  halves +10.1 / +5.9) -> no split possible, no tracker change.
- Health: fast paper 04:41, slow 04:45, follow 04:08 (report 04:03, ~60 min at 05:03), boosts 04:30, MM v2 04:01, books 04:45 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No network from this run (proxy
  refuses Polymarket / Kalshi / Deribit / Hyperliquid), so no Actions-dependent idea could be run.
- Next: N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward arm (30 end-times); N58 first settlements (by event; one-off vs recurring);
  N42 11-26; COPY-1 to 300 / 100 (watch sharp - control); N85 / N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-19 09:02-09:45 UTC cycle 41 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 08:39; slow 08:43-08:45): lock_x 44 trades / 39 end-times 41 won +6.3%/$ (>= 0.80 core
  41 / 37 +1.6%/$, -1.3 pts/share [-10.2, +5.9]; the 3 cheap fills still carry it); BTC/ETH >= 0.80 forward arm since 01:00: 4 trades / 3
  end-times, all won, +$3.96 (needs 30). lock_x50 +8.4%, lock_p_majors 34 / 31 +5.4%; lock_m 327 -2.0%, lock_b 138 +0.8%, lock_p_z2 388
  -1.4%. N21 forward BTC/ETH 162 windows / 148 won -2.7%, alts 185 / 162 -5.8% (decision 11-21). LP-1 v2 132 runs / 4.94 d: formula
  $2,019 (upper bound), trading -$424, pessimistic -$698; 102 settled, 71 open leftovers (guard OK), 3 quoted; forward_core 82 markets $452
  vs +$34 / +$5 (passed c39; waits for Yoav's OK on the read-only reward-history query). Options N42 (options_tail_readout.py): forward rest
  20 / 16 won +10.3 pts on 8 coin-dates (6 positive) -> reached the 8-coin-date line, survives its kill rule; forward tails 5 / 0 -7.7 (4);
  48 open -> next read 11-26 (lesson 6: still ~8 direction bets). converge 22 / 21 -$3.33 (81 open, mark -$39); young 81 / 44 -$123 (56
  open); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64 (chart_events_seen 0); mention 9 / 7 -$7.50, 15 open. COPY-1 114 h: sharp 81
  primaries settled / 55 events +4.0 pts (+3.2 at 5 min; bar 300 / 100), control 80 / 40 +4.4 (control >= sharp: no wallet skill yet).
  N58 launch tracker (08:20): 39 open, 0 settled, open_past_end 0, no new first-look candidate since 11-18 22:04 (11 h); the tracker's own
  history has a 14-h gap on 11-18 01-15 too (launches come in batches) -> not yet a bug; recheck at c42 (lesson 10: > 24 h = bug).
- Test (outside the box N91, twin_markets.py, local, tape a + c): same question in two events, ends within 24 h: ~7 genuine twin questions
  with overlapping prints in 12 weeks -> DEAD by count (lesson 8).
- Test (adjacent N90, relist_no.py, local, tape a + c, rules fixed before looking): 'another X by <date>' relists, launch-day NO -14.0 pts
  [-28.3, -1.6] on 39 events vs +3.6 for all other launch-day NO -> DEAD (wrong sign). YES mirror +12.4 [-3.6, +29.1] is one half only.
- Health: fast paper 08:43, slow 08:46, follow 08:21 (report 08:15, < 70 min), boosts 08:55, MM v2 08:31, books 09:00, live snapshot 08:05
  - OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No network to Polymarket from
  this run (proxy refuses gamma).
- Next: N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward arm (30 end-times); N58 candidate gap recheck + first settlements; N42 11-26;
  COPY-1 to 300 / 100; N85 / N81 / N63 / N61 / N67 need Actions; N45 11-30.

## 11-19 13:00-13:40 UTC cycle 42 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 12:38; slow 12:45-12:47): lock_x 45 trades / 40 end-times 41 won +5.1%/$ (-0.1 pts/share
  [-9.8, +7.0]); a cheap ETH fill at 0.58 lost at 12:24, >= 0.80 core 41 / 37 +1.6%/$ (-1.3 pts [-10.2, +5.9]); BTC/ETH >= 0.80 all-time
  21 / 20 end-times all won +5.3 pts (post-hoc); the pre-registered forward arm since 01:00: 4 trades / 3 end-times all won +$3.96 (needs
  30). lock_x50 +7.8%, lock_p_majors 36 +4.5%; lock_m 333 -2.2%, lock_b 143 +1.0%, lock_p_z2 396 -1.6%. N21 forward BTC/ETH 168 windows /
  152 won -3.4%, alts 194 / 170 -5.4% (decision 11-21). LP-1 v2 136 runs / 5.11 d: formula $2,048 (upper bound), trading -$419,
  pessimistic -$701; 107 settled, 70 open leftovers (guard OK), 4 quoted; forward_core 82 markets $453 vs +$28 / +$6 (passed c39; waits
  for Yoav's OK on the read-only reward-history query). Options N42 forward rest 20 / 16 +10.3 pts (8 coin-dates), tails 5 / 0 -7.7, 51
  open -> 11-26. converge 23 / 22 -$2.14 (0.94-0.97: 19 / 19 +3.4%; 0.90-0.94 4 / 3 -18.8%), 81 open, mark -$40; young 82 / 44 -$133 (57
  open); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64 (chart_events_seen 0); mention 19 / 16 -$2.46 (6 events), 6 open. COPY-1 118 h:
  sharp 84 primaries settled / 57 events +2.9 pts (+2.1 at 5 min; bar 300 / 100), control 82 / 42 +4.4 -> control still >= sharp. N58
  launch tracker (12:32): 39 positions, first settlement 1 mention market lost (-$10.24); 38 open, open_past_end 0; no new candidate since
  11-18 22:04 (15 h, 797 listings 'not accepting orders' on watch) -> c43: if still none and the tape / listing shows culture launches, it
  is a bug (lesson 10).
- Test (adjacent N92, culture_bigyes.py, local, exact N78 rows + orders_a, rules fixed before looking): launch-hour NO where a YES taker
  order >= $200 came before the follower's fill: 12 markets / 10 events of 1,458 / 547 (0.8%), +13.6 pts [-11.2, +33.6]; the rest +8.2
  [5.8, 10.5]; NONE - BIG -6.7 / -2.7 by half -> DEAD (no filter; the launch hour is small tickets only, as N76 said). N58 rows by half:
  older +10.6, newer +5.7 [2.8, 8.9] - still positive, watch (lesson 24).
- New (outside the box N93): court-docket markets vs the public docket -> DEAD by count (125 legal-titled events since 2020 in the
  closed-event list, ~25 a year, mostly one-off headline cases; tape group c 7 markets / 6 events in 12 weeks).
- Health: fast paper 12:45, slow 12:50, follow 12:33 (report 12:26, < 70 min at 13:03), boosts 12:10, MM v2 12:31, perps 12:50, books
  13:00, live snapshot 11:04, external 12:10 - OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place,
  no orders. gh has no valid token in this run, so no Actions dispatch (N85 / N81 / N63 / N61 / N67 still wait).
- Next: N58 candidate-gap check (c43); N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward arm (30 end-times); N42 11-26; COPY-1 to
  300 / 100 (sharp vs control); N45 11-30.

## 11-19 17:02-17:40 UTC cycle 43 (scheduled)
- Read-outs (fast trades.jsonl unchanged since c42; slow 16:46-16:48): lock_x 45 trades / 40 end-times 41 won +5.1%/$ (-0.1 pts/share
  [-9.8, +7.0]); >= 0.80 core 41 / 37 +1.6%/$; BTC/ETH >= 0.80 all-time 21 / 20 end-times won +5.3 pts (post-hoc); forward arm since 01:00
  unchanged 4 trades / 3 end-times (needs 30). N21 forward BTC/ETH 169 windows / 153 won -3.3%, alts 203 / 179 -4.8% (decision 11-21).
  LP-1 v2 141 runs / 5.28 d: formula $2,086 (upper bound), trading -$414, pessimistic -$728; 108 settled, 70 open leftovers (guard OK), 5
  quoted; forward_core 83 markets $453 vs +$21 / +$3 (passed c39; waits for Yoav's OK on the read-only reward-history query). Options N42
  forward rest 20 / 16 +10.3 pts (8 coin-dates), tails 5 / 0 -7.7, 56 open -> 11-26. converge 24 / 23 -$1.74 (80 open, mark -$36); young
  83 / 44 -$143 (58 open); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 24 / 20 -$5.64 (7 events). COPY-1 122 h: sharp 94
  primaries settled / 60 events +2.4 pts (+1.1 at 5 min; bar 300 / 100), control 83 / 43 +4.8 -> control still >= sharp. N58 launch
  tracker: 43 positions, 3 settled (1 mention event, -3.7 pts), 40 open, open_past_end 0.
- N58 candidate-gap check (lesson 10): NOT a bug. Listings arrive at the base rate (58 first looks on 11-19 by 16:45, ~3.5 / h), but every
  first look meets the empty 0.01 / 0.99 seed book and is skipped 'ask outside'; the retry arm buys the first real book (4 today, 39 of 43
  positions). That is the tape test's design (follower at the first real fill), so the decision read is first + retry from now (fixed
  before any retry position settled).
- Test (outside the box N94, round_threshold.py, local, tape a + c ex-mention, rules fixed before looking): round thresholds (one
  significant digit) NO +8.7 pts [2.8, 13.5] on 169 events vs non-round +6.0 [1.6, 10.4] (175), halves +4.7 / +12.6 -> letter-PASS, but
  robustness kills the mechanism: ex-Rotten-Tomatoes round +2.3 [-3.2, 8.2] vs other +7.4; group c round +2.5 vs other +6.9; paired gap
  +7.1 [-4.7, 18.4] (53 events) -> DEAD as a mechanism; it is the RT ladders. Spawned N95 (RT score ladders NO +11.4 [2.7, 20.0], 36
  films, halves +3.3 / +19.4) -> READY.
- Test (adjacent N3, boxoffice_later.py, local, tape a): later-weekend box-office ladders 25 in 12 weeks; Saturday favourite +3.5 pts
  [-7.0, +10.0] on 15 events; drop-ratio chain 5 events -> DEAD by count.
- Health: fast paper 16:46, slow 16:52, follow 16:46 (report 16:37, < 70 min), boosts 16:37, MM v2 16:01, perps 12:50, books 17:00 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No network (proxy refuses
  Polymarket / Polygon RPC) and gh has no valid token -> no Actions dispatch (N85 / N81 / N63 / N61 / N67 still wait).
- Next: N95 split test (time-to-end, top rung, older half) on the tape; N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward arm (30
  end-times); N58 first + retry settlements; N42 11-26; COPY-1 to 300 / 100.

## 11-19 21:00-21:40 UTC cycle 44 (scheduled)
- Read-outs (fast trades.jsonl, last entry 20:48; slow 20:49): lock_x 45 trades / 40 end-times 41 won +5.1%/$ - no new lock_x signal since
  12:24 (lock_m / lock_b / lock_p_z2 still trading to 20:39, so the bot is up); BTC/ETH >= 0.80 forward arm still 4 / 3 end-times won (needs
  30). lock_x50 +7.8%, lock_p_majors 36 / 33 +4.5%; lock_m 339 -2.0%, lock_b 149 +1.2%, lock_p_z2 402 -1.5%. LP-1 v2 145 runs / 5.45 d:
  formula $2,109 (upper bound), trading -$448, pessimistic -$748; 109 settled, 74 open leftovers, 4 quoted. Options N42 forward rest 23 / 19
  won +13.6 pts on 8 coin-dates (6 positive), tails 5 / 0 -7.7, 50 open -> 11-26. converge 25 / 24 -$0.61 (79 open, mark -$42); young 93 /
  45 -$225 (+10 settled, 1 won: the 11-16 week's stock / ETF 'hit LOW' touches and 11-18 'close above' - one sell-off bet, lesson 6;
  decision at the 11-30 end dates); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64; mention 24 / 20 -$5.64 (7 events). COPY-1 126.7 h:
  sharp 99 primaries settled / 65 events +3.5 pts (+1.9 at 5 min; bar 300 / 100), control 91 / 47 +4.8 -> control still >= sharp. N58:
  61 positions, 4 settled (2 events) +0.3 pts, 57 open, open_past_end 0.
- Test (adjacent N95, rt_ladder.py, local, tape a - the only group with RT markets, rules fixed in c43): RT ladder NO +11.4 pts [2.8, 19.8]
  on 36 films, older half +3.3 (kill line +3 -> survives by 0.3), newer +19.4; pre-registered splits: 24-168 h before end +12.0 [2.0, 21.4]
  on 30 films, halves +7.5 / +16.2; middle rungs +14.3 [4.9, 23.5]; NO 0.30-0.60 +15.0 [3.8, 25.1]; top rung +3.7, bottom -4.3, > 7 d
  +10.8 (older -0.6). -> TESTING as a forward paper tracker on the time split only (rt_paper.py, hourly in spike_paper.yml, $10 at the
  real NO ask; rung and price logged, not filtered). Honest caveat: found by looking (lesson 22), ~3 films a week -> 15 films ~5 weeks.
  rt_paper.py ran offline here without crashing (no network); first real run is the next slow-paper hour - check rt_report.json
  rt_markets_seen > 0 at c45 (lesson 10).
- Test (outside the box N96, local_language.py, local, tape c politics, rules fixed before looking): big takers (>= $200) in markets about
  non-English-speaking countries, follower a300: -0.65 pts [-3.1, +1.8] on 74 events (halves -0.5 / -0.9) vs US +1.8 [0.6, 3.1] -> DEAD,
  wrong sign; no general mispricing there either (first entries YES -2.4, NO +0.7).
- Health: fast paper 20:48, slow 20:51, follow 20:58 (report 20:58), launch 20:56, boosts log to 19:20+, books 21:00 - OK. Tracebacks only
  the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No network (proxy refuses Polymarket) and gh has no
  valid token -> no Actions dispatch (N85 / N81 / N63 / N61 / N67 still wait).
- Next: c45 check rt_paper's first run (markets seen, positions); N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward arm (30 end-times);
  N58 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 01:00-01:40 UTC cycle 45 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 00:44; slow 00:50): lock_x 46 trades / 41 end-times 42 won +5.0%/$ (-0.04 pts/share
  [-9.1, +7.0]); >= 0.80 core 42 / 38 +1.7%/$; 11-19 day -$3.99 (an alt loss). BTC/ETH >= 0.80 forward arm since 11-19 01:00: 5 trades / 4
  end-times all won (needs 30). lock_x50 +7.7%, lock_p_majors 37 +4.5%; lock_m 342 -1.9%, lock_b 151 +1.3%, lock_p_z2 406 -1.4%. N21 forward
  BTC/ETH 174 windows / 158 won -3.0%, alts 216 / 191 -4.5% (decision 11-21). LP-1 v2 150 runs / 5.62 d: formula $2,125 (upper bound),
  trading -$443, pessimistic -$761; 116 settled, 72 open leftovers, 1 quoted; forward_core 90 markets $469 vs +$4 / -$5 (passed c39; waits
  for Yoav's OK on the read-only reward-history query). Options N42 forward rest 23 / 19 +13.6 pts (8 coin-dates), tails 5 / 0 -7.7, 54
  open -> 11-26. converge 25 / 24 -$0.61 (79 open, mark -$43); young 94 / 46 -$219 (95 open; 11-30); box office 9 / 8 -$0.96; charts 3 / 3
  +$3.64; mention 24 / 20 -$5.64 (3 open). N95 rt_paper first runs OK: 82 RT markets seen, 16 in window, 7 open, 0 settled, open_past_end 0.
  COPY-1 / N58 frozen at 20:58 (see Health): sharp 99 / 65 events +3.5 pts, control 91 / 47 +4.8; N58 61 positions, 4 settled.
- Test (adjacent N97, fan_ladder.py, local, tape a, rules fixed before looking): fan-count ladders ex-RT, NO upper rungs -3.9 pts [-19.7,
  +8.7] on 13 events -> DEAD. Lesson-10 check: box office / views events hold one 'at least' market each, so a kill-only post-hoc read
  (fan_ladder_single.py): single-threshold NO +0.8 [-5.6, +6.9] on 106 events, halves +7.8 / -6.0 -> the RT effect does not generalise.
- New (outside the box N98): conjunction questions -> DEAD by count (~2 genuine compound questions in 12 weeks on tapes a + c).
- Health: fast paper 00:49, slow 00:52, MM v2 01:02, boosts 00:23, books 01:00, live snapshot 00:05 - OK. Tracebacks only the old pilot-log
  (2) / script-log (1); no MemoryErrors. STOP in place, no orders. BROKEN: follow.yml run 38 (from 20:58) saved nothing for 4 h - its
  21:58 save hit 'local changes would be overwritten' mid-rebase (the tracker writes upd-*.jsonl while git rebases) and every later save
  failed on the leftover rebase-merge. Fixed save() (abort a stuck rebase first, --autostash, abort after a failed pull), pushed, cancelled
  run 38 and the old-code run 39; the Hand-over step re-dispatches on main with the fix. The 20:58-01:03 COPY-1 / N58 polls are lost (no
  orders involved). No network to Polymarket from this run.
- Next: c46 check follow report 'updated' moves hourly with the fixed save (lesson 10); N21 decision 11-21; lock_x BTC/ETH >= 0.80 forward
  arm (30 end-times); N95 first settlements; N58 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 05:00-05:30 UTC cycle 46 (scheduled)
- Read-outs (fast trades.jsonl, last entry 04:48; slow 04:52): lock_x 49 trades / 43 end-times 45 won +4.9%/$ (+0.14 pts/share [-8.6,
  +7.0]); >= 0.80 core 45 / 40 +1.8%/$; BTC/ETH >= 0.80 all-time 22 / 21 end-times all won +5.2 pts (post-hoc); forward arm since 11-19
  01:00 still 5 trades / 4 end-times all won (needs 30). Halves +8.8%/$ (<= 11-14) vs +2.6% (>= 11-15). lock_x50 +7.3%, lock_p_majors 38
  +4.4%; lock_m 350 -2.1%, lock_b 156 +0.8%, lock_p_z2 412 -1.4%. N21 forward BTC/ETH 175 windows / 159 won -3.0%, alts 224 / 197 -4.8%
  (decision 11-21 - heading for DEAD). LP-1 v2 155 runs / 5.78 d: formula $2,133 (upper bound), trading -$446, pessimistic -$741; 117
  settled, 72 open leftovers, 1 quoted. Options N42 forward rest 23 / 19 +13.6 pts (8 coin-dates, 6 positive), tails 5 / 0, 57 open ->
  11-26. converge 25 / 24 -$0.61 (81 open, mark -$43); young 94 / 46 -$219 (97 open; 11-30); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64;
  mention 24 / 20 -$5.64 (4 open). N95 rt_paper 82 seen, 11 in window, 8 open, 0 settled, open_past_end 0. COPY-1 129.6 h: sharp 101
  primaries / 67 events +3.5 pts (+1.9 at 5 min), control 99 / 51 +3.75 (+4.4 at 5 min) -> control still >= sharp. N58 86 positions, 4
  settled, 82 open, open_past_end 0. No row crossed a kill or promote line this cycle.
- Follow chain (c45 fix) CONFIRMED: Follow paper commits 02:05, 03:05, 04:05, 05:05 - hourly saves work again.
- Test (outside the box N100, flip_leg.py, local, tapes a ex-mention + b + c, rules fixed before looking): follow a wallet's flip leg (first
  trade the other way within 7 d) at a300: -1.2 pts [-1.5, -0.8] on 3,139 events, halves -1.2 / -1.2 -> DEAD (too small to fade after the
  spread, wrong sign to follow). Post-hoc kill-only: big flips (>= $200) +3.5 [2.6, 4.4] on 1,883 events vs big never-flipped entries +2.3
  [1.6, 2.9] -> a big flip is a big taker + ~1 pt, the price band carries it; no new arm (it backs COPY-1's control arm).
- Test (adjacent N99, count_bracket_upper.py, local, tapes a + c, rules fixed before looking): NO on post-count brackets above the leading
  bracket, 0.60-0.90, 6-120 h: -2.9 pts [-6.5, +0.7] on 83 events, halves -2.7 / -3.1; placebo below +2.3 -> DEAD, wrong sign.
- Health: fast paper 04:51, slow 04:53, follow 05:05 (report 03:59 -> 05:05 commit), boosts 04:48, MM v2 05:01, books 05:00 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders.
- Next: N21 decision 11-21 (forward -3.0% / -4.8% -> expect DEAD); lock_x BTC/ETH >= 0.80 forward arm (30 end-times); N95 first
  settlements; N58 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 09:00-09:40 UTC cycle 47 (scheduled)
- Read-outs (fast trades.jsonl, last entry 08:49; slow 08:53-08:54): lock_x 63 trades / 48 end-times 59 won +9.2%/$ (+4.3 pts/share [-3.6,
  +10.5]) - up from 49 / 43 because of ONE move: 11-20 06:04-06:14 13 trades on 7 coins all won (+$60 of the day's +$61, lesson 6). Split by
  breadth (N101): 3+ assets in a window 3 end-times +16.2 pts; 1-2 assets 45 end-times +0.15 pts [-8.3, +7.5] -> honest lock_x number is ~0.
  >= 0.80 core 53 / 44 +3.3%/$ (+0.9 pts [-6.5, +6.5]). BTC/ETH >= 0.80 forward arm since 11-19 01:00: 7 trades / 6 end-times all won (needs
  30). lock_x50 +9.8%, lock_p_majors 45 +8.1%; lock_m 370 -0.8%, lock_b 177 +3.1%, lock_p_z2 438 -0.3% (all lifted by the same move). N21
  forward BTC/ETH 183 windows / 167 won -2.0%, alts 244 / 216 -3.2% (decision 11-21, still negative). LP-1 v2 159 runs / 5.95 d: formula
  $2,147 (upper bound), trading -$437, pessimistic -$744; 118 settled, 73 open leftovers, 2 quoted. Options N42 forward rest 28 / 22 won
  +11.0 pts on 10 coin-dates (7 positive), tails 7 / 0 -7.8, 57 open -> 11-26. converge 29 / 28 +$3.68 (0.94-0.97 24 / 24 +3.6%, 0.90-0.94
  5 / 4 -13.4%; 77 open, mark -$33); young 95 / 46 -$229 (96 open; 11-30); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64 (1 open); mention 24
  / 20 -$5.64 (4 open). N95 rt_paper 82 seen, 8 open, 0 settled, open_past_end 0. COPY-1 133.7 h: sharp 103 primaries / 69 events +3.8 pts
  (+2.2 at 5 min; bar 300 / 100), control 104 / 52 +3.9 (+4.5 at 5 min) -> control still >= sharp. N58 86 positions, 4 settled (+0.3 pts),
  82 open, open_past_end 0. No row crossed a kill or promote line.
- Test (outside the box N102, date_ladder_hazard.py, local, tapes a + b + c, rules fixed before looking): NO on a near date-ladder rung
  priced >= 5c above the far rung's constant-hazard fair: -9.4 pts [-18.9, +0.2] on 68 events (halves -0.1 / -19.2); base arm -13.1
  [-21.7, -5.6] on 81 events -> DEAD, wrong sign (near-rung NO loses in its last 2 weeks; the newer half is election 'concede by' ladders).
- Test (adjacent N101, lock_x breadth split, see read-outs) -> no arm by count (3 broad end-times); recorded as the lock_x caveat.
- Health: fast paper 08:52, slow 08:55, follow 08:17 (report 08:09, < 70 min at 09:00), boosts 08:09, MM v2 08:31, replay 08:00, books
  09:00, live snapshot 04:04 - OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders.
- Next: N21 decision 11-21 (forward -2.0% / -3.2% -> expect DEAD); lock_x BTC/ETH >= 0.80 forward arm (30 end-times; read it by window
  breadth too); N95 first settlements; N58 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 13:00-13:40 UTC cycle 48 (scheduled)
- Read-outs (fast trades.jsonl, last entry 12:54; slow 12:55): lock_x 64 trades / 49 end-times 59 won +7.5%/$ (one new loss 11:09, -$17.4;
  the 06:04 broad move still carries most of the total, see N101); >= 0.80 core 53 / 44 +3.3%/$. BTC/ETH >= 0.80 forward arm since 11-19
  01:00: 7 trades / 6 end-times all won (needs 30). lock_x50 +9.0%, lock_p_majors 45 / 39 +8.1%; lock_m 376 -0.8%, lock_b 181 +2.9%,
  lock_p_z2 446 -0.4%. N21 forward BTC/ETH 189 windows / 173 won -1.8%, alts 249 / 220 -3.3% (decision 11-21, still negative). LP-1 v2
  163 runs / 6.12 d: formula $2,147 (upper bound), trading -$439, pessimistic -$747; 118 settled, 76 open leftovers, 0 quoted; forward_core
  95 markets $487 vs +$19 / -$10. Options N42 forward rest 28 / 22 +11.0 pts (10 coin-dates, 7 positive), tails 7 / 0 -7.8, 59 open ->
  11-26. converge 29 / 28 +$3.68 (77 open, mark -$33); young 95 / 46 -$229 (98 open; 11-30); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64;
  mention 24 / 20 -$5.64. N95 rt_paper 82 seen, 9 open, 0 settled, open_past_end 0. COPY-1 137.9 h: sharp 104 primaries / 70 events +4.0
  pts (+2.5 at 5 min; bar 300 / 100), control 105 / 52 +3.9 (+4.5 at 5 min) -> sharp = control. N58 86 positions, 4 settled (+0.3 pts), 82
  open, open_past_end 0. No row crossed a kill or promote line.
- Test (adjacent N103, urgent_taker.py, local, tapes a + b + c, rules fixed before looking): big takers who swept >= 5c above the last
  same-way print, follower a300: -2.8 pts [-4.7, -0.8] on 1,105 events, halves -2.1 / -3.4; calm big takers -1.4 -> DEAD, wrong sign. At
  their own fill sweepers -2.2 vs calm +1.8 [0.8, 2.8] -> LESSONS 30 (urgency is overpaying, not information).
- Test (outside the box N104, dormant_wake.py, local, tapes a + b + c, rules fixed before looking): follow the first taker after >= 48 h of
  silence: +1.95 pts [0.4, 3.5] on 833 events, placebo (6-24 h) -1.5, but halves +4.5 / -0.4 and below the +3 line -> DEAD (lesson 24).
- Health: fast paper 12:54, slow 12:57, follow 12:30 (report 12:20), boosts 12:34, MM v2 13:01, books 13:00, live snapshot 12:05 - OK.
  Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders. No Actions dispatch needed.
- Next: N21 decision 11-21 (forward -1.8% / -3.3% -> expect DEAD); lock_x BTC/ETH >= 0.80 forward arm (30 end-times; by breadth); N95 / N58
  settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 17:00-17:40 UTC cycle 49 (scheduled)
- Read-outs (fast trades.jsonl, last settled entry 16:49; slow 16:56-16:58): lock_x 65 trades / 50 end-times 60 won +7.5%/$ (+3.2 pts/share
  [-5.2, +9.6]); >= 0.80 core 54 / 45 +3.4%/$ (+1.0 pts); BTC/ETH >= 0.80 forward arm since 11-19 01:00 still 7 trades / 6 end-times all won
  (needs 30). N21 forward BTC/ETH 193 windows / 177 won -1.7%, alts 259 / 230 -2.9% (decision 11-21, still negative). LP-1 v2 168 runs / 6.29
  d: formula $2,151 (upper bound), trading -$454, pessimistic -$745; 121 settled, 73 open leftovers, 1 quoted. Options N42 forward rest 28 /
  22 +11.0 pts (10 coin-dates, 7 positive), 61 open -> 11-26. converge 29 / 28 +$3.68 (78 open, mark -$39); young 99 / 46 -$269 (4 new
  settlements all lost, -$40; 95 open; 11-30); box office 9 / 8 -$0.96; charts 3 / 3 +$3.64 (2 open); mention 24 / 20 -$5.64 (4 open). N95
  rt_paper 82 seen, 10 in window, 9 open, 0 settled, open_past_end 0. COPY-1 142.3 h: sharp 112 primaries / 74 events +4.7 pts (+3.3 at 5
  min; bar 300 / 100), control 115 / 56 +3.4 (+3.8 at 5 min) -> sharp ahead at the fill, equal at 5 min. N58 86 positions, 4 settled (+0.3
  pts), 82 open, open_past_end 0. No row crossed a kill or promote line.
- Test (adjacent N105, second_big.py, local, tapes a + b + c, rules fixed before looking): a second different wallet >= $200 the same way
  within 48 h: +3.1 pts [2.2, 4.0] on 2,039 events vs the first big taker +2.5 [1.9, 3.1] on 3,070 -> adds +0.6 (rule +1.5) -> DEAD.
- Test (outside the box N106, herd_contra.py, local, same tapes, rules fixed before looking): fade a crowd whose first 30 entrants put >= 80%
  of $ one way: -4.6 pts [-5.6, -3.7] on 2,301 events -> DEAD, wrong sign. Its HERD control (follow the majority at the next majority-way
  a300) +3.5 [2.5, 4.5] on 2,291 events, halves +3.5 / +3.5. Post-hoc kill check (herd_follow_check.py): same a300 band 0.70-0.92 in all
  markets -0.5, in non-herd markets -3.6, herd +3.3 [2.0, 4.5] (1,727 events), share >= 0.9 +5.5; every fortnight with > 80 events positive.
  Found by looking -> N107: out-of-sample pull of the newest closed markets (herd_oos.py via run_script.yml; tape_entries.py got OUT_TAG so
  the canonical tapes are untouched), scored only on markets ending after the canonical tape. PASS -> forward paper tracker.
- Health: fast paper 16:56, slow 17:00, follow 16:42 (report 16:42), boosts 16:56, MM v2 17:01, books 17:00, live snapshot 17:04 - OK.
  Tracebacks only the old pilot-log / script-log; no MemoryErrors. STOP in place, no orders.
- Next: c50 read herd_oos_report.json (N107); N21 decision 11-21 (expect DEAD); lock_x BTC/ETH >= 0.80 forward arm (30 end-times); N95 / N58
  settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-20 21:00-21:40 UTC cycle 50 (scheduled)
- Read-outs (fast trades.jsonl, last entry 20:53; slow 19:57-21:03): lock_x 69 settled / 53 end-times 61 won +3.8%/$ (count by settled
  result; c49 counted 65 / 60); BTC/ETH >= 0.80 forward arm since 11-19 01:00: 8 trades / 7 end-times, 7 won - first loss (needs 30).
  lock_p_majors 46 +5.4%; lock_m 389 -1.7%, lock_b 194 +1.4%, lock_p_z2 461 -0.8%. LP-1 v2 171 runs / 6.41 d: formula $2,155 (upper bound),
  trading -$413, pessimistic -$695; 121 settled, 74 open leftovers, 0 quoted. converge 29 / 28 +$3.68 (79 open, mark -$40); young 103 / 49
  -$261 (98 open; 11-30); box office 9 / 8 -$0.96; charts 5 / 5 +$4.53; mention 25 / 20 -$15.86 (one -$10 loss; 3 open). N95 rt_paper 91
  seen, 9 open, 0 settled, open_past_end 0. COPY-1 146.2 h: sharp 123 primaries / 79 events +4.3 pts (+3.3 at 5 min; bar 300 / 100),
  control 148 / 62 +0.8 (+0.9 at 5 min) -> sharp now clearly ahead of control (first time by > 3 pts). N58 86 positions, 15 settled
  (was 4): -28.8 pts on 4 events (12 of them N66 retries in 2 mention events, -35); decision arm 3 / 1 event; open_past_end 0 - far from the
  100 / 40 kill read, but the retry arm is the one to watch. No row crossed a kill or promote line.
- N107 OOS read (herd_oos_report.json, c49 dispatch) said DEAD on 75 events, but groups a and c scored 0 markets: the 'unseen' cut was
  max(old scheduled end) and early-resolved markets keep Dec / Jan ends (lesson 10, added). herd_oos2.py (unseen = condition id not in the
  canonical tape, rule and line unchanged): HERD +2.47 pts [-1.9, +6.7] on 127 events (halves +4.2 / +0.8; a +7.1 / b +0.3 / c +1.7),
  HERD_B +1.1 vs BASE -1.6 -> PASS by a hair -> TESTING as rolling OOS pulls (next 11-27), kill if pooled < +1 after 300 events.
- Test (adjacent N108, herd_dip.py, local, rules fixed before looking): herd-way entry only on a pullback >= 3c below the herd's VWAP:
  canonical +6.7 [5.6, 7.7] on 1,785 events (halves +6.0 / +7.3), OOS +1.1 [-4.5, +6.5] on 94 events -> DEAD by its rule (OOS >= +2).
- New (outside the box N109): moved deadlines (endDate edits) -> READY, cheapest test = diff endDate across markets_active snapshots in git.
- Health: fast paper 20:57, slow 21:03, follow 20:42 (report 20:38), boosts 20:17, MM v2 20:31, replay 20:24, books 21:00, live snapshot
  21:04 - OK. Tracebacks only the old pilot-log / script-log; no MemoryErrors. STOP in place, no orders. No dispatch needed.
- Next: N21 decision 11-21 (expect DEAD); N109 count test; N107 pull #2 11-27; lock_x BTC/ETH forward arm (30 end-times); N58 retry arm;
  N95 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.

## 11-21 01:00-01:45 UTC cycle 51 (scheduled)
- Read-outs (fast trades.jsonl, last entry 00:59; slow 00:00-00:04): lock_x 71 trades / 55 end-times 63 won +3.8%/$ (-0.65 pts/share
  [-9.6, +6.8]); >= 0.80 60 / 50 -0.6%/$; BTC/ETH >= 0.80 forward arm since 11-19 01:00: 9 trades / 8 end-times, 8 won, -$10.7 (needs 30).
  lock_x50 +5.9%, lock_p_majors 47 +5.4%; lock_m 398 -1.5%, lock_b 200 +1.6%, lock_p_z2 469 -0.8%. N21 DECISION: forward BTC/ETH -2.0%/$ on
  202 windows / 8 days, alts -3.8% on 280 -> DEAD. LP-1 v2 176 runs / 6.58 d: formula $2,156 (upper bound), trading -$420, pessimistic -$709;
  125 settled, 71 open leftovers, 1 quoted; forward_core 96 markets $495 vs +$47 / +$35. Options N42 forward rest 31 / 24 +9.2 pts (10
  coin-dates, 7 positive), tails 7 / 0 -7.8, 60 open -> 11-26. converge 29 / 28 +$3.68 (80 open, mark -$38); young 123 / 66 -$206 (125 open;
  11-30); box office 9 / 8 -$0.96; charts 5 / 5 +$4.53; mention 27 / 22 -$7.21. N95 rt_paper 91 seen, 9 open, 0 settled, open_past_end 0.
  COPY-1 150.4 h: sharp 123 primaries / 79 events +4.3 pts (+3.3 at 5 min; bar 300 / 100), control 149 / 63 +0.8. N58 98 positions, 18
  settled -18.1 pts on 5 events (CI [-25, +5]; retry arm 15 / 4 events -21.0; decision arm 3 / 1), open_past_end 0. No other row crossed a line.
- Test (READY N109, moved_deadline.py, local, 494 hourly books snapshots, 13,324 markets, 22 days): 285 endDate edits, 15 later by >= 1 d,
  1 with >= 3 d left on the old end -> DEAD by count (rule needed >= 8 here).
- Test (outside the box N111, attention_spike.py, local, books snapshots, rules fixed before looking): fade a >= 5c 24 h move when 24 h
  volume jumps >= 5x: -3.7 pts [-6.1, -1.4] on 20 events; follow -2.8; placebo fade -4.2 on 80 -> DEAD (round-trip spread, no overreaction).
- New (adjacent N110): COPY-1 x HERD agreement -> READY (forward split only, rule fixed now).
- Health: fast paper 00:59, slow 00:04, follow 00:55 (report 00:50, chain saving), boosts 00:45, MM v2 00:01, replay 21:06 (6-hourly),
  books 01:00, live snapshot 00:04 - OK. Tracebacks only the old pilot-log (2) / script-log (1); no MemoryErrors. STOP in place, no orders.
- Next: N110 tagging script for follow primaries; N107 pull #2 11-27; lock_x BTC/ETH forward arm (30 end-times); N58 kill read at 100 / 40;
  N95 settlements; N42 11-26; young 11-30; COPY-1 to 300 / 100.
