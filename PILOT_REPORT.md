# Live pilot, 2026-11-05: result and decision

Real money, real orders, 14:51-20:12 UTC (about 5.5 hours of quoting at minimum size, 8 markets at a time).
Paused with STOP at 20:12 UTC. All positions closed or merged back to cash by 06:00 UTC on 11-06.

| | Model estimate | Actual |
|---|---|---|
| Liquidity reward (paid by Polymarket for 11-05) | $11.51 | **$2.36** (spread over 40 markets) |
| Trading result (our own 21 maker fills) | about -$4 | about **-$18** |
| Account | $238.79 at start | **$224.06** at the end, all cash (-$14.73, rewards and a $1.20 credit included) |

## What happened
- Reward share was a fifth of our estimate. The estimate takes the competitors' depth in the book at quote
  time; in practice our small orders earned a much smaller share of each pool.
- Losses came mostly from three markets (two 2-year Treasury yield questions, Israel coalition): bought, the
  price kept falling, sold to exit, about -$15 together. The other fills were roughly flat.
- Bookkeeping bugs found and fixed during the pilot: the positions feed listed 1 of 5 positions (valuation
  now from exchange token balances); the trade log recorded whole matches instead of our share (now the
  maker_orders entry with our wallet); deposits counted as profit in the daily-loss check (now corrected
  from the activity feed).

## Conclusion
At live reward rates the strategy loses: rewards about 1/8 of the trading loss. Even with trading losses back
to the simulated level, a 5x reward shortfall does not close. The paper market makers overstate rewards in the
same way, so their positive numbers should not be read as evidence of profit.

## Options
1. Stop and withdraw (recommended).
2. One more narrow test: 2-3 calm markets, wider offers, no macro or political-event markets, 1-2 days.
3. Keep the pilot paused; continue research on paper with the reward model recalibrated to the actual payout.
