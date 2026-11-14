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
- Extended SKIP (date-specific announcements etc.) replayed: rewards 14.6 (-4.5/h) vs losses
  -7.9 (+2.9/h): net +7.6 < +9.4. NOT adopted - the jumpy markets are also the ones with the
  big pools, and the vol-penalised ranking already handles the trade-off. Lesson: every
  "obvious" exclusion must be replayed; two of three so far made things worse.
- Size-by-calmness clamp 0.25-3x (was 0.5-2x): net +9.8/h on $6.2k vs +9.4 on $7.2k: ~+20% per $
  (cap 4x never binds). Ranking vol weight 50 (was 20): +8.2 - worse. Keep 20; clamp change is a
  candidate for the final config, not adopted live yet (live variants stay fixed for the week).
- Reward formula re-checked against docs.polymarket.com/market-makers/liquidity-rewards: S=((v-s)/v)^2*b,
  Q_min = max(min(Q1,Q2), max(Q1,Q2)/3) for mids 10-90c (single-sided scores at 1/3), sampled
  once a minute, Q_normal per sample, summed per UTC day, $1 minimum. Our model matches; our
  competitor estimate (book-aggregate min) overstates competition => share estimate conservative.
  Note: spread is measured from the "size-cutoff-adjusted midpoint" (orders below min size ignored)
  - we use the raw mid; small difference.
- WALLET-AWARE stand-aside (replay, trade record refetched with wallet addresses; 75% of taker
  trades come from wallets with a score): threshold decile 9 -> net +8.7/h; decile 7 -> +8.3/h;
  baseline rerun on the same record +9.0/h. Fills unchanged (820 vs 836). No gain: the fills
  that hurt are not predicted by the wallet's past record. Dropped for the MM. (The persistent
  LOSERS finding stands; it is a taker idea, not an MM one, and its edge is thin after fees.)
- 14-DAY VOL (collect_hist.py: hourly prices for 30 days, all 15k reward markets; daily job
  volfeat.yml): size-by-calmness + ranking using 14-day vol instead of 48h -> net +10.8/h on
  $5.3k (vs +9.0 on $6.7k same record): net per $ +50%. Biggest gain since size-by-calmness,
  and principled (less noisy vol estimate). ADOPTED in live "2cl" (now = 2c + size by 14d
  calmness + lean); 2cv stays as the 48h control. Applying MAX_JUMP to the 14-day max move
  (jump14): rewards collapse, net +4.0 - not adopted.
- SOCCER vs PINNACLE (exp_pinnacle.py; 1,110 matched games, 3,148 markets, 8 leagues since Aug
  2025): Polymarket pre-kickoff prices are as sharp as Pinnacle closing (Brier 0.1939 vs
  0.1947 at 1h); mean |difference| ~1c; betting toward Pinnacle LOSES after fees (-7.6c/share at
  2c threshold, 1h). Polymarket soccer is efficient. Dead. (Pipeline kept; daily job disabled.)
- 14d vol + clamp 0.25-3x: net +13.2/h on $4.0k (rewards 18.5 unchanged, trading -6.1): net per $
  2.5x the plain 2c+sizevol baseline. Insight: in thin reward markets our share saturates, so
  size beyond the competing depth adds exposure without reward -> testing size-by-competition.
  ref 0.003: +11.1; lean on top of vol14: +10.3 (no longer helps - within noise).
- Size capped at 1x competing depth (comp1): +13.6/h on $3.7k; 2x: +13.4 on $3.9k. Marginal on
  top of the vol clamp (rarely binds). Live "2cl" redefined to the frontier: vol14 + clamp
  0.25-3x + comp1 (lean dropped). 2cv stays the control.

## 11-04 06:50 morning check
- First out-of-sample night for the frontier config (live 2cl, 12h): +19.7/h net on $5.3k
  (rewards 35.3, trading -16.6). Control 2cv +11.1 on $8.6k; 2c +5.2; wide +1.8; 1c -28; tight
  -33 (most fills -> most losses); v1 +42.5 (optimistic accounting). Jobs chaining, data fresh.
- Replay over all 73h: frontier +16.5/h on $4.1k vs baseline +11.3 on $7.1k. Central-bank
  exclusion (fed/fomc/ecb/boe/boj): identical result - kept on principle.
- Dry-run quoter: ~37 cancel+post per 10-min tick for ~100 open orders (fine for rate limits);
  daily loss limit redefined on NET P&L incl. estimated rewards (trading alone loses ~$200/day
  by design, rewards ~$400/day).
- Scaling the frontier: N=40 +16.5/h on $4.1k (0.40%/h); N=60 +19.5 on $6.4k (0.31%/h); N=100
  +22.5 on $9.3k (0.24%/h). More capital deployable with diminishing per-$ return. Pilot sizing
  note: a few hundred dollars covers only 3-5 markets (~$10-25/day of rewards) - enough to
  verify payouts, not to earn.
- 11-04 12:30 midday: live 17.5h since the 2cl redefinition: 2cl +19.9/h on $5.1k; 2cv +10.1 on
  $9.1k; 2c +3.9; wide +4.1; 1c -20.9; tight -23.2; v1 +48 (optimistic accounting). Order holds.
  Scheduled volfeat run did not fire (GitHub cron) - dispatched by hand, second cron added.
  PILOT: SDK broker + live tick + pilot workflow built (dry mode); waiting for the user's secrets.
- 11-04 19:40 OUT-OF-SAMPLE DAY (replay of 11-03 23:00 -> 11-04 17:00, cold start, rules frozen
  before this data existed): frontier +19.7/h on $4.1k (rewards 23.9, trading -5.8) vs baseline
  2c+sizevol +6.0/h on $6.9k (rewards 24.6, trading -19.9). Same rewards, a third of the loss.
  Live 2cl over the same day: +19.8/h on $3.8k. Replay and live agree.

## 11-04 night batch (93h record, frontier = vol14 + clamp 0.25-3 + comp1: +16.5/h on $5.25k = 3.14/$k/h)
- 1.5c offers (rounded UP to the market tick; the unrounded version was an artefact): +17.2 on $5.1k (3.35/$k)
- size ref 0.004 (harder cut in jumpy markets): +16.9 on $4.6k (3.68/$k); ref 0.007 worse; clamp low 0.1: 3.24/$k
- event cap $75: +16.4 on $4.7k (3.51/$k); skew 2c: same; exit at mid: same; exit at 1c: worse
- N=20: +12.4 on $2.4k (5.1/$k); N=8: +9.0 on $0.8k (11.1/$k) - diminishing returns per market, as before
- COMBO (1.5c + ref 0.004 + cap 75): +17.35/h on $4.48k = 3.88/$k/h (+24% per $). ADOPTED for 2cl and
  the pilot "live" variant. Plateau reached in this family: every tweak moves net by a few %.
