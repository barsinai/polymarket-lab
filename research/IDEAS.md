# Idea barrel

Rule: always 3+ ideas in TESTING, the next ones ranked in READY. Every idea gets the cheapest decisive test first
(history or replay), then a paper tracker with executable prices, then (only with the user's explicit OK) a small live test.
Status: TESTING (paper/backtest running) · READY (next up) · PARKED (needs something) · DEAD (killed by data, with the number).

## TESTING
| idea | why it could work | test | started | read-out |
|---|---|---|---|---|
| Slow favourites: YES 0.95-0.98, non-sports, 3-30 d | holders sell near-certain outcomes early; the discount is a time premium | history 6,570 markets (+2%/position, 99.5%); converge_paper.py at real asks | 11-10 | first settlements 11-13 |
| lock_x (5m/15m lock + 2 s persistence + margin >= 1 bp + rem >= 6 s) with the exact price to beat | the K bug made our 'locks' wrong in knife-edge windows; exact K + persistence + margin removes them | replay 48 trades 100% +11%/$; paper lock_x / lock_x50 / lock_xk | 11-11 | 11-13 |
| lock_early (60-140 s, z >= 2.5, 2 s persistence) | before the last minute the market under-reacts to a large move | replay 65 trades 97% +4.9%; out of sample 17/17 | 11-09 | ongoing |
| Weather W1: latest ensemble forecast vs temperature buckets (40 cities, 11 buckets, daily) | physics ensembles (ECMWF 51 + GFS 31 + ICON 40 members), fresh runs, hourly METAR max per the rules. PRIOR: 11-01 a 2-day-old deterministic forecast lost to the market (Brier .199 vs .164) - this is the stronger model, low prior | weather_paper.py: model probability for every bucket, paper buys at real asks, Brier vs market | 11-11 | 11-14 |
| Young markets, NO side: stand-alone non-sports binaries < 72 h old, YES mid 0.30-0.50 | history: priced 0.425, resolved YES 0.237 (n 283) - but history prices may be mids of empty books | young_paper.py at real NO asks, $10 | 11-11 | as they resolve (1-60 d) |
| Riskless structure (negRisk sums, ladders) at news time | dislocations appear when news hits and books are thin | arb_scan.py hourly, arb_log.jsonl | 11-11 | weekly |
| Research journal (my forecasts with sources) | reading + cross-checking beats the crowd on slow political/econ questions | forecast_log.py, Brier vs market | 11-10 | weeks |

## READY (ranked)
1. **Weather W2 same-day nowcast (low prior).** The max only rises: a bucket below a METAR is dead. 11-02: after the
   day's max is in, the winner trades at ~$1.00 in 99% of 36k markets (bots). What is untested is the hour right after
   each METAR in the afternoon. Test: minute price history vs METAR times (IEM ASOS archive).
2. **Weather W0 skill backtest.** Open-Meteo historical forecasts (previous runs) vs IEM METAR outcomes for the 40
   stations: calibration of bucket probabilities, the station bias of each city, before trusting W1's trades.
4. **Scheduled data buckets (CPI, PPI, payrolls, Fed).** Bucket markets vs a distribution centred on consensus /
   nowcast (Cleveland Fed CPI nowcast) with the historical surprise sd; Kalshi prices on the same release as a cross-check.
5. **Maker on slow favourites.** Rest a bid 1c under the ask on the YES 0.95-0.98 set: spread + time premium; risk:
   fills come when news hits. Test: from the hourly tracker, how often the later ask trades through our bid level.
6. **Liquidity rewards on near-certain markets.** Reward programs pay resting orders near the mid; on near-certain slow
   markets adverse selection is small (the 11-05 pilot lost on crypto markets, where it is large). Test: CLOB rewards
   endpoint -> pools per $ of qualifying liquidity on the convergence set.
7. **4-hour windows with the exact K.** Fewer, slower, maybe less contested than 5m; lock and lock_early per window type.

## PARKED
- Sports vs sharp bookmaker odds (needs an odds-API key from the user).
- Kalshi vs Polymarket automatic pairing (titles do not match; manual for named series only).

## DEAD (number that killed it)
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
