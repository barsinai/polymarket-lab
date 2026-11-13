# Idea barrel

Rule: always 3+ ideas in TESTING, the next ones ranked in READY. Every idea gets the cheapest decisive test first
(history or replay), then a paper tracker with executable prices, then (only with the user's explicit OK) a small live test.
Status: TESTING (paper/backtest running) · READY (next up) · PARKED (needs something) · DEAD (killed by data, with the number).

## TESTING
| idea | why it could work | test | started | read-out |
|---|---|---|---|---|
| LP-1: sole liquidity provider in UNCONTESTED reward markets (quote two-sided at minimum size around a fair price we estimate) | Polymarket pays $121k/day of liquidity rewards; 837 of the 1,487 largest pools checked (>= $10/day, $22k/day in total) have NO quote within the reward band (empty books, median spread 0.65), and stay that way (94% still empty 2 h later; current pool in place a median 6.4 days; e.g. $250/day Jensen Huang/SpaceX, $200/day Daft Punk/Coachella, GTA VI Metascore 99 - unchanged since 11-06). By the published rules a sole two-sided maker gets the whole pool. Why unclaimed: you must know the fair price of obscure questions (a bot quoting the empty book's 0.50 mid is wiped out). Contested markets are the opposite: paper MMs lose 5-7% of fill notional and the pilot was paid 1/5 of our estimate -> all 6 paper variants -$90..-730/day | lp_screen.py (pool vs volume vs competition, all reward markets). PAPER (user asked for no-money first, 11-13): lp_paper.py hourly in the slow job - enters only markets where our formula share >= 50% (first run: 60 markets, pools $4,962/day, $1,827 of min-size two-sided quotes around Polymarket's displayed price); measures fills two ways (public taker trades that would have hit us; pessimistic: the price moved through our quote = full size taken), competition arrival, and the formula reward (an UPPER bound: the payout itself needs real orders). Read: fills/losses per $ vs pool per $ after 3-5 days | 11-13 | 11-16..18 |
| converge_day: last-day favourites 0.95-0.99 (both sides), non-sports, excl. tweet counts / data releases / crypto | holders pay to exit near-certain outcomes; insurance premium on the rare upset | 15-min books 10-31..11-13 (exact fees, executable asks, one entry per market, first time within 24 h of the end): 167/167 won, +2.0%/$ per trade held < 1 day (130 question families, median depth $672 within 1c). History (6,570 markets, daily prices): YES 0.95-0.98 1-3 d before the end 300 cases 99.33% +1.4%, 3-7 d 407 99.75% +2.2%; non-sports YES 0.95-0.98 1-3 d: 2 losses in 343 (0.6%: a player transfer, a mayoral race). Tweet buckets 30/32 (-4.2%) and data releases 2/3 excluded. BUT the 5-month history (hist_prices.py, 369 liquid non-sports, Jun-Nov, +0.5c + fee): 11 losses (3.0%), -0.7%/$ - +0.6..+1.0% in 5 of 6 months, August -11.8% (war events on the last day: Iran airspace / UAE / shipping); the 2-week books were a calm period. Expect ~0; paper converge_paper.py NAME=converge_day (hourly, $20) only to see the calm-period yield | 11-13 | 100 settled (~2 weeks) |
| Slow favourites: YES 0.95-0.98, non-sports, 3-30 d | holders sell near-certain outcomes early; the discount is a time premium | history 6,570 markets (+2%/position, 99.5%); converge_paper.py at real asks. 11-13 01h: 2 settled: UK GDP NO +$0.78; a soccer draw NO at 0.91 -$20 is a pre-filter 11-10 position (sports + below 0.95 - not the rule, LESSONS 10); 90 open, mark -$34. 11-13 17h: 4 settled 3 won -$18 (rule-conforming non-sports 3/3 +3.5%); 88 open, mark -$27 | 11-10 | first settlements 11-13 |
| lock_x (5m/15m lock + 2 s persistence + margin >= 1 bp + rem >= 6 s) with the exact price to beat | the K bug made our 'locks' wrong in knife-edge windows; exact K + persistence + margin removes them | replay 48 trades 100% +11%/$; paper lock_x / lock_x50 / lock_xk. 11-12 17h: paper 8 trades 7 won +8.1%/$ ($20) / +20.6% ($50); 11-12 alone 4/5 -$9.9 (small n). 21h: 10 trades 9 won +6.9%/$; lock_mv 10/10 +4.9%. 11-13 01h: lock_x 16 trades 15 won +12.3%/$ (12 end-times, 2 days: +$20 / +$14); lock_mv 19/19 +7.9% (14 end-times, one day) - need 30+ end-times over 4+ days. 11-13 05h: lock_x unchanged 16 (no new signal), lock_mv 21/21 +7.5% (15 end-times). CAVEAT: since lock_mv started (11-12 10:29) ALL 27 paper lock_m trades won, the 6 that lock_mv filtered out too (+6.4%) - the filter has not been tested on a losing day yet; lock_x ∩ lock_mv 11/11 +14.4% (7 end-times). 11-13 13h (c6): lock_mv FIRST LOSS (sol 5m 13:00, Down 0.97, margin 7.6 bp, 57 s) -> 25/26 +1.8%/$ (19 end-times); lock_x unchanged 16 / 15 +12.3% (no signal since 11-12 22h). 11-13 17h (c7): lock_x 17 / 16 +12.0% (13 end-times, 3 days); lock_mv 30 / 29 +2.2% (22); N7 intersection x∩mv 12/12 +13.6% on 8 end-times, mv-only 18 / 17 -3.2% -> lock_mv's value is all in its overlap with lock_x (lock_p ∩ mv identical); lock_p 36 / 33 +8.2% (31 end-times, 4 days) | 11-11 | 11-16 |
| lock_early (60-140 s, z >= 2.5, 2 s persistence) | before the last minute the market under-reacts to a large move | replay 65 trades 97% +4.9%; out of sample 17/17. 11-12 17h paper: 32 trades 30 won +0.9%/$ (days +2.2 / +16.6 / -19.3 / +5.4 $) - break-even ~95%, now at 93.8%. Kill at 50 trades if <= 0. 21h: still 32 trades +0.9%. 11-13 01h: 36 trades 34 won +1.4%/$ (27 end-times). 11-13 05h: 39 trades 37 won +1.9%/$ (28 end-times). 11-13 17h: 41 / 39 +2.1% (30 end-times) | 11-09 | 50 trades |
| Weather W1: latest ensemble forecast vs temperature buckets (40 cities, 11 buckets, daily) | physics ensembles (ECMWF 51 + GFS 31 + ICON 40 members), fresh runs, hourly METAR max per the rules. PRIOR: 11-01 a 2-day-old deterministic forecast lost to the market (Brier .199 vs .164) - this is the stronger model, low prior | weather_paper.py v1 (per-station bias + residual sd from 60 days of METARs vs archived forecasts, weather_bias.py): probability for every bucket, paper buys at real asks, Brier vs market. First run: 80 events, model-vs-market distance 0.27, 26 positions. 11-12 17h: first day settled, 31 positions on 15 events (all Asia, one day = ~1-3 weather regimes): 21 won, +$139 on $155, but +$78 is one 6c YES (Taipei 28C); without Taipei +$54 on 14 events. Need 10+ days. 11-13 01h: paper 62 settled 36 won +$153 on $310; scored 31 events / 341 buckets, ALL one day (11-12): Brier model .0732 vs market .0662 - market still better. 11-13 17h: paper 143 settled 81 won +$106 on $715; v1 73 settled +$114, v0 -$8; YES 26 / 5 won +$94 (a few longshots carry it); Brier not re-scored (gamma is blocked from the cycle sandbox; run weather_score.py via Actions) | 11-11 | 11-22 |
| Young markets, NO side: stand-alone non-sports binaries < 72 h old, YES mid 0.30-0.50 | history: priced 0.425, resolved YES 0.237 (n 283) - but history prices may be mids of empty books | young_paper.py at real NO asks, $10. 11-12 17h: real NO ask = NO mid + 10.5c (median, n 36). History re-run at executable prices (young_exec_history.py, 72-h first price): path questions ('hit/by/before', 138 events) +16%/$ at +10.5c, fixed-date (32 events) -31%; BUT completed path markets started 2026H2: 34 events, YES 36%, -6.6%/$ (2025H2/2026H1 +29..+31%). Paper 9 settled 0 won -$90: 7 are one bet (stock 'hit LOW' touches, 11-12 sell-off) + 2 Jensen Huang; early settlements are YES-biased (touches resolve early). Decide at the 11-13..11-30 end dates: kill if <= 0 on 20+ events. 21h: 12 settled 0 won -$120 (all early path touches / Huang; 50 open). 11-13 01h: 16 settled 3 won -$115; path 13/13 lost (~3 independent bets: 11-09 week stock touches, Huang x2), fixed-date 3/3 won +$15; N1 spread cap <= 5c keeps 26/63 (median spread 7.5c). 11-13 05h: 18 settled 3 won -$135 (2 more path touches lost: META/PLTR 'hit LOW', Huang). 11-13 17h: 28 settled 3 won -$235; marked to now_yes incl. those ending today: 36 'hit (HIGH/LOW) Week of November 9' positions -$168 (one week; their NO ask was NO mid + 13c median), 12 'close above' +$2, 23 other -$27. N17 census: touch YES IS rich on last prices, but the +13c NO spread eats it (see DEAD) | 11-11 | 11-30 |
| Sports vs Pinnacle (no-vig fair vs Polymarket asks, NBA + NHL moneylines and totals, pre-game) | sharp books set the true price; Polymarket books may lag | sharp_compare.py 3 snapshots a day, paper buys at fair - ask >= 2c, closing-line value + results. First snapshot 11-11: 48 pairs, |mid - fair| median 0.6c, p90 of fair - ask +0.7c, max +2.8c (main lines are tight) | 11-11 | 11-18 |
| Riskless structure (negRisk sums, ladders) at news time | dislocations appear when news hits and books are thin | arb_scan.py hourly, arb_log.jsonl | 11-11 | weekly |
| Options-implied fair value (Deribit) vs BTC/ETH price markets (above / below / between / touch) | a deep options market prices the same dates; Polymarket crowds may misprice tails and touches | options_probe.py PAPER=1 every 2 h: model + book log (Brier at resolution), $10 paper at edge >= 4c, 0.5-10 d. 11-12 14h: 16 paper positions, mostly one bet (ETH stays above 1,900 this week: market prices the dip richer than options); First snapshot 459 markets: above/below/between within +-1c (median), tails 1-2c rich, ETH ATM buckets 3.5-7c cheap on 6 dates, touches noisier (my touch model is the weakest part) | 11-12 | 11-19 |
| Box-office Saturday favourite (N2b): opening-weekend brackets, side priced 0.80-0.97 on Sat 14-02 UTC (Friday gross public) | the crowd is slow to turn Friday's number into a near-certain weekend; few traders, resolution Monday on actuals | history 134 films / 78 weekends (boxoffice_census.py, hourly last prices, +c cost): 95.5% won at avg 0.91, +4.1%/$ (+1c) / +2.9% (+2c), 54/60 weekends >= 0; but 2024..2025H1 -2%, 2025H2..2026Q1 +6..+8%. Paper boxoffice_paper.py at real asks, $10, hourly. 11-13 01h: out of window, 0 markets seen yet (first check Sat 11-14 14 UTC) | 11-12 | 30 weekends (~7 months) - size ~$10-50/bracket |
| Ranking-chart favourites (N10): Netflix top 10 / App Store #1 / Spotify #1 / Billboard #1, event favourite 0.60-0.97, 2-24 h before end | the chart is readable (daily Spotify / App Store charts, FlixPatrol for Netflix) before the event ends; few traders read it | history 208 events (charts_census.py, hourly last prices, fees off): band 0.70-0.85 won 87-90% vs priced 0.78 (23-38 events); fav 0.60-0.85 +5.6%/$ at +2c (49 events, end-24h), +13.6% (26, end-2h); Netflix fav +6.7% (72), App Store -6.2% (37); 2025 half -5.4% vs 2026 +6.2%. Leaders >= 0.95 won only 92-96% (3-4 losses). Paper charts_paper.py hourly at real asks, $10, rules fav + tail (leader NO <= 6c). First run 11-13 05:21: 12 live chart events; fees are now ENABLED on them (history: off) and favourite books are wide (Spotify #1 bid 0.41 / ask 0.76) -> spread cap 10c + fee 0.07p(1-p); 2 positions kept (App Store #2 paid/free) | 11-13 | 30 events (~3-4 weeks) |
| Research journal (my forecasts with sources) | reading + cross-checking beats the crowd on slow political/econ questions | forecast_log.py, Brier vs market | 11-10 | weeks |

## READY (ranked)
N1. **(adjacent, 11-12) Young NO, path questions only, with a spread cap.** History at executable prices: path-type +16%/$,
   fixed-date -31%; the real NO ask is 10.5c over the mid. Rule: path questions only, NO ask - NO mid <= 5c (half the
   cost), and group touches by underlying + week (LESSONS 6). Exposed to 3 (spread), 5 (the last half is -6.6%), 11
   (early YES). Cheapest test: young_paper.py already logs mid + ask -> re-score the open set at end dates by those filters.
N2. -> tested 11-12 (cycle 2): preview momentum DEAD, Saturday favourite -> TESTING (N2b).
   N1 note 11-13: on the 16 settled young positions the filters do not help yet (path 0/13, cap <= 5c 1/4); decide at end dates.
N5. -> tested 11-13 (cycle 3), PARKED (see below). N6. -> tested 11-13 (cycle 3), DEAD.
N7. **(adjacent, 11-13 c3) lock_x + lock_mv intersection at $20-50 with a 15m-window weight.** Both paper rules are 15/16 and 19/19 but on 12-14
   end-times; the intersection is the cleanest signal. Exposed to 1 (still the 2-s loop), 5 (one-two days). Cheapest test: score the
   intersection on data/fast/trades.jsonl (same slug+side in both strats) and in the exact-K replay; read at 30 end-times.
N9. -> tested 11-13 (cycle 4), DEAD (see below). N10. -> tested 11-13 (cycle 4), TESTING.
N11. **(adjacent, 11-13 c4) Netflix chart nowcast.** If N10's Netflix favourite edge is real, the source is FlixPatrol daily ranks (public, days
   before Netflix's Tuesday top 10). Score the leader by days at #1 in FlixPatrol vs the market favourite; only buy when they agree and
   the price is 0.60-0.85. Exposed to 13 (the chart is public), 9, 3. Cheapest test: FlixPatrol pages for 10 past weeks (read-only) vs outcomes.
N8. -> tested 11-13 (cycle 5), TESTING (mention_paper.py). Was: **(outside the box, 11-13 c3) Earnings-call MENTION markets ('What will X say during the call?', 579 closed markets).** Resolve on
   the call audio; the previous 4-8 transcripts of the same company give a per-word base rate (CEO verbal habits, recurring segments).
   Why the crowd could be wrong: traders guess from headlines; word frequency in past calls is public but tedious. Exposed to 13
   (base rates are priced), 9, 3 (thin books). Cheapest test: census of closed mention markets, price 1 day before vs outcome by
   price band (calibration first; only if mis-calibrated, fetch transcripts).
N12. -> tested 11-13 (cycle 5): lock_m 15m-only, TESTING read-out.
N15. -> tested 11-13 (cycle 6), DEAD as a strategy (see DEAD). N15b **(adjacent, 11-13 c6) Converge dip entry.** Buy the converge set only when
   the best ask is >= 1c under its trailing 24-h median (order books: such dips are +1.0c higher 24 h later, 34/70 back at the median).
   Could save ~1c of a ~2c edge, but some dips are news (LESSONS 2). Test: add a 'dip' tag to converge_paper entries (it already sees
   asks hourly) and compare settled dip vs non-dip entries; needs 30+ settled events.
N16. **(outside the box, 11-13 c6) Elon tweet-count markets (weekly / 3-day buckets) vs the public running tally.** The count only rises;
   buckets below it are dead and the rest follow a rate. Recorded books in the final hours are tight (dead buckets 0.001, sum of asks
   1.037) - bots read the tracker. Exposed to 1, 9 (our rate model vs theirs), 8. Cheapest test: closed weekly events, bucket prices on
   day 3-5 vs a Poisson/neg-binomial rate model from the tally then; first check the tracker history is reachable from Actions.
N13. **(outside the box, 11-13 c5) Equity-index / gold / oil daily 'close above X' and 'up or down' markets vs futures.** CME futures trade
   nearly 24 h and options give a full distribution; Polymarket SPX/NDX/gold daily markets are priced by retail. Why the crowd could be
   wrong: overnight futures moves and the exact close rule (official close vs a time print) are read slowly. Exposed to 1 (index bots exist),
   9, 13. Cheapest test: census of closed daily index markets, last price at 13:00 ET vs a normal model from the prior close + implied vol
   (VIX) and the outcome; needs a free futures/index history source reachable from Actions (check first).
N14. **(adjacent, 11-13 c5) Mention NO for the other speakers, single-event only.** Restrict the 'other' set to events that are one speech /
   presser (title 'during ...' with a start time, not 'this week'), which removes the early-YES path bias. Test: tag the census rows by title.
N17. -> tested 11-13 (cycle 7), DEAD as a taker (see DEAD). N17b **(adjacent) maker NO on weekly stock touch ladders**: rest a NO bid at
   NO mid on YES 0.30-0.50 rungs in the first 24-48 h; the touch premium (+8..+10 pts) would then be earned, not paid. Exposed to 2
   (fills come when the stock is moving toward the strike - exactly the touches), 6 (one week = one bet). Test: young_paper/books already log
   bid/ask; replay 'would my bid at mid have filled' with the CLOB trades of week-of ladders before believing it.
N18. **(outside the box, 11-13 c7) Rotten Tomatoes score markets vs the live review count.** The Tomatometer is a running tally: after
   ~80-100 reviews it rarely moves more than 2-3 points, and reviews land days before resolution. Why the crowd could be wrong: anchoring
   on the first ~20-review score, which regresses; few traders model the remaining drift. Exposed to 13 (score is public - edge only in
   the drift model), 9, 3 (thin books: use real asks from the start, LESSONS 3 / N8), 2. Cheapest test: census of closed RT markets
   (title 'Rotten Tomatoes'), price 1-3 days before end vs outcome by band - and the real spread from Kalshi/our books before any yield claim.
N3. **(adjacent, 11-12 c2) Later-weekend box-office brackets (2nd..6th weekend).** Drop ratios are predictable (genre, CinemaScore, Friday
   number); same Saturday-favourite rule. Exposed to 2, 3, 5. Cheapest test: rerun boxoffice_census on the 'Second/3rd..Weekend' titles.
N4. **(outside the box, 11-12 c2) Music chart markets (Billboard Hot 100 / 200 #1, Spotify daily #1).** Billboard's tracking week ends
   Thursday, the chart posts the next Tuesday; daily Spotify/Apple charts and mid-week industry projections are public days earlier.
   Why the crowd is slow: few traders read the projections. Exposed to 9 (our projection must beat theirs), 2, 8 (small books).
   Cheapest test: census of closed chart markets: price 1-3 days before resolution vs outcome, favourite yield at +2c.
OLD N2. **(outside the box, 11-12) Box-office opening-weekend markets vs Thursday previews.** Friday morning the trades print
   Thursday-preview grosses; opening weekend is ~7-12x previews by genre/franchise (public history). Why the crowd is
   slow: a few manual traders, thin books, numbers land 08-10 ET Friday. Exposed to 9 (our multiplier must beat the
   crowd's) and 2. Cheapest test: list closed box-office markets (gamma search 'box office' / 'opening weekend'),
   price at Fri 12:00 UTC vs the preview-multiplier model and the outcome; needs 20+ films to mean anything.
0. DEAD 11-13 (see DEAD: hook artifact). Was: **Push-driven lock_m for ETH/SOL (latency, not edge):** capacity_v1 (bot trades, legit): their cheap asks vanish in
   0.04-0.11 s after our 2-s REST look. The websocket replay that said +21..+39% at 0.05-1 s had a 1.5-s lookahead (11-12);
   without it, local 11-08..11-10: -3..-5% at <= 1 s. Read-out: server lockm.jsonl lines with "feed": "rx" (from 11-12 13h).
0b. DEAD 11-13 (see DEAD: hook artifact). Was: **Binance nowcast (testing 11-12):** RTDS carries Binance prices ~1 s before the Chainlink prints they anticipate
   (arrival 0.43 s vs 1.46 s; return correlation +0.3..+0.44 with Chainlink's same/next second). Model = last received
   Chainlink print x Binance move since its timestamp. Test: lifetimes FEED_TIME=bn vs rx vs ts (ts = perfect 1.5-s foresight,
   the ceiling). Live cost: none (same socket, the bot already stores the topic).
0a. **BTC lock_m sized up:** BTC asks survive (78% > 1 s) and others bought $1.3k per signal at <= our price; edge thin (+2-3%).
   Test: P&L of BTC lock_m at $100 / $250 / $500 against the recorded book (walk the levels).
1. **Weather W2 same-day nowcast (low prior).** The max only rises: a bucket below a METAR is dead. 11-02: after the
   day's max is in, the winner trades at ~$1.00 in 99% of 36k markets (bots). What is untested is the hour right after
   each METAR in the afternoon. Test: minute price history vs METAR times (IEM ASOS archive).
2. **Weather W0 skill backtest.** Open-Meteo historical forecasts (previous runs) vs IEM METAR outcomes for the 40
   stations: calibration of bucket probabilities, the station bias of each city, before trusting W1's trades.
3a. **Count markets with a public running tally** (tweet counts per week, etc.): bucket prices vs a rate model updated
   from the live count (like W2: the count only rises). Test: list the active count markets and their tally sources first.
4. **Scheduled data buckets (CPI, PPI, payrolls, Fed).** Bucket markets vs a distribution centred on consensus /
   nowcast (Cleveland Fed CPI nowcast) with the historical surprise sd; Kalshi prices on the same release as a cross-check.
5. **Maker on slow favourites.** Rest a bid 1c under the ask on the YES 0.95-0.98 set: spread + time premium; risk:
   fills come when news hits. Test: from the hourly tracker, how often the later ask trades through our bid level.
6. **Liquidity rewards on near-certain markets.** Reward programs pay resting orders near the mid; on near-certain slow
   markets adverse selection is small (the 11-05 pilot lost on crypto markets, where it is large). Test: CLOB rewards
   endpoint -> pools per $ of qualifying liquidity on the convergence set.
7. DEAD 11-13 (the 15m +14% was the hook artifact; bot-up 15m windows 16 trades +3.4%). Was: **15-minute windows on their own.** Replay: lock_p 15/15 +10-12%/$, lock_early 15/15 +15%, lock_c 12 92% +21% (5m: +4-7%). Fewer
   competitors on the slower window? A 15m-only rule set with its own sizing, once the paper sample is 30+.
8. **4-hour windows with the exact K.** 48 windows a day; the bot only watches their last 140 s - widen it for 4h.

## PARKED

- N5 scheduled-data favourites (11-13, data/history daily prices): CPI/GDP/jobs/Fed buckets at 0.90-0.98 1-7 d before: 50 positions /
  ~20 releases, +1..+5%/$ at +2c vs other non-sports +0.4..+1.1% (2,000 positions) - same as the converge rule, too few releases to tell
  apart. Revisit when converge_paper has 20+ settled data-release markets.

- Kalshi vs Polymarket automatic pairing (titles do not match; manual for named series only).

## DEAD (number that killed it)
- Touch ladders, taker (N17, 11-13, hit_census.py: 352 weekly + 156 monthly stock/commodity 'hit (HIGH/LOW)' events 2026-04..11-06, 4,592
  rungs with hourly last prices, crypto not reached in the time budget): touch YES is RICH - at start + 24 h YES priced 0.27 resolved
  0.17, 0.43 -> 0.35; dip touches (LOW) worst (YES 0.1-0.5 -47%/$, HIGH -25%). NO on YES 0.30-0.50: +9.4%/$ at +2c + fee (1,052 rungs,
  283 events, 19/28 weeks positive), +4.3% at +5c; at mid-life +0.7%. But the real NO ask on these ladders in their first 72 h is NO
  mid + 13c (median, 36 young-paper rungs, week of 11-09) and last prices overstate NO edges (mention census +15% -> negative at Kalshi
  asks). At +13c the edge is gone; the week of 11-09 (-$168 on 36 rungs) is one of the 9/28 losing weeks. Kept as maker idea N17b.
- Sports favourite-longshot bias (11-13): the 15-min books said pre-game favourites 0.60-0.90 won above their ask (+2..+10%/$, ~340
  markets, 2 weeks; NBA 15/15). 5 months of history (hist_prices.py, 8,871 moneylines with prices, Jun-Nov): leagues where every game
  has big volume are CALIBRATED at 3 h before the start - MLB won 60.7% at price 60.5%, NHL 62.9/63.0, NFL 68.2/67.1, esports 70.0/70.2;
  after +0.5c and the fee, majors + esports: favourite -2.0%/$ (n 629), underdog -7.2%. The 'favourites lose' gap in other leagues
  (-4 pts, n 3,999) grows with FINAL volume (-2.5 / -3.6 / -5.8 pts by tercile; inside MLB +7.9 -> -4.3) = selection, not an edge.
  No pre-game drift either (buy 24/12/6 h before, sell before the start: -1.4..-6.8%). Tracker removed.
- Mention markets NO as a taker (N8/N14, 11-13, kalshi_mentions.py: Kalshi hourly candles with the real yes bid/ask, 473 mention
  series, 9,623 settled markets / 494 events): YES is only 0-6 pts rich at the MID (e.g. mid 0.35 said 0.33, mid 0.47 said 0.42-0.43)
  and the spread is 3-9c, so NO bought at 1 - yes_bid loses in EVERY band: -0.1..-13.7%/$ 3 h before, -0.7..-23% 24 h before (events
  positive 41-208 of 187-262). The Polymarket census +14.6% was last-trade prices (LESSONS 3). mention_paper kept only as a spread log.
  Possible maker version (sell YES at the ask into retail buyers) untested, low prior (adverse selection from people who know the script).
- Weather W2 same-day dead buckets (11-13, data/weather/sameday.jsonl after the obsTime fix, 1,705 rows / 719 dead-bucket rows):
  0 with a YES bid >= 1c, 0 with a NO ask <= 0.985 - bots clear them. The one pre-fix case (London 7C bid 6.5c, resolved NO) was a one-off.
- Websocket-speed lock_m / lock_b replay / 15m-only (11-13, server lockm.jsonl 11-11 13h..11-13 15h, 389 window-trades at 0.1 s): split by
  whether the paper bot was running in the window's last minute - bot running: 137 trades on 95 end-times (1.4 each), 92.6% won, -0.3%/$ at
  0.1 s, -0.9% at 1 s, -6.4% at 2 s (rx, cap 0.97, 5m); bn the same (+1.3 / -2.1%); 15m 16 trades +3.4%. Bot stopped (our hourly hook, one
  slot per hour drifting ~5 min/h): 252 trades on 40 end-times (4.8 each), +14..+20%/$, and the count barely falls from R 0.1 s to 2 s
  (184 -> 179) - cheap asks that 'persist' are a frozen recording. Where replay and paper both traded (61 windows) prices agreed (0.929 vs
  0.924) and P&L was +1.3%. The heavy replay in the hook (650 MB, 927 MiB box) made the recorder fall behind (LESSONS 14). Hook step removed;
  lag_check server job measures recording lag by minute.
- Time-of-day / dip buying of slow favourites (N15, 11-13, tod_asks.py, 1,261 book snapshots, 192 tokens / 189 events): asks lowest 04-05 UTC
  but only -0.13c vs the day median (max-min 0.22c; placebo p95 0.08c); weekends not cheaper; 1c dips: ask +0.97c and bid +0.21c over the dip
  ask 24 h later (70 events). Cents (LESSONS 8); kept only as an entry rule idea (N15b).
- lock_m cool-down after a loss (N9, 11-13, paper lock_m 133 trades / 8 losses on 7 end-times): no clustering - trades within 30 min after a
  loss 3/4 -5.7%, within 60 min 11/12 +9.1% vs rest +0.2%; losses share an end-time only once (2 trades). Nothing to skip on.
- Earnings beat base rate (N6, 11-13, 470 closed 'beat quarterly earnings?' markets, 2025-09..2026-03, earnings_beat_census.py): the
  market already prices the ~73% beat rate - D-1 avg price 0.734 vs YES 0.737, Brier .156 vs base rate .194. YES all -2.2%/$ at +2c,
  YES 0.40-0.80 -10.2% (calibration 0.7-0.8 band: 0.75 priced, 0.67 won), YES 0.80-0.95 +0.6% (= 0 after fee), 2026 half -7.6%. NO 0.80-0.97
  +15% on 7 cases only. Lesson 13.
- Box-office preview momentum (11-12, 134 films): buy the direction of the Thu 22 -> Fri 18 UTC move at Fri 18 + 2c: +4.7%/$ on
  111 films, but a placebo with no news (Wed 22 -> Thu 18) gives +8.4%, entry at Fri 16/20/23 UTC +1.9/0.0/-3.7%, newest period -4.5%;
  move vs residual corr 0.07. Hourly-price noise, not under-reaction. The Fri 18 -> Sat 18 move: -13%/$ (overshoot, not drift).
- Maker on a lock (11-12, local 11-08..11-10, exact K, prints by receive time): rest a bid 0.90-0.97 on the locked side
  while z >= 2.5: fills come only from sellers who know better - filled windows won 48-67%, -28..-38%/$.
- Nested windows (11-12): a 5m and a 15m window ending the same second resolve on the same TWAP, so Up(lower K) +
  Down(higher K) pays >= $1. Riskless (asks + fees < $1) in 9 of 463 pairs, 3-32 shares, cents each; at fixed times the
  pair is fairly priced (-1..-3% = spread + fees).
- After the end (11-12): books and trades go on ~30 s past the end, when the final TWAP is already known, but no
  winner ask under 0.99 after end + 2 s in 7 h of recordings.
- Flow filter for locks (server flow_v3, 239 windows, 11-11 18h..11-12): flow toward Up -> outcome 8.3 pts BELOW the mid
  (n 36), toward Down -1.6 (n 42): the local +4.2 / -6.1 did not replicate.
- Late favourite at the ask, server sample (flow_v3): -31%..+5%/$ by band; the only positive cell (0.90-0.95 at 20 s,
  n 14) is noise next to its neighbours.
- Earlier lock entries 1-4 min before the end (replay, 11-12): z >= 3 at 60-140 s -0.2%/$, z >= 2.5 at 140-240 s 0.0%,
  z >= 3.5 anywhere 60-240 s -17%.
- Late favourite at the ask, no model (local recordings, 11-12): buy the side whose best ask is 0.60-0.95 at 20/40/60 s
  before the end: -36%..+0.1%/$ (cheap asks that survive late are cheap for a reason). The mid-based +10 pts was the spread.
- Weather fair value from a 2-day-old deterministic forecast (11-01): Brier .199 vs market .164. Known-outcome weather after the day's max (11-02): bots, winner at $1.00 in 99%.
- Date-ladder arbitrage (11-02, 468 ladders; 11-11 census again): cents.
- Big sparse ridge (11-02, 39k features, 1M rows): +1.5c val / -0.4c lockbox on fair rows - no robust edge.
- 5m: dog, fav, exact, pairs (rare), sweeper (~0 after fees), maker replays, copy-trading, flow-filtered MM.
- 5m window-start mispricing (exact K, 2,000 windows): the market beats the model even at rem 270-300 s (Brier 0.219 vs
  0.221); trading the gap -6.5..-10.7%/$.
- Ridge / logistic-ridge with 45 features: log loss 0.326 vs market 0.325; error not predictable (test R^2 -0.14).
- Cross-asset (BTC leads alts): coefficient 0.02; rule -11..-26%/$.
- Parity maker (15m/5m pairs): one leg fills in 45%, -$380 on 554 pairs.
- Jump chaser: 38% win, -23%/$.
- Spike fade (slow markets): 96 24-h exits -17.6%.
- Longshot NO (YES 2-10c): fairly priced (~0 except +0.75% in the last week).
- Endgame after the end date: 0.97-0.995 +0.17%/position.
