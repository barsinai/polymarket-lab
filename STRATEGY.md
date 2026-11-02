# The strategy (living document)

_Last updated 2026-11-02. Plain-English summary of what we are doing, why, and what would make
us stop. Details and evidence live in `research/QUEUE.md` and `results/`._

## What we do

**We are paid to provide liquidity.** In each chosen market we keep one offer to buy and one
offer to sell, close to the current price. Income comes from three places:

1. **Polymarket liquidity rewards** - a daily pool per market, split among people whose offers sit
   close to the price. This is most of the expected income.
2. **The gap** - when both our offers are taken we buy slightly below and sell slightly above.
3. **Maker rebates** - Polymarket pays makers 15-25% of the fee the other side paid.

We do **not** try to predict outcomes. Two days of tests on 630,000 past markets showed that
Polymarket's prices are accurate enough that simple price patterns and price-based models have
no edge once the data is selected fairly.

## Why this should work, and the evidence so far

- Polymarket pays ~$585k/day in rewards across ~15k markets. Many pools go to thin markets with
  almost no competing offers.
- In markets more than a week from their end, trades are *noise*: after someone takes an offer,
  the price tends to drift back (-0.2c over 24h, from 2.8M trades). That is the habitat where a
  market maker earns the gap instead of losing it.
- Paper trading (real books, real trades, pretend offers) over the first day: estimated rewards
  about ten times larger than trading losses.

## The rules (version 2, running as four variants)

- Only markets with a reward pool, a book no wider than 4c, mid-price between 10c and 90c,
  **more than 7 days** from their end, no game within 6 hours, no data releases / rate
  decisions / "between X and Y" number questions.
- Rank by expected reward per dollar, divided by recent price movement. Quote the best 40
  (variant "wide": the best 200 at minimum size).
- Offers at mid +-1c (variants: +-2c, reward-zone edge), size 200 shares per side.
- Re-quote every 10 minutes. Lean offers against what we hold; stop adding above 2x size.
- Keep working off positions in markets we leave. Cap exposure at $300 per Polymarket event.
- Stand aside after three big (>= $500) one-directional trades in a row.

## What would make us stop or change

- Trading losses persistently above ~50% of estimated rewards.
- A single news jump costing more than two days of rewards in one market (event cap too loose).
- Live payouts (when we test them) below one third of the estimate.

## What is NOT verified and only a live test can verify

- The exact reward share Polymarket would pay us (our formula follows their docs, simplified).
- Queue position: in a real book, orders ahead of ours fill first.
- Our own effect on the markets we enter.

## Go-live checklist (none started)

1. One full week of paper results across the four variants; pick one.
2. Legal/tax check for Israel (the user's call; local advice).
3. Always-on server (not GitHub jobs), API keys, kill switch, daily loss limit, position caps.
4. Pilot with money the user is fine losing entirely (a few hundred dollars), 2-4 weeks,
   compare real payouts with the estimate.
5. Scale only if the pilot matches the paper numbers.

## Ideas tested and dropped (so we don't redo them)

Price-pattern bets (fade jumps, long shots, favourites), ML models on price features, trade-flow
and "smart wallet" features, question-template effects, soccer draws/unders, crypto fair value,
weather forecasts, weather known-outcome, date-ladder logic arbitrage, multi-option sum
arbitrage (all either no edge, bot-dominated, or an artefact of selection bias).