- PILOT config replay (8 markets, minimum size): +2.8/h on ~$430 (~$65/day). Treat as an upper bound:
  tiny orders in thin markets get the full modelled share; whether Polymarket pays it is the pilot's question.

## 11-06 NEW-STRATEGY ROUND (pilot paused; user: keep account, find a winning strategy, no live trading)
- Pilot post-mortem: reward pools change every few hours (10-15% of 13k markets per snapshot; e.g. a
  Eurovision pool 101 -> 88 -> 75 -> 2 $/day within a day; min size 20 -> 50). Stale configs = main
  reason for the 9x reward overestimate. Started track_boosts.py (boosts.yml): reward configs every
  5 min + book competition after each boost.
- PERPS FUNDING (Polymarket Perps vs Hyperliquid, 60 days, hourly): persistent gaps on alt-coins:
  ARB -36% APR mean gap, ETHFI -33, LINK -19, ENA -14, AAVE -13 (Polymarket funding below
  Hyperliquid). Simple rule (hold the hedged pair when the trailing-24h gap > 0.002%/h): 25-47% APR
  while held, BTC/ETH/SOL ~0. Not yet costed (fees both venues, mark-price basis, depth); needs a
  Hyperliquid account. Data rate-limited for ~15 coins: refetch slower.
- Holding rewards: 3.25% APR on listed long-dated markets, valued Yes+No at mid; complete sets not
  explicitly addressed in the docs. Small.
- Combos: RFQ-only (no order book), makers quote with own models; SDK has open_rfq_session (maker
  side) and request_combo_quote. Needs authenticated quote requests to study (no trades).
- 11-07 FAST UP/DOWN: resolution rule calibrated on 546 windows: Up iff mean of the last 60 s >= mean of
  the 60 s before the start (536/546 agree with our Binance proxy; the "window mean vs start spot" model
  v1 agreed 456/546). v1 paper: 600 trades, -$41 on $10.4k staked (+$340 day 1, -$382 day 2) = noise
  around zero with a wrong model. v2 model built on the calibrated rule; logs every book observation.

## 11-07 fast bot v2: first 2 hours
- v2 (calibrated rule, model vs book): 32 settled paper trades, 56% wins at avg price 0.64, -$107 on $540 staked.
- Offline check on 800 book observations: the market's mid beats our model at every horizon (log loss 0.55 vs 0.75
  at 2-2.5 min left; 0.19 vs 0.70 in the last minute). Our model picks direction 51% of the time, the market 75%.
  The "edge" we see is where the market knows better. v2 alone is not a strategy.
- Now running three paper strategies side by side: v2, fav (buy the market favourite at 0.60-0.95 with <= 90 s left),
  fav_agree (fav only when our model agrees). Every observation is logged with spot and K for offline testing.

