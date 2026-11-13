# Idea barrel

Rule: always 3+ ideas in TESTING, the next ones ranked in READY. Every idea gets the cheapest decisive test first
(history or replay), then a paper tracker with executable prices, then (only with the user's explicit OK) a small live test.
Status: TESTING (paper/backtest running) · READY (next up) · PARKED (needs something) · DEAD (killed by data, with the number).

## TESTING
| idea | why it could work | test | started | read-out |
|---|---|---|---|---|
| Slow favourites: YES 0.95-0.98, non-sports, 3-30 d | holders sell near-certain outcomes early; the discount is a time premium | history 6,570 markets (+2%/position, 99.5%); converge_paper.py at real asks. 11-13 01h: 2 settled: UK GDP NO +$0.78; a soccer draw NO at 0.91 -$20 is a pre-filter 11-10 position (sports + below 0.95 - not the rule, LESSONS 10); 90 open, mark -$34 | 11-10 | first settlements 11-13 |
| lock_b: lock_m with the Binance nowcast (prints in flight from the crypto_prices topic) | our Chainlink view is 1.45 s stale, Binance on the same socket 0.43 s | replay 20 h: rx -3..-5% vs bn +1.8..+4.6%/$ at <= 0.5 s. Server 11-12 06-13h (8 h, ~50 trades): rx +7.4..+8.4%, bn +6.5..+8.4% - the nowcast adds nothing there; one hour -$74, the rest positive (lumpy). Pooled with local: ~0. Paper lock_b (2-s tick). 11-12 17h read-out: server lockm.jsonl 11-11 18h..11-12 15h (21 h, unique windows): rx 191 trades 88.5% +9.1%/$ at 0.1 s (72 end-times), bn 170 trades +9.8%; nowcast +0.7 pts only. Paper lock_b 1 trade; paper lock_m 114 trades 93% -0.5%/$ (the 2-s bot never gets these asks). 11-12 21h: server 29-30 h unique windows rx 250 trades +7.5%/$ at 0.1 s, bn 227 +7.5% (+9.6% at 1 s); paper lock_m 117 trades 93.2% -0.4%/$, lock_b 3/3. 11-13 01h: server 33-34 h unique windows rx 285 trades +7.6%/$ at 0.1 s (108 end-times), bn 261 +8.0% (1 s: rx +8.1, bn +10.0); paper lock_m 128 trades 93.8% +0.6%/$ (days -16/-6/+37/-4 $), lock_b 13/13 +8.6% (9 end-times). 11-13 05h: server 39 h unique windows rx 301 trades +7.7%/$ at 0.1 s (115 end-times), bn 276 +8.5% (1 s: rx +8.7, bn +10.7); paper lock_m 133 trades 94% +0.8%/$, lock_b 18/18 +8.5% (14 end-times). 11-13 09h: server 41 h rx 329 trades 88% +8.4%/$ at 0.1 s (123 end-times; scored won/ask - 1 - 0.07(1-ask)), bn 300 +8.9%; paper lock_m 133 unchanged (no new lock_m signal 05-09h), lock_b 20/20 +8.0% (16 end-times) | 11-12 | 11-15 |
| lock_x (5m/15m lock + 2 s persistence + margin >= 1 bp + rem >= 6 s) with the exact price to beat | the K bug made our 'locks' wrong in knife-edge windows; exact K + persistence + margin removes them | replay 48 trades 100% +11%/$; paper lock_x / lock_x50 / lock_xk. 11-12 17h: paper 8 trades 7 won +8.1%/$ ($20) / +20.6% ($50); 11-12 alone 4/5 -$9.9 (small n). 21h: 10 trades 9 won +6.9%/$; lock_mv 10/10 +4.9%. 11-13 01h: lock_x 16 trades 15 won +12.3%/$ (12 end-times, 2 days: +$20 / +$14); lock_mv 19/19 +7.9% (14 end-times, one day) - need 30+ end-times over 4+ days. 11-13 05h: lock_x unchanged 16 (no new signal), lock_mv 21/21 +7.5% (15 end-times). CAVEAT: since lock_mv started (11-12 10:29) ALL 27 paper lock_m trades won, the 6 that lock_mv filtered out too (+6.4%) - the filter has not been tested on a losing day yet; lock_x ∩ lock_mv 11/11 +14.4% (7 end-times) | 11-11 | 11-16 |
| lock_early (60-140 s, z >= 2.5, 2 s persistence) | before the last minute the market under-reacts to a large move | replay 65 trades 97% +4.9%; out of sample 17/17. 11-12 17h paper: 32 trades 30 won +0.9%/$ (days +2.2 / +16.6 / -19.3 / +5.4 $) - break-even ~95%, now at 93.8%. Kill at 50 trades if <= 0. 21h: still 32 trades +0.9%. 11-13 01h: 36 trades 34 won +1.4%/$ (27 end-times). 11-13 05h: 39 trades 37 won +1.9%/$ (28 end-times) | 11-09 | 50 trades |
| Weather W2 data (same-day buckets already impossible by today's METARs, hourly log data/weather/sameday.jsonl) | if dead buckets still trade above 1c or their NO below 99c, that is riskless | count after 2-3 days. 11-13 01h: London 7C (bid 6.5c at obs max 8) resolved NO as expected; NYC 54-55F pending; Munich 5C bid 15c at obs 6 (11-13) pending. 11-13 09h BUG (LESSONS 10): observed_max used aviationweather reportTime (nominal hour: a 23:51 METAR is stamped 00:00), so the previous evening's last report counted toward today -> 'dead' flags at local midnight (NYC 46-47F at 00:05 local, Munich 5C bid 15-27c all night, SF 62-63F NO ask 0.54). Fixed to obsTime (+ raw DDHHMMZ fallback); W2 rows before 11-13 09:30 UTC are unreliable for early-day calls - count only rows logged after the fix | 11-12 | 11-16 |
| Weather W1: latest ensemble forecast vs temperature buckets (40 cities, 11 buckets, daily) | physics ensembles (ECMWF 51 + GFS 31 + ICON 40 members), fresh runs, hourly METAR max per the rules. PRIOR: 11-01 a 2-day-old deterministic forecast lost to the market (Brier .199 vs .164) - this is the stronger model, low prior | weather_paper.py v1 (per-station bias + residual sd from 60 days of METARs vs archived forecasts, weather_bias.py): probability for every bucket, paper buys at real asks, Brier vs market. First run: 80 events, model-vs-market distance 0.27, 26 positions. 11-12 17h: first day settled, 31 positions on 15 events (all Asia, one day = ~1-3 weather regimes): 21 won, +$139 on $155, but +$78 is one 6c YES (Taipei 28C); without Taipei +$54 on 14 events. Need 10+ days. 11-13 01h: paper 62 settled 36 won +$153 on $310; scored 31 events / 341 buckets, ALL one day (11-12): Brier model .0732 vs market .0662 - market still better | 11-11 | 11-22 |
| Young markets, NO side: stand-alone non-sports binaries < 72 h old, YES mid 0.30-0.50 | history: priced 0.425, resolved YES 0.237 (n 283) - but history prices may be mids of empty books | young_paper.py at real NO asks, $10. 11-12 17h: real NO ask = NO mid + 10.5c (median, n 36). History re-run at executable prices (young_exec_history.py, 72-h first price): path questions ('hit/by/before', 138 events) +16%/$ at +10.5c, fixed-date (32 events) -31%; BUT completed path markets started 2026H2: 34 events, YES 36%, -6.6%/$ (2025H2/2026H1 +29..+31%). Paper 9 settled 0 won -$90: 7 are one bet (stock 'hit LOW' touches, 11-12 sell-off) + 2 Jensen Huang; early settlements are YES-biased (touches resolve early). Decide at the 11-13..11-30 end dates: kill if <= 0 on 20+ events. 21h: 12 settled 0 won -$120 (all early path touches / Huang; 50 open). 11-13 01h: 16 settled 3 won -$115; path 13/13 lost (~3 independent bets: 11-09 week stock touches, Huang x2), fixed-date 3/3 won +$15; N1 spread cap <= 5c keeps 26/63 (median spread 7.5c). 11-13 05h: 18 settled 3 won -$135 (2 more path touches lost: META/PLTR 'hit LOW', Huang) | 11-11 | 11-30 |
| Sports vs Pinnacle (no-vig fair vs Polymarket asks, NBA + NHL moneylines and totals, pre-game) | sharp books set the true price; Polymarket books may lag | sharp_compare.py 3 snapshots a day, paper buys at fair - ask >= 2c, closing-line value + results. First snapshot 11-11: 48 pairs, |mid - fair| median 0.6c, p90 of fair - ask +0.7c, max +2.8c (main lines are tight) | 11-11 | 11-18 |
| Riskless structure (negRisk sums, ladders) at news time | dislocations appear when news hits and books are thin | arb_scan.py hourly, arb_log.jsonl | 11-11 | weekly |
| Options-implied fair value (Deribit) vs BTC/ETH price markets (above / below / between / touch) | a deep options market prices the same dates; Polymarket crowds may misprice tails and touches | options_probe.py PAPER=1 every 2 h: model + book log (Brier at resolution), $10 paper at edge >= 4c, 0.5-10 d. 11-12 14h: 16 paper positions, mostly one bet (ETH stays above 1,900 this week: market prices the dip richer than options); First snapshot 459 markets: above/below/between within +-1c (median), tails 1-2c rich, ETH ATM buckets 3.5-7c cheap on 6 dates, touches noisier (my touch model is the weakest part) | 11-12 | 11-19 |
| Box-office Saturday favourite (N2b): opening-weekend brackets, side priced 0.80-0.97 on Sat 14-02 UTC (Friday gross public) | the crowd is slow to turn Friday's number into a near-certain weekend; few traders, resolution Monday on actuals | history 134 films / 78 weekends (boxoffice_census.py, hourly last prices, +c cost): 95.5% won at avg 0.91, +4.1%/$ (+1c) / +2.9% (+2c), 54/60 weekends >= 0; but 2024..2025H1 -2%, 2025H2..2026Q1 +6..+8%. Paper boxoffice_paper.py at real asks, $10, hourly. 11-13 01h: out of window, 0 markets seen yet (first check Sat 11-14 14 UTC) | 11-12 | 30 weekends (~7 months) - size ~$10-50/bracket |
| Ranking-chart favourites (N10): Netflix top 10 / App Store #1 / Spotify #1 / Billboard #1, event favourite 0.60-0.97, 2-24 h before end | the chart is readable (daily Spotify / App Store charts, FlixPatrol for Netflix) before the event ends; few traders read it | history 208 events (charts_census.py, hourly last prices, fees off): band 0.70-0.85 won 87-90% vs priced 0.78 (23-38 events); fav 0.60-0.85 +5.6%/$ at +2c (49 events, end-24h), +13.6% (26, end-2h); Netflix fav +6.7% (72), App Store -6.2% (37); 2025 half -5.4% vs 2026 +6.2%. Leaders >= 0.95 won only 92-96% (3-4 losses). Paper charts_paper.py hourly at real asks, $10, rules fav + tail (leader NO <= 6c). First run 11-13 05:21: 12 live chart events; fees are now ENABLED on them (history: off) and favourite books are wide (Spotify #1 bid 0.41 / ask 0.76) -> spread cap 10c + fee 0.07p(1-p); 2 positions kept (App Store #2 paid/free) | 11-13 | 30 events (~3-4 weeks) |
| Mention markets NO (N8): 'What will X say during the earnings call?', NO when YES mid 0.10-0.40, 1-30 h before the call | the crowd overprices words being said: history earnings calls words at 0.20-0.35 said 12%, 0.35-0.50 said 24-26% | mention_census.py (36 calls / 411 markets 2025-02..2026-02, hourly last prices): NO on YES 0.10-0.40 +14.6%/$ (24 h, 29 calls, 22 positive) / +17.3% (2 h, 27 calls, 6/7 months) at +2c + fee, both halves positive; YES all -15..-18%. Other speakers +9% (24 h) / +1.8% (2 h) - path markets, shadow rule. Paper mention_paper.py hourly at real NO asks, spread <= 6c, $10 per word | 11-13 | 30 calls (earnings season: ~3-6 weeks) |
| lock_m 15m windows only (idea 7 / N12) | fewer fast competitors on the slower window | server websocket lock_m (41 h, rx, 0.1 s): 15m 73 trades +14.0%/$ on 25 end-times (cluster bootstrap 95% +2.8..+23.5), 5m 256 +6.8% on 104 (-4.5..+17); bn 15m +12.6%; 2-s paper lock_m 15m 13/13 +6.4% (10 end-times). Read-out from existing logs, no new code | 11-13 | 40 15m end-times over 4+ days |
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
N13. **(outside the box, 11-13 c5) Equity-index / gold / oil daily 'close above X' and 'up or down' markets vs futures.** CME futures trade
   nearly 24 h and options give a full distribution; Polymarket SPX/NDX/gold daily markets are priced by retail. Why the crowd could be
   wrong: overnight futures moves and the exact close rule (official close vs a time print) are read slowly. Exposed to 1 (index bots exist),
   9, 13. Cheapest test: census of closed daily index markets, last price at 13:00 ET vs a normal model from the prior close + implied vol
   (VIX) and the outcome; needs a free futures/index history source reachable from Actions (check first).
N14. **(adjacent, 11-13 c5) Mention NO for the other speakers, single-event only.** Restrict the 'other' set to events that are one speech /
   presser (title 'during ...' with a start time, not 'this week'), which removes the early-YES path bias. Test: tag the census rows by title.
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
0. **Push-driven lock_m for ETH/SOL (latency, not edge):** capacity_v1 (bot trades, legit): their cheap asks vanish in
   0.04-0.11 s after our 2-s REST look. The websocket replay that said +21..+39% at 0.05-1 s had a 1.5-s lookahead (11-12);
   without it, local 11-08..11-10: -3..-5% at <= 1 s. Read-out: server lockm.jsonl lines with "feed": "rx" (from 11-12 13h).
0b. **Binance nowcast (testing 11-12):** RTDS carries Binance prices ~1 s before the Chainlink prints they anticipate
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
7. **15-minute windows on their own.** Replay: lock_p 15/15 +10-12%/$, lock_early 15/15 +15%, lock_c 12 92% +21% (5m: +4-7%). Fewer
   competitors on the slower window? A 15m-only rule set with its own sizing, once the paper sample is 30+.
8. **4-hour windows with the exact K.** 48 windows a day; the bot only watches their last 140 s - widen it for 4h.

## PARKED

- N5 scheduled-data favourites (11-13, data/history daily prices): CPI/GDP/jobs/Fed buckets at 0.90-0.98 1-7 d before: 50 positions /
  ~20 releases, +1..+5%/$ at +2c vs other non-sports +0.4..+1.1% (2,000 positions) - same as the converge rule, too few releases to tell
  apart. Revisit when converge_paper has 20+ settled data-release markets.

- Kalshi vs Polymarket automatic pairing (titles do not match; manual for named series only).

## DEAD (number that killed it)
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
