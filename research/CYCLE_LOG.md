# Cycle log (newest at the bottom)

- 11-12 16:00 UTC (setup): LESSONS.md + CYCLE.md written. State: lock_m server rx +7..8% / bn same (8 h, ~50 trades,
  lumpy, pooled with local ~0); options paper 16 positions (~2 independent bets); weather 270 open, 0 settled;
  converge first settlements 11-13. Next: first scheduled cycle.

## 11-12 17:10 UTC cycle 1 (scheduled)
- Read-outs: paper lock_m 114 trades 93% -0.5%/$; lock_early 32 trades 93.8% +0.9%/$ (one -$19 day; kill at 50 if <= 0);
  lock_x 8 trades 7 won +8.1%/$ (n small); lock_mv 8/8 +5.2%; lock_b 1 trade. Server websocket study (lockm.jsonl, 21 h,
  deduped by window): rx 191 trades 88.5% +9.1%/$ at 0.1 s, bn +9.8% -> the Binance nowcast adds ~0.7 pts; the edge
  is at <= 0.1 s, where the 2-s bot is never first (LESSONS 1). Weather W1 day 1: 31 positions / 15 Asian events +$139,
  $78 of it one 6c YES. Converge 1/1 +$0.78 (91 open). Young NO 0/9 -$90 (early-settlement bias, see below).
  Sharp: no position (lines tight). Options: 21 open, none settled.
- Test (adjacent): young NO at executable prices on history (research/slow/young_exec_history.py): real NO ask = mid +
  10.5c; path questions +16%/$ (138 events), fixed-date -31% (32); completed 2026H2 path markets -6.6% (34 events) vs
  +29..31% earlier halves. Not dead, not good: decision at the end dates (11-30). New lesson 11 (early settlements biased).
- New ideas: N1 young NO path-only + spread cap (adjacent); N2 box-office opening weekend vs Thursday previews (outside).
- Health: fast paper 16:32, slow 16:41 OK. combos/sample.py crashed every hour (outcomes is a dict) -> fixed. pilot STOP
  mode, no orders. smoke.py UnboundLocalError when the feed is unreachable (GitHub runner, 14:37) - cosmetic, noted.
- Next: N2 census of closed box-office markets; read young at 11-13 end dates; lock_early at 50 trades; weather day 2-3.
