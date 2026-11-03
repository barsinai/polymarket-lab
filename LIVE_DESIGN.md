# Live market-maker design (research only - nothing here places orders)

_Drafted 2026-11-03 from Polymarket's documentation (trading quickstart, market-makers/trading,
fees, maker rebates, liquidity rewards). To be verified against the live API in dry-run mode
before any order is sent._

## What Polymarket gives us (facts gathered)

- **SDK:** official Python package `polymarket` (`AsyncSecureClient.create(private_key=..., wallet=...)`),
  env vars `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_WALLET_ADDRESS`. Funding is **pUSD on Polygon**.
- **Order types:** GTC (resting), GTD (expires), FOK/FAK (immediate). **Post-only** exists:
  the order is rejected if it would take liquidity. We use post-only GTC/GTD for everything.
- **Batch posting** of several orders; each result must be checked separately.
- **No order edits:** cancel and replace. **Cancel-all** exists; after any reconnect, fetch open
  orders and recent trades before quoting again.
- **Per-market rules:** minimum price increment (tick, 0.01 or 0.001) and minimum order size
  (5 shares); read them before quoting. Markets must be "accepting orders".
- **Inventory mechanics:** buys use pUSD; sells need the outcome tokens. Buying No at 0.48 is
  the same as selling Yes at 0.52, so a two-sided quote is a Yes bid plus a No bid (both pUSD).
  Holding Yes+No of one market = $1 and can be merged back to pUSD.
- **Fees:** makers pay nothing; makers earn 15-25% of taker fees as rebates (daily, min $1).
- **Rewards:** per-market daily pools, sampled every minute, two-sided scoring, paid daily
  (min $1 per market per day). Read via the sampling-markets endpoint we already record.
- **Streams:** a market stream (books) and a user stream (our orders / fills).

## Architecture (small, boring on purpose)

```
 [always-on VPS, ~$5/mo]
   quoter.py  (one process, asyncio)
     - loads config: variant rules (from paper_mm2), limits, kill switch file
     - market stream  -> local book cache (mid, best bid/ask, depth)
     - user stream    -> fills -> inventory, cash, P&L ledger (sqlite)
     - every 10-30 s: for each chosen market decide desired quotes; diff vs open orders;
       cancel/replace only what changed (post-only GTC)
     - every 10 min: refresh universe (rewards table, jump filter, event caps) - same code
       as the paper trader, so paper and live stay comparable
     - every hour: write a report (same shape as data/paper_mm2/report.json) + push to repo
   watchdog (systemd timer): if quoter is dead or stale > 2 min -> cancel-all via a tiny
   independent script, alert
```

## Safety rules (hard limits in code, not in a config someone can forget)

1. **Kill switch:** a file `STOP` in the working dir -> cancel-all, exit. Also a chat command later.
2. **Daily loss limit:** realised + unrealised trading P&L below -X for the UTC day -> cancel-all,
   stop quoting until a human restarts. X = 3% of the pilot capital.
3. **Per-market cap** (1x quote size of inventory), **per-event cap** ($150), **total capital cap**.
4. **Post-only always.** Any order that would cross is rejected by the exchange, not us.
5. **Staleness guard:** no book update for a market in 60 s -> cancel its quotes.
6. **Reconnect protocol:** on any disconnect: cancel-all, re-sync open orders and fills, resume.
7. **Dry-run mode:** identical code path with `send=False`; logs the orders it would send and
   validates them against tick/min-size rules. Runs for 48 h before the first real order.
8. **Secrets:** private key only on the VPS, in an env file readable by one user; never in git.

## What the pilot must measure (2-4 weeks, a few hundred dollars)

- Actual daily reward payouts per market vs our estimate (the single most important number).
- Actual fill rate vs the paper trader's (queue position effect).
- Rebates received.
- Trading P&L per market, with the same breakdowns as the paper reports.

## Ledger (tax requirement, see TAX_ISRAEL.md)

Every fill, reward payment, rebate, deposit, withdrawal and USDC/pUSD conversion goes into an
append-only sqlite table with: UTC time, market, side, shares, price, USD value, counterparty
type (fill / reward / rebate / transfer), the Bank of Israel USD-ILS rate of the day, and the
on-chain tx hash where there is one. Exported monthly as CSV. This is what lets an accountant
argue "business income" (net, with losses deductible) rather than "gambling winnings" (gross),
and what the bank will ask for when money comes back.

## Open items before building

- Confirm Israel legality/tax (user).
- Confirm the SDK's limit-order and post-only calls and the user-stream message format in
  dry-run mode (no account needed for public streams; account needed for user stream).
- Decide the pilot variant from the paper comparison (end of this week).