## 11-07 midday (Fable): exact feed, linkage, trade tape
- RESOLUTION, EXACT: "Up iff Chainlink 60 s TWAP at the end >= price to beat (same TWAP at the start)". Official
  priceToBeat/finalPrice live in Gamma eventMetadata; final>=ptb reproduces 598/598 results. Polymarket's public
  RTDS websocket (wss://ws-live-data.polymarket.com, topics crypto_prices_chainlink / crypto_prices_twap_sixty)
  carries the exact feed for btc, eth, sol, xrp, doge, bnb, hype, zec. Binance sits ~14 bp ABOVE Chainlink
  (median -13.9 bp, 10-90% -15..-13) - the wobble in that gap decided the close windows v2 lost. Margin
  |final-ptb|: median 4.8 bp, 10% of windows < 0.85 bp.
- LINKAGE: the 15 m window and the 5 m window that ends with it have IDENTICAL finalPrice (132/132). With
  K15 != K5 one of the four outcome combinations is impossible -> one share of each right side pays >= $1,
  $2 in 35/132 pairs (26%). Asks summed to 1.03-1.22 in 40 paired obs (consistent, no free money seen yet).
- v4 bot (research/fast/updown_paper.py + rtds.py): 8 assets, K = official price to beat, Chainlink spot,
  strategies exact / lock / fav / dog / pair, obs every 2 s in the last 120 s, model track every 5 s.
- TRADE TAPE (data/fast/tape.jsonl.gz: 1.49M fills, $15.5M, 9,163 wallets, 598 windows; Data API v2):
  * 1,349 regular wallets (>=30 windows, >=$500): 464 profitable after full taker fees, 885 losing; net -$286k.
    Big losers: directional gamblers betting Up 70-76% of the time (win 32-35%).
  * Winner types: sweeper (0.97-0.99 in the last minute, 324 windows, 100%, +0.9%/$ on $194k); set-seller
    (sells both sides, never buys, 231 windows, +4.2%/$ on $133k, no fees); late knowers (buy 30-120 s
    before the end, 90% of windows won, exact-feed users); last-seconds set arbitrage (loser at 0.03 + winner
    at 0.96 < $1, 0x855e..., 181/221 windows). Our obs: ask_up+ask_down never < 1.00 in 361 paired reads
    (median 1.01) -> the taker arb is swept in < 3 s. Not for us.
  * "Dog" (cheap side 30-120 s before the end): +22..+32%/$ on $220k of fills BUT 5 windows = $90k of the
    $100k, median window -$74, ETH and 15 m negative. Informed late flips, not a resting mispricing. Control only.
  * Naive set-seller replay from the tape (asks = last print + spread): -3..-8% of capital per window; fills
    adversely selected because tape prices lag. A maker needs the exact feed; replay tomorrow from model.jsonl.
- 11-07 16:40 Bugs found in the v4 data: (1) the RTDS websocket goes silent after ~40 min and the recorder did not
  reconnect -> Binance fallback for the rest of each hour (76k msgs/h = 40 min x 32 streams); fixed (reconnect on
  20 s silence). (2) priceToBeat is fetched before Polymarket fills it in; now re-read at +45 s, +90 s, and before
  the last 2 min. Verified vs official numbers: feed TWAP at start == priceToBeat exactly (70/70), our mean of the
  last 60 s of Chainlink prices within 0.14 bp (97% < 0.3 bp); Binance pre-mean 10% of the time > 12 bp off.
  Chainlink feed is smoothed: sigma from 30 s returns is 1.43x the 1 s sigma (adopted 30 s sigma at 11:06).
- 11-07 16:45 With 200 clean windows the market beats the model at ALL horizons (log loss 0.21 vs 0.26 at 30-60 s;
  the 27-window "model wins in the last minute" was noise). z is honest (z 1-2: 98% realized; z 2-3: 97.5%).
  LOCK (z>=2, ask<=0.97, last 60 s): 20 chances / 288 windows, 18 won, +3.5%/$ after fees (early). PAIRS: with
  clean data sum<1 is rare (one XRP window at 0.97 where K15~K5); the SOL 0.75 "arb" was the wrong Binance K.
  exact -$139 on 224 (now restricted to z>=1, ask>=0.30); dog -$397 on 186 (dead, control); fav -$16.
  Report page corrected (section 7).

## 11-08 06:30 morning verdict (full night on the clean feed, ~1,750 windows, 8 coins)
- Feed == oracle: feed TWAP at end == official finalPrice in 1,638/1,638 windows (0.000 bp); at start == priceToBeat
  639/639. Our outcome view is exact. Hourly sigma swings 2-4x within a day -> added per-asset sigma floor.
- Paper by rule (since v4 start): exact -$710 on $14.9k (1,666 trades), fav -$533 on $12.3k, dog -$2,822 on $8.6k
  (all dead); lock +$41 on $1,037 (80 trades, 85%); pair (riskless) +$23 on $209 (3 real pairs post-fix, 1-3%
  margins); pair_ev +$29 on $381 (26 clean pairs, noisy).
- LOCK realism: of 79 lock asks, 23 had already risen at the next reading (2 s) - all 23 winners; all 12 losers
  persisted. Fill 2 s late at the new ask (<=0.97): +$23.93 on $927 (+2.6%). Persisted-only: -$30. The edge is
  mostly speed. 6/12 losers were asks < 0.50 (market disagreed) -> LOCK_MIN_ASK 0.50 (71 trades, 93%, +6.4% paper).
- Sweeper trade (98-99c, last 15-60 s, z>=2): 98c n=189 98.9% +0.8%/$, 99c n=426 98.8% -0.3%/$: ~zero.
- MAKER replay with exact-feed pricing vs the tape (1,669 windows): -6.2% of capital/window at 2-3c spread,
  -3.2% at 10c, +0.4% at 20c. Informed takers lift us. The real set-seller must be faster/smarter.
- Verdict: no exploitable edge for a REST-polling participant in these markets. Next: measure quote lifetimes with
  the CLOB websocket (decides whether a sub-second bot could catch the lock asks), and move research effort to
  slow-market making with flow-quality filters (80M-trade tape).
- 11-08 09:50 WEBSOCKET HOUR 1 (06:21-07:23 UTC, 240 token-windows, 330k top-of-book records): only 10 "locked
  and <= 0.97" episodes; 3 lasted < 0.15 s, 7 lasted 38-60 s (persistent = the marginal/losing kind: 8 won 2 lost,
  -$16 on $121 at any reaction time). REST poll vs websocket at the same instant: identical 95.3% of reads
  (99th pct |diff| 3c): our polling is not what we were missing; the market simply does not leave cheap locked
  asks around. Decision: do not build the fast bot; keep recording one more day for the final lifetime numbers.
  Recorder now runs as its own process (the in-thread version was dropped by the server as a slow consumer,
  22 reconnects/hour: GIL contention with the bot).
- 11-08 09:50 "exact" ran all night with the OLD unrestricted rule (an edit missed after re-indentation): -$1,072
  on $17.5k. Under the intended rule (rem<=60, z>=1, ask>=0.30) the same night: -$67 on $941 (83 trades). Only
  z>=2 & ask>=0.5 (= lock) is positive (+3% on 39). Dead either way; rule now applied as a control.
- 11-08 PATIENT BIDS backtest (53k random closed markets, 80M trades): deep dislocations revert on average
  (X=0.15: resting bid +7.9%/$ to resolution, +3.2% sold 24h later, 8,051 fills; taker 5-30 min after the print
  +9.1%/+14.9%, 4,352). Direction: buy No after a Yes spike works (+9%/+22%), buy Yes after a dump loses.
  BUT median ~0, 50% positive, top-20 fills = 79-100% of P&L; the money is cheap No (<= 20c) paying off big.
  Positive expectation, lottery-shaped; capital-inefficient for resting bids (0.04-0.06 fills per market-day).
- 11-08 11:30 COPY-TRADING (t-stat-selected wallets, 25k train / 28k test markets): skilled wallets (2,488) earn
  +2.4-2.6%/$ themselves, but the price move after their trades happens within the first hour (small trades:
  +2.0% at 1 h, +2.0% at 24 h, i.e. nothing after 1 h). Copying 1 h later with 1c in/out: -5%/$ at 24 h, -2.5%
  to resolution, same as copying random wallets. Weak wallets (5,814): -1.7..-3.8%/$, drift against them
  -0.4..-1.2%; fading them after 1 h nets < spread. Net skilled-minus-weak flow per market-day: no predictive
  power for the next day. Dead as a slow strategy: their edge is speed on news.
- 11-08 17:40 SLOW MAKER REPLAY (quotes at last print +-S, $20/side, 23k test markets, fills from real prints,
  marked at resolution): S=2c -5.1%/$ filled (67k fills), S=5c -6.1%, S=10c -3.7%. By counterparty: skilled
  wallets -8..-24%, "other" -4..-6%, weak wallets -1.2% (2c), -2.1% (5c), +6.8% (10c, 574 fills). Market flow
  score (trailing-7-day weak-minus-skilled share) does NOT separate: every bucket negative. Adverse selection is
  general, not confined to known-skilled wallets; and the counterparty cannot be chosen. #3 closed.
- 11-08 19:10 SPEED, re-measured: CLOB websocket events reach Helsinki 15-18 ms after the server stamp (median
  18 ms, 369k events) -> the matching engine is in Europe; my "220 ms RTT" assumption was wrong by 4-5x. US
  runner (Arizona) sees 160 ms to clob /time. RTDS Chainlink prices arrive 0.8-1.9 s after their stamp; the
  relay's Binance stream is synchronous with the Chainlink stream (+-1 s). User approved building the fast
  bot (paper first): research/fast/FAST_DESIGN.md. Bot now logs REST book-read RTT (report.rest_ms).

