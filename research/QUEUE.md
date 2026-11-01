# Research queue (worked through continuously; newest status at the bottom of each item)

Rules: find on data before May 2026, confirm on Jun-Oct (events unseen), real measured costs,
one bet per market where repeats would inflate counts. Anything that survives -> paper trading.

1. [x] Template scan: group all markets by question template (numbers/names stripped), find
       templates whose prices are consistently wrong (train period), confirm on test period.
2. [x] Soccer deep dive: every soccer market type (winner, draw, O/U lines, BTTS, exact score,
       halftime) and by league; where are prices wrong after costs?
3. [ ] Full-data rebuild when price download finishes (data/REMAINING == 0), rerun everything.
4. [ ] Multi-option events: do candidates' prices add up? Fade the over-priced set (full data).
5. [x] Crypto price markets: fair value from exchange price + volatility (needs exchange data
       downloaded in Actions).
6. [x] Weather markets: fair value from forecasts / climatology (external data).
7. [ ] Time effects: hour of day, weekend, time since market creation.
8. [ ] Paper-trading / replay scoreboard review every few hours; hunt bugs.

## Status log
- 11-01 14:30 Template scan: 11 mispriced templates in training; none pass test after mean
  costs; with typical (median) costs, soccer draws d=1 is closest (+8c, CI incl. 0).
- 11-01 14:40 Draws deep dive: draw priced 24.7c, happened 29.8% (4,818 matches); +11c/$ after
  typical costs, both periods positive. Already paper-traded (soccer_low). TOP LEAD.
- 11-01 14:45 Started crypto fair-value work (item 5): Coinbase hourly prices download.
- 11-01 15:05 Crypto fair value: looked like a big edge, but it came from using exchange prices
  up to 1h fresher than the market price. With exchange prices >=1h old the fair value is no
  better than the market and loses money. DEAD (any edge is latency, i.e. bots' territory).
- 11-01 15:10 Next: template track record as a model feature (item 9).
9. [x] Model + template feature: each template's training-period mispricing (shrunk) as a
       feature; test with typical costs, cheap markets.
- 11-01 15:20 Template track-record feature: hurts the model (overfits). DROPPED.
- 11-01 15:25 Real fill costs of paper bets (v2): model picks pay ~0.75c above listed price
  (median 0.55c; >2c only 10%). => "typical (median) cost" backtests are the realistic ones.
  Boosted model in cheap markets at typical costs: +7c..+10c/$ (Jun-Oct), CI above 0.
- 11-01 15:35 Weather fair value (2-day-old gridded forecast, per-city bias/spread fit on
  training): worse than market on Jun-Oct (Brier .199 vs .164 at 1 day), loses money. DEAD.
- 11-01 15:50 Model robustness (cheap markets, typical costs, Jun-Oct): positive in 4/5 months
  (Sep ~0), days 1-7, both sides; strongest in soccer props; LOSES when buying >70c favourites.
  PRE-REGISTERED (before any paper outcome seen): "model_v2" = live model signal with
  model edge > 3c, side priced 10-70c, 1-7 days to scheduled end. Score from paper logs.
10. [ ] Kalshi comparison: download Kalshi settled markets + price history; match questions
        (Fed, CPI, elections, sports); does the gap between the two predict the outcome?
- 11-01 15:55 Paper bug #2: some tennis/basketball markets have an end date ~7 days after the
  game, so v2 still bet on matches in progress (lost almost all). v3: skip if gameStartTime is
  within 1 day, or the price moved >5c in the last hour. Scoreboard counts v3 only (from ~13:00 UTC).
- 11-01 16:20 Multi-option events (item 4, on ~85% data): options normalised by the event sum
  predict slightly better; "No on over-share options when sum>1.08" +15c (before May) / +10.5c
  (Jun-Oct) at average costs - BUT live books show the real No price is 4c (median) / 8c (mean)
  above 1 - listed Yes in exactly those events (wide books are why sums exceed 1). Lesson:
  costs must be measured conditional on the signal. Added to paper trading as multi_no.
- 11-01 16:20 Live recording widened (+markets ending within 4 days with >=$500): 12,059
  markets/hour (was ~9,700); first v3 hour: model 1226, fade_jump 102, multi_no 37,
  fade_week 31, longshot 26, soccer_low 6 signals.
- 11-01 16:40 Draws by league (tags cover 39%): no edge in big leagues (Premier League +3c n.s.,
  La Liga -4c, UCL -2c, UEL -6c); the +6c gap sits in untagged, mostly lower-profile leagues.
  => draw edge = less-watched leagues (thinner books). Paper trading decides.
- 11-01 16:35 Kalshi download restarted (own job, no parlays, 2025+, saves as it goes).
