# Fast Up/Down bot - design (11-08 evening, approved for build; paper first, live only with explicit OK)

## Why it might work now (measured)
- Polymarket's CLOB websocket delivers book events to Helsinki 15-18 ms after the server stamp (369k events):
  the matching engine is in Europe. Reaction budget from here: ~20 ms in + ~5 ms compute + ~40-60 ms order RTT.
- Our view of the outcome is exact (feed TWAP == official final 1,638/1,638; price to beat 639/639).
- The crowd sees the Chainlink stream 0.8-1.9 s after the oracle stamp (RTDS delivery); a direct exchange feed
  leads it by ~1 s. In the last 60 s that lead sharpens the "locked" call.
- What killed the slow bot: profitable asks vanished within 2 s; 3 of 10 episodes in the first websocket hour
  lived < 150 ms, 7 persisted (those were the losers). Open question for the full-day recording: the share of
  profitable episodes that live >= 80 ms.

## Architecture (one asyncio process on the Helsinki server)
1. Feeds: RTDS (Chainlink price + TWAP60, 8 coins) and CLOB market websocket for the active window tokens
   (subscribe ~150 s before each window's end); optional direct Binance/Coinbase websocket for the 1 s lead.
2. State per window: K (official price to beat via Gamma, re-read until present; fallback feed TWAP at start),
   A (mean of feed prices since end-60), sigma (30 s returns, per-asset floor), local books.
3. Decision on EVERY event (feed tick or book change), < 1 ms: p_side, z; rule = lock (z >= 2.5, 0.50 <= ask
   <= 0.97, last 60 s) and riskless pairs (sum + fees <= 0.995). Everything else stays off.
4. Order path: pre-signed ladder per token (prices 0.50..0.97 step 0.01, size $20, FAK/immediate-or-cancel,
   expiration 30 s) refreshed when the window enters its last 150 s; warm HTTPS session; on signal POST the
   ladder order at min(ask, 0.97) -> fills at the best available asks up to that price (we do not chase a
   single quote). Paper mode: do not POST; instead record the signal time and let the recorder show whether
   the ask survived >= REACTION_MS (80 ms) - that is the realistic paper fill.
5. Risk: max $40 per window, max 3 open windows, daily loss stop $15, STOP file, no orders outside the
   last 60 s, never without k_src in (ptb, twap, chainlink) and a live feed (< 3 s old).
6. Logging: every signal with ask/size at signal time, ask at +80 ms/+250 ms/+1 s (from the recorder),
   result, P&L under each reaction assumption.

## Build order (11-09)
- a) fastbot.py paper mode (feeds + decision + signal log), running beside the current bot (separate process).
- b) order-path latency probe on the server (authenticated read-only call, keep-alive) - needs the pilot
  secrets, so it runs as a step in the fast_paper workflow once, dry.
- c) replay of 1 day of recorder data under the realistic-fill rule; go/no-go on live.