## 11-09 06:50 WEBSOCKET DAY (2,926 windows, 11.8M top-of-book changes): PATIENCE BEATS SPEED
- REST RTT Helsinki -> CLOB: min 39 ms, p50 49, p90 58 (13k book reads). WS events: 15-18 ms after the stamp.
- 169 locked-and-cheap episodes (z>=2.5, ask 0.50-0.97, last 60 s): 151 won / 18 lost. P&L by acting only after the
  condition persisted R seconds, paid at the ask prevailing then ($20 cap): 50 ms +0.3%, 100 ms +1.2%, 500 ms +0.4%,
  1 s +4.7% (85 ep.), 2 s +6.8% (66), 3 s +9.0% (57), 5 s +9.1% (49), 10 s +10.0% (43). Fast-vanishing cases are
  mostly flickering locks that reverse; persistent ones are the real ones AND still on sale.
- Capacity: median $16 at the ask after 2 s (25-75%: $8-42). Day at $20/trade: +$62; at $50: +$118. Per asset:
  btc/eth/bnb 29/29, 15 m 10/10; losers in doge/hype/sol/xrp/zec. One day, 5 losers: not proof.
- Decision: do NOT build the fast bot. New paper rule lock_p (lock must persist 2 s) running since 06:4x; keep
  recording; judge after several days. Report section 12 added. FAST_DESIGN.md kept for reference.
- 11-09 10:50 Today's additions: (1) lock_p variants in paper (lock_p1/p3/p5, lock_p_z2/z3, lock_p_majors,
  lock_p_15m, lock_p_50) for a multi-day comparison. (2) Maker variant of the persistent lock (bid one tick under
  the ask, recordings): filled 10 of 32 episodes, +3.2% on $200 vs taker +0.1% on the same 32: no real gain,
  dropped. (3) Early entry (60-140 s before the end, z>=2, persistence): negative at every persistence level
  (win 58-83% vs ~88% needed): the market is right before the last minute. Dead. (4) spike_monitor.py: hourly
  paper bot on GitHub Actions fading >=15c day-moves in long-dated markets (44 positions on the first run,
  2,100 markets scanned); report in data/slow/spike_report.json.

## 11-10 00:10 SERVER INCIDENT + THE REAL REASON LOCKS LOSE
- Incident: the server job materialised every recording ever published (4.5 GB tree + 6 GB .git), copied all of
  it to /tmp each hour, and once the disk filled (04:23 and again 21:24) `cp` left 0-byte copies that the
  restore step committed over good archives (bookws 11-08T22..11-09T03 lost in HEAD, others appended with
  duplicate members: T10 held the same hour 13x). Plain hour files were still tracked, so every `reset --hard`
  restored them and compress() appended them again. Fixed in fast_paper.yml: fresh small sparse checkout per
  job (no bookws/rtds/history chunks), recordings in /home/runner/pilot-data (3-day retention), publish only
  archives modified during the job, never 0-byte files, deletions of checkout copies only when skip-worktree.
  Archives rebuilt deduplicated from git history + plain files (bookws 355 -> 67 MB, rtds 518 -> 48 MB, all
  hours recovered except bookws 11-09T20). Readers dedupe lines. Old job cancelled 23:39, new one running.
- Lock family backfilled from the 2-s obs tape (replay_lock_variants.py; reproduces the bot's lock counts
  59/70 vs 52/67): lock 131 trades 91.6% +6.2%/$; lock_p (2 s) 54 90.7% +5.3%; lock_p_z2 137 93.4% +3.5%;
  majors 40 95%; 15m 12/12; early 44 95.5% +3.7%. With REST sampling every 2 s the instant rule is already a
  persistence filter, so lock_p adds nothing here.
- The losers are not noise: 3 of 5 lock_p losses were knife-edge windows (official |final-ptb| 0.00-0.02 bp)
  where our own K estimate (k_src chainlink, official ptb not yet published) was off by 0.13-0.17 bp, and one
  (xrp) where the last 2-4 s of a sharp dip did not enter the official TWAP the way the model assumed. The
  model's sd has no term for K error or timestamp misalignment, so z explodes near the end (z 10-22 and wrong).
  By margin of the predicted TWAP over K: >= 1 bp 93 trades 97% +$140; 0.3-1 bp 62-67% win, -$35.
- New paper rules lock_m (lock and margin >= 1 bp) and lock_pm (+2 s): on the tape 95 trades 96.8% +10.5%/$
  (+$142 in ~2 days at $20) and 35/35 +12.7%. In-sample threshold: the paper run is the out-of-sample test.

## 11-10 02:10 WHERE THE LOCK EDGE ACTUALLY IS (price band), and what the margin filter cannot fix
- settle.py (results only, no tape) replaces wallets.py for refreshing results_meta.json; run via run_script.
- Out of sample since the 21:39 restart (14 lock trades): lock 78.6% -$4.7; lock_m 8/9 -$1.9 (one loss at ask 0.97: btc 23:05 window,
  our K == official ptb exactly, final-ptb = -0.00 bp, margin at rem 25 s was 1.75 bp -> the price moved 4 bp in 25 s). A single
  0.97 loss (-$20) wipes 30 wins (+$0.6 each).
- Replay by ask price (4 days, lock): asks 0.93-0.97 = 78 of 131 trades, 2/3 of the capital, P&L -0.2%/$. Asks < 0.93: +17%..+50%/$.
  The market is right when it quotes 0.95+ on a "locked" side; our information is worth something only while it still quotes 0.70-0.92.
- First-signal study (150 windows): with <= 20 s left a cheap ask (0.50-0.70) on the locked side wins 2/7 -> the market has caught up
  and knows; rem 21-60 cheap asks 24/24.
- Calibration (76k obs vs official finals): projection error |final-proj| p99 by rem decade: 1.1 / 2.1 / 5.1 / 7.0 / 10 / 18 bp
  (pooled), per asset btc 0.4..9 bp, zec 2..28 bp. Model sd is calibrated in the body (ratio sd 1.0-1.2 for rem 10-60) but fat
  tailed (3% beyond 2.5 sd vs 1.2% normal; rem < 10 s ratio sd 3.6 = K error + timestamp misalignment).
  Obs-level loss rate at z >= 2.5 is 0.1-0.2%; trade-level loss is 8-10% because we trade exactly when the market disagrees -> the
  market's disagreement carries information; a bigger margin (>= p90/p95/p99 of the asset's own error at that rem) does NOT raise
  the win rate (90.6% vs 90.3%) - the filter removes trades, not losses.
