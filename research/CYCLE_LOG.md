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

## 11-12 20:10 UTC check-in (main session)
- Weather W1 scored at settlement (research/slow/weather_score.py, first snapshot ~1 day ahead, 17 events / 187 buckets,
  all Asia 11-12): Brier model 0.0741 vs market 0.0685 - the market is better; winning bucket model 0.195 vs market 0.302
  (model too spread). Paper +$140 is mostly one 6c YES (luck, not skill). Same as the 11-01 prior (LESSONS 9). Keep
  scoring 3 more days (independent weather days, not cities); kill W1 if Brier still worse on 60+ events.
- Dead buckets (W2): London 7C bid 6.5c at obs max 8, NYC 54-55F bid 2.1c at 55.9 - not settled yet (resolve with the
  official source next day); if they lose, a same-day dead-bucket NO is near-riskless but size is a few $.
- Server websocket lock study, 30 h common hours: rx +4.6% (0.1 s) .. +6.6% (1 s), bn +4.7 .. +7.6%; 7 of 30 hours negative.
  The REST paper lock_m at the same time: -0.5% on 114 trades -> the gap between websocket-speed and our 2-s loop is the edge.

## 11-12 21:00 UTC cycle 2 (scheduled)
- Read-outs: server websocket lock_m (lockm.jsonl, 29-30 h, unique windows, flat $10 no fee): rx 250 trades +7.5%/$ at 0.1 s,
  bn 227 +7.5% (1 s: rx +8.1, bn +9.6) - the nowcast still adds ~nothing at 0.1 s; paper (2-s bot) lock_m 117 93.2% -0.4%/$,
  lock_x 10 9 won +6.9%, lock_mv 10/10 +4.9%, lock_b 3/3, lock_early unchanged 32 +0.9%. Young NO 12 settled 0 won -$120 (early
  path touches, LESSONS 11; decide at end dates). Weather 35 settled +$140 (one 6c YES); Brier model .074 vs market .069 unchanged.
  Converge 1/1, 91 open. Options 26 open, 0 settled. Sharp 0 positions.
- Test (N2 box office, research/slow/boxoffice_census.py via run_script, 619 markets / 134 films / 78 weekends 2024-02..2026-03,
  hourly last prices + c cost): Brier Thu22 .103 / Fri18 .077 / Sat18 .042 / Sun18 .015.
  (B) preview momentum DEAD: +4.7%/$ at +2c on 111 films, but placebo (no-news window) +8.4%, entry hour flips the sign -> lesson 12.
  (C) Saturday favourite 0.80-0.97 at Sat 14-02 UTC: 95.5% won at 0.91, +2.9%/$ at +2c, 54/60 weekends >= 0, stable across
  Saturday hours; 2024..2025H1 -2%, later +6..+8%. Real spread unknown -> paper boxoffice_paper.py (hourly, Sat 14-02 UTC, real
  asks, $10) added to spike_paper.yml. First entries Sat 11-14 if box-office markets are listed.
- New ideas: N3 later-weekend brackets (adjacent); N4 music chart markets vs daily charts / projections (outside the box).
- Health: fast paper 20:45, slow 21:05 OK. pilot-log combos AttributeError is the old 16:32 log (fixed in cycle 1; the log is only
  copied when the pilot job saves). Pilot STOP, no orders. No MemoryErrors.
- Next: N3 census (cheap rerun); first Saturday box-office paper; lock_x/xk read 11-13; converge + young first end dates 11-13.
