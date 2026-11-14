# Lessons from failures (read before proposing an idea)

Each lesson is a pattern behind several dead ideas. A new idea must say which lessons it is exposed to and why it
survives them. Add a lesson whenever an idea dies for a reason not already here.

1. **Latency edges belong to bots.** Fast crypto fair value (11-01), BTC-leads-alts, jump chaser, cheap lock asks
   that vanish in 0.04-0.11 s: anything that wins only by seeing a public price first is gone before a 2-s REST loop
   (and probably before a websocket loop) can act. Ask: who else sees this signal, and how fast?
2. **A cheap price that survives is cheap for a reason.** Late favourite at the ask (-36..0%), maker bid on a lock
   (fills only from sellers who know better, 48-67% win), after-end snipes. Resting orders get filled by the informed;
   prices that sit still are usually right.
3. **Mids lie; trade at executable prices with fees.** Late favourite +10 pts on mids was the spread; history
   prices are often mids of empty books (young markets). Every backtest uses the ask/bid that existed then + 0.07p(1-p).
4. **Lookahead hides in timestamps.** The +21..+39% websocket replay used Chainlink prints at their source time, 1.45 s
   before they arrived; 11-01 crypto fair value used exchange prices up to 1 h fresher than the market price. Always
   replay by RECEIVE time and ask "could I have known this then?"
5. **Small samples are lumpy and regress.** lock_m: one hour -$74 next to seven positive ones; flow filter +4.2 local
   became -8.3 on the server; 17/17 out of sample means little when trades cluster in a few windows. Count independent
   events (windows, days, underlyings), not trades; replicate on a second period before believing.
6. **Correlated positions are one bet.** 16 options paper positions were ~2 bets on ETH staying above 1,900. Group by
   underlying/date before counting edge or risk.
7. **Big models on market data find nothing the market doesn't know.** Ridge with 45 features, 39k-feature sparse
   ridge, template feature: log loss equal to the market. Edges come from outside information or structure, not from
   fitting the price history.
8. **Riskless structures exist but are cents and tiny size.** negRisk sums, date ladders, nested windows (9/463,
   <= 32 shares). Worth an alarm, not a strategy.
9. **The market beats a weaker model.** 2-day-old deterministic weather forecast lost (Brier .199 vs .164); 5m window-
   start model lost even at 270-300 s. Only bring a model that is clearly better informed than the crowd (fresher data,
   the exact resolution rule, a deeper market like options).
10. **Infra bugs masquerade as results.** Wrong K (price to beat), code not picked up until the next publish, memory caps,
    missed snapshots during outages. Before reading a number, check the run actually used the code and data you think. Also check which clock a timestamp is (11-13: aviationweather 'reportTime' is the nominal hour, not the observation time).
11. **Early settlements are a biased sample.** Path questions ('hit X', 'announced by') resolve YES the moment they happen
    and NO only at the end; the first paper settlements and the newest history half are therefore YES-heavy (young NO: 0/9
    in paper, 2026H2 history YES 36-39%). Read a tracker at its end dates, or compare only markets that are all finished.

12. **Run a placebo window.** A 'news move' rule on hourly history (box-office preview momentum +4.7%) did as well on a window with
    no news (+8.4%) and flipped sign with the entry hour. Before believing a reaction effect, test the same rule where there is
    no news and at neighbouring clock times; an effect that is not specific to the news is noise in the price series.

13. **A public base rate is already in the price.** Earnings 'beat' markets (470): priced 0.734, resolved 0.737. When the edge is a fact
    anyone can look up (beat rates, seasonal averages), assume the crowd has it; bring information that is fresher or per-case.

14. **Our own machine is part of the data.** The server's websocket lock replay said +8..+11%/$ for two days; all of it came
    from windows that ended while our hourly hook ran a heavy replay on the same 927 MiB box (4.8 cheap-lock trades per
    end-time at +14..+20% vs 1.4 and ~0% while the bot ran). The recorder fell behind, stamped book records late, and the
    replay bought asks that were already gone. Tell-tales: an opportunity rate that depends on OUR schedule, and 'cheap'
    prices that survive R = 0.1 s and R = 2 s alike. Split every replay result by our own activity (bot up/down, jobs running)
    and by recording lag (rx - exchange ts) before reading it.

15. **Two calm weeks are not a sample for a tail strategy.** Last-day favourites 0.95-0.99 won 167/167 in the 15-min books (10-31..11-13,
    no war news) and lost 11 of 369 over Jun-Nov (August: 5 losses, -11.8%: last-day war events). Near-certain strategies need the
    bad months in the sample; read them over a year or not at all.