- New paper rules (in the bot from ~02:41 UTC): lock_c = lock & ask <= 0.92 & (rem > 20 or margin >= 1 bp) [replay 51 trades 92.2%
  +$139 / +22%/$, 4 losers]; lock_cm (+ margin >= 1 bp) [40, 92.5%, +24%/$]; lock_cp (+ 2 s persistence, rem > 20) [19, 94.7%].
  Capacity caveat: median stake $9-10 (the cheap ask is usually 5-15 shares), so ~+$35/day at $20 cap even if it holds.
  Both selections (price band, last-20-s exclusion) were found in sample on 150 windows -> the paper run from here is the test.
- 02:10 cross-check on the websocket recordings (lifetimes.py, now window-level = one trade per window-side, first episode that
  persisted R s): in-sample day ask<=0.97 R=2 s: 50 windows 90% +2.5%/$ (the earlier +6.8% was episode-level: a flickering window
  counted many times); cheap band ask<=0.92 R=2 s: 27 windows 81.5% +0.6%/$. Same hours in the obs replay: lock_c 18 trades 83%
  +9.7%/$. Break-even at an 80c average ask is 81% -> over those hours the cheap-band edge is thin; 11-07 and daytime 11-08
  (no websocket coverage) carried the 4-day replay. New 4 hours (11-09T21..11-10T00): 11 windows 82% +7%/$ at R=2 s.
  Status of lock_c: candidate, not proof. Needs 3-4 paper days.

## 11-10 04:50 RECORDINGS: corrupt hours found, policy change (user OK)
- 3 of the 6 new rtds archives (11-09T23, 11-10T00, T02) had a damaged first gzip member: at a part end the bot sets rt_stop,
  the recorder thread starts its shutdown compress, the interpreter exits mid-write -> leftover .tmp -> the next compress
  appended to it. Fix: rtds no longer compresses at shutdown (plain hour file just continues, like bookws), compress never
  appends to a leftover .tmp; repair_gz.py keeps the good members (ran here; the hook runs it on the server hourly).
- CORRECTION of the 04:00 note: the "new 4 hours: 11 windows 82% +7%/$ at R=2 s" websocket figure was computed on the corrupt
  feed (stale prices from 23:00 on). Repaired, 11-09T21..11-10T02 (1198 windows): locked-and-cheap 13 windows at R=0.05 s,
  77% win, -$36.5; at R=2 s 1 window (lost); ask<=0.92: 5 windows 60% -$15. Last night the lock family lost on both tapes.
- Policy (user: "סבבה"): raw recordings stay on the server only (7-day retention); git gets data/fast/hourly/lifetimes.jsonl
  (research/fast/hourly.sh between parts: repair_gz, settle.py with RESULTS_META=$STORE/results_meta.json, lifetimes.py
  HOUR mode at caps 0.97/0.92). Repo stays public (user: fine as long as nothing is profitable). Existing archives in the
  tree (11-08..11-10) stay for analysis here; the 6 GB history is not rewritten.

## 11-10 05:30 RIDGE / LOGISTIC-RIDGE MODEL (user request): the market mid is the best predictor we have
- research/fast/ridge_model.py: 118,622 rows (2-s looks at Up tokens, rem <= 140 s, both books present), 4,038 windows,
  ~45 features (our TWAP model: z, margin, sigma, sd, g, K source; books: both asks, mid, spread, sizes, market-minus-model;
  price path 2..60 s returns, 60-s range, BTC 10/30-s return, market-wide co-movement count; time of day; asset/window
  one-hots; interactions z*rem, mid*rem, margin/sd, market logit). Train 11-07+11-08 (90k rows), test 11-09+11-10 (28k).
- Out-of-sample log loss: market mid 0.3248 | our phi(z) 0.3539 | ridge-logistic (any C) 0.3260. The model's heaviest
  weight is the market's own logit (+1.76 standardized). It does not beat the market; nothing we add moves it.
- Ridge on the forecast error (final - projection, bp): train R^2 +0.13, test R^2 -0.14 -> the error is unpredictable.
- Trading on model-vs-market mispricing (edge 5c over ask+fee): phi(z) -8.2%/$, ridge -5.7%/$; "average" +6% = one lucky day.
- Calibration (test days): favourites are slightly under-priced by the market (mid 0.944 -> realized 0.967; 0.816 -> 0.885),
  i.e. 2-3% on favourites before the spread; consistent with 'fav ~0 after fees' (taker). A maker variant would face the
  same adverse selection as the lock.
- Binance relay vs Chainlink lead (rtds, 25k prints/asset): corr with the next 2-s Chainlink return 0.04 (btc) .. 0.19 (eth),
  slope 0.05..0.27 bp/bp on a 1-bp lead -> fractions of a bp; not a feature worth having at our speed.
- Lock by window length (replay): 5m n124 90% +6%/$; 15m n22 91% +3%/$ (lock_c 15m 7/7 +28%); 4h: 72 settled windows, too few.

## 11-10 05:20 TRACK 4 (parity maker) DEAD ON THE TAPE; tracks 1-3 started (user: "continue with all of them")
- parity_maker.py on 554 aligned 15m/5m pairs (pairs tape, 4 days): resting bids on both legs adding to 0.90/0.95/0.98,
  posted at <= 100 s: both legs fill in 5-8% of pairs, ONE leg fills in 45% -> adverse selection (the leg that fills is
  the one going wrong): P&L -$370..-$385 on ~$1.8k staked, of which one-leg positions -$440..-$450. Taker riskless
  (sum <= 0.995 at some tick) 20 of 554. Dead.
- Research track: research/slow/scan_markets.py -> data/slow/candidates.json (284 markets resolving in 0.5-28 days, liq >=
  $5k, vol24 >= $500, binary, 3-97c, crypto price windows excluded), resolution-rule tags for track 3.

## 11-10 06:30 RESEARCH TRACK: first journal (27 forecasts, 5 paper positions)
- research/slow/forecast_log.py (add/score; EDGE 8 pts for a 'conviction' position, 'longshot' NO when my p <= 4% and the
  market is >= 2 pts above it; $20 paper stake), data/research/forecasts.jsonl, score_forecasts.py via run_script.
- Clusters researched: Iran/Hormuz (blockade end, ceasefires, PortWatch traffic), Spain Nov 29 election (40dB/Sigma Dos),
  Hegseth exit, WTI one-touch ladder (lognormal 55% vol reproduces the middle strikes; tails priced 4% vs model 0.5-1.3%).
