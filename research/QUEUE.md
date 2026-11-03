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

## 11-01 17:30 MAJOR: selection bias in all historical tests
Kalshi draws: priced ~25%, happened 12% in the least-traded games vs 32% in the most-traded
(by FINAL volume); by volume BEFORE the bet: 25% vs 25%. Our listing keeps markets by FINAL
volume >= $5k, so dramatic outcomes (upsets, comebacks, late equalisers) are over-represented.
Re-test on rows with >= $5k traded BEFORE the bet (trades sample): fade-7-day, fade-1-day,
long shots: gone or negative. Draws: correctly priced. Boosted model (biased-trained): +4-6c
won-minus-price on Jun-Oct but CI includes 0 (n=175-496); retrained on unbiased rows only
(3.6k): nothing. => Historical "edges" were mostly the bias. Paper trading (selects markets by
volume at the time) is unbiased. Building a fair history: collect_volume.py (all markets,
volume before each bet moment).

## 11-01 21:45 Full-data rebuild (631k markets, 1.0M rows) judged on FAIR rows only
>= $5k traded before the bet (fully fair; 4,845 test rows Jun-Oct): every model and rule is
~0c won-minus-price (all CIs include 0) and negative after costs. Models trained on fair rows
only: also ~0 or negative. At >= $1k (only partly fair: $1-5k-before markets still needed a
$5k final to be listed) the boosted model's edge>6c shows +3.5c (CI +0.7..+6.3) - a hint at
most, contaminated by the same bias.
CONCLUSION: no evidence that simple price-pattern or price-based model strategies beat
Polymarket prices once selection is fair. Market prices are well calibrated.
Next directions (no prediction needed): 11. market making / liquidity rewards (earn the
spread + Polymarket's reward payments; risk = being picked off). 12. live cross-site gaps
(Kalshi vs Polymarket on identical questions, real time). Paper trading continues as the
unbiased forward test of everything already pre-registered.

## 11-01 22:15 NEW DIRECTION: liquidity rewards (market making) - most promising so far
Polymarket pays ~$585k/day in liquidity rewards across 14.8k markets (sampling-markets API;
recorded daily from now on). Using our hourly books: a small two-sided quote (200 shares/side,
~$196, at 1c from mid) would capture a reward share worth a median ~0.9%/day of capital
(top decile ~5.7%/day), stable over 20 hours, excluding live games / markets ending < 2 days.
BEFORE RISK. Unknowns: (1) adverse selection - fills when the price moves against us;
(2) exact reward formula (we use the published shape, simplified); (3) intra-hour competition.
13. [ ] Paper market-making simulator: each hour, pretend to quote mid+-1c in the best reward
        markets; fills detected from real trades in the following hour; P&L = fills marked to
        later prices/resolution + estimated rewards. This is the honest test.
- 11-01 22:40 Paper market making live (paper_mm.py, inside the hourly job): 40 best reward
  markets, quotes mid+-1c, 200 shares/side, fills from real taker trades the next hour,
  inventory limit 3x size, settles at resolution. Reward credit is an ESTIMATE (published
  formula shape); fills and inventory P&L are real-data based. Watch: fills vs rewards.
- 11-01 22:55 Paper MM first 3 hours: 57 fills, estimated rewards $321, trading P&L about -$30
  (cash +5, inventory at mid -35), total +$291 on $7,840 of quotes. Reward formula checked vs
  Polymarket docs (S=((v-s)/v)^2*b, Q_min two-sided rule, c=3, per-minute sampling, $/day
  pools): our shape matches; aggregating competitors instead of per-maker Q_min can misstate
  our share by up to ~3x. Practitioner guide: main risk = news jumps near catalysts. Change:
  only markets >5 days from their end (was 2).
14. [ ] Verify reward share more tightly: per-maker scoring needs order-level books (we
        record price levels only); consider recording the raw book for the 40 quoted markets.
- 11-02 05:45 Paper MM v1 after 11h: est. rewards $944 (upper bound), trading -$91, 153 fills in
  40 markets; 26/40 filled on one side only; 122 markets ever quoted (hourly re-pick abandons
  positions); losses from one-sided inventory in news-sensitive markets (Shas, ISM PMI).
  => Paper MM v2 live (paper_mm2.py, own job, every 10 min): requote 10 min, inventory skew,
  exit-only quotes for held positions, $300 cap per question family, rank by reward/vol, skip
  data releases / rate decisions / numeric ranges. Compare v1 vs v2 over the week.
- 11-02 06:05 Price download COMPLETE (REMAINING 0; final save worked after the events-file fix).

## 11-02 09:10 Toxic-flow study (2.8M taker trades >= $20, 53k markets): results/toxicity.json
Price drift in the trade's direction (what a market maker on the other side loses):
  by days to end: <1d +0.8c (in-game), 3-7d +1.0c, 7-30d -0.2c, >30d -0.2c  (REVERTS!)
  by kind: game winner +1.0c, crypto +0.7c, other +0.3c, soccer prop ~0, politics -0.3c
  by trade size: $20-100 +0.3c, $100-500 +0.7c, $500-2k +1.4c, >$2k +2.3c (big = informed)
  by hour: mild; US afternoon slightly worse, 21 UTC oddly benign. Not decisive.
=> In markets > 7 days from their end, flow is noise on average: fills earn the half-spread AND
   the price tends to come back. Exactly the MM habitat. (Final-volume bias, if anything,
   overstates toxicity here.) Changed v2: only markets > 7 days from end (was 5).
   Three v2 variants now live: 1c / 2c / reward-zone-edge offsets; book-width <= 4c required;
   exposure cap by Polymarket event id.
- 11-02 12:05 MM comparison (per hour, est. rewards / trading / net): v1 hourly-1c $84/-9/+74
  (18h); v2-1c $49/-17/+32 (6.7h, incl. one hour pruned to 13 mkts); v2-2c $32/-7/+25 (5.5h);
  v2-edge $3/+2/+5 (quadratic score ~0 at the edge: dead as a reward strategy, keep as
  control). All variants concentrate in the same few "AI release date" markets (Gemini
  Carbon, GPT Astra, Anthropic IPO): high pool, low competition, binary news risk -> winner's
  curse candidate; event cap ($300) is the backstop. Checks: exit-only quotes active (10),
  event cap respected (max $236), no settlements yet (all >7d). Too early to rank v1 vs v2.

## 11-02 14:00-16:00 deep dive (Fable)
- Fees (Polymarket docs): takers pay rate*p*(1-p) per share (crypto 7%, sports/most 5%,
  politics/finance 4%, geopolitics 0); MAKERS PAY NOTHING and earn 15-25% of taker fees as
  rebates. Added: taker fees to the betting paper trader (makes it honest), maker rebates to
  MM v2 (small extra income, shown separately).
- MM "wide" variant live: min-size quotes in 200 markets, same ~$7.9k capital.
- Trade-tape filter in v2: pull quotes after 3 consecutive >=$500 one-directional taker trades.
- Date-ladder logic arbitrage ("by Nov 15" vs "by Nov 30" etc., 468 ladders, 51 hours of
  books): essentially none (47c total). Bots keep ladders consistent. DEAD as a taker trade.
- New reward markets (1-3 days old): median competitor score 49 vs ~250 for older ones, pool
  $32/day; price volatility only modestly higher (0.6c/h vs 0.45c/h median). => fresh markets
  are attractive for MM; rewards snapshot now refreshed every 6h so they enter the universe.
- Known-outcome weather (buy the winning temperature bucket after the day's max is in): by
  21:00 local the winner already trades at ~$1.00 in 99% of 36k markets. Bots. DEAD.
- 11-02 20:40 Evening review (per hour): v1 $86 rewards / -$13 trading (26h); v2-1c $58/-21
  (12h); v2-2c $41/-12; v2-edge $5/0; v2-wide $48/-20 (5.6h, 332 fills in 200 mkts).
  Losses in every variant come from "by <date>" news-event markets (US x Cuba meeting,
  Trump speaks to Merz / al-Sharaa, Anthropic IPO): a single fill then a 20-30c jump.
  Added a data-driven JUMP FILTER: hourly recorder keeps 48h of mids per market
  (data/live/mids_48h.json.gz; 750 of 10.7k markets jumped >10c/h in the last 2 days);
  v2 excludes them and uses their 48h vol for ranking. Betting paper: 33 resolved, negative.
- 11-02 22:15 BIG SPARSE RIDGE (39,306 features: numeric, price band x horizon/category/
  deadline/negrisk, market age, weekday, hour, event size, sibling sum, 3,000 question words,
  words x band; 1.0M rows; alpha by validation). On BIASED rows it looks real: +3.3c (val),
  +2.5c (lockbox) for lean>2c. On FAIR rows: +1.5c val (CI +0.2..+2.7), -0.4c lockbox (CI
  -3.6..+2.7); trained on fair rows only: ~0 / negative. => no robust edge yet; fair sample
  still small (12k val / 8k lockbox rows). Rerun when data/volume completes (~Wed). The
  biased-vs-fair gap is the lesson: a convincing +3c that is pure selection bias.

## 11-03 07:00 Morning review
- Volume-before-bet collection COMPLETE (646k markets): fair filter now covers 95.6% of rows;
  77k rows fair at >= $5k (most moments simply had < $5k traded yet).
- Big ridge rerun on complete fair data: same picture - fair val +1.7c (CI +0.4..+2.8),
  fair lockbox -0.2c (CI -2.8..+2.3). Biased rows still show +3.3c/+2.5c. No robust edge.
- Fair battery (Jun-Oct, 18k fair rows): all rules ~0 or negative after costs. Two faint
  positives: boosted model trained on fair rows, edge>3c: +1.9c won-minus-price (CI +0.6..
  +3.1) but ~0 after taker costs (lean candidate only); FAVOURITES 80-95c one day before the
  end: +2.6c (CI +1.3..+4.1), +1.6%/bet after typical taker cost -> as a MAKER this is the
  "parking" idea. => new paper variant "park" to build.
- MM overnight: v1 $86/-7 per hour (37h); v2-1c $56/-16; v2-2c $41/-20; v2-edge $5/-5;
  v2-wide $42/-27 (15h). Losses dominated by "US x Iran ceasefire continues through Nov"
  (-$100+ per market in 2c/edge/wide; the event cap allowed ~3 such markets) and "by <date>"
  diplomacy questions. Jump filter cut fills ~20-60% with no reward loss (short sample).
  Jump-risk study (535k market-days): "by <date>" questions move >15c on 22% of days vs 17%
  for others; crypto $-threshold questions ~50%; sports/election futures 2-9%.
  CHANGE (all v2 variants): exclude by-<date>/through-<month>, $-threshold, ceasefire/truce
  questions; event cap $150. v1 stays as the unfiltered reference.
- Betting paper: model 79 resolved -42%; fade_week -81%; fade_jump -12%. Negative as expected.

## 11-03 16:30 Data API v1 retired + REPLAY ENGINE
- Polymarket retired Data API v1 at ~06:35 UTC: fills undetected in all paper MMs until ~14:50
  UTC (rewards still accrued). Migrated trades/holders/OI to v2 (cursor pages). Live lesson:
  need a "no trades seen while markets active" alarm that pulls quotes.
- Replay engine (replay_mm.py): paper_mm2.tick() over 64h of recorded hourly books with fills
  from the full v2 trade record (11.8k markets). Hourly requotes => pessimistic vs 10-min live.
  Results ($/hour; capital ~$9-11k): 1c 25.9 rew / -25.2 trade / +3.2 net; 2c 19.1/-15.9/+4.7;
  wide 15.4/-15.9/+1.6; tight 26.7/-26.6/+2.7; park 3.9/-12.5/-8.2 (favourites drift down).
  => at hourly speed trading losses ~= rewards: requote speed is decisive; the live loop must
  be seconds, not minutes. 2c beats 1c.
- Rule switches on 2c: SIZE BY CALMNESS net +9.4/h on $7.2k (vs +4.7 on $9.2k): doubles net
  per $. Max-jump 5c: rewards fall more than losses. Pool floor $20: no effect. Pause-after-
  fill: rerunning. => new live variant "2cv" (2c + size by calmness) replaces the dead "edge".
- Pause-after-fill: net +4.55/h vs +4.69 plain 2c. No gain. Dropped.

## 11-03 18:15 IDEATION ROUND (user asked for novel ideas) - studies + replays
- Hourly-book microstructure (exp_micro.py, 173k market-hours, reward universe):
  * Book imbalance within 2c of mid predicts next-hour mid move, monotonic over deciles:
    top decile +0.12c, bottom -0.09c (corr 0.04). Microprice is WORSE than mid (dropped).
  * 1h reversal: after a >=0.5c move the next hour gives back ~0.13c; after >=3c, 0.35c
    (4,790 cases). Supports keeping quotes up after moves (and explains pause-after-fill).
  * Competition: flat by hour of day and weekday (no timing edge). Markets <3 days old have
    ~1/4 the competing depth and 7-20x reward per competing share, but move 2c/h vs 0.3c.
    Weather: 850 shares competing, 25x reward yield, 2c/h moves.
- Replays (2c + size-by-calmness base = +9.42/h): LEAN one tick toward the heavier side when
  |imbalance|>0.4 -> +10.35/h (trading -9.0 vs -10.8, rewards 18.3 vs 19.1). Adopted as live
  variant "2cl" (replaces park, which lost -8/h). YOUNG markets (<3d old): almost no universe
  survives the >7d-to-end + jump filters (18 fills) - dropped. WEATHER: rewards 24/h but
  trading -36/h -> net -8/h. Dead.
- Wallet skill (exp_wallets.py, 80M trades, 54k random markets, train markets closed before
  May 1 / test after): persistence is weak (Spearman 0.06 across 20.7k wallets). LOSERS
  PERSIST: worst-decile wallets lose -3.7%/$ out of sample on outcomes and the price drifts
  -1.9% against them in 24h; decile 2 -1.7%. Winners barely: top decile +2.3%/$ on outcomes
  but +0.5% 24h drift; decile 9 negative. 94% of trades come from wallets with no record
  (sample covers 1/12 of markets). Uses: (a) fade bottom-decile wallets - gross +3.7%/$ to
  resolution vs ~1.3% taker fee: thin but real, needs full-market wallet coverage; (b) as a
  maker, fills from top-decile wallets cost ~0.5-1% - mild protection value. Queued: keep
  wallet ids in the replay trade record and test wallet-aware quoting.
- Holding rewards: Polymarket pays ~3.25-4% APY (daily, from its treasury) on position value
  in selected long-dated markets ("Earn x%" tag). Both Yes and No count. Not a strategy, but
  inventory parked in those markets is not dead money.
- Soccer vs Pinnacle: pipeline built (soccer.yml: football-data.co.uk closing odds for 8
  leagues + hourly Polymarket histories for 12k moneyline/draw markets since Aug 2025);
  analysis exp_pinnacle.py ready: calibration vs Pinnacle, taker test at 1h/6h/24h before
  kickoff with fees. Running tonight.
- Tax/legal notes for Israel written (TAX_ISRAEL.md): no official position; gambling 35% on
  gross (bad for an MM) vs business income (deductible losses, likely for a bot); crypto
  treated as an asset; ledger from day one.
- REQUOTE SPEED (replay_fast.py: intra-hour simulation from the trade tape, mid estimated
  from last taker buy/sell prices, 2c+sizevol selection): trading loss per hour at requote
  every 3600s -7.3, 600s -9.0, 60s -8.6, 5s -8.5 (fills 536 -> 590). => Speed does NOT fix
  the loss (correction to the 16:30 note). The loss is adverse selection at the moment of the
  trade, not stale quotes afterwards. Caveat: tape-based mids lag the real book, so a bot that
  watches the book could still do somewhat better; cannot be measured offline.
- LOSS DECOMPOSITION (2c+sizevol replay, 804 fills, mm_loss_decomp.py): -941 marked at the
  next snapshot, -635 marked 24h later (a third reverts). 236 fills in hours with a >=5c move
  account for -772 of -941; hours with <2c moves are breakeven. Per-$ loss ~7% of notional.
  Worst markets: date-specific announcements (Gemini release window, Anthropic IPO on Nov 20),
  Oscar nominations (4 sibling markets, -187), James Bond casting, benchmark score. Category:
  "Other" -15%/$, Sports -11%, Economy -10%, Tech -6%, Politics -3%.
  => SKIP extended: "on/between <month> <day>", "nominated for", "announced as", "be released".
  Overfitting risk acknowledged (3 days of data); these are news-binary templates by nature.
- Offset 3c: rewards 11.8 / trading -6.4 / net +6.1 (< +9.4 at 2c). HOLD inventory with
  two-sided quotes instead of dumping at mid: net +5.4 (worse: catches more toxic flow in
  de-selected markets). Dumping at mid stays.
