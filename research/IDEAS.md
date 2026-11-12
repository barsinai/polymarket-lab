# Idea barrel

Rule: always 3+ ideas in TESTING, the next ones ranked in READY. Every idea gets the cheapest decisive test first
(history or replay), then a paper tracker with executable prices, then (only with the user's explicit OK) a small live test.
Status: TESTING (paper/backtest running) · READY (next up) · PARKED (needs something) · DEAD (killed by data, with the number).

## TESTING
| idea | why it could work | test | started | read-out |
|---|---|---|---|---|
| Slow favourites: YES 0.95-0.98, non-sports, 3-30 d | holders sell near-certain outcomes early; the discount is a time premium | history 6,570 markets (+2%/position, 99.5%); converge_paper.py at real asks | 11-10 | first settlements 11-13 |
| lock_b: lock_m with the Binance nowcast (prints in flight from the crypto_prices topic) | our Chainlink view is 1.45 s stale, Binance on the same socket 0.43 s | replay 20 h: rx -3..-5% vs bn +1.8..+4.6%/$ at <= 0.5 s; paper lock_b (2-s tick) + server lockm.jsonl feed bn per hour | 11-12 | 11-15 |
| lock_x (5m/15m lock + 2 s persistence + margin >= 1 bp + rem >= 6 s) with the exact price to beat | the K bug made our 'locks' wrong in knife-edge windows; exact K + persistence + margin removes them | replay 48 trades 100% +11%/$; paper lock_x / lock_x50 / lock_xk | 11-11 | 11-13 |
| lock_early (60-140 s, z >= 2.5, 2 s persistence) | before the last minute the market under-reacts to a large move | replay 65 trades 97% +4.9%; out of sample 17/17 | 11-09 | ongoing |
| Weather W2 data (same-day buckets already impossible by today's METARs, hourly log data/weather/sameday.jsonl) | if dead buckets still trade above 1c or their NO below 99c, that is riskless | count after 2-3 days | 11-12 | 11-14 |
| Weather W1: latest ensemble forecast vs temperature buckets (40 cities, 11 buckets, daily) | physics ensembles (ECMWF 51 + GFS 31 + ICON 40 members), fresh runs, hourly METAR max per the rules. PRIOR: 11-01 a 2-day-old deterministic forecast lost to the market (Brier .199 vs .164) - this is the stronger model, low prior | weather_paper.py v1 (per-station bias + residual sd from 60 days of METARs vs archived forecasts, weather_bias.py): probability for every bucket, paper buys at real asks, Brier vs market. First run: 80 events, model-vs-market distance 0.27, 26 positions | 11-11 | 11-13 (resolves daily) |
| Young markets, NO side: stand-alone non-sports binaries < 72 h old, YES mid 0.30-0.50 | history: priced 0.425, resolved YES 0.237 (n 283) - but history prices may be mids of empty books | young_paper.py at real NO asks, $10 | 11-11 | as they resolve (1-60 d) |
| Sports vs Pinnacle (no-vig fair vs Polymarket asks, NBA + NHL moneylines and totals, pre-game) | sharp books set the true price; Polymarket books may lag | sharp_compare.py 3 snapshots a day, paper buys at fair - ask >= 2c, closing-line value + results. First snapshot 11-11: 48 pairs, |mid - fair| median 0.6c, p90 of fair - ask +0.7c, max +2.8c (main lines are tight) | 11-11 | 11-18 |
| Riskless structure (negRisk sums, ladders) at news time | dislocations appear when news hits and books are thin | arb_scan.py hourly, arb_log.jsonl | 11-11 | weekly |
| Options-implied fair value (Deribit) vs BTC/ETH price markets (above / below / between / touch) | a deep options market prices the same dates; Polymarket crowds may misprice tails and touches | options_probe.py PAPER=1 every 2 h: model + book log (Brier at resolution), $10 paper at edge >= 4c, 0.5-10 d. First snapshot 459 markets: above/below/between within +-1c (median), tails 1-2c rich, ETH ATM buckets 3.5-7c cheap on 6 dates, touches noisier (my touch model is the weakest part) | 11-12 | 11-19 |
| Research journal (my forecasts with sources) | reading + cross-checking beats the crowd on slow political/econ questions | forecast_log.py, Brier vs market | 11-10 | weeks |

## READY (ranked)
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

- Kalshi vs Polymarket automatic pairing (titles do not match; manual for named series only).

## DEAD (number that killed it)
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