- Positions: NO Hormuz-normal (longshot), NO Hegseth-out by 14/21/30 (0.94/0.85/0.81), NO WTI-dips-to-80 (0.385, model-only).
- Excluded on principle: markets about Anthropic / "best AI model" (I am an Anthropic model: conflict of interest, no edge).
- Mechanics notes (track 3): the US-Iran 'effective ceasefire by date X' markets resolve ~14 days AFTER X (first day of a
  14-day clean period must start by X); Spain 'next PM' resolves whenever a PM is sworn in (by March 2028) despite the
  Nov 30 end date shown; the Hegseth 'by November 30' market keeps a slug saying October 31 (extended market).

## 11-10 07:10 EXPERIMENT PROGRAM (user: "run many experiments until something works")
- Exp 2 cross-asset consistency (cross_asset.py, 73k ticks, 2,904 alt windows): outcome correlation alt/btc 0.35; adding the
  BTC market's logit to the alt's own: coefficient 0.02, test log loss 0.3750 vs 0.3736 -> nothing. Rule "buy the alt in BTC's
  direction when the alt is cheap": 23-57% win, -11..-26%/$ (the alt is cheap because it is going the other way). Dead.
- Exp 3 lock by session/weekday (replay, 4 days; coverage confounded: 129 weekend vs 17 weekday trades): lock_c weekend 45
  trades 93% +27%/$ vs weekday 6 trades 83% -6%; by session 00-16 UTC 28 trades 100% +33%/$ vs US 16-24 UTC 23 trades 83%
  +8%. Paper rules lock_cq (00-16 UTC) and lock_cw (weekend) added. Hypothesis: thin hours = stale books.
- Exp 4 window length: lock_c 15m 7/7 +28% (replay) - too few; scoring by window type continues.
- Exp 1 history: history_pull.py (6 months of resolved binaries + daily CLOB price paths) -> history_backtest.py (longshot /
  favourite / convergence by band, horizon, month, category). Running.
- Exp 5 Kalshi: kalshi_scan.py (events API, no parlays/sports, title match >= 0.25 to our candidates). Pending.
- Exp 6 sports vs Pinnacle: no free odds feed; needs an odds-API key from the user. Parked.
- Exp 7 window-start: the bot now reads the books for the whole 5-minute window (LAST_S=300 from the next job): does the market
  in the first minute reflect spot-vs-K (which we know from the RTDS TWAP before priceToBeat is published)? Data from 11-11.
- Exp 5 Kalshi (kalshi_scan.py): events API works (12,000 open events; 1,354 liquid non-sports binaries with dollar-string
  prices); naive title matching to our candidates is useless (40 'matches', all different questions). Automatic pairing
  parked; the research track cross-checks Kalshi by hand for the events it forecasts.
- Jump chaser (jump_react.py, 1,207 Chainlink jumps >= 4 bp in the last 120 s): the Up ask moves >= 5c within 30 s in only
  ~22% of cases; buying Up after an upward jump wins 38% (-23%/$). A 2-s jump is noise, not information. Dead.
- Exp 1 first pass (1,590 resolved markets, vol >= $2k, daily last-trade prices + 1c): favourite 0.90-0.97 with 1-14 d left:
  ~150 positions, 100% hit, +2..+6.7%/position; convergence (side >= 0.85-0.90, 1-3 d): 85-98 positions, 98-99% hit, +2.4-2.6%
  (worst month 2026-06: -7..-10%). Longshot NO at 2-5%: 97-99% hit, ~0..+1.25%/$ (fairly priced). YES at 15-25% resolved YES
  29% (n 34, one month drives it). converge_paper.py now takes the favourite at the REAL best ask hourly (17 positions,
  avg ask 0.960, 7.6 d) inside spike_paper.yml (renamed 'slow paper': spike + convergence + journal scorer).
- Exp 1 on 6,570 resolved markets (dense Sep 29-Nov 10 + sparse Feb-Sep; 1,813 YES wins): the robust edge is YES priced
  0.95-0.98 bought 3-14 days before resolution: 407 positions 99.8% +2.2%/$ (3-7 d), 416 positions 99.0% +1.5% (7-14 d),
  no losing month; 1-3 d: 300, 99.3%, +1.4%. YES 0.90-0.95: weaker (+0.3..+2.3%, 94-96%). NO side (YES at 2-10c): +0.75%
  only in the last week, ~0 or negative beyond; 10-25c longshots resolved YES more than priced (selling them loses).
  Early exit at 0.99 and the 'stable' filter do not add. The 15-40c YES anomaly of the first sample does not replicate.
  Convergence (side >= 0.95, 1-3 d): 702, 98.9%, +1.0% per 2.2 d. converge_paper.py band widened to 0.98 (both sides
  recorded; YES is the strategy, NO the control). Evidence report section 15 (heat grids).
- 09:10 by category: the YES 0.95-0.98 edge is NON-sports only (3-7 d: 393 positions 100% +2.43%; 7-14 d: 410, 99.5%, +1.97%;
  14-30 d: 419, 99.5%, +2.12%); sports favourites at 0.95-0.98 LOSE (-4..-32%, 67-93% hit: live games flip). Tracker now
  skips sports, takes YES first (NO capped at 5/run as control), up to 30 days, ask <= 0.985. 37 paper positions open.
- Spike fade first 24-h exits: no_after_spike 22 exits -10.8%, yes_after_dump 19 exits -11.5% (continuation, not reversal).
  Resolution P&L still pending.
- Server hook verified: repair 0, 3,400 windows settled on the server, lifetimes T07 (224 windows, 3-5 episodes, all won),
  hourly/lifetimes.jsonl published; store 307M after LAST_S=300.

## 11-11 07:45 HINDSIGHT IN THE WEBSOCKET STUDY (correction) + morning numbers
- lifetimes.py used the OFFICIAL priceToBeat (md["ptb"]) for z; for 5m windows it is published only late, the bot never has it
  in the lock window (bot lock trades since 11-09: K from twap 16 trades 94% +$1.4; K from Chainlink proxy 63 trades 84% -$40).
  The server's hourly summaries (11-10 +15..+22%/$) carried that hindsight. Now K_EST=bot (60-s TWAP topic at the start, else
  the mean of Chainlink prints in the minute before) is the default; hourly.sh back-fills recent hours with it.
- Local recordings 11-08..11-10T02, window level, bot K: cap 0.97 R=2 s 46 windows 87% +0.8%/$; R=3 s +3.2%; cap 0.92 R=2 s 27
  windows 78% -2.2%. With official K (cap 0.92): 34 windows 77% -4.8%. Lock family ~break-even at best. 