16. **Never select a history by FINAL volume** (11-01, again 11-13): upsets and late drama attract volume, so the sample is full of
    them. Inside MLB the favourite's edge falls from +7.9 to -4.3 pts from the lowest to the highest final-volume tercile; in leagues
    where every game clears the bar the market is calibrated. Select by what was knowable at the entry time, or use leagues/markets
    that all pass the bar.

17. **On Polymarket the passive side pays the informed side** (11-14, public trade tape: 5.5M taker trades, 49k markets, 12 weeks).
    Taker entries under $10 lose 1.3 points per share [-1.5, -1.2], $200-1,000 win +1.2 [+0.6, +1.9]; taker P&L after fees is
    +2.7% of cost in mention [+1.4, +4.0], +3.7% movies, +1.6% youtube, +0.2% weather, -1.6% politics. Makers earn the spread from
    small orders and give it back, and more, to the few who know something. 'Be the house' (resting quotes, reward farming, combo
    quoting) is the losing seat unless the reward is larger than that loss - the opposite of Kalshi. Matches our pilot and 6 paper MMs.

18. **A default listing can hide the winners.** The combo positions endpoint returns OPEN + RESOLVED_LOSS unless each status is
    asked for; every wallet looked like -100%. Before reading any wallet table, check that both sides of the book add up to about
    minus the fees.

19. **Per-$ returns are a long-shot lottery; measure edge in price points per share** (win - price - fee), clustered by event.
    'Follow sharp wallets' was +9.6% per $ and -1.4 points per entry on the same trades.

20. **Never set a 'fair value' from priors without reading the news.** LP-1 v1: I put Jensen Huang -> SpaceX at 1% while a November
    story had the market bidding 10-21c; the paper MM then 'earned' +$437 from that and from hourly re-fills against the same
    resting bids (no inventory cap).

21. **One snapshot is not persistence.** 'Reward pools nobody quotes' came from one screen and a 2-h recheck; in the paper run 98
    of 127 quoted markets had a competitor inside the band within 15 h. Measure 'unclaimed' as a duration over days.

22. **A bootstrap interval does not protect a rule found by looking.** 'Trades >= $1,000 win +6.4 points [3.2, 9.9]' (61 events,
    a hash SAMPLE of 6 categories, threshold and categories chosen after seeing the table) became -1.3 [-3.9, +1.2] on ALL events
    of the same six weeks and -1.7 [-5.8, +1.6] on 13,002 orders / 968 events. Heavy-tailed event sums make the interval too narrow
    and the forking paths are not in it. Before building: all events, a second period, and categories never looked at.

23. **The weighting decides the sign - simulate the fill, not the average.** Same tape, takers buying favourites at 0.95-0.98:
    per market side the maker who sold to them earned +1.8 points; per print he lost 1.5; a resting bid pegged to the last print
    lost 1.8 [-2.6, -0.8]; a live-pegged bid got -0.1 [-1.0, +0.9]. Choose the unit by how the strategy would really be filled
    (one fill per market, at the price that existed when we could act) and replay the sequence.

24. **An edge that is in one half and not in the other is gone.** Mention markets, buy NO at <= 0.50 at the first real fill:
    +16.9 points [13.2, 21.0] in Aug 17 - Sep 30, +0.8 [-3.0, +4.2] in Oct - Nov. The 12-week average (+9.3 [6.4, 12.3]) would have
    looked like a discovery. Always print the halves and the weeks before the total.

## Where edges plausibly still live (derived from the above)
- Information the crowd processes slowly and bots don't cover: resolution-rule details (exact station, exact candle,
  rounding), public running tallies, scheduled data with good nowcasts, slow non-sports questions.
- A deeper market pricing the same thing (options vs crypto price markets, Pinnacle vs sports) - only where the
  Polymarket book is thin and nobody arbitrages it.
- ~~Being paid for patience on near-certain outcomes~~ - as a TAKER this is dead (11-14 tape: buying at 0.80-0.995 loses 1.1-2.8 points
  per share after fees in every category and month, 4,000+ events). Liquidity rewards: only where the pool beats lesson 17.
- Our own information in a niche where informed takers visibly win and the input is text or a public number we can read
  (mention markets, box office / charts, model leaderboards): the tape says skill is paid there (lesson 17), copying is not.