- Bot since 11-10 02:41: lock 64 trades 87.5% -$35; lock_c 17 82% -$10; lock_p 14 93% +$10; lock_early 17/17 +$21 (+7.2%/$);
  lock_p_50 +$13. Only lock_early and the persistence variants are positive, on small n.
- Spike fade: 96 24-h exits -$139 (-17.6%); mean move of the bought token ask->bid -5.8c (fade NO) / -2.4c (fade YES); about
  the spread plus a little continuation. Momentum mirror would net ~0 after two spreads. Dead at 24 h; resolutions pending.
- Convergence tracker: 85 open (29 YES / 56 NO control) -> NO control capped at 25 open. No settlements yet (first 11-13).

## 11-11 13:30 THE K BUG, lock_x, and the arbitrage census (user: "think deeply, find a winning strategy")
- The RTDS crypto_prices_twap_sixty message stamped EXACTLY at the window start = official priceToBeat in 2,796 of 2,796
  windows where it was recorded (the message 1 s later differs in 89%); the one at the end = finalPrice. It arrives ~1.5 s
  after the stamp (p99 2.6 s). The bot asked for it at the first tick of the window, before it arrived, and fell back to a
  Chainlink-print average (k_src chainlink: 72% of windows; 84% win vs 94% with twap). Fix: twap_exact(), the window start
  waits up to 8 s for it (k_src 'twapx').
- Replay of the bot's whole 2-s tape (11-07..11-11) with the exact K: lock +2.7% -> +4.8%/$; lock_p +5.5% -> +7.4% (95.3%).
  Remaining lock_p losers: margin < 1 bp or <= 5 s left. lock_p & margin >= 1 bp & rem >= 6 s: 48 trades, 100%, +11.4%/$
  (bot K) / 45 trades 100% +11.9% (exact K), every day positive; $50 cap +$116 over ~3.5 bot-days. Paper rules lock_x ($20),
  lock_x50 ($50), lock_xk (exact K only) from the next server part. The rem >= 6 cut is in-sample: paper decides.
- Arbitrage census (arb_scan.py, 2,100 events, 17,246 books, POST /books): negRisk outcome sums and date/threshold ladders.
  After fixing survival ('continues through') and downward/'top N' directions: 29 'opportunities', all cents on $1-$200 of size
  with capital locked for months (FDV ladders 0.3-0.8c, Discord IPO buckets 4c on 5 shares). Competed away. Kept hourly in the
  slow-paper workflow to log news-time dislocations (data/slow/arb_log.jsonl).
- Endgame (buy the leader after the end date, history): 0.97-0.995 +0.17%/position; 0.90-0.97 non-sports 55 cases 100% +4.6%
  over ~7 d (disputed/slow resolutions) - niche, small n.

## 11-12 06:40 first night with the exact K
- K == official ptb in every 5m window since 13:00 UTC (k_src twapx).
- Since the fix (15.5 h, bot's own paper trades): lock 30 trades 96.7% +5.4%/$; lock_m (margin >= 1 bp) 28/28 +6.8%;
  lock_c 6/6 +21%; lock_x 3/3 +44% (persistence now rarely holds: with the exact K the ask moves past 0.97 within 2 s).
  The only loss: xrp 23:59, margin 0.65 bp, official final-ptb 0.01 bp (excluded by lock_m / lock_x).
  lock_m before the fix (11-09 22:42 .. 11-11 13:00): 69 trades ~91%, -$6. The K error was the difference.
- Sharp odds 22:05 snapshot: 70 pairs, |mid - fair| median 0.5c, max fair - ask +1.7c -> no paper position (threshold 2c).
- Weather: 211 open (94 calibrated); first resolutions today. Converge 89 open, first 11-13. Young 31 open.

## 11-12 08:50 CAPACITY / LATENCY of the lock signals (server job capacity_v1, 45 signals since the K fix)
- Survival of the cheap ask after the bot's 2-s look: median 0.48 s; > 0.25 s in 53%, > 1 s in 40%.
- By asset: BTC survives (median 2.1 s, 78% > 1 s) and is deep: after our signal others bought $776 median / $1,286 mean at
  <= our price. ETH/SOL: gone in 0.04-0.11 s (fast bots), $85-108 median. XRP/DOGE/BNB/HYPE/ZEC: $0-23 median.
- The trade-off: where the size is (BTC) the edge is thinnest (lock_m BTC 91-93%, +2-3%/$ in the replays; a BTC lock_m loss at
  11-12 04:29 with margin 1.79 bp); where the edge is fat (ETH/SOL/BNB/DOGE lock_m 96-100%, +8..+13%) the ask is gone in
  a tenth of a second and holds $25-200.
- flow_v1 hit the 420-s limit (30 h of events, full JSON parse); flow_v2 tests the time window before parsing (5 h in 26 s).

## 11-12 11:10 lock_m reality check + server incident
- Since the K fix (11-11 13:00 .. 11-12 08:30 UTC): lock_m 36 trades 91.7% -$13.8 (11-11: 16/16 +$17.6; 11-12: 17/20 -$31.4);
  lock_c 10 70% -$22.5; lock_x 5 80% +$5.7. One burst lost BTC + SOL (+ XRP 15m) at 04:29 UTC with margins 1.8-6.3 bp and
  ~50 s left; HYPE 04:54 lost at ask 0.50 (the market disagreed hard). Wins pay +$0.6, losses -$20: at asks 0.95-0.97 the
  break-even is ~96-97%. Not a strategy yet.
- Hypothesis (exact-K replay, in-sample): last-60-s range > 2x the margin -> lock_m 88.6% ~0 P&L; else 95-96% +6..+9%/$.
  Paper rule lock_mv from the next part.
- Server incident: the 08:28 hook ran the new server job lockm_push_v1 (lifetimes over ~20 h of book events in one process);
  the job was cancelled at 08:39 (runner most likely out of memory), no hand-over. Job removed; lock_m per hour now runs in the
  regular hook, one hour of data per process (data/fast/hourly/lockm.jsonl). Bot restarted by dispatch.
- 11-12 12:30 BUG (lookahead) in the websocket lifetime study (lifetimes.py, hourly lifetimes.jsonl / lockm.jsonl): the model
  used each Chainlink print from its source timestamp, but prints ARRIVE ~1.45 s later (p50; p10 1.2, p99 2.3 s), while the book
  was replayed by receive time -> the study saw the price ~1.5 s before the market could. Fixed: FEED_TIME=rx (default); old
  lines superseded and redone by the hook. Effect, local 11-08..11-10, lock_m exact K: with lookahead +0.4..+5.5%/$, without
  -3.1..-4.7% at 0.05-1 s latency (+1.3% at 2 s, +5.2% at 5 s, 34-51 trades). The server's +21..+39% (11-12 07-11 h) was
  the lookahead. The paper bot itself and the 2-s tape replays were never affected (they only use what had arrived).
- 11-12 Experiments on the recordings, all DEAD: maker bid on a lock (fills win 48-67%, -28..-38%); nested 5m/15m windows
  (riskless in 9/463 pairs, cents); post-end sniping (no winner ask < 0.99 after end + 2 s); flow filter (server flow_v3 did
  not replicate); late favourite on the server sample (-31..+5%).
- 11-12 New lead: RTDS also carries Binance prices (topic crypto_prices, btc eth sol xrp doge bnb) that arrive ~0.43 s after
  their timestamp vs ~1.46 s for Chainlink; Binance returns correlate +0.3..+0.44 with Chainlink's same and next second.
  Test: lifetimes FEED_TIME=bn (last received Chainlink print x Binance move since its timestamp).
- 11-12 13:00 Binance nowcast replay (20 local hours, lock_m exact K, cap 0.97): bn +1.8/+2.0/+3.4/+4.6/+3.7/+5.5/+5.0%/$ at
  0.05/0.1/0.25/0.5/1/2/5 s vs rx -3.1/-4.0/-4.7/-4.0/-3.6/+1.3/+5.2 (~75 trades each; a hint). Paper rule lock_b live from the
  next part; server runs bn per hour into lockm.jsonl. End-second check: winner asks <= 0.95 in the last 6 s exist only in
  windows that finished < 1 bp from K (genuine coin flips), so nothing free at the end either.
- 11-12 Options-implied fair value (new, options_probe.py): Deribit public API works from Actions. 552 BTC/ETH price markets
  (hourly/daily above, below, between buckets, touches). Daily/weekly within +-1c of the options median; tails 1-2c rich;
  ETH 2,000-2,100 bucket 3.5-7c cheap on all 6 dates (model 0.59 vs ask 0.52 tomorrow); long-dated far-OTM YES rich
  (BTC 150k by end-2027: 0.21 vs 0.06). Tracker every 2 h with paper buys at >= 4c and a Brier log.
- 11-12 17h cycle 1: young NO history at executable prices (young_exec_history.py, data/research/young_exec_history.json):
  path questions +16%/$ at the real +10.5c NO spread (138 events), fixed-date -31% (32), completed 2026H2 path -6.6% (34).
  Next up: N2 box-office census (closed markets, Fri 12:00 UTC price vs preview multiplier).

## 11-12 21:00 cycle 2
- Box office census (134 films): preview momentum dead (placebo +8.4% > signal +4.7%); Saturday favourite +2.9%/$ at +2c,
  first half -2% -> paper tracker boxoffice_paper.py at real asks (hourly, Sat 14-02 UTC). Ideas N3 (later weekends), N4 (music charts).

## 11-13 01:15 cycle 3
- Earnings beat census (470 markets): calibrated (0.734 priced vs 0.737 won) -> DEAD, lesson 13. Scheduled-data favourites: same as converge,
  PARKED. Weather Brier still worse than market (31 events, one day). Paper lock_x 15/16 +12%, lock_mv 19/19 +8% but 1-2 days only.
  Next: N7 (lock_x ∩ lock_mv), N8 earnings-call mention census, Saturday box-office paper.

## 11-13 05:10 cycle 4
- Charts census (208 Netflix/App Store/Spotify/Billboard events): favourite 0.60-0.85 +5.6%/$ at +2c (49 events), Netflix +6.7% (72), App
  Store -6.2% -> paper charts_paper.py. lock_m cool-down dead (no loss clustering). lock_mv's 21/21 came on days when every lock won.
  Next: N11 FlixPatrol nowcast if the Netflix paper holds; N8 mention census; N3/N4 still queued.

## 11-13 09:10 cycle 5
- Mention markets (N8): YES rich; earnings-call NO on words 0.10-0.40 +15..+17%/$ on 27-29 calls (history, last prices) -> paper
  mention_paper.py. lock_m 15m +14% vs 5m +7% on the websocket sample (25 end-times) -> read-out. W2 same-day 'dead bucket' flags were a
  timestamp bug (reportTime), fixed. Next: mention paper spreads, W2 recount, Saturday box office.

## 11-13 13:15 cycle 6
- Slow paper had not pushed since 09:14 (mention files missing from the Save step) - fixed. lock_mv first loss (25/26 +1.8%). Order-book
  time-of-day test (N15): asks of slow favourites lowest 04-05 UTC but only by 0.2c; 1c dips revert +1c in 24 h -> N15b converge dip entry.
  N16 tweet-count markets: books tight in the last hours. Next: verify slow push, box office Sat, mention scan coverage.

## 11-13 18:10 cycle 7
- Touch ladders (N17, 1,228 'hit' events): YES rich on last prices (0.27 priced -> 0.17), NO +9% at +2c but the real NO spread early in the
  week is +13c -> DEAD as taker; maker variant N17b. lock_mv adds nothing outside lock_x (x∩mv 12/12, mv-only -3%). New: N18 Rotten Tomatoes.
  Next: weather Brier via Actions, lock_x/lock_p to 30 end-times, box office Saturday.

## 11-13 21:40 cycle 8
- W1 weather model DEAD (Brier .0732 vs market .0635, 66 events); lock_mv DEAD (outside lock_x -6.4%); RT census: near-certain 39/39 +3.9%
  (26 films) but ~5 events/month -> PARKED into N19. lock_p at 32 end-times +8.1%, week mark 11-17. New: N19 running tallies, N20 UMA window.

## 11-14 01:40 cycle 9
- N20 UMA window DEAD (winners at 0.999 in the last 2 h, 17/19 non-sports; recorder coverage thin). New N21 lock_be: lock signals on BTC/ETH
  +3.5%/$ (179 windows) vs alts -3.2% (265) in sample -> forward read-out only. N22 Argentina CPI vs Buenos Aires City CPI (READY).
  lock_x 18/16 +9.2%, lock_p 39/35 +6.8% (34 end-times), lock_early -0.6% near its kill rule. Next: lock_p week mark 11-17, LP-1 48 h read.
