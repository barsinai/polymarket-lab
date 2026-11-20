# Idea barrel

Rule: always 3+ ideas in TESTING, the next ones ranked in READY. Every idea gets the cheapest decisive test first
(history or replay), then a paper tracker with executable prices, then (only with the user's explicit OK) a small live test.
Status: TESTING (paper/backtest running) · READY (next up) · PARKED (needs something) · DEAD (killed by data, with the number).

## TESTING
| idea | why it could work | test | started | read-out |
|---|---|---|---|---|
| LP-1: sole liquidity provider in UNCONTESTED reward markets (quote two-sided at minimum size around a fair price we estimate) | Polymarket pays $121k/day of liquidity rewards; 837 of the 1,487 largest pools checked (>= $10/day, $22k/day in total) have NO quote within the reward band (empty books, median spread 0.65), and stay that way (94% still empty 2 h later; current pool in place a median 6.4 days; e.g. $250/day Jensen Huang/SpaceX, $200/day Daft Punk/Coachella, GTA VI Metascore 99 - unchanged since 11-06). By the published rules a sole two-sided maker gets the whole pool. Why unclaimed: you must know the fair price of obscure questions (a bot quoting the empty book's 0.50 mid is wiped out). Contested markets are the opposite: paper MMs lose 5-7% of fill notional and the pilot was paid 1/5 of our estimate -> all 6 paper variants -$90..-730/day | lp_screen.py (pool vs volume vs competition, all reward markets). PAPER (user asked for no-money first, 11-13): lp_paper.py hourly in the slow job, the exact strategy: enter only where nobody quotes inside the band (formula share >= 50%); fair = researched long shot / near-certainty (data/slow/lp_fair.json) or the middle of a real two-sided book (spread <= 20c), never an empty book's stale displayed price; quote the WIDEST two-sided band that still scores (half-width just under the max spread: alone = 100% at any width), minimum size; re-centre on the size-cutoff-adjusted midpoint of the whole book (others' orders can move it -> silent zero); leave after 2 runs with a competitor inside the band. Start 18:43 UTC: 38 markets (29 book + 9 long shots), pools $3,219/day, $982 of quotes; measures fills two ways (public taker trades that would have hit us; pessimistic: the price moved through our quote = full size taken), competition arrival, and the formula reward (an UPPER bound: the payout itself needs real orders). Read: fills/losses per $ vs pool per $ after 3-5 days. 11-14 16h (c13, v2 8 runs / 0.25 d): formula reward $290 (upper bound), pessimistic fills 56 -$138, 78 of 97 markets saw a competitor; worst losses = same-day weather buckets (Warsaw/Ankara/London) - the informed side again (LESSONS 17). c8 (20:23, 3 runs, 0.07 d): 46 markets quoted, $1,187 of quotes, formula reward $145 so far (upper bound), fills 77 trading +$10, pessimistic fills 20 -$59; 26 markets saw a competitor - too early. 11-13 21:50: user wants SIMULATION ONLY (no live test approved); report field budget_slice = the 48 h / $200 test simulated 11-14 01h (c9): 8 runs / 0.24 d: formula reward $427 (upper bound), fills +$147 / pessimistic -$145, 63 of 91 markets saw a competitor; $200 slice net +$7.2 at 100% pay, -$2.9 at 20%. 48-h read 11-15 ~19 UTC. 11-14 (deep session): v1 numbers are NOT usable - the +$437 'trading P&L' was hourly re-fills against the same resting bids (no inventory cap) plus my uninformed manual fair values (LESSONS 20); 98 of 127 quoted markets had a competitor inside the band within 15 h, 58 exits for competition, 40 pools removed -> the 'unclaimed for a week' premise was one snapshot (LESSONS 21). Restarted as v2 (inventory cap 2x size, manual fair values removed, state reset). The tape adds: passive makers lose to informed takers in these categories (LESSONS 17) - read v2 on pessimistic fills only.  **11-16 17h READ-OUT (2.3 d, 63 runs, 213 markets; after a bug fix)**: BUG - lp_paper never settled a market (the Gamma list drops closed markets; same class as options_probe 11-13), so leftover inventory in 126 markets sat at the fair price of our last run; settling 60 resolved markets and re-marking 67 open leftovers moved trading P&L from -$248 to -$436 (tape fills, 648) and from -$610 to -$760 (pessimistic, 163 fills) - every LP-1 trading number logged 11-14..11-16 was too rosy (LESSONS 28). Formula reward $1,615 (UPPER bound) -> break-even needs Polymarket to pay 27% (tape) / 47% (pessimistic) of the formula; paid 100% +$1,180 / +$855, 50% +$372 / +$48, 20% -$113 / -$437. Competitor inside the band in 188 of 213 markets (117 exits, median 2.3 h, 72 within 3 h); 92 pools removed; 2 still quoted; formula accrual $1,047 in the first 24 h -> $354 in the last 24 h. By kind: weather 68 markets formula $191 vs -$240 / -$302 (loses more than the whole pool); live count/mention/views 18: $541 vs -$231 / -$386; core 127: $884 vs +$35 / -$73 (48 of them still hold open inventory, not final); forward core 32 markets / 1.7 d: $156 vs +$29 / -$20. The $200 / 48 h slice (8 markets): formula $93, -$37 / -$69 -> +$57 / +$25 if paid in full, -$18 / -$50 if paid 20%. VERDICT told to the user: the 48-h / 5-market live test as proposed is NOT worth his OK (premise 'nobody quotes' failed; the test would be mostly weather/count pools). Next, in order: (1) core bar 11-18..19 (no action); (2) proposed, needs his OK because it uses the account key: a READ-ONLY query of our own reward history (CLOB GET /rewards/user/markets?date=, L2 auth) for the pilot days = what Polymarket really paid per market vs our formula, no orders; (3) only if both are good: a few-hour, 3-5 core markets, min-size live check watching GET /rewards/user/percentages. Nothing live was started. | 11-13 11-14 21h (c14, 13 runs / 0.42 d): formula $502 (upper bound), pessimistic 78 fills -$204, trade fills 236 -$64; 100 of 121 markets saw a competitor. Split (lp_fill_split.py, in-sample): weather same-day 36 markets formula $100 vs pessimistic -$167 (fills -11.5% of notional), the rest 85 markets $401 vs -$37 (fills +0.3%) -> N35; report now carries by_kind with a forward block (opened >= 11-14 21:00). All fills so far are Saturday -> N33 clock split not readable yet.  11-15 08h (c17, 26 runs / 0.92 d): formula $1,009 (upper bound), trading -$262, pessimistic 104 fills -$425; 137 of 155 saw a competitor. forward_other 15 markets: formula $120 vs pessimistic -$145 (two MrBeast day-1 views buckets -$65 / -$56 realistic) - N35 failing so far; forward_core only 2 markets. 11-15 20h (c20, 39 runs / 1.42 d): formula $1,386 (upper bound), trading -$221, pessimistic 141 fills -$529; 157 of 178 saw a competitor, 12 still quoted; forward_other 23 markets $322 vs pessimistic -$196 (N35 failing), forward_core 9 markets $31 vs -$7. 11-16 00h (c21, 44 runs / 1.59 d): formula $1,450 (upper bound), trading -$220, pessimistic 149 fills -$557; 168 of 190 saw a competitor, 10 still quoted; forward_other 33 markets $379 vs -$196, forward_core 18 markets $73 vs -$12 (pessimistic = -17% of formula, passing so far but tiny). 11-16 08h (c23, 48-h read, 53 runs / 1.93 d): formula $1,513 (upper bound), trading -$224, pessimistic 158 fills -$566; 179 of 202 markets saw a competitor, only 7 still quoted ($471/day of pools); at 20% pay net +$78 with trade fills; forward_other 38 markets $425 vs -$197 (-46%, N35 FAILING), forward_core 23 markets $119 vs -$13 (-11%, passing, tiny); the 'uncontested pools' premise is gone - LP-1 as a whole is now only the forward_core read.| core bar 11-18..19; user's answer on the read-only reward-history query |
| Slow favourites: YES 0.95-0.98, non-sports, 3-30 d | holders sell near-certain outcomes early; the discount is a time premium | history 6,570 markets (+2%/position, 99.5%); converge_paper.py at real asks. 11-13 01h: 2 settled: UK GDP NO +$0.78; a soccer draw NO at 0.91 -$20 is a pre-filter 11-10 position (sports + below 0.95 - not the rule, LESSONS 10); 90 open, mark -$34. 11-13 17h: 4 settled 3 won -$18 (rule-conforming non-sports 3/3 +3.5%); 88 open, mark -$27 | 11-10 | first settlements 11-13 |
| lock_x (5m/15m lock + 2 s persistence + margin >= 1 bp + rem >= 6 s) with the exact price to beat | the K bug made our 'locks' wrong in knife-edge windows; exact K + persistence + margin removes them | replay 48 trades 100% +11%/$; paper lock_x / lock_x50 / lock_xk. 11-12 17h: paper 8 trades 7 won +8.1%/$ ($20) / +20.6% ($50); 11-12 alone 4/5 -$9.9 (small n). 21h: 10 trades 9 won +6.9%/$; lock_mv 10/10 +4.9%. 11-13 01h: lock_x 16 trades 15 won +12.3%/$ (12 end-times, 2 days: +$20 / +$14); lock_mv 19/19 +7.9% (14 end-times, one day) - need 30+ end-times over 4+ days. 11-13 05h: lock_x unchanged 16 (no new signal), lock_mv 21/21 +7.5% (15 end-times). CAVEAT: since lock_mv started (11-12 10:29) ALL 27 paper lock_m trades won, the 6 that lock_mv filtered out too (+6.4%) - the filter has not been tested on a losing day yet; lock_x ∩ lock_mv 11/11 +14.4% (7 end-times). 11-13 13h (c6): lock_mv FIRST LOSS (sol 5m 13:00, Down 0.97, margin 7.6 bp, 57 s) -> 25/26 +1.8%/$ (19 end-times); lock_x unchanged 16 / 15 +12.3% (no signal since 11-12 22h). 11-13 17h (c7): lock_x 17 / 16 +12.0% (13 end-times, 3 days); lock_mv 30 / 29 +2.2% (22); N7 intersection x∩mv 12/12 +13.6% on 8 end-times, mv-only 18 / 17 -3.2% -> lock_mv's value is all in its overlap with lock_x (lock_p ∩ mv identical); lock_p 36 / 33 +8.2% (31 end-times, 4 days). 11-13 21h (c8): lock_x 17 / 16 +11.9% (no signal since 13:29); lock_mv 34 / 32 -0.6%, mv-only 22 / 20 -6.4% -> lock_mv DEAD; lock_p 37 / 34 +8.1% (32 end-times, 4 days; contains all 17 lock_x trades: p∩x +11.9%, p-only 20 / 18 +3.9% on 19 end-times). lock_p started 11-10 00:05 -> a full week on 11-17: if still >= +5% on 40+ end-times, write the numbers up for the user 11-14 01h (c9): lock_x 18 / 16 +9.2%/$ (14 end-times, 3 days; new loss hype 5m Down 0.92 margin 14.6 bp at 48 s, -$7.3); lock_p 39 / 35 +6.8% (34 end-times, 4 days). Both losses since c8 are alts - see N21. 11-14 05h (c10): lock_x 18 / 16 +9.2% (14 end-times, no new signal); lock_p 39 / 35 +6.8% (34 end-times, 4 days) unchanged; lock_p_majors 13/13 +14.1%. | 11-11 11-14 09h (c11): lock_x 18 / 16 +9.2%, lock_p 39 / 35 +6.8% (34 end-times) unchanged (bot down 06:58-09:03). SPLIT BY ENTRY PRICE (lock_price_split.py): lock_p's profit is 7 trades bought at 0.52-0.74 (+$34.7, 5/7 won); its 32 trades at >= 0.80 made +$4.7 = +1.0%/$ (28 end-times); lock_x >= 0.80: 15 / 13 -3.9%. For the 11-17 write-up: the 'lock' edge is in the few windows where the market strongly disagrees, not in the 0.9x locks -> see N25. 11-14 17h (c13): lock_x / lock_p unchanged (no signal since 11-13 20:09; not a bug: lock_p_z2 fired 21 times since, max z 2.59 vs 17 before - a calm day, and none of the 3 z >= 2.5 held 2 s). 11-14 21h (c14): lock_x 19 / 17 +8.8% (15 end-times), lock_p 40 / 36 +6.6% (35), lock_p_majors 14/14 +13.2%; N25 forward >= 0.80 27/27 +5.2% (19 end-times), < 0.80 1/1. | 11-17 | 11-15 21h (c20): lock_x 19 / 17 +8.8% (no signal since 11-14), lock_p 42 / 37 +5.1% (37 end-times, one new loss), lock_p_majors 15/15 +13.3%; lock_m 204 / 186 -2.2%. N25 forward: < 0.80 6 / 2 -65.5% (5 end-times) -> N25 DEAD; >= 0.80 73 / 68 -0.1% (52 end-times) = zero. 11-16 01h (c21): lock_x 19 / 17 +8.9% (no signal since 11-14), lock_p 43 / 38 +5.1% (38 end-times), majors 15/15 +13.4%; lock_m 206 / 187 -2.8%; >= 0.80 forward 77 / 71 -1.3% (56 end-times). 11-17 01h (c27): lock_p WEEK MARK +2.2% on 53 / 46 (47 end-times) < the +5% bar -> lock_p CLOSED (DEAD); lock_x 27 / 24 +7.0% (23 end-times, needs 30+; its week mark 11-19), lock_x50 +11.0%, lock_p_majors 22 / 21 +5.4%; lock_m 238 -2.6%, lock_p_z2 280 -0.6%. 11-18 05h (c34): lock_x 34 trades / 30 end-times 31 won +6.4% (7 days) - the 30-end-time bar is reached; formal week read 11-19 (>= +5%). 11-19 01h (c39) WEEK READ: 39 trades / 35 end-times / 8 days, 36 won, +6.5%/$ (+$44) - passes the +5% letter, BUT $37 of the $44 is 3 fills bought at 0.52-0.69; the 36 fills at >= 0.80 made +1.2%/$ (-2.3 pts/share [-12.3, +5.9], 33 end-times), halves +8.8% / +4.4%, interval of the total spans zero (+0.7 pts [-9.7, +8.6]). BTC/ETH 19/19 +10.1%, BTC/ETH >= 0.80 17/17 +5.5% - a split chosen after looking (lesson 22) and N21's broader BTC/ETH forward is -2.6% on 150 windows. VERDICT: not proposable; kept running. Pre-registered forward arm from 11-19 01:00: lock_x BTC/ETH only, read at 30 new end-times: keep only if >= +3%/$ with no fill < 0.80 counted (one loss at 0.95 costs ~16 wins). 11-19 05h (c40): 41 trades / 37 end-times 38 won +6.4%/$; >= 0.80 core 38 / 35 +1.3%/$ (-1.8 pts [-11.5, +5.7]); forward arm BTC/ETH >= 0.80 (from 01:00): 1 / 1 won (needs 30). |
| N21 lock_be: lock signals on BTC/ETH only (first signal per window, any lock_* rule) | Chainlink BTC/ETH feeds are the deepest and least noisy; alt 'locks' at the same bp margin are knocked over by alt volatility and thinner books (HYPE, SOL, ZEC negative) | in-sample split of data/fast/trades.jsonl (11-07..11-14, first signal per window): BTC/ETH 179 windows 168 won +3.5%/$, 6/8 days >= 0; alts 265 / 230 -3.2%, 1/8 days > 0. Retrospective split (LESSONS 5) -> forward read-out only counts trades after 11-14 01:00 UTC: research/fast/lock_be_readout.py (no bot change) 11-14 05h (c10): forward 5 windows (all alts, 5/5 +4.9%), 0 BTC/ETH yet (night). | 11-14 11-14 09h (c11): forward BTC/ETH 1 window (+4.0%), alts 11 / 10 -1.2%. 11-14 13h (c12): forward BTC/ETH 4 / 4 +7.8%, alts 12 / 11 -1.0% (1 day). 11-14 17h (c13): forward BTC/ETH 12 / 12 +5.9%, alts 18 / 17 +2.5% (1 day) - both positive on a calm day, the split is not showing yet. 11-14 21h (c14): forward BTC/ETH 19 / 19 +5.3%, alts 21 / 20 +2.7% (1 day).  11-15 09h (c17): forward BTC/ETH 30 / 30 +5.4%, alts 35 / 31 -2.1% (2 days) - the split shows for the first time. 11-15 21h (c20): forward BTC/ETH 43 / 41 +1.7%, alts 48 / 40 -6.2% (2 days). 11-16 01h (c21): forward BTC/ETH 45 / 42 -0.8% (3 days), alts 50 / 42 -5.5% - BTC/ETH now below its +2% bar. 11-16 09h (c23): forward BTC/ETH 57 / 52 -3.2% (3 days), alts 56 / 46 -8.2% - failing; formal decision 11-21.| 11-21: forward >= 60 windows over 5+ days and >= +2%/$ |
| Young markets, NO side: stand-alone non-sports binaries < 72 h old, YES mid 0.30-0.50 | history: priced 0.425, resolved YES 0.237 (n 283) - but history prices may be mids of empty books | young_paper.py at real NO asks, $10. 11-12 17h: real NO ask = NO mid + 10.5c (median, n 36). History re-run at executable prices (young_exec_history.py, 72-h first price): path questions ('hit/by/before', 138 events) +16%/$ at +10.5c, fixed-date (32 events) -31%; BUT completed path markets started 2026H2: 34 events, YES 36%, -6.6%/$ (2025H2/2026H1 +29..+31%). Paper 9 settled 0 won -$90: 7 are one bet (stock 'hit LOW' touches, 11-12 sell-off) + 2 Jensen Huang; early settlements are YES-biased (touches resolve early). Decide at the 11-13..11-30 end dates: kill if <= 0 on 20+ events. 21h: 12 settled 0 won -$120 (all early path touches / Huang; 50 open). 11-13 01h: 16 settled 3 won -$115; path 13/13 lost (~3 independent bets: 11-09 week stock touches, Huang x2), fixed-date 3/3 won +$15; N1 spread cap <= 5c keeps 26/63 (median spread 7.5c). 11-13 05h: 18 settled 3 won -$135 (2 more path touches lost: META/PLTR 'hit LOW', Huang). 11-13 17h: 28 settled 3 won -$235; marked to now_yes incl. those ending today: 36 'hit (HIGH/LOW) Week of November 9' positions -$168 (one week; their NO ask was NO mid + 13c median), 12 'close above' +$2, 23 other -$27. N17 census: touch YES IS rich on last prices, but the +13c NO spread eats it (see DEAD) 11-14 01h (c9): 48 settled 20 won -$161 / $480 (-34%); early settlements are YES-heavy (LESSONS 11) - read at the 11-16..11-30 end dates. | 11-11 | 11-30 |
| Riskless structure (negRisk sums, ladders) at news time | dislocations appear when news hits and books are thin | arb_scan.py hourly, arb_log.jsonl | 11-11 | weekly |
| Options-implied fair value (Deribit) vs BTC/ETH price markets (above / below / between / touch) | a deep options market prices the same dates; Polymarket crowds may misprice tails and touches | options_probe.py PAPER=1 every 2 h: model + book log (Brier at resolution), $10 paper at edge >= 4c, 0.5-10 d. 11-12 14h: 16 paper positions, mostly one bet (ETH stays above 1,900 this week: market prices the dip richer than options); First snapshot 459 markets: above/below/between within +-1c (median), tails 1-2c rich, ETH ATM buckets 3.5-7c cheap on 6 dates, touches noisier (my touch model is the weakest part) 11-14 01h (c9): paper 13 settled 3 won -$89 / $130, but all on 11-12/11-13 (BTC fell; ~2 independent events, LESSONS 6); 43 open. Not readable yet. 11-14 17h (c13): 19 settled 6 won -$114, 53 open (unchanged). | 11-12 11-14 21h (c14): 25 settled 7 won -$156 / $243, 58 open - still a handful of BTC/ETH-move events.  11-15 08h (c17): 31 settled 11 won +$13 / $298 but -23 pts/share: +$177 is two BTC 'dip' long shots at 0.07/0.11 on 11-14; ex those -$144 -> N42 split. 11-15 20h (c20): 40 settled 12 won -$52 / $378, 68 open; N42 forward 0 settled (24 tails, 23 crash bets).| 11-19 |
| Box-office Saturday favourite (N2b): opening-weekend brackets, side priced 0.80-0.97 on Sat 14-02 UTC (Friday gross public) | the crowd is slow to turn Friday's number into a near-certain weekend; few traders, resolution Monday on actuals | history 134 films / 78 weekends (boxoffice_census.py, hourly last prices, +c cost): 95.5% won at avg 0.91, +4.1%/$ (+1c) / +2.9% (+2c), 54/60 weekends >= 0; but 2024..2025H1 -2%, 2025H2..2026Q1 +6..+8%. Paper boxoffice_paper.py at real asks, $10, hourly. 11-13 01h: out of window, 0 markets seen yet (first check Sat 11-14 14 UTC). 11-14 17h (c13): BUG - in window 14-16 UTC it saw 0 box-office markets while LP-1 was quoting 'Ebenezer' Opening Weekend (the 4-day end-date scan with a 4,000 offset cap is filled by up/down markets, same as converge_day). Fixed (search + tag listing first, paged scan to 20,000 as fallback); first weekend partly lost | 11-12 11-14 20h (c14): fix works - 27 box-office markets seen (search 148 / tag 118 rows), 6 open positions, median spread 7c. | 30 weekends (~7 months) - size ~$10-50/bracket |
| Ranking-chart favourites (N10): Netflix top 10 / App Store #1 / Spotify #1 / Billboard #1, event favourite 0.60-0.97, 2-24 h before end | the chart is readable (daily Spotify / App Store charts, FlixPatrol for Netflix) before the event ends; few traders read it | history 208 events (charts_census.py, hourly last prices, fees off): band 0.70-0.85 won 87-90% vs priced 0.78 (23-38 events); fav 0.60-0.85 +5.6%/$ at +2c (49 events, end-24h), +13.6% (26, end-2h); Netflix fav +6.7% (72), App Store -6.2% (37); 2025 half -5.4% vs 2026 +6.2%. Leaders >= 0.95 won only 92-96% (3-4 losses). Paper charts_paper.py hourly at real asks, $10, rules fav + tail (leader NO <= 6c). First run 11-13 05:21: 12 live chart events; fees are now ENABLED on them (history: off) and favourite books are wide (Spotify #1 bid 0.41 / ask 0.76) -> spread cap 10c + fee 0.07p(1-p); 2 positions kept (App Store #2 paid/free). 11-16 (c22): BUG - chart_events_seen = 0 in every run of the last days (the 2-24 h end-date scan with a 3,000 offset cap is filled by crypto up/down events, LESSONS 10 again); fixed with text search + paged scan to 20,000; the paper sample since ~11-13 is lost | 11-13 | 30 events (~3-4 weeks) |
| COPY-1: copy the takers with a winning record, at the real ask seconds later | The only public signal that held out of sample on the 12-week tape (5.5M taker trades, 49k markets): 666 wallets picked on the older 6 weeks kept +1.6 points per share [1.1, 2.1] (+7.7% of cost) in the newer 6; the 51 largest winners +2.7 [1.9, 3.5]. Order size alone is nothing (DEAD below). WEAK POINT: at the next same-way print by someone else (>= 60 s later, median 5 min) the follower kept only +0.5 [-0.1, +1.1] (whales 0.0) - the price moves about 1c before others trade; in thin books the winner takes the whole cheap offer (probe: MrBeast views YES bought at 0.69, next ask 0.93). Open question: does being 10-40 s behind instead of minutes keep the edge? My prior that it passes: ~30% | research/slow/follow_paper.py in its own chained hosted workflow (follow.yml, public feed + public books, no account, no orders): 148 wallets that won in BOTH halves (research/slow/follow_whitelist.json, built by tape_whitelist.py); paper-buys $20 at the best ask after their order/accumulation >= $50 if the ask is <= their price + 3c; one per market+direction+day; control group = every 5th order >= $1,000 by other wallets (back-test says ~0). Logs ask vs their price, lag, ask 5/60 min later, bid/ask 24/72 h later; data/follow/report.json  11-14 13h (c12, 1.9 h tracked): sharp 5 positions / 1 primary, control 7; sharp ask minus their price median +10.9c (p25 +3.2c) at a median 217 s lag - only 20% of sharp signals pass the +3c cap (control: 0.0c, 100%). Early sign of the WEAK POINT: the price runs before we can copy. 11-14 17h (c13, 6.1 h): sharp 36 positions / 10 primary (0 settled), control 51 / 35 (1 settled, lost); sharp ask minus their price median +4.7c (p25 +2.0c), 31% pass the +3c cap, lag 187 s. | 11-14 11-14 21h (c14, 10.1 h): sharp 58 positions / 20 primary, 0 settled; ask minus their price median +4.6c, 36% pass the cap, lag 168 s; control 7 primaries settled -3.1 pts. 11-15 21h (c20, 33 h): sharp 60 primaries, 4 settled 4/4 +39.7 pts (n=4, meaningless); control 25 settled / 12 events +0.1 pts. 11-16 00h (c21, 37 h): sharp 72 primaries (46/day), 4 settled 4/4 (n=4); control 25 / 12 events +0.1 pts. 11-16 16h (c25, 50.5 h): sharp 114 primaries, 19 settled / 13 events 16 won +6.5 pts (weather 11 settled -1.4, the rest 8 settled +17; n tiny); control 39 / 16 events +1.9 pts.  11-18 13h (c36, 94 h): sharp 69 primaries settled / 46 events +3.1 pts (+2.3 at 5 min later), control 67 / 31 +2.3; N80 tape walk-forward puts the follower's ceiling at ~+0.5 (cap <= 3c: +0.51 [0.1, 1.0]) 11-18 21h (c38, 102.6 h): sharp 74 primaries settled / 50 events +3.2 pts (+2.4 at 5 min later), control 76 / 37 +4.0 (control >= sharp); N84 tape: >= 24 h horizon only +0.57 [0.1, 1.0], no arm | FIXED RULE: sharp primary >= 300 settled, >= 100 events, >= 10 days: >= +1.5 pts with the 95% interval above 0 -> propose a small live test; < +0.5 or interval top < +1.5 -> DEAD |
| N38 LP-1 core: ex-weather AND ex-live-count/mention/views markets (report split of LP-1 v2, by_kind.core / forward_core) | the count markets are watched live by the people who trade them (Caedrel 'say X N+ times on stream', White House post counts, MrBeast views): in-sample 0.59 d count/mention 11 markets formula $65 vs pessimistic -$56 (realistic -$89, one stream market -$79); core 92 markets formula $523 vs pessimistic -$39, realistic +$30 | lp_paper.py by_kind (regex fixed 11-15 01:00, forward = markets opened after 01:00 UTC) | 11-15 | with LP-1: 11-16 (48 h), 11-19 (5 d); pass = forward_core pessimistic P&L > -25% of formula reward over 3+ days and 40+ markets; exposed to 5/22 (split chosen after looking), 17, 21 11-19 01h (c39) 5-DAY READ: forward_core 79 markets / ~4 d, formula $422 (upper bound) vs tape +$42 / pessimistic +$26 -> PASSES the bar. Caveats: formula is an upper bound (pilot was paid ~1/5 of our estimate), LP-1 quotes only 3 markets now (pools shrink / competitors arrive). Next step unchanged: the READ-ONLY reward-history query still waits for Yoav's OK (account key, no orders). |
| N42 options paper split: tails (paid < 0.20) vs the rest, points per share, clustered by coin+date | the options-implied model may be right only where Polymarket underprices crash tails (lottery buyers sell them, LESSONS 2 reversed), while its mid-range 'edges' are just the market knowing more (LESSONS 9) | research/slow/options_tail_readout.py, no bot change. In-sample (settled by 11-15 09:00): tails 5 / 2 won +28.7 pts/share (3 coin-dates, 1 positive; +$147 is two BTC 'dip to 65k/64k on 11-14' YES at 0.07/0.11), rest 26 / 9 won -33.0 pts (6 coin-dates, 0 positive, -$134). Open book: 24 of 25 tails are crash bets, 0 of 48 rest are -> the book is short a crash on one side and long it on the other; it is ONE bet on ETH/BTC direction (LESSONS 6). Exposed to 5, 6, 19, 22 (split chosen after looking) | 11-15 | forward (opened >= 11-15 09:00) at 11-19 and 11-26; rest kill if forward <= 0 pts on 8+ coin-dates; tails need 20+ coin-dates (months) 11-19 01h (c39): forward rest 12 / 10 +13.1 pts on 6 coin-dates (needs 8+ to decide; in-sample rest was -30.1), forward tails 4 / 0 -7.9 (3), 49 open -> no decision; next read 11-26. 11-19 09h (c41): forward rest 20 / 16 won +10.3 pts on 8 coin-dates (6 positive) -> reaches the 8-coin-date line and survives the kill rule (<= 0); tails 5 / 0 -7.7 (4); 48 open (10 of 11 tails crash bets). Still ~8 BTC/ETH-direction bets (lesson 6) -> keep, next read 11-26. |
| N58 culture launch-hour NO (forward paper, launch_paper.py inside the follow.yml chain, poll 150 s) | seed books on fresh culture markets sit near 0.50 and fans buy YES; the NO side is cheap until the market has been looked at (tape: +7.4 pts per market [5.5, 9.3], 614 events; N60: still +8.4 [6.0, 10.7] with the follower >= 300 s late, halves +10.6 / +5.8; 24-72 h later +0.7) | new culture listing < 60 min old, lives >= 24 h, $10 at the real NO ask 0.05-0.90, NO spread <= 10c, fee paid; one per market; report guard settled / open_past_end | 11-16 | kill if <= +1 pt or event CI low < -1 after 100 markets / 40 events; promote after 300 / 100 / 3 weeks 11-17 05h (c28): first report OK - 3 h, 129 new listings, 3 bought, 0 settled; skips mostly placeholder outcomes (86 not accepting orders, 29 no NO ask); tape split: edge sits in single / narrow events (+16.6 / +7.5), wide +4.2 11-17 c29: + N66 arms (retry / activated placeholder) reported separately; decision on the first-look arm only. 11-17 c30: + N68 'late' arm (one look at 1-6 h); 3 open / 0 settled after 11 h (first arm only so far). 11-18 c34: 7 open (3 first, 4 retry), 0 settled, open_past_end 0; N76 capacity: small-ticket ($8 median single-price NO per market) -> $10-20 per market at most. 11-18 c35: 7 open, 0 settled; N78 split (tape): one-off events +11.1 vs recurring series +4.1 (ex-mention recurring +1.7) -> read the forward book by series kind too (positions carry 'ev'). 11-19 c42: 39 positions, first settlement = 1 mention market lost (-$10.24, -40 pts); no new candidate since 11-18 22:04 (15 h; 797 listings 'not accepting orders' watched) -> bug if > 24 h at c43; N92 (big YES first) DEAD, no filter. 11-19 c43: the first look always meets the empty 0.01/0.99 seed book (58 / 58 first looks on 11-19, 428 on 11-18), so 39 of 43 positions are 'retry' (first real book < 60 min) - the tape's follower-at-first-real-fill design; decision read = first + retry (fixed before any retry settled). |
| N95 RT score ladders, NO side 1-7 d before end (rt_paper.py hourly in spike_paper.yml, $10 at the real NO ask, fee 5%*a(1-a); rung / ask / hours logged) | fans buy the high Tomatometer thresholds on hype while the score is a public running count that tends to drift down as more reviews arrive; few traders, thin books | tape (rt_ladder.py, c44, rules fixed in c43): NO +11.4 pts [2.8, 19.8] on 36 films, halves +3.3 / +19.4 (older half passed the +3 kill line by 0.3); 24-168 h before end +12.0 [2.0, 21.4] on 30 films, halves +7.5 / +16.2; middle rungs +14.3, NO 0.30-0.60 +15.0 (logged, not filtered). Found by looking (N94 -> N95, lesson 22) and only group a has RT markets, so the paper run is the real test. Kill if <= +1 pt per share after 15 films; propose only after 30 films and both halves > 0 (~3 films a week -> ~10 weeks). Guard: settled / open_past_end in rt_report.json. | 11-19 | 15 films (~5 weeks) |
| Research journal (my forecasts with sources) | reading + cross-checking beats the crowd on slow political/econ questions | forecast_log.py, Brier vs market | 11-10 | weeks |

## READY (ranked)
N100. -> 11-20 (cycle 46), DEAD (see DEAD). **(outside the box, 11-20 c46) Forced exits / flip legs:** a taker who bought one way and later
   trades the other way in the same market is mostly exiting for reasons of his own book (stop-loss, capital, profit-taking), so the flip leg
   could be uninformed (fade it) - or a reversal by someone who was in the market is the strongest tape signal (follow it). Every earlier tape
   study used first entries only. Exposed to 22, 24, 23, 17, 5/6. flip_leg.py + flip_leg_big.py (post-hoc).
N99. -> 11-20 (cycle 46), DEAD (see DEAD). **(adjacent to N95 / N97, 11-20 c46) Post-count brackets, NO above the leading bracket:** fans buy
   the 'spree' brackets above the current favourite of Elon / CZ weekly post-count events, like RT upper rungs. Exposed to 2, 13, 22, 24.
   count_bracket_upper.py.
N98. -> 11-20 (cycle 45), DEAD by count (see DEAD). **(outside the box, 11-20 c45) Conjunction questions ('Will X and Y both happen'):**
   the conjunction fallacy says people price 'A and B' above what A and B imply, so YES on compound questions should lose. Exposed to 8
   (count), 13, 5/6. Cheapest test: count genuine compound questions on tapes a + c.
N97. -> 11-20 (cycle 45), DEAD (see DEAD). **(adjacent to N95, 11-20 c45) Fan-count ladders ex-RT:** if fans overbuy high Tomatometer
   rungs, they should overbuy high box-office / YouTube-views / Netflix-views / album-sales thresholds too -> NO on upper rungs. Exposed to
   22 (RT was found by looking), 24, 13, 26. fan_ladder.py + fan_ladder_single.py.
N96. -> tested 11-19 (cycle 44), DEAD (see DEAD). **(outside the box, 11-19 c44) Local-language politics:** markets about non-English-
   speaking countries (Brazil, Japan, Poland, Latvia, Israel ...) are priced by an English-speaking crowd reading translated headlines late;
   local readers should show up as big takers who win more there than in US politics. Exposed to 22, 24, 5/6, 27, 13. local_language.py.
N95. -> 11-19 (cycle 44), TESTING (rt_paper.py). **(spawned by N94, 11-19 c43) Rotten Tomatoes score ladders ('Will X score at least 80 / 90 / 92 on the Tomatometer')
   vs the live Tomatometer.** Tape: NO on RT ladders (all thresholds, first entry per market+side, follower a300, fee) +11.4 pts [2.7,
   20.0] on 36 films, YES -7.6; but halves +3.3 / +19.4 (lesson 24 warns). Why the crowd could be wrong: fans buy high thresholds on
   hype; the score is a public running count (reviews arrive over days after the embargo lifts, early scores drift DOWN as more critics
   post) - a 'running count' market nobody models. Exposed to 24 (one half), 13 (the score is public live), 26 (count fills after the
   embargo lift vs before), 5/6 (36 films; one film = one bet), 22 (found by looking at N94). Cheapest decisive test: tape only, split RT
   NO entries by 'before / after the first review-count move' is not possible offline -> instead by hours before end (> 7 d, 1-7 d, < 1 d)
   and by threshold rank in the ladder (top rung vs the rest), fixed now; plus group b / an older period if the tape has one. DEAD if
   the older half stays <= +3 or < 30 films.
N94. -> tested 11-19 (cycle 43), DEAD as a mechanism (see DEAD). **(outside the box, 11-19 c43) Round-number thresholds** ('at least
   90', 'above 100k', '1,000+' with one significant digit) vs non-round ones: headline milestones should carry a YES attention premium.
   Exposed to 13, 22, 24, 5/6. Test: round_threshold.py on tape a + c.
N93. -> tested 11-19 (cycle 42), DEAD by count (see DEAD). **(outside the box, 11-19 c42) Court-docket markets ('ruled / sentenced /
   indicted by <date>', sentence-length buckets) vs the public docket.** Why the crowd could be wrong: traders read headlines, not dockets;
   a scheduling order that sets the hearing after the deadline, or the prosecution's sentencing memo, is public days before the price moves.
   Exposed to 13 (dockets are public), 25/26 (does the docket arrive before the price settles?), 8/5 (count), 11. Test: count first.
N92. -> tested 11-19 (cycle 42), DEAD (see DEAD). **(adjacent to N58 / N78 / lesson 17) Culture launch-hour NO split by who bought YES
   before us** (any YES taker order >= $200 before the follower's fill vs only small tickets): lesson 17 says big takers are informed, so
   NO should be wrong where a big YES came first. Exposed to 5, 6, 22, 24. Test: culture_bigyes.py on the exact N78 rows + orders_a.
N91. -> tested 11-19 (cycle 41), DEAD by count (see DEAD). **(outside the box, 11-19 c41) Twin markets: the same question listed in two
   events** (a stand-alone market and an outcome of a multi-outcome event, or two copies of one series). Why the crowd could be wrong:
   nobody arbitrages across events, so YES in the cheap copy + NO in the dear one locks 1 - cost. Exposed to 8 (riskless = cents, tiny),
   3 (executable prices), 5. Test: twin_markets.py on the tape.
N90. -> tested 11-19 (cycle 41), DEAD (see DEAD). **(adjacent to N58 / N82 / N52) 'Another X by <date>' relists: launch-day NO.** Series
   that re-list right after the thing happened (another AI sandbox escape, Russia captures X again, another GTA VI trailer): the crowd just
   watched it happen, so near-rung YES should be overbid. Exposed to 11, 13, 5/6, 24, 22. Test: relist_no.py on the tape.
N89. -> tested 11-19 (cycle 40), DEAD (see DEAD). **(outside the box, 11-19 c40) Question wording: does the YES premium belong to the
   token or to the drama?** Where the question is negated / 'stays' / 'remains', YES = nothing happens; if crowds overbet that SOMETHING
   happens, YES there should be cheap. Never used the wording before. Exposed to 13, 22, 24, 5/6, 7. Test: wording_side.py on the tape.
N88. -> tested 11-19 (cycle 40), no change (see DEAD). **(adjacent to N58 / N78 / N82) Culture launch-hour NO by event width** (stand-alone
   binary vs 2-4 vs 5+ markets per event): fans overbid several named siblings in wide events. Exposed to 5, 6, 22, 24. culture_width.py.
N87. -> tested 11-19 (cycle 39), DEAD by count (see DEAD). **(outside the box, 11-19 c39) Hurricane / tropical-storm markets ('a hurricane
   makes US landfall by <date>', named-storm counts) vs the NHC tropical outlooks.** Why the crowd could be wrong: NHC publishes 2- and 7-day
   formation odds and cones on a schedule, and late-season climatology is low, while traders follow storm narratives. Exposed to 13, 5/6
   (one season = a few correlated questions), 26. Cheapest decisive test: count questions + price history locally (events_closed, data/prices).
N86. -> tested 11-19 (cycle 39), DEAD (see DEAD). **(adjacent to N58 / N76) Culture launch-hour NO as the maker the fans buy YES from.** N58
   is real on the tape but tiny as a taker ($8 of NO per market); the fans' YES buying is the flow that makes NO cheap, so a resting NO bid
   would earn the spread, pay no fee and be bigger. Exposed to 17 / 23 (who fills a resting order), 22, 24.
N85. **(outside the box, 11-18 c38) On-chain rule clarifications: Polymarket posts market clarifications through the UMA adapter's
   bulletin board (an on-chain 'update' to the question's ancillary data, timestamped) and shows them as 'Additional context'.** Why the
   crowd could be wrong: most holders never re-read the rules; a clarification that narrows what counts ('only official sources', 'a
   ceasefire must be announced by both sides') moves the fair value at a known second, and the book may take hours to follow. Exposed to
   1 (resolution bots may watch the same contract), 26 (count fills AFTER the post, not how big the move is), 2, 5/6 (one clarification
   per event; count events). Cheapest decisive test (needs network: run_script via Actions, public Polygon RPC, no account): pull the
   bulletin-board update events of the last 12 weeks, join to the tape by questionID, and measure (a) how many updates there are on
   markets with fills (DEAD if < 30 events), (b) the price move from the post to +6 h vs a placebo time 24 h earlier, (c) follower
   fills >= 300 s after the post in the direction of the next 6 h move, points per share by event, halves. DEAD if (b) is not larger
   than the placebo or (c) <= +1 pt.
N84. -> tested 11-18 (cycle 38), UNCLEAR by the rule, no COPY-1 arm. **(adjacent to COPY-1 / N80) Copy only in markets that end >= 24 h
   after the entry.** COPY-1 paper (in-sample): ends < 24 h -4.0 pts (34 events) vs 1-7 d +17.1 (15). Tape walk-forward (copy_horizon.py,
   follower >= 300 s, COPY-1 3c cap): good wallets < 24 h -0.1 [-1.5, +1.2] (379 events), 1-7 d +0.2 [-0.3, +0.9] (667), 7-60 d +1.0
   [+0.3, +1.7] (730), 24 h-60 d +0.57 [+0.1, +1.0] (996; halves +0.7 / +0.4), placebo others -1.0 -> below the +1.5 bar; horizon only
   moves the follower from ~0 to ~+1. The paper's 1-7 d +17 is noise. Exposed to 1, 5, 22, 24.
N83. -> tested 11-18 (cycle 37), DEAD (see DEAD). **(outside the box, 11-18 c37) Earthquake markets vs the Gutenberg-Richter prior**
   (daily 'biggest earthquake on <date>' ladders, weekly M5.5+ / M6.5+ counts). Why the crowd could be wrong: the base rate is a physics
   law few traders look up and the buckets are narrow. Exposed to 13, 9, 26, 5.
N82. -> tested 11-18 (cycle 37), UNCLEAR by the rule, no tracker change. **(adjacent to N58 / N60) Culture launch-hour NO on deadline
   ladders ('X by Nov 24 / Nov 28 / Dec 1')** - on 11-18 N58 bought 18 of its 26 positions in five 'streamer finishes GTA VI by' ladders
   in ~30 min (lesson 6). Tape: ladder +3.9 pts [-10.9, +20.0] on only 14 events / 58 markets (4% of N60 rows), earliest rung +2.0,
   later rungs +4.5, one bet per event +12.7 [-4.0, +26.8]; non-deadline +8.4 [6.1, 10.7] (529 events). Too few ladders to cap them;
   the forward N58 read must count events (its decision rule already does: 100 markets / 40 events).
N81. **(outside the box, 11-18 c36) Weekend equity: Polymarket stock / index 'up or down' and 'close above X' markets that settle on the
   Monday (or Friday-close markets still trading after the bell) vs 24/7 equity perpetuals (Hyperliquid HIP-3 stock / index perps).** Why
   the crowd could be wrong: between Friday 21:00 and Monday 13:30 UTC the Polymarket book has no live underlying to anchor on, while the
   weekend perp prices weekend news (tariff posts, geopolitics, earnings guidance) continuously; up/down crowds price ~0.50 + drift. Exposed
   to 1 (bots that already quote off the perp: check how fast PM follows a perp move), 13 (the perp is public), 9 (we bring only the deeper
   market), 6 (one weekend = one bet per index; count weekends, not tickers). Cheapest decisive test (needs network: run_script via Actions):
   Hyperliquid candle history of the equity perps (weekend hours) + Polymarket Monday up/down markets' tape over the last 12 weekends: when
   the perp has moved >= 1% since Friday close, was the PM ask on the perp's side still <= perp-implied P - fee - 2c, and did it fill
   (follower >= 300 s)? DEAD if < 12 weekends with a >= 1% move or the gap closes within 5 min.
N80. -> tested 11-18 (cycle 36), DEAD (see DEAD). **(adjacent to COPY-1) Copy only while the price has not run away (gap between the
   follower's price and the sharp wallet's price <= 1c).** If the +0.5 follower edge is an average of 'no move -> edge kept' and 'price ran
   -> edge gone', a tighter cap would keep a real edge; or a small gap means the market did not believe the wallet (lesson 2). Exposed to 1,
   2, 5, 22, 24.
N79. -> tested 11-18 (cycle 35), DEAD (see DEAD). **(outside the box) AI model release-date ladders ('next Gemini Pro / Claude /
   GPT / Grok model released on / by <date>', 27 events, 203 markets with fills).** Why: AI fans buy near-date YES on hype and labs slip -
   or leak-readers buy YES early and NO is the sucker side. Exposed to 6 (one release settles a whole ladder + sibling events), 11, 13, 1.
N78. -> tested 11-18 (cycle 35), UNCLEAR by the rule, kept as a read-out split of N58. **(adjacent to N58 / N74) Culture launch-hour NO:
   one-off events vs recurring series.** If regulars re-price each weekly copy from the last one (lesson 13), the fan premium should
   live in one-offs. Exposed to 5, 22, 24, 13.
N77. -> tested 11-18 (cycle 34), DEAD by arithmetic (see DEAD). **(outside the box) Polymarket holding rewards (4%/yr paid on
   positions in ~270 long-dated markets, mostly 2028 politics): carry both sides, or long-shot NO + reward.** Why it could work: the
   reward removes the cost of capital that keeps long-dated long-shot YES rich; nobody we know prices that in. Exposed to 8 (cents), 6 / 15
   (20 events, 2028 tails), 13 (the reward is public). Test: today's active-market snapshot.
N76. -> tested 11-18 (cycle 34), done: N58 is SMALL-TICKET (see DEAD / sizing). **(adjacent to N58 / N60 / N68) How much money does culture
   launch-hour NO hold?** An +8 pt edge on $10 is 80c a market; before any live talk, measure the dollars real takers put in and earned in
   the same window. Exposed to 23 (weighting), 8 (size), 22.
N75. -> tested 11-18 (cycle 33), DEAD (see DEAD). **(outside the box) YouTube view-count bucket ladders (MrBeast / MrBeast Gaming
   'views on day N / week N', GTA VI trailer views).** Growth curves are regular and the count is public live; fans spread mass over
   neighbouring buckets? Exposed to 26, 9, 6, 13.
N74. -> tested 11-18 (cycle 33), DEAD as a mechanism (see DEAD). **(adjacent to N58 / N60) Culture launch-hour NO by the clock: is it
   'nobody awake to correct the seed book' (US night / weekend) or fans buying YES (flat)?** Exposed to 5, 22, 24.
N73. **(outside the box, 11-17 c32) Esports match markets vs sharp esports lines.** Polymarket now lists many CS2 / LoL / Dota 2 /
   Valorant match winners; Pinnacle-style books price the same matches with deep limits. Why the crowd could be wrong: esports books on
   Polymarket are thin and fan-driven (team loyalty, regional fans, lesson 17 says fans over-price their side), and our sports compare
   covers only NBA / NHL, so nobody we know of arbitrages tier-2 matches. Exposed to 1 (live in-match bots: PRE-MATCH only), 13 (the sharp
   line is public), 9 (we bring no model, only the deeper market), 5 (one tournament = correlated teams). Cheapest decisive test: one
   sharp_compare-style snapshot (Actions) of pre-match esports moneylines vs Polymarket asks: how many matches a day, how many with
   no-vig fair - ask > fee + 2c; only if >= 10 / day, a paper arm in sharp_compare.py.
N72. -> tested 11-17 (cycle 32), DEAD (see DEAD). **(adjacent to N58 / N68) Culture ex-mention NO in the last 48 h before the end.**
   N68's placebo said fans over-price YES after listing; do they again near the release / show day? Exposed to 1, 2, 11/15, 24.
N71. -> tested 11-17 (cycle 31), DEAD by count (see DEAD). **(outside the box) Collectible price Over/Under markets (Pokemon sealed
   product / single-card prices, strike ~ the price at listing, resolve ~1 month later on a public price tracker).** Why the crowd could be
   wrong: collectors buy 'Over' on what they love while new-set product usually drifts down. Exposed to 6 (one date = one bet), 5, 13.
N70. -> tested 11-17 (cycle 31), DEAD (see DEAD). **(adjacent to N58 / N68) Culture launch-hour NO above the tracker's band (NO 0.90-0.98).**
   The largest priced skip of launch_paper.py is 'ask outside 0.05-0.90' (41 of 207 candidates). Do fans also keep a few cents of hope on
   near-dead YES? Exposed to 2, 15, 8.
N68. -> 11-17 (cycle 30), TESTING as the 'late' arm of the N58 tracker. **(adjacent to N58 / N66) How fast does culture launch-hour NO decay?**
   The tracker buys only < 60 min old markets (3 positions in 11 h). Tape (culture_decay.py, rules fixed before looking, follower >= 300 s,
   first fill per market per age bucket, clustered by event): NO < 1 h +7.1 pts [5.1, 9.1] (600 events), 1-3 h +5.1 [2.2, 7.8], 3-6 h +4.6
   [2.1, 7.2], 6-24 h +3.5 [1.8, 5.1]. DECISION 1-6 h: +4.6 [2.6, 6.8] on 515 events, halves +6.7 / +2.5 [-0.3, +5.4] (newer half weaker,
   lesson 24 watch), ex-mention +3.7, top event 4%, markets with no launch-hour fill (what the arm adds) +4.1 [1.0, 7.6] -> PASS. Placebo:
   culture YES in the same buckets -4.1 [-6.6, -1.5] -> it is YES over-pricing by fans (one side), not general culture-taker skill.
   Exposed to 1, 5/6, 22, 24 (newer half). Built: 'late' arm in launch_paper.py, one look at L + 1..6 h, same buy rule and kill rule.
N67. **(outside the box, 11-17 c29) Token-launch FDV markets vs pre-launch perps.** Polymarket lists 'X FDV above $Y one day after launch'
   ladders for upcoming tokens; pre-market perpetuals on other venues (Hyperliquid pre-launch perps, exchange pre-market trading) price the
   same FDV with real money and leverage, continuously, days before the launch. Why the crowd could be wrong: the FDV ladder is a thin
   culture-like book of airdrop farmers and fans (YES on big numbers), and nobody converts a perp price + circulating-supply fine print into
   ladder probabilities. Exposed to 9 (only a deeper market, not our model), 13 (the perp is public: priced?), 3 (thin ladder books: real
   asks), 6 (one launch = one bet: unit = token), 11 (use finished launches only), resolution fine print (which price source, which minute,
   fully diluted supply definition). Cheapest decisive test: Gamma closed history of 2025-26 FDV ladders (Actions, no orders) + the public
   candle history of the matching pre-launch perps; implied P(FDV > Y) from the perp mid 24 h before launch with a lognormal at the perp's
   own realised vol vs the ladder ask then, follower fills from the tape. DEAD if < 15 tokens or the ladder ask is within the perp-implied
   band. -> READY (needs history: run_script).
N66. -> 11-17 (cycle 29), TESTING as two arms of the N58 tracker. **(adjacent to N58 / N62) Culture late-adds + the tracker's one-look rule.**
   launch_paper.py marked every market 'seen' at first sight: 158 of 161 candidates in its first 7 h were skipped for transient reasons (86
   'not accepting orders' placeholders 'Person A..L', 35 no NO ask, 28 ask outside band, 7 spread) and never re-read. A placeholder that opens
   later IS a culture late-add. Tape (lateadd_culture.py, pre-registered splits, the pooled number was a c27 side read): culture late-add NO,
   launch hour, follower >= 300 s, one fill per market: +11.0 pts [5.1, 16.5], 118 events; halves +9.9 [-0.5, 19.5] / +11.7 [4.7, 18.8];
   ex-mention +9.7 [2.2, 17.4]; largest event 11% of the points; delay 1-3 d +7.1, >= 3 d +14.5; same markets 24-72 h later +4.9 -> PASS.
   Built: 'retry' arm (transient skip re-read every poll while < 60 min old) and 'activated' arm (placeholders watched 14 d by id, L = the
   time it opens). Same kill rule as N58, per arm.
N65. -> tested 11-17 (cycle 28), DEAD (see DEAD). **(outside the box) The catch-all outcome ('Other' / 'another' / 'none' / 'no one').** Fans bid named
   candidates; the field bucket has no fan base, so its YES might be under-priced. wide_other_census.py.
N64. -> tested 11-17 (cycle 28), PARKED (see PARKED). **(adjacent to N58 / N59 / N62) Wide-event launch-hour NO outside culture.** If N58 is structural
   (N seed books near 0.50 sum to >> 1 until the event is looked at), it should work in wide non-culture events too. wide_other_census.py.
N63. **(outside the box, 11-17 c27) 'Slot-only' events: 'by <date>' markets on things that can only happen on scheduled days (Congress votes only on session days, SCOTUS rules only on opinion days, agencies publish on fixed weekdays).** Why the crowd could be wrong: 'will the bill pass / X be ruled by <date>' trades like a smooth hazard, but when the chamber is in recess (August, the pre-midterm October recess, Thanksgiving week) or no opinion day is left before the deadline, YES is near-zero yet holders keep a few cents of hope and NO holders sell early (time value). Exposed to 2 (a cheap YES that survives may be right: pro-forma sessions, unanimous consent), 13 (the calendar is public: priced?), 8 (cents per share), 11 (path questions: use finished markets only), 15 (tail). Cheapest decisive test: tape group c 'by <date>' markets naming Congress / House / Senate / bill / Supreme Court, entries while the chamber is out with no session day before the deadline (2026 House + Senate calendars and the SCOTUS opinion-day list, read from the official pages), NO side follower fill >= 300 s, points per share clustered by event, halves. DEAD if < 30 events or <= +1 pt. -> READY (needs the calendars).
N62. -> tested 11-17 (cycle 27), DEAD (see DEAD). **(adjacent to N58 / N59) Late-added outcomes: buy NO in the launch hour of an outcome added >= 24 h after its event listed, non-culture.** lateadd_census.py.
N61. **(outside the box, 11-16 c26) Year-end lists from one publisher on a known date: words of the year (Collins / Cambridge / Oxford / Merriam-Webster), Spotify Wrapped #1s, Google Year in Search, TIME Person of the Year.** Why the crowd could be wrong: one-off annual questions with no model; the sources publish in stages (Collins and Cambridge before Oxford / M-W, shortlists and public votes before the pick, regional Wrapped screenshots before the global post, Spotify's own mid-year charts) and the first stage is a strong hint for the next. Exposed to 13 (the hint is public: priced?), 26 (count fills AFTER each hint, not how good the hint is), 5/6 (one event per list per year: pool lists and years), 11 (all finished). Cheapest decisive test: Gamma closed history of the 2024 and 2025 versions (Actions, no orders): price of the eventual answer 7 d / 24 h before the announcement and right after the previous stage's publication, with the fills that traded in between from the trade tape. DEAD if < 15 lists or no fills after the hint. -> READY (needs Gamma, run via run_script).
N60. -> tested 11-16 (cycle 26), PASSED (folded into the N58 tracker). **(adjacent) Does N58 survive our latency?** launch_latency.py, same tape, one NO fill per market: follower >= 60 s +8.8 pts [6.5, 11.2] (554 events), >= 300 s +8.4 [6.0, 10.7] (543), halves +10.6 / +5.8, non-mention +5.6 [2.9, 8.1]; 86% of the fills are in the first 10 min after the first trade (later ones are fewer and noisier: 10-30 min +6.4 [-2.3, +15.0], 83 events). Median NO price drift 60 s -> 300 s: 0c. So the forward tracker polls every 150 s.
N58. -> 11-16 (cycle 26), TESTING (launch_paper.py). **(adjacent to young-market NO / mention NO, 11-16 c25) Culture launch-hour NO: buy NO right after a new culture market lists.**
   Found AFTER looking at N59's table (LESSONS 22: forking path - treat the number as a hypothesis, not a result). On the 12-week tape,
   group a (mention, movies, music, youtube, awards, pop-culture), NO side, follower fill (next NO print by someone else >= 60 s later) in
   the first hour after the market's first trade: one fill per market +7.4 pts [5.5, 9.3] on 614 events / 112 launch days; older half +8.7,
   newer +5.6 [2.8, 8.4]; mention +10.9, non-mention +4.6 [2.2, 6.8] (both halves +4.9 / +4.1); the same NO side 24-72 h after launch +0.7
   [-1.2, +2.6]; weather NO +0.1, politics/econ/tech NO +2.8 [-0.3, +5.9]. Why it could be real: seed books on fresh culture markets are
   quoted around 0.50 and fans buy YES on 'will X happen'; the NO side is cheap until the market has been looked at. Exposed to 22 (found by
   looking), 24 (mention blanket NO decayed 16.9 -> 0.8: watch the newer weeks), 3 (a follower print shows a price existed, not our size),
   1 (listing bots), 11 (all tape markets are finished - OK). Next: forward paper tracker on NEW listings (culture tags, poll every ~10 min
   inside the follow.yml chain, $10 at the real NO ask in the first hour if ask <= 0.90 and spread <= 10c, fee paid); pre-registered:
   kill if forward <= +1 pt per market or its event interval reaches below -1 after 100 markets / 40 events; promote after 300 / 100 / 3 weeks.
N56. -> tested 11-16 (cycle 24), DEAD (see DEAD). **(outside the box) The insider footprint: follow FRESH wallets.** Famous insider cases
   are new addresses that buy one political / geopolitical outcome big before the news; a first-ever trade is knowable when it prints.
   COPY-1 follows wallets with a record, fresh ones have none. Exposed to 17 (new accounts are mostly retail), 22, 5/6, 1. Test:
   fresh_wallet_census.py, group c, follower fill 60 s later + fee, by event, halves, pre-registered kill rule.
N57. -> tested 11-16 (cycle 24), DEAD (see DEAD). **(adjacent to COPY-1 / lesson 17) Fresh wallets in culture / mention markets**, where
   the tape says informed takers are paid most. Same script and rule, group a.
N54. -> tested 11-16 (cycle 23), DEAD (see DEAD). **(outside the box) Scheduled US macro release buckets (CPI MoM / annual, core CPI,
   PPI, ISM, unemployment, UMich, eggs).** Backlog item 4 since 11-01, never run. Why: 0.1-wide buckets around a public consensus /
   Cleveland Fed nowcast; fans may spread money over surprise buckets. Exposed to 13, 5, 6. Test: macro_census.py, favourite 0.60-0.97
   6-168 h by release, pre-registered kill rule.
N55. -> tested 11-16 (cycle 23), DEAD (see DEAD). **(adjacent to N17 touch-YES-rich / options model) Treasury-yield 'how high / how low
   in <month>' touch ladders.** Why: N17 found touch YES rich; a deep underlying, maybe tighter books. Exposed to 6 (one month = one bet), 11.
N52. -> tested 11-16 (cycle 22), DEAD (see DEAD). **(outside the box) Service-status / running-count markets: ChatGPT outages, 'Claude go
   down N times', GitHub longest critical incident, Codex limit resets, SpaceX launches.** Never touched. Why: they resolve on public status
   pages / launch logs (a running count anyone can read), priced by AI fans who may over-price drama. Exposed to 13, 26, 5 (few months), 6.
   Test: statuspage_census.py, count-bucket favourite 0.60-0.97 6-168 h, clustered by end day, pre-registered kill rule.
N53. -> tested 11-16 (cycle 22), DEAD (see DEAD). **(adjacent to N43 gas / N45 leaderboards) Ornn GPU rental price index month-end buckets.**
   Why: slow published index, buckets wider than a month's move, few traders. Exposed to 6 (all GPUs end on the same day), 5, 13.
N50. -> tested 11-16 (cycle 21), DEAD (see DEAD). **(outside the box) Reality-TV elimination / eviction markets (Big Brother, DWTS, AGT).**
   Why: Big Brother's eviction vote is visible days early on the 24/7 live feeds / spoiler sites; judged + voted shows are priced by fans.
   Exposed to 5 (16 events), 6, 17. Test: tv_awards_census.py, favourite 0.60-0.97 6-168 h, big takers, halves.
N51. -> tested 11-16 (cycle 21), DEAD (see DEAD). **(adjacent to N45) Pre-decided awards (Ballon d'Or, Nobel, VMAs, Emmys): favourite late.**
   Why: the result is fixed before the ceremony and leaks (Ballon d'Or, Nobel lists), the crowd is fans. Exposed to 6 (one ceremony = one
   bet), 5, 22. Test: same script, clustered by ceremony.
N49. -> tested 11-15 (cycle 20), PARKED (see PARKED). **(outside the box) US midterm race markets after election night.**
N48. -> tested 11-15 (cycle 20), DEAD (see DEAD). **(adjacent) Rain markets as a running count: YES locked once METARs show >= 0.01 in.**
N47. -> METAR check 11-15 (cycle 20): rain DEAD (see DEAD), tornado PARKED (series stopped). **(outside the box) City rain / tornado-risk binaries.**
N45. **(outside the box, 11-15 c18) AI-leaderboard markets (LMArena / LiveBench / AI-agent 'best / 2nd / 3rd lab end of <week|month>').**
   Never touched. Why the crowd could be wrong: the resolving leaderboard is public and moves rarely inside a month, the books are thin and
   priced by AI fans who over-weight 'a new model drops this week'. Tape (leaderboard_census.py, rule pre-registered): favourite 0.60-0.97
   24-168 h out +3.7 pts [-1.0, +7.1] on 46 events (40 positive), 6-24 h +5.6 [4.7, 6.3] (15 events), halves +3.3 / +4.1, follower holds;
   BUT the events bunch on 16 end-days (month-ends): clustered by end-day +3.7 [-0.5, +6.2], 12/16 days positive. Losses are the weekly
   'best AI model on <date>' markets in weeks a new model dropped (08-31 -7.9, 09-07 -11.6, 11-02 -18.5) and three 3rd-place / LiveBench
   month-end markets (-26..-31). OpenRouter share weekly: -5.9 [-13.0, +1.4] (30 events) -> not part of it. Exposed to 6 (one month-end
   = one bet), 15 (a calm-quarter tail), 22 (monthly-vs-weekly split seen after looking), 13. Next: forward paper on the 11-30 month-end
   markets (one cluster) - needs a small tracker in the slow hook; decision only after 6+ month-end/week-end clusters.
N44. -> tested 11-15 (cycle 18), DEAD (see DEAD). **(adjacent) N41's count-bucket favourite on tweet / post counts.**
N41. -> checked 11-15 (cycle 17), DEAD as a source edge (see DEAD). **(outside the box, 11-15 c16) Ship-transit count markets.**
N42. -> 11-15 (cycle 17), TESTING as a read-out split of the options paper. **(adjacent) Options paper: tails vs the rest.**
N43. -> tested 11-15 (cycle 17), DEAD (see DEAD). **(outside the box) Daily US gas-price (AAA) 1-cent bucket markets.**
N31. -> tested 11-14 (cycle 13), DEAD (see DEAD). **(adjacent) N28/N29 favourite bid on the categories never looked at** (movies, music, tweets,
   youtube raw tapes: the out-of-category replication LESSONS 22 asks for before building the N29 poller).
N32. -> tested 11-14 (cycle 13), DEAD (see DEAD). **(outside the box) Does the informed taker sleep?** Maker P&L by the clock of the taker's entry
   (weekend / weekday 04-12 UTC = US night / weekday US day), 12-week tape, both halves: if the informed trade in US hours, a maker who quotes only
   at night or on weekends faces uninformed flow (time-of-week liquidity was a brainstorm prompt never tested).
N38. -> 11-15 (cycle 15), TESTING as a report split of LP-1 v2 (by_kind.core). **(adjacent) LP-1 without weather and live-count markets.**
   Same reason as N35 one level up: wherever the outcome is being counted live (stream word counts, post counts, video views) the taker sees the
   count before our hourly quote moves. Exposed to 5/22 (split seen after looking, < 1 day), 17, 21. Forward only.
N39. -> 11-15 (cycle 15), DEAD (see DEAD). **(outside the box) Central-bank decision markets vs the consensus.** ~15 central banks a month, thin
   books outside the Fed/ECB, outcome usually telegraphed: is the consensus bucket under-priced 1-7 days out?
N33. **(adjacent, 11-14 c13) LP-1 v2 off-US-hours only.** N32 says the maker's loss is concentrated in US daytime (-2.0% of cost [-4.2, -0.3]) and
   is ~0 at US night (+0.8 [-1.1, +2.8]); LP-1's pessimistic fills are the reward-killer. Rule: same LP-1 v2 quotes, but pull them 12-04 UTC on
   weekdays; reward is earned per minute quoted, so the pool share falls ~45% while the adverse-selection loss may fall more. Exposed to 17, 23
   (average vs our fill), 5. Cheapest test: split LP-1 v2's pessimistic fills by UTC hour at its 48-h read (11-16) - no new code.
N35. -> 11-14 (cycle 14), TESTING as a report split of LP-1 v2 (by_kind). **(adjacent) LP-1 v2 without same-day weather buckets.**
   lp_fill_split.py on LP-1 v2 (0.42 d, Saturday only): weather same-day temperature buckets 36 markets, formula reward $100 (upper bound) vs
   pessimistic fills -$167, trade fills 161 marked to the latest fair -11.5% of notional; everything else 85 markets, formula $401 vs pessimistic
   -$37, 75 fills +0.3%. Why: weather buckets are where informed takers read METARs hours before the book moves (W2: bots clear dead buckets);
   tape: weather takers only +0.2% but in our quotes we are the slow side. Exposed to 5/22 (split seen after looking, one day) -> forward only
   (markets opened after 11-14 21:00), 17, 21 (competition still arrives). Read with LP-1 at 48 h and 5 d. N33's clock split needs weekday data
   (all fills so far are Saturday).
N36. **(adjacent, 11-14 c14) Weather same-day buckets: the informed side, on paper.** If LP-1 bleeds on weather because someone reads the latest
   METAR first, the reverse is to be that taker - but W2 (dead buckets cleared by bots) and W1 (model lost) say we are slower. Low prior; only
   worth testing if LP-1's weather fills cluster within minutes after METAR times (check timestamps vs :50-:56 METAR minute at the 48-h read).
N37. -> 11-14 (cycle 14), DEAD (see DEAD). **(outside the box) Trump approval-rating buckets vs the RCP average.** Buckets resolve on the
   RCP average at noon ET on the date - a smoothed series that moves a few tenths a week. If the crowd prices it as noisier than it is, the
   favourite bucket wins more than priced 1-3 days out. Exposed to 13 (RCP is public), 3 (thin buckets; last prices only), 5, 24.
N34. **(outside the box, 11-14 c13) Kalshi-only weekly series that Polymarket copies a day later.** When Polymarket lists a new recurring series
   (TSA, gas, box office, charts), Kalshi has often run the same question for months with real bid/ask history; Polymarket's first weeks are
   priced by few traders. Use Kalshi's settled history as the per-series prior and Kalshi's live book as the fair price for the Polymarket copy.
   Why the crowd is wrong: new-series books are thin and early traders anchor on the bucket mid; Kalshi's book is deeper. Exposed to 13 (Kalshi is
   public), 1 (arb bots cover pairs that exist for long), 3, 5. Cheapest test: from data/slow/kalshi_matches.json + recorded books, the price gap
   Kalshi mid vs Polymarket ask in the first 14 days of each matched series vs later, and which side the outcome favoured; needs 10+ series.
N27. **(outside the box, 11-14 deep session) Mention markets with a transcript model.** The tape says mention is where information is paid
   most clearly (takers +2.7% of cost [1.4, 4.0] in both halves; wallets that won there keep +2.9 points per entry out of sample; the blanket NO
   edge is gone, so the winners are selecting words). The input is text: previous transcripts of the same speaker / company, the agenda, the news
   of the week - reading that is what we do best. Why the crowd could be wrong: per-word habits are tedious to count; retail buys YES on 'obvious'
   words (YES at 0.50-0.95 in the last day loses 6 points in both halves). Exposed to 13 (base rates may be in the price), 9 (our model vs theirs),
   3 (use the real NO/YES ask), 24. Cheapest decisive test: 40-60 closed earnings-call and Trump events from the 12-week file; per-word frequency in
   the speaker's 4-8 PREVIOUS events only (no lookahead) vs the last print 24 h before; bet where model and price differ by >= 15 points, at the
   next real fill + fee; needs transcripts reachable from Actions (check first). Kill if the edge is < +3 points per share on 30+ events.
N29. -> DEAD 11-14 (cycle 13, see DEAD: did not replicate on movies/music/tweets/youtube). Was: **(adjacent, 11-14 c12) Favourite bid, forward paper on live mention/awards books (from N28).** N28's replay (below) is +2.3 points per
   share on 63 events with the interval touching 0 and only 15 fills in the older half. Pre-registered NOW, before any forward data: peg a bid
   one tick over the best bid on the side priced 0.94-0.985, mention + awards + other text-resolved categories, 1 h - 7 d before the end,
   CANCEL after a selling print below the previous one (both replay losses were fills on a falling price; this filter was seen in-sample, so it
   only counts forward). Why the crowd is wrong: holders who want out before resolution pay ~2-4c for immediacy (LESSONS 17 seen from the other
   side). Exposed to 15 (tail: 2 losses of ~97 pts wipe 80 wins), 23 (the fill sequence), 2 (who sells to a resting bid on a favourite?).
   Cheapest decisive test: add the peg to follow_paper.py (it already reads the public trade feed + books every few minutes), $20 per side,
   fill only on a later real selling print at or through our price; read at 150 fills / 60 events / 3 weeks: >= +1.5 pts with interval > 0.
N30. **(outside the box, 11-14 c12) Google 'Year in Search' markets vs Google Trends.** Polymarket lists '#1 trending person / search on Google
   in <year>' style markets; Google publishes the lists in early December and its rule is TRENDING (spike vs the previous year), not most
   searched - a fine-print gap where the crowd votes for the most famous name. Google Trends (YTD vs last year) is readable weeks earlier.
   Exposed to 13 (Trends is public), 5 (one release a year = ~1-3 independent events: a lottery ticket, not a strategy), 9. Cheapest test:
   census of closed 2024/2025 Year-in-Search markets (gamma, via Actions): did the favourite 2 weeks before release win, and did the
   Trends spike leader? Under 10 events -> PARKED at once.
N28. -> tested 11-14 (cycle 12), see N29. **(adjacent, 11-14) Bid for favourites instead of taking them.** Replay on the raw tapes in the repo
   (mention + awards only; research/slow/tape_favbid.py, live peg one tick above the selling print, first fill per market side, no maker fee,
   rows in the last hour dropped): 140 fills / 63 events, bid 0.963, won 0.986 (2 losses), +2.27 points per share [-0.0, +3.7]; mention
   +1.8 [-1.1, +3.7] (57 events), awards +3.8 (6 events); Aug-Sep only 15 fills, Oct-Nov 125 / 59 events +3.65 with 0 losses; fills after a
   falling print +0.9 [-4.1, +4.1] (both losses), flat/up +3.0..+4.2; >= 7 d before the end -0.2. Same sign as the 6-week number (+1.8 on
   402 sides) but a tail strategy with 2 losses in the sample (LESSONS 15) -> not a result yet; forward paper as N29.
N1. **(adjacent, 11-12) Young NO, path questions only, with a spread cap.** History at executable prices: path-type +16%/$,
   fixed-date -31%; the real NO ask is 10.5c over the mid. Rule: path questions only, NO ask - NO mid <= 5c (half the
   cost), and group touches by underlying + week (LESSONS 6). Exposed to 3 (spread), 5 (the last half is -6.6%), 11
   (early YES). Cheapest test: young_paper.py already logs mid + ask -> re-score the open set at end dates by those filters.
N2. -> tested 11-12 (cycle 2): preview momentum DEAD, Saturday favourite -> TESTING (N2b).
   N1 note 11-13: on the 16 settled young positions the filters do not help yet (path 0/13, cap <= 5c 1/4); decide at end dates.
N5. -> tested 11-13 (cycle 3), PARKED (see below). N6. -> tested 11-13 (cycle 3), DEAD.
N7. **(adjacent, 11-13 c3) lock_x + lock_mv intersection at $20-50 with a 15m-window weight.** Both paper rules are 15/16 and 19/19 but on 12-14
   end-times; the intersection is the cleanest signal. Exposed to 1 (still the 2-s loop), 5 (one-two days). Cheapest test: score the
   intersection on data/fast/trades.jsonl (same slug+side in both strats) and in the exact-K replay; read at 30 end-times.
N9. -> tested 11-13 (cycle 4), DEAD (see below). N10. -> tested 11-13 (cycle 4), TESTING.
N11. **(adjacent, 11-13 c4) Netflix chart nowcast.** If N10's Netflix favourite edge is real, the source is FlixPatrol daily ranks (public, days
   before Netflix's Tuesday top 10). Score the leader by days at #1 in FlixPatrol vs the market favourite; only buy when they agree and
   the price is 0.60-0.85. Exposed to 13 (the chart is public), 9, 3. Cheapest test: FlixPatrol pages for 10 past weeks (read-only) vs outcomes.
N8. -> tested 11-13 (cycle 5), TESTING (mention_paper.py). Was: **(outside the box, 11-13 c3) Earnings-call MENTION markets ('What will X say during the call?', 579 closed markets).** Resolve on
   the call audio; the previous 4-8 transcripts of the same company give a per-word base rate (CEO verbal habits, recurring segments).
   Why the crowd could be wrong: traders guess from headlines; word frequency in past calls is public but tedious. Exposed to 13
   (base rates are priced), 9, 3 (thin books). Cheapest test: census of closed mention markets, price 1 day before vs outcome by
   price band (calibration first; only if mis-calibrated, fetch transcripts).
N12. -> tested 11-13 (cycle 5): lock_m 15m-only, TESTING read-out.
N15. -> tested 11-13 (cycle 6), DEAD as a strategy (see DEAD). N15b **(adjacent, 11-13 c6) Converge dip entry.** Buy the converge set only when
   the best ask is >= 1c under its trailing 24-h median (order books: such dips are +1.0c higher 24 h later, 34/70 back at the median).
   Could save ~1c of a ~2c edge, but some dips are news (LESSONS 2). Test: add a 'dip' tag to converge_paper entries (it already sees
   asks hourly) and compare settled dip vs non-dip entries; needs 30+ settled events.
N16. **(outside the box, 11-13 c6) Elon tweet-count markets (weekly / 3-day buckets) vs the public running tally.** The count only rises;
   buckets below it are dead and the rest follow a rate. Recorded books in the final hours are tight (dead buckets 0.001, sum of asks
   1.037) - bots read the tracker. Exposed to 1, 9 (our rate model vs theirs), 8. Cheapest test: closed weekly events, bucket prices on
   day 3-5 vs a Poisson/neg-binomial rate model from the tally then; first check the tracker history is reachable from Actions.
N13. **(outside the box, 11-13 c5) Equity-index / gold / oil daily 'close above X' and 'up or down' markets vs futures.** CME futures trade
   nearly 24 h and options give a full distribution; Polymarket SPX/NDX/gold daily markets are priced by retail. Why the crowd could be
   wrong: overnight futures moves and the exact close rule (official close vs a time print) are read slowly. Exposed to 1 (index bots exist),
   9, 13. Cheapest test: census of closed daily index markets, last price at 13:00 ET vs a normal model from the prior close + implied vol
   (VIX) and the outcome; needs a free futures/index history source reachable from Actions (check first).
N14. **(adjacent, 11-13 c5) Mention NO for the other speakers, single-event only.** Restrict the 'other' set to events that are one speech /
   presser (title 'during ...' with a start time, not 'this week'), which removes the early-YES path bias. Test: tag the census rows by title.
N17. -> tested 11-13 (cycle 7), DEAD as a taker (see DEAD). N17b **(adjacent) maker NO on weekly stock touch ladders**: rest a NO bid at
   NO mid on YES 0.30-0.50 rungs in the first 24-48 h; the touch premium (+8..+10 pts) would then be earned, not paid. Exposed to 2
   (fills come when the stock is moving toward the strike - exactly the touches), 6 (one week = one bet). Test: young_paper/books already log
   bid/ask; replay 'would my bid at mid have filled' with the CLOB trades of week-of ladders before believing it.
N18. -> tested 11-13 (cycle 8), PARKED (see below). Was: **(outside the box, 11-13 c7) Rotten Tomatoes score markets vs the live review count.** The Tomatometer is a running tally: after
   ~80-100 reviews it rarely moves more than 2-3 points, and reviews land days before resolution. Why the crowd could be wrong: anchoring
   on the first ~20-review score, which regresses; few traders model the remaining drift. Exposed to 13 (score is public - edge only in
   the drift model), 9, 3 (thin books: use real asks from the start, LESSONS 3 / N8), 2. Cheapest test: census of closed RT markets
   (title 'Rotten Tomatoes'), price 1-3 days before end vs outcome by band - and the real spread from Kalshi/our books before any yield claim.
N19. **(adjacent, 11-13 c8) Running-tally near-certainties at 0.90-0.97, 1-3 d before the end.** RT census: 0.90-0.97 favourites won
   39/39 (26 films) at end-72h, +3.9%/$ at +2c + fee; the tally (reviews / views / streams) cannot move far once large. Same pattern as
   converge but with a structural reason for low tail risk (no war-news path, LESSONS 15). Exposed to 15 (tails), 3 (thin books), 8 (size).
   Cheapest test: tag converge_paper entries whose question resolves on a running tally (Rotten Tomatoes, Metacritic, YouTube views,
   chart streams) and widen the band to 0.90 for them only; compare their settled yield with the rest at 30+ events.
N20. -> tested 11-14 (cycle 9), DEAD (see DEAD). Was: **(outside the box, 11-13 c8) The UMA proposal window.** Once a resolution is PROPOSED on UMA, the 2-h liveness usually ends with
   that answer (disputes are rare); a book still trading the proposed side at < 0.99 in that window pays the gap. Why the crowd could leave
   it: retail does not watch the oracle, the gap is small, and capital is locked ~2 h + settlement. Exposed to 1 (bots read the oracle),
   8 (cents), 2 (disputed proposals are the ones still cheap). Cheapest test: closed markets with umaResolutionStatuses (proposed ->
   resolved timestamps) vs hourly CLOB prices in that window; count how often the proposed side traded < 0.98 and how often it was disputed.
N21. -> 11-14 (cycle 9), TESTING (forward read-out). **(adjacent, 11-14 c9) lock_be: lock signals on BTC/ETH only.** Across every lock_*
   paper rule (first signal per window), BTC/ETH 179 windows +3.5%/$ vs alts 265 windows -3.2%; every lock loss since c8 was an alt.
   Why the crowd/bots could be wrong: they price 'locks' by distance in bp, but an alt bp margin is worth far less than a BTC one (vol, thin
   Chainlink alt feeds). Exposed to 5 (split chosen after looking -> forward only), 1 (2-s loop), 6 (windows on one day correlate).
   Cheapest decisive test: forward read-out from trades.jsonl (no bot change), 60+ windows over 5+ days.
N22. **(outside the box, 11-14 c9) Argentina monthly CPI buckets vs the Buenos Aires City CPI (IPCBA).** INDEC's national CPI resolves the
   Polymarket buckets ('Argentina monthly inflation between 1.6% and 1.8%'); the City statistics office publishes its own monthly CPI a few
   days earlier, and the two track closely (same month, overlapping basket). Why the crowd could be wrong: a Spanish-language release from a
   city office, not on English macro calendars; the books are thin and bots do not cover it. Exposed to 13 (if traders do read it, it is
   priced within hours), 5 (one event a month), 3 (thin books). Cheapest test: closed Argentina CPI events (Gamma, via Actions), bucket
   prices the day before and the day after the IPCBA release vs the INDEC outcome; IPCBA history from estadisticaciudad.gob.ar (read-only).
   If the price already jumps on the IPCBA day, dead; if it moves only on the INDEC day, paper it.
N23. -> tested 11-14 (cycle 10), DEAD (see DEAD). Was: **(adjacent) last-day favourites minus geopolitics** - if August's war-event losses
   were the whole tail, a topic filter would leave a calm-period yield. It does not.
N24. -> tested 11-14 (cycle 10), PARKED. **(outside the box) Earthquake markets vs the USGS feed** (magnitude revisions, 'M7+ by date',
   yearly M7 counts; USGS publishes within minutes, few traders read the catalog). Census (quake_census.py via Actions): Gamma search found
   only 13 earthquake markets (yearly 2026 M7 count buckets, a 2021 US M4.5 market), 11 with a qualifying USGS quake, no hourly price
   history long enough to time a reaction. ~1 event a month at best -> too few events to test; revisit only if a tag listing shows more.
N25. **(adjacent, 11-14 c11) lock_cheap: lock signals the market prices < 0.80.** lock_price_split.py: lock_p's +$39 is 7 trades bought at
   0.52-0.74 (+$34.7, 5/7 won, 7 end-times); its 32 trades at >= 0.80 are +1.0%/$; lock_x >= 0.80 is -3.9%. Across all lock_* (first signal
   per window) < 0.80: 53 / 32 won +4.4%/$ (7 days), 0.80-0.95 ~0, >= 0.95 -2.0%. Why it could be real: when the Chainlink/TWAP price says
   'locked' but the book still says 0.5-0.7, the crowd may be reading a different (lagging) reference. Why it may not: a lock our model sees
   and a 0.52 ask nobody takes is LESSONS 2 / 14 (stale book or our K is wrong), and 7 events is LESSONS 5. Test: forward-only read-out from
   11-14 09:00 UTC (chosen after looking) + check each cheap fill against the recorded websocket book (was the ask there 1-2 s later?).
   Also: books capped our $20 order in 211 of 458 first signals; capped -2.8%/$ vs full-size +0.5% (losers sit in thin books).
N26. -> tested 11-14 (cycle 11), PARKED (see PARKED). **(outside the box) TSA checkpoint-passenger buckets** vs tsa.gov's daily throughput.
N3. -> tested 11-19 (cycle 43), DEAD by count (see DEAD). **(adjacent, 11-12 c2) Later-weekend box-office brackets (2nd..6th weekend).** Drop ratios are predictable (genre, CinemaScore, Friday
   number); same Saturday-favourite rule. Exposed to 2, 3, 5. Cheapest test: rerun boxoffice_census on the 'Second/3rd..Weekend' titles.
N4. **(outside the box, 11-12 c2) Music chart markets (Billboard Hot 100 / 200 #1, Spotify daily #1).** Billboard's tracking week ends
   Thursday, the chart posts the next Tuesday; daily Spotify/Apple charts and mid-week industry projections are public days earlier.
   Why the crowd is slow: few traders read the projections. Exposed to 9 (our projection must beat theirs), 2, 8 (small books).
   Cheapest test: census of closed chart markets: price 1-3 days before resolution vs outcome, favourite yield at +2c.
OLD N2. **(outside the box, 11-12) Box-office opening-weekend markets vs Thursday previews.** Friday morning the trades print
   Thursday-preview grosses; opening weekend is ~7-12x previews by genre/franchise (public history). Why the crowd is
   slow: a few manual traders, thin books, numbers land 08-10 ET Friday. Exposed to 9 (our multiplier must beat the
   crowd's) and 2. Cheapest test: list closed box-office markets (gamma search 'box office' / 'opening weekend'),
   price at Fri 12:00 UTC vs the preview-multiplier model and the outcome; needs 20+ films to mean anything.
0. DEAD 11-13 (see DEAD: hook artifact). Was: **Push-driven lock_m for ETH/SOL (latency, not edge):** capacity_v1 (bot trades, legit): their cheap asks vanish in
   0.04-0.11 s after our 2-s REST look. The websocket replay that said +21..+39% at 0.05-1 s had a 1.5-s lookahead (11-12);
   without it, local 11-08..11-10: -3..-5% at <= 1 s. Read-out: server lockm.jsonl lines with "feed": "rx" (from 11-12 13h).
0b. DEAD 11-13 (see DEAD: hook artifact). Was: **Binance nowcast (testing 11-12):** RTDS carries Binance prices ~1 s before the Chainlink prints they anticipate
   (arrival 0.43 s vs 1.46 s; return correlation +0.3..+0.44 with Chainlink's same/next second). Model = last received
   Chainlink print x Binance move since its timestamp. Test: lifetimes FEED_TIME=bn vs rx vs ts (ts = perfect 1.5-s foresight,
   the ceiling). Live cost: none (same socket, the bot already stores the topic).
0a. **BTC lock_m sized up:** BTC asks survive (78% > 1 s) and others bought $1.3k per signal at <= our price; edge thin (+2-3%).
   Test: P&L of BTC lock_m at $100 / $250 / $500 against the recorded book (walk the levels).
1. **Weather W2 same-day nowcast (low prior).** The max only rises: a bucket below a METAR is dead. 11-02: after the
   day's max is in, the winner trades at ~$1.00 in 99% of 36k markets (bots). What is untested is the hour right after
   each METAR in the afternoon. Test: minute price history vs METAR times (IEM ASOS archive).
2. **Weather W0 skill backtest.** Open-Meteo historical forecasts (previous runs) vs IEM METAR outcomes for the 40
   stations: calibration of bucket probabilities, the station bias of each city, before trusting W1's trades.
3a. **Count markets with a public running tally** (tweet counts per week, etc.): bucket prices vs a rate model updated
   from the live count (like W2: the count only rises). Test: list the active count markets and their tally sources first.
4. **Scheduled data buckets (CPI, PPI, payrolls, Fed).** Bucket markets vs a distribution centred on consensus /
   nowcast (Cleveland Fed CPI nowcast) with the historical surprise sd; Kalshi prices on the same release as a cross-check.
5. **Maker on slow favourites.** Rest a bid 1c under the ask on the YES 0.95-0.98 set: spread + time premium; risk:
   fills come when news hits. Test: from the hourly tracker, how often the later ask trades through our bid level.
6. **Liquidity rewards on near-certain markets.** Reward programs pay resting orders near the mid; on near-certain slow
   markets adverse selection is small (the 11-05 pilot lost on crypto markets, where it is large). Test: CLOB rewards
   endpoint -> pools per $ of qualifying liquidity on the convergence set.
7. DEAD 11-13 (the 15m +14% was the hook artifact; bot-up 15m windows 16 trades +3.4%). Was: **15-minute windows on their own.** Replay: lock_p 15/15 +10-12%/$, lock_early 15/15 +15%, lock_c 12 92% +21% (5m: +4-7%). Fewer
   competitors on the slower window? A 15m-only rule set with its own sizing, once the paper sample is 30+.
8. **4-hour windows with the exact K.** 48 windows a day; the bot only watches their last 140 s - widen it for 4h.

## PARKED
- N64 wide-event launch-hour NO outside culture (11-17 c28, wide_other_census.py, local, 12-week tape; event >= 6 original-batch markets, launch hour,
  NO, follower >= 300 s, one per market, unit = event): +1.04 pts [-0.2, +2.3] on 362 events - passes the pre-registered letter (> +1, low > -1,
  halves same sign) by 0.04 pt, but halves +1.9 [0.4, 3.5] / +0.2 [-2.0, 2.2]: lesson 24 says that is gone. Not built. ai/tech +2.5 [0.8, 4.4]
  (59 events) was seen after looking - re-test only on a fresh tape. Diagnostic for N58: culture launch-hour NO is NOT structural - single
  markets +16.6 [5.9, 26.8] (59 events), 2-5 wide +7.5, >= 6 wide +4.2; the edge is culture fans, not the YES overround.

- N49 US midterm race markets after election night (11-15 c20, election_late_census.py, 12-week tape, 133 races / 51k fills): pre-election
  favourite 0.60-0.97 +5.3 pts [-0.2, +9.7] (one national night = few independent events, LESSONS 6), election night +2.4 [-6.0, +9.2] (59
  races), long shots -7.5 everywhere. The idea itself (races still counting days later, priced off the current margin) has only 5 resolved
  late races in the tape (-9.5 pts, n 159 fills) - not testable on this tape. Needs: a later tape with the CA/AZ late calls, and a county
  count source; next real use = the 2028 cycle or special elections. Parked.
- N18 Rotten Tomatoes favourites (11-13 c8, rt_census.py, 264 markets / 64 RT events 2021-2026, hourly CLOB last prices, +c + fee):
  near-certain 0.90-0.97 won 39/39 at end-72h (26 films, +3.9%/$ at +2c), 26/26 at end-24h (19 films, +3.5%); the 'anchoring' band
  0.60-0.90 flips sign with the clock (end-72h 0.80-0.90 -18% on 19 films, end-24h +8.6% on 12, end-6h +15% on 6) = noise (LESSONS 5).
  Only ~5 RT events a month, last prices (LESSONS 3; recorded RT books 11-08/09: 0.4-3c spreads). Not a strategy alone -> folded into N19.

- N5 scheduled-data favourites (11-13, data/history daily prices): CPI/GDP/jobs/Fed buckets at 0.90-0.98 1-7 d before: 50 positions /
  ~20 releases, +1..+5%/$ at +2c vs other non-sports +0.4..+1.1% (2,000 positions) - same as the converge rule, too few releases to tell
  apart. Revisit when converge_paper has 20+ settled data-release markets.

- N26 TSA passenger buckets (11-14 c11, tsa_census.py via Actions, 488 markets / 70 events Nov 2025 - Mar 2026, hourly CLOB last prices,
  +c + fee, fees were off): YES is rich at 0.10-0.50 (0.16-0.19 priced -> 0.08-0.14 won; 0.39-0.41 -> 0.27-0.38). Favourite side 0.80-0.90
  (mostly NO on the second-best bucket) +9.7 / +11.1 / +7.3%/$ at +2c at end-72h / 24h / 6h (67/69, 45/46, 34/36; 27-35 days, 25-33
  positive); 0.60-0.80 flips sign with the clock (+7.8 / -6.3 / -1.7%) = noise. One 4-month period only, last prices (LESSONS 3, 5).
  No TSA market is live now (last ended March 2026), so no paper test possible. tsa.gov throughput page is reachable from Actions (200,
  table) -> if the series relaunches: paper at real asks + the stage-2 YoY model. Check the active-market scan for 'TSA' weekly.

- Kalshi vs Polymarket automatic pairing (titles do not match; manual for named series only).

## DEAD (number that killed it)
- N100 forced exits / flip legs (11-20 c46, flip_leg.py, local, tapes a ex-mention + b + c, rules fixed before looking): a wallet's first
  trade the other way within 7 d of its first leg (>= $20), >= 1 h before the end, follower a300, fee: follow the flip -1.2 pts [-1.5, -0.8]
  on 3,139 events (halves -1.2 / -1.2; a -0.4, b weather -2.1, c -0.3); placebo first legs -0.3 -> neither FOLLOW (>= +3) nor FADE
  (<= -4, the opposite ask's spread eats 2-5 pts) -> DEAD. Post-hoc (flip_leg_big.py, kill-only): big flips (>= $200) +3.5 [2.6, 4.4]
  on 1,883 events, halves +3.7 / +3.3, all three groups +3.3..+3.8 - but big first entries by wallets that never flipped are +2.3
  [1.6, 2.9] on 2,659 events, and both are carried by the cheap side (p < 0.40: +9.7 vs +5.6; p >= 0.70: -0.5 vs +1.0). A big flip is
  a big taker (COPY-1 control's +3.75) plus ~1 pt: no separate mechanism, no new arm.
- N99 post-count brackets, NO above the leading bracket (11-20 c46, count_bracket_upper.py, local, tapes a + c, Elon / CZ 'post N-M'
  events with >= 4 brackets, favourite = highest YES among brackets that printed in the prior 6 h, NO 0.60-0.90, 6-120 h before end,
  follower a300, fee, rules fixed before looking): -2.9 pts [-6.5, +0.7] on 83 events, halves -2.7 / -3.1; below-favourite placebo +2.3
  [-3.2, +7.6] -> DEAD, wrong sign (the brackets above the leader are if anything cheap: posting sprees happen). The RT upper-rung effect
  does not carry to running post counts (with N97: it is RT-specific or noise; N95's forward paper decides).
- N97 fan-count ladders ex-RT (11-20 c45, fan_ladder.py, local, tape a movies / pop-culture / youtube / music / awards ex-mention ex-RT,
  rules fixed before looking): ladders with >= 3 parsed rungs, NO on the upper half, first taker entry, follower a300, fee: -3.9 pts
  [-19.7, +8.7] on 13 events (halves -6.0 / -2.4); lower-rung placebo -16.4; YES upper +3.6 -> DEAD. Lesson 10 check: box office / views
  events carry ONE 'at least' market each (the open top bracket next to 'between' brackets), so the fixed rule saw none of them;
  fan_ladder_single.py (post-hoc, kill-only): single-threshold NO +0.8 [-5.6, +6.9] on 106 events, halves +7.8 / -6.0; box office +4.1
  [-6.7, +15.4] (42), views -5.8 (43). The RT effect does not generalise to other fan counts; N95's forward paper is its only test.
- N98 conjunction questions (11-20 c45, count only): genuine 'A and B' questions on tapes a + c: ~2 events in 12 weeks (Hormuz deal x
  Senate, oil x Senate); every other ' and ' match is a title ('Klara and the Sun') or a pair of countries -> DEAD by count (lesson 8).
- N96 local-language politics (11-19 c44, local_language.py, local, tape group c politics, rules fixed before looking): first taker entry >= $200 per market+side, follower a300, fee: LOCAL (non-English-speaking countries, 509 markets) -0.65 pts [-3.1, +1.8] on 74 events, halves -0.5 / -0.9, vs US +1.8 [0.6, 3.1] (334 events) -> DEAD, wrong sign. Any-size first entries LOCAL YES -2.4, NO +0.7: no general mispricing either. ANGLO (UK / Canada / ...) big NO +9.4 [0.6, 20.2] on 17 events is one post-hoc cell (and the keyword class leaks: a Brazilian governor race landed in ANGLO) - not followed up.
- N94 round-number thresholds (11-19 c43, round_threshold.py, local, tape a + c ex-mention, upward-threshold questions with a number >= 10,
  first entry per market+side, follower a300, fee; rules fixed before looking): ROUND NO +8.7 pts [2.8, 13.5] on 169 events vs OTHER NO
  +6.0 [1.6, 10.4] (175), halves +4.7 / +12.6 -> passed the letter, but the robustness checks kill the mechanism: group a +14.3 vs group c
  +2.5 (OTHER +6.9); ex-Rotten-Tomatoes ROUND +2.3 [-3.2, 8.2] vs OTHER +7.4; paired within-event gap +7.1 [-4.7, 18.4] (53 events);
  events with one kind only ROUND +4.1 vs OTHER +7.3. The 'round' effect is the RT ladders (80 / 90 are round) -> N95. Upward-threshold
  NO in general (+6) is the known YES premium, not new.
- N3 later-weekend box-office brackets (11-19 c43, boxoffice_later.py, local, tape group a): 119 markets / 25 ladders in 12 weeks (~2 a
  week); Saturday favourite 0.80-0.97 +3.5 pts [-7.0, +10.0] on 15 events (halves -3.1 / +10.1); drop-ratio chain YES (prev winning
  bracket x 0.45 / 0.60) 5 events -> DEAD by count (lesson 5/8).
- N93 court-docket markets (11-19 c42, local count on the closed-event list data/events_closed.jsonl.gz, 125,600 events since 2020, and
  tape group c): 125 events with a legal word in the title in ~5 years (~25 a year), most of them one-off headline cases (Trump / SBF / CZ
  indictments and sentences) with 1-7 markets; tape group c has 7 legal markets / 6 events in 12 weeks -> DEAD by count (< 30 comparable
  events a year; lesson 5/8). Sentencing memos before sentence-length buckets are the one real early read, ~3 cases a year.
- N92 culture launch-hour NO by who bought YES first (11-19 c42, culture_bigyes.py, local, the exact N78 rows: 1,458 markets / 547 events,
  +8.2 pts [5.8, 10.4]): only 12 markets / 10 events (0.8%) saw a YES taker order >= $200 before the follower's fill; they were +13.6 pts
  [-11.2, +33.6], no-big +8.2 [5.8, 10.5]; NONE - BIG -6.7 / -2.7 by half -> DEAD (the flag almost never fires and points the wrong way).
  Confirms N76: the launch hour is small tickets only; nothing to filter on. N58 rows newer half +5.7 [2.8, 8.9] vs older +10.6 (lesson 24
  watch: still positive).
- N91 twin markets (11-19 c41, twin_markets.py, local, 12-week tape groups a + c): identical full question text in different events with
  ends within 24 h, ex 'another / again' relists: 270 pairs, but almost all are generic texts ('Will the earnings call not air?') in
  different events; only 11 pairs (~7 independent questions: one Musk tweet-count ladder listed twice, Hormuz x Senate combos, Trump-Carney)
  ever had prints on both sides within 10 min, 8 of them a >= 2c lock (on a300 prints, not a resting book) -> DEAD by count (< 30 events;
  lesson 8). The 0.59 'lock' on the duplicated Musk bucket says the two copies were not the same question (different count windows).
- N90 'another X by <date>' relists, launch-day NO (11-19 c41, relist_no.py, local, 12-week tape groups a + c, finished markets, first taker
  entry per market+side within 24 h of the first trade, follower a300, fee): 68 relist markets, NO -14.0 pts [-28.3, -1.6] on 39 events
  (34 families), halves -3.0 / -23.0; all other launch-day NO +3.6 [2.6, 4.7] (1,568 events) -> DEAD, wrong in sign. The mirror (YES +12.4
  [-3.6, +29.1], 30 events) is one half only (-5.4 / +27.8: the war-heavy Sep-Nov tape; lesson 24) and was seen after looking -> not built;
  re-check on the next tape refresh only.
- N89 question wording (11-19 c40, wording_side.py, local, 12-week tape groups a ex-mention + c, finished markets, mid-life entry: age
  >= 24 h and >= 24 h before end, first taker entry per market+side, follower at a300, fee): negated / 'stay-remain' questions are only
  66 of 5,295 markets (1.2%, 33 events). YES there -7.7 pts [-19.3, +6.1] (halves -6.5 / -11.0), NO +5.7 [-6.1, +17.0]; the drama story
  (YES = nothing happens is cheap) is wrong in sign, the token story is not significant and too rare to trade. Baseline mid-life: YES
  -0.5 [-1.7, +0.7], NO +0.5 [-0.6, +1.4] -> no mid-life side edge at all. DEAD (count + sign). First run had NO at -36 pts: I read the
  win bit as 'YES won' - it is 'this direction's token won' (lesson 10; fixed before reading).
- N88 culture launch-hour NO by event width (11-19 c40, culture_width.py, exact N78 rows): 1,399 of 1,458 rows (506 of 547 events) are in
  events with 5+ markets: wide +8.0 pts [5.6, 10.3] (halves +10.1 / +5.9; ex-mention +4.9 [2.3, 7.5]), single 25 events +18.4, small 16
  +11.0 -> no class to drop, no split possible (culture launches ARE wide events). No tracker change.
- N86 culture launch-hour NO as the MAKER (11-19 c39, culture_maker.py, local, 12-week tape group a, N60 filters, first YES taker entry
  300-3600 s after listing at YES 0.10-0.95 = our resting NO fill, maker fee 0, optimistic queue): +1.55 pts [-1.9, +4.9] on 426 events
  (halves +2.2 / +1.0) vs the NO taker +8.2 [5.9, 10.6] (548); on the 424 markets that have both, maker +8.1 vs taker +9.2 (-1.1;
  halves -2.3 / +0.1); placebo (maker holding YES) -9.7. Markets where only fans arrive and nobody takes NO are the ones where YES is
  right -> the maker seat is filled exactly where the edge is not. Capacity median 1 YES wallet / ~$17 per market. DEAD (lesson 29).
- N87 hurricane / tropical-storm markets (11-19 c39, outside the box, local census of events_closed): 39 weather-hurricane markets in 5
  seasons (~30 distinct questions, 7 resolved YES, $7.8M volume), 0 with price history in data/prices -> DEAD by count (one season = a
  handful of correlated questions; can never reach 30 independent events). Steam / Twitch counts: 3 Steam weekly-seller events on the
  tape, also too few.
- N35 LP-1 ex-weather (report split of LP-1 v2, 11-14..11-19, forward_other): 104 markets, formula reward $811 (upper bound) vs tape -$28 /
  pessimistic -$222 = -27% of the formula over 4+ days (bar > -25%). The non-core 'other' set (views / count / mention) gives back the pool
  to informed takers (lesson 17); only the core split (N38) passes.
- N83 earthquake markets vs Gutenberg-Richter (11-18 c37, quake_gr.py, local, 12-week tape group b, 142 markets / 23 events, textbook
  constants N(M>=5) = 3.97/day, b = 1, fixed before looking): only 32 taker entries happen before the day / week starts (the trading is
  intraday, after the catalog starts filling); rule GR - price >= 5c: 3 fills, -10.7 pts; all pre-period entries -2.4 [-10.0, +4.5]
  (9 events); Brier market .115 vs GR .107 on 25 markets (no gap worth trading). After the day ends (+1 h) the winning side already
  trades at 0.96-0.999 (34 markets / 9 days, 2 fills <= 0.95 on 1 day) -> DEAD (no pre-period volume; after-day read is crumbs, lesson 26).
- N80 copy only at a small price gap (11-18 c36, copy_gap.py, local, 12-week tape groups a + c, tape_entries_an walk-forward 'good'
  wallets (1,540, picked on markets that ended in the older 6 weeks), their newer-half pre-event entries, follower = next same-way print
  >= 300 s later, fee paid, event-clustered, rules fixed before looking): gap <= 1c +0.33 pts [-0.1, +0.8] (36k entries / 1,077 events),
  halves +0.4 / +0.3; COPY-1's own cap (<= 3c) +0.51 [+0.1, +1.0]; all gaps +0.12; gap > 10c -3.6. Placebo (other wallets) -1.0 at
  gap <= 1c -> picking wallets is worth ~+1.3 pts over random, but the follower's absolute edge is ~0-0.5, below COPY-1's +1.5 bar.
  A small gap does NOT keep the wallet's edge (lesson 2: the price that does not move is the one the market did not believe). Diagnostic
  after looking: 1-3c +1.4 [0.4, 2.4] - not acted on (lesson 22). Prior for COPY-1's own read: expect regression from +3.1 toward ~+0.5.
- Sports vs Pinnacle, NBA + NHL pre-game moneylines / totals (11-11..11-18, sharp_compare.py, 19 snapshots, 882 pairs / 113 games):
  fair - ask median -0.5c, p90 +0.6c, p99 +1.6c, max +2.8c; 1 pair of 882 had fair - ask >= 2c; |mid - fair| median 0.5c -> 0 paper
  positions in a week -> DEAD. Polymarket main-line NBA / NHL books track the sharp line within a cent (lesson 13, the sharp line is public
  and arbitraged). The snapshot job can be reused for N73 (esports, thinner books) before its odds credits (412 left) run out.
- N79 AI model release-date ladders (11-18 c35, ai_release_ladders.py, 12-week tape group c, ai/tech events with 'releas' in the
  slug, entries >= 24 h before the end, follower >= 300 s at 0.05-0.90, fee paid, rules fixed before looking): NO side +0.7 pts
  [-6.8, +7.4] on 26 events / 20 model lines, halves -7.5 / +8.8; YES mirror -1.9 [-8.2, +5.3] (long shots < 0.30 -3.9) -> DEAD by count
  (< 30 model lines) and by sign flip. Release ladders are calibrated within noise; nothing to bring without leak data (lesson 1).
- N78 (not dead; recorded here for the number) culture launch-hour NO by series kind (11-18 c35, culture_series.py, exact N60 F300 rows
  listed >= 7 d after the tape start, 1,458 markets / 547 events): one-off events +11.1 pts [7.7, 15.0] (249 events), recurring series
  +4.1 [1.2, 7.2] (243), gap +6.3 / +7.3 in the halves; recurring newer half +1.9 [-1.7, +6.0]; recurring ex-mention +1.7 [-1.2, +4.5]
  (182 events: tweets counts +3.1, MrBeast views +0.4, Netflix/box office -4.1); recurring mention still +11.2. Rule needed recurring
  <= +1 -> UNCLEAR, no tracker change (lesson 22: the ex-mention cut was found after looking). Read N58's forward book by kind.
- N76 culture launch-hour NO capacity (11-18 c34, culture_capacity.py, 12-week tape, culture markets listed 08-17..11-09 living >= 24 h,
  taker NO first entries 300-3600 s after listing at 0.05-0.90, rules fixed before looking): only 864 of 7,825 markets (11%) had any such
  NO taker; single-price NO cost per market median $8, p75 $23, p90 $57 (all-cost upper bound $23 / $78 / $279); the real takers' dollar
  edge was $48/day in total ($25/day on single-price rows) and SHARE-weighted only +2.3 pts [-5.6, +10.2] (393 events) vs +8 per market
  at one $10 fill - the big tickets did not earn it (pop-culture -4.7, youtube -5.2 share-weighted; mention +14.8, movies +15.0, music
  +31.6). Top-10 markets = 196% of the dollar edge. -> N58 stays a $10-20 per market idea: even if it passes, it is tens of dollars a
  day, not a strategy to scale (lessons 8 / 23). No tracker change; the category split is NOT a new rule (lesson 22).
- N77 holding-reward carry (11-18 c34, markets_active snapshot 05:03, 266 holding-reward markets, median 1.97 y to end): two-sided
  carry costs 1 + spread (median 0.1c) and earns the 4%/yr reward = cash yield, not an edge; long-shot NO (YES <= 0.05, 197 markets
  but 20 events) earns a median 4.8%/yr IF it wins = +0.8%/yr over the reward for 2028 tail risk and a rate Polymarket can change ->
  DEAD by arithmetic.
- N74 culture launch-hour NO by the clock (11-18 c33, culture_clock.py, the exact N60 F300 rows, clock by listing time, rules fixed
  before looking): US day (Mon-Fri 13-04 UTC) +9.5 pts [6.5, 12.5] (348 events), US night +8.6 [2.4, 14.6] (132), weekend +4.8 [0.2, 9.4]
  (138); off-hours minus day -3.2 (halves -2.0 / -4.1) -> the 'nobody is awake' story is wrong (if anything the edge is LARGER when the
  US is awake). Consistent with N68's placebo: fans buying YES, not absent correctors. The tracker keeps polling 24/7; no rule change
  (a day-only filter would be a forking path, lesson 22).
- N75 YouTube view-count bucket ladders (11-18 c33, views_buckets.py, 12-week tape, 624 markets / 89 events, entries 1-48 h before the
  end, follower >= 300 s, first fill per market+side, clustered by video-date): FAV (token 0.50-0.95 on YES) -4.1 pts [-9.1, +1.3]
  (108 fills / 41 units), halves -8.8 / +0.5; FADE (NO 0.50-0.95) -0.3 [-2.1, +1.5] (244 / 42), halves +0.2 / -0.7 -> DEAD: the live
  public count is priced (lesson 26). Unit caveat: day-N events of one video carry different dates, so 'videos' overcount (~2x);
  it only widens the intervals of two arms that are already <= 0.
- N72 culture ex-mention NO 1-48 h before the end (11-17 c32, culture_endno.py, 12-week tape, rules fixed before looking, market age >= 24 h,
  lives >= 72 h, follower >= 300 s at the next print 0.05-0.90, first fill per market): -0.2 pts [-1.7, +1.4] on 289 events; halves +0.4 /
  -0.8; 1-12 h -7.9 (35 events), 12-48 h +0.2; movies -5.0 [-8.1, -2.3], pop-culture +1.9 [0.0, 4.3] (one category of five, found by
  looking: not a lead). YES placebo -0.7 [-2.1, +0.6] -> by the last two days culture books are calibrated; the fan YES premium is a
  launch-time effect (N58 / N68 decay curve) and the end of the market does not bring it back.
- N70 culture launch-hour NO at 0.90-0.98 (11-17 c31, culture_highno.py, 12-week tape, rules fixed before looking, follower >= 300 s, first
  fill per market < 1 h after listing): -0.5 pts [-2.1, +1.0] on 374 events (win 94.4% at avg 0.947); halves -1.0 / +0.0; ex-mention -1.0;
  0.90-0.95 +1.0 [-1.8, +3.5], 0.95-0.98 -1.2. Control (tracker band 0.05-0.90) reproduces +8.7 [6.4, 11.1] on 540 events. Fans over-price
  YES in the middle, not on near-dead outcomes -> the tracker's 0.90 cap is right; no change.
- N71 collectible price Over/Under (11-17 c31, collectible_ou.py, 12-week tape): 40 markets but only 2 end dates (09-01, 10-01; 20 products
  each), YES won 14/40 at first prints ~0.50; follower 'Under' +22.6 pts on 21 markets (+11.2 / +37.7 by date), 'Over' -7.9 -> the direction
  fits the idea but it is 2 independent bets (lesson 6) -> DEAD by count. The series is not in the tape after 10-01; revive only if it
  returns monthly (then paper 'Under' at listing, read after 6+ dates).
- N69 twin markets (11-17 c30, outside the box, local count on the 12-week tape meta): the same question (normalised text, end within 1 day)
  listed in two different events, priced by two crowds. Only 36 twin groups in 12 weeks outside sports, and most are overlapping rolling
  'by <date>' series of the same topic (Iran / Ukraine / GitHub incident) and v2 relistings -> ~20 independent topics < 30 -> DEAD by count;
  even when the gap exists it is a riskless-cents structure (lesson 8) that arb_scan already alarms on. No price test run.
- N65 catch-all outcome YES (11-17 c28, wide_other_census.py, 12-week tape, question matches other/another/none/no one, event >= 4 markets, 6-168 h
  before the end, follower >= 300 s): -1.2 pts [-17.8, +20.6] on 20 events (< 30 -> DEAD by rule); the regex mostly hits titles ('Another GTA VI
  trailer', 'Nobody Wants This') - real 'Other' buckets barely appear in our tape's categories. Only way back: Gamma closed negRisk 'Other' markets.
- N62 late-added outcomes, non-culture (11-17 c27, lateadd_census.py, local, 12-week tape; late-add = market's first trade >= 24 h after  its event's first, launch-hour NO, follower >= 300 s, one fill per market): -2.3 pts [-9.0, +3.9] on 319 markets / 131 events, halves  +3.4 / -13.5 -> DEAD by its rule (politics +4.4, ai/tech -3.3, geo -2.9, economy -11.7; all intervals wide). Original launch-hour NO,  non-culture +1.0 [-0.1, +2.2] (1,309 events) = N59 again. Side read (inside N58's scope, not a new idea): CULTURE late-adds NO +11.0  [5.0, 16.9] on 118 events vs culture original launches +5.6 [3.0, 7.9]; culture late-add YES -12.3 -> read the N58 forward run split by  'event older than 24 h at listing'.
- lock_p (11-17 c27, week mark of its pre-set rule): +2.2% per $ on 53 trades / 47 end-times (started 11-10) < the +5% bar -> closed.  Its early +6.8% was 7 trades bought at 0.52-0.74 (11-14 split); the 0.9x locks are ~0 (lesson 2). lock_x keeps running to 11-19.
- N59 new market launches, pooled (11-16 c25, launch_census.py, local, 12-week tape, 937k entries, launch = first trade, markets
  living >= 24 h): follower fill in the launch hour +0.3 pts [-0.5, +1.0] on 3,379 events (by launch day [-0.4, +1.1]), halves +1.06 /
  -0.58 -> DEAD by its rule. The first takers' own fills +0.5 [0.2, 0.9] (very first entry +0.9) vs -0.5 at 24-72 h: the seed book is a
  little stale and the first 60 s take it (lesson 1). YES side -2.0, NO side +2.0 [0.8, 3.3] -> the culture part became N58 (READY).
- N56 insider footprint / fresh wallets, politics-geo-tech-econ (11-16 c24, fresh_wallet_census.py, local, 12-week tape; fresh = the
  address's first entry anywhere in the tape, >= 21 d after its start): follower 60 s later -0.93 pts [-2.8, +0.4] on 49,873 entries /
  949 events; halves +4.95 (107 events) / -1.65; even the LOOKAHEAD upper bound (total cost >= $500) -1.05 [-3.8, +1.6] (264 events);
  geopolitics -0.4, politics -1.6, ai/tech -1.5. Old wallets >= $500 +3.1 (lookahead, lesson 22 already killed the big-taker rule).
- N57 fresh wallets in culture / mention (same script, group a): -3.19 pts [-4.5, -1.9] on 585 events, mention -7.6, pop-culture -2.5;
  >= $500 upper bound +1.4 [-3.4, +7.1]. A first trade from a new address is a retail signal, not an insider one (lesson 27).
- N54 US macro release buckets (11-16 c23, macro_census.py, local, 12-week tape, 27 releases / 21k taker fills): favourite 0.60-0.97
  6-168 h -10.0 pts [-21.5, +2.7] by release (15/27 positive), follower -12.0; older half +2.2, newer -18.1 [-31.9, -1.8]; long shots
  -2.4, mid 0.20-0.60 -0.2, after the release (< 6 h) +3.9 [-1.0, +9.5] on 17 releases (crumbs, lesson 26); small takers -4.1 [-5.9, -2.4],
  big +1.5 [-2.6, +4.9]. The crowd is calibrated around the consensus (lesson 13) and over-confident in it lately; nothing to buy.
- N55 Treasury-yield touch ladders (11-16 c23, same script, 14 ladders / 7k fills): only 2 finished months (Sep, Oct) -> dead by the
  pre-registered rule (< 4 months). Favourite >= 24 h -9.0 pts [-17.2, +0.5], YES long shots +8.9 [-2.7, +26] - the opposite of N17's
  'touch YES rich', i.e. two months of moving yields (lesson 6), not a property of the market.
- N52 service-status / running-count markets (11-16 c22, statuspage_census.py, local, 12-week tape, 28 events / 27 end days: Claude 'go
  down', ChatGPT outage days, GitHub longest incident, Codex resets, SpaceX launches): count-bucket favourite 6-168 h +6.2 pts [-4.7, +13.9]
  per event (22), by end day [-10.8, +15.4] (25 days, 13 positive) -> below the pre-registered bar (end-day interval must stay above -2).
  Follower 60 s later +9.6 [-2.1, +18.3], halves +4.8 / +8.6, big takers +4.7 [-2.5, +10.6]: positive everywhere but 2-3 events per family.
  Cheap re-check on the next tape refresh (no tracker): if 6 more weeks keep the favourite >= +5 with the end-day interval above 0, revive.
- N53 Ornn GPU rental index month-end buckets (11-16 c22, same script, 15 events but only 5 end days): favourite 6-168 h -0.2 pts
  [-9.5, +8.9] by end day; long shots < 0.20 -4.7 [-7.1, -2.2] (5/5 days negative: the maker seat, lesson 17); big takers >= $200
  +5.7 [1.4, 9.7] on 14/15 events but 5 month-ends -> lesson 17 again, nothing to copy at our size.
- N50 reality-TV eliminations / evictions (11-16 c21, tv_awards_census.py, local, 12-week tape, 16 events: 9 DWTS weeks, 6 Big Brother
  evictions, 1 AGT): favourite 0.60-0.97 6-168 h out +1.2 pts [-4.4, +7.5] on 15 events, halves -4.0 / +8.2, 1-6 h -13.2; large takers
  >= $200 +1.4 [-7.2, +9.1]; long shots +5.0 [-1.7, +12.4]. No sign the live-feed information is unpriced; DEAD by its rule (interval < -2).
- N51 pre-decided awards favourite (11-16 c21, same script, 60 award markets / 43 events / 9 ceremonies: Ballon d'Or, Nobel, VMAs, Emmys):
  favourite 6-168 h +3.7 pts [-1.7, +7.9] per event, but clustered by ceremony +3.7 [-4.9, +5.2] (6 of 9 positive); 1-6 h -5.2. DEAD by its
  rule. Side note (seen after looking, LESSONS 22): takers >= $200 +4.3 [0.9, 7.5] on 48 events and the 60-s follower +4.5, small takers
  -2.0 [-3.5, -0.2] - lesson 17 again - but by ceremony the follower is [-2.4, +8.0] on 11 units. Nothing to build; COPY-1 already
  copies culture wallets.
- N47 rain city binaries (11-15 c20, riskday_metar.py via Actions, 12-week tape, 361 markets / 26 dates, IEM ASOS hourly METARs +
  IEM-archived CLI): the answer IS public before the end - METAR day sum >= 0.01 in agrees with the resolution on 357/361 markets (CLI 359/361;
  misses = trace vs 0.01, one Phoenix 'M') - but the CLI comes out within ~1-2 h of the climate day and every after-day fill came after it.
  Only 23 fills on 26 dates traded after the day ended: 7 on the METAR side +9.4 pts [-23, +34] (5 dates), 16 against it, all lost (-34.7).
  The edge per share is real and the size is ~$0.03 per date at 1 share per fill -> DEAD as a strategy (LESSONS 8, 26). Tornado part:
  series stopped (11-05 the last date seen) -> not tested further.
- N48 rain as a running count (11-15 c20, same script): YES fills after the METARs already showed >= 0.01 in that climate day (obs <= fill -
  15 min): 9 / 9 won, +8.5 pts on 4 dates, avg price 0.912 - right, and nine fills in 12 weeks. DEAD (capacity, LESSONS 8/26).
- N25 lock_cheap (forward read-out from 11-14 09:00, c20): lock signals priced < 0.80: 6 trades / 2 won -65.5%/$ on 5 end-times, against
  an in-sample +4.4%; >= 0.80 73 / 68 -0.1% (52 end-times). The cheap 'locks' are the market knowing better (LESSONS 2/14). DEAD.
- N46 month-end RANK markets beyond LMArena (11-15 c19, riskday_census.py, 12-week tape, N45 rule pre-registered): largest / 2nd / 3rd
  largest company: favourite 24-168 h -40.1 pts [-47.4, -0.2] on 6 events (the 0.90 favourites won 44%: Microsoft/NVIDIA/Apple swaps),
  168-720 h -17.0; best / 2nd / 3rd Chinese AI company 6-168 h +0.5 [-9.0, +7.1] (9 events); top Spotify artist 1 event. DEAD by its rule -
  N45's effect is not a 'rank market' effect; a live public number that can swap at month-end is priced too confidently, not too shyly.
- N44 count-bucket favourite on tweet / post counts (11-15 c18, leaderboard_census.py, 12-week tape, 343k taker entries / 133 weekly events,
  N41 rule unchanged): favourite 0.60-0.97 6-24 h before end -3.1 pts [-10.5, +3.2] on 105 events, follower -1.8, newer 6 weeks -7.5
  [-17.5, +0.2]; 1-6 h -5.1. The +11 pts of ship transits (N41) does not generalise to count buckets whose tracker is live -> DEAD by its rule.
- N41 ship-transit count markets (11-15 c17, transit_check.py via Actions): markets ARE live (153: Bab el-Mandeb / Hormuz weekly buckets, 'any day' thresholds, Panama Canal weekly), but the resolving source does not lead: IMF PortWatch (ArcGIS, reachable from Actions) had its last day at 11-08 on 11-15 - a ~7-day lag, so the 'Nov 9-15' buckets resolve about a week AFTER their end date and the last-day price is set by people with faster AIS data, not by a number we can read first. The tape's +11.1 pts [-0.8, +18.8] (29 events) stays an unexplained favourite effect: replicate once on the next tape refresh (new weeks only, same rule) before any tracker. LESSONS 25.
- N43 daily US gas price (AAA) 1-cent buckets (11-15 c17, gas_census.py, 12-week tape: 26 days / 156 markets / 1,560 taker entries, all 6-24 h before end): favourite 0.60-0.97 -4.7 pts [-16.4, +6.4] (26 days), halves -5.1 / -4.6; a linear-trend nowcast from the two previous resolved days hits the bucket only 46% (24 days) and its trades are -0.9 pts [-22, +18]; NO on buckets the nowcast rejects +4.5 [-15, +25] on 19 days. Calibration fine (0.80-0.97 priced 0.90, won 0.87). Nothing here; a real nowcast needs daily station data (GasBuddy/OPIS) we do not have.
- lock_early (11-15 c16, its pre-registered kill rule: 50 settled trades and <= 0): 51 trades 47 won -2.1%/$ on 37 end-times (11-09..11-15).
  All 51 bought at >= 0.80. Autopsy (N40): BTC/ETH 21 / 19 -4.6% (20 end-times), alts 30 / 28 -0.1% - the N21 'majors are cleaner' split does
  NOT carry to the 60-140 s signal, so no lock_early_be variant. The bot still logs it; ignore it in read-outs.
- N40 lock_early on BTC/ETH only (11-15 c16, adjacent, in-sample on data/fast/trades.jsonl): 21 trades -4.6%/$ - dead on arrival.
- N39 central-bank decision markets (11-15 c15, cb_decision_census.py, 12-week tape entries_c: 31 meetings / 129 markets / 31,746 real taker
  entries, fees paid, event-clustered): favourite side 0.60-0.97 bought 24-168 h before the end -0.2 points per share [-29.8, +17.6] on 22 meetings,
  -9.9 equal-weight per meeting; follower 60 s later +0.7 [-30, +18]; non-major banks -1.7 (19 meetings); older 6 weeks +16, newer -12.5 (sign
  flips); 7-30 days out -21.7 [-39.8, -5.2] (30 meetings). Calibration: 0.80-0.90 priced 0.85 won 0.72, 0.90-0.97 priced 0.93 won 0.89 - the
  upsets are real and priced (or under-priced). Only the >= 0.97 bucket is positive, +0.4 [-0.3, +0.9] (28/29 meetings) = cents (LESSONS 8).
  Only 3 Fed/ECB/BoE/BoJ meetings in the window. LESSONS 13: the consensus is public and the market already holds it.
- N37 Trump approval-rating buckets (11-14 c14, approval_census.py via Actions, 382 markets / 101 events Jan 2025 - Feb 2026, RCP average,
  hourly CLOB last prices, +c + fee): the favourite is NOT underpriced - fav side 0.60-0.97 at +2c: end-72h -5.3%/$ (234 / 78 events, both
  halves negative: -7.8 / -2.9%), end-24h -4.6% (79 events), end-6h -0.7% (75); the one positive cell (0.60-0.80 at end-6h +7.9%) is -3.6 and
  -11.7% at the other clocks = noise. Calibration is close (0.30-0.50 priced 0.39, won 0.31-0.44). On last prices, which flatter (LESSONS 3),
  it is already negative. RCP returns 403 to Actions anyway. LESSONS 13.
- N29 / N31 favourite bid (11-14 c13, tape_favbid.py CATS=movies,music,tweets,youtube, raw tapes never used for N28): live peg, first fill per
  market side 500 fills / 180 events, bid 0.967, won 0.964 (18 losses), -0.31 points per share [-2.2, +1.3]; the pre-registered N29 rule (1 h - 7 d,
  no fill after a lower selling print) +0.30 [-1.9, +2.1] on 130 events; music -5.1, movies/youtube +0.7; weighted by prints +1.6 [+0.5, +2.4]
  (LESSONS 23 again). The mention/awards +2.3 does not travel -> the N29 poller is not built.
- N32 maker by the clock (11-14 c13, tape_clock.py, 1.51M taker entries >= 1 h before the end, 12 weeks): maker P&L % of taker cost, weekend -0.3
  [-1.8, +1.2], weekday 04-12 UTC +0.8 [-1.1, +2.8] (older +0.1 / newer +1.5), weekday 12-04 UTC -2.0 [-4.2, -0.3]; points per entry +0.1..+0.15
  everywhere. The informed trade a bit more in US hours but no slot pays a maker anything robust before our own fill selection; per-category
  cells flip between halves (geopolitics night +5.4 [-0.4, +13.2] is a forking path). Kept only as N33's question for LP-1.
- TAPE STUDIES 11-14 (deep session; research/slow/tape_census.py, tape_entries.py + tape_*.py; public data-api trade tape, real fills, fees
  paid, event-clustered bootstrap; 12 weeks: culture 10,169 markets / 1.40M trades, weather 29,508 / 2.19M, politics-economy-tech-geo 9,256 / 1.87M):
  - 'Be the house' (passive maker / reward farmer in slow categories): maker P&L as % of taker volume, 6-week census: weather -0.9 [-1.4, -0.4],
    youtube -3.8 [-5.9, -1.2], movies -1.9 [-3.7, -0.3], mention pre-event -2.2 [-4.1, 0.0]; 12 weeks: takers after fees +2.7% of cost mention,
    +3.7% movies, +2.6% ai/tech (half of it one event), +0.2% weather; makers only win where the flow is opinion (politics takers -1.6%). LESSONS 17.
  - Combo (RFQ parlay) maker: 99,599 resolved maker positions / 46 days: -$497k = -3.8% of the bettors' $13.0M stake; tickets < $5 +11.4%
    [2.5, 20.3], >= $10k -25.5% (94 tickets = -$413k); the four small makers lost 8-14% of stake and quit in 1-3 weeks. Small requester: no
    robust edge (combo price / product of legs median 1.03; the bettor-friendly weeks are the last three only). Sampler stays off (needs the user's OK).
  - Follow big taker orders: orders >= $1,000 (13,002 / 968 events): -1.65 points per share [-5.8, +1.6] at their own price; first per
    market+direction+day (6,165): -0.2 [-1.7, +1.3], follower at the next same-way print -1.2 [-2.8, +0.2]; >= $10,000: -10.4 [-21.0, -0.8] (the
    Iran-ceasefire YES pile-up). The 6-week '+6.4 [3.2, 9.9]' was 61 sampled events (LESSONS 22). Wallets with winning BIG orders do not persist (-1.0).
  - Copy sharp wallets a minute later / rest bids under them: persistence is real (+1.6 [1.1, 2.1] at their prices, out of sample) but the next
    print by others keeps +0.5 [-0.1, +1.1] (whales 0.0); passive bids below their price fill 54-76% and lose 3.2 [-5.3, -1.3]. Real-time copy is
    the one open variant -> COPY-1 in TESTING.
  - Buy near-certain outcomes ('bonds') as a taker: price 0.80-0.90 -2.8 [-3.3, -2.2], 0.90-0.95 -2.5 [-3.0, -2.1], 0.95-0.98 -1.9 [-2.2, -1.6],
    0.98-0.995 -1.1 [-1.3, -0.9] points per share after fees (one unit per market side, ~4,000-4,600 events, every category, every month Aug-Nov);
    tally markets (leaderboards, charts, box office, counts) -1.8 [-2.8, -1.0] at 0.90-0.98, no better than opinion markets (-2.3). Real BUYS of the
    favourite lose 0.7-1.2 (spread + fee); the larger part is holders dumping the cheap side at its bid (-3.5..-5.1). This also closes N19 as a taker.
  - Resting bids on the cheap side (the mirror of the above): pegged to the last print -1.8 [-2.6, -0.8] (falling knives); pegged live, one fill
    per market side: -0.1 [-1.0, +0.9]. The '+2 points for the maker' exists only per market side, not per fill we would get (LESSONS 23).
  - Mention markets, blanket NO (first real NO fill per market at <= 0.50, >= 1 h before the start; 1,967 markets / 266 events): +9.3 points
    [6.4, 12.3] over 12 weeks = +16.9 [13.2, 21.0] in Aug 17 - Sep 30 and +0.8 [-3.0, +4.2] in Oct - Nov (Trump +1.2, earnings -5.9 [-11.2, -0.2],
    other +5.0 [-2.8, 12.8]); YES share of resolutions rose from 42% to 49%. Gone (LESSONS 24). Still true in both halves: YES bought at 0.50-0.95 in
    the last 24 h loses 6 points (-6.7 / -5.8) - a reason not to buy YES, not a trade (NO in the same window +1.8 [-2.2, +6.3] in the newer half).
- converge_day / N23 last-day favourites 0.95-0.99, with or without a war filter (11-14 c10, research/slow/converge_geo_split.py on the
  5-month hourly history, 755 non-sports non-crypto markets / 750 events Jun-Nov, first price in the last 24 h, +0.5c + fee): 24 losses
  (3.2%, priced ~3.5%) -1.3%/$; geopolitics keyword set (fixed before looking) 280 / 6 losses -0.4%, the rest 475 / 18 -1.9% (primaries,
  World Cup awards, a tweet bucket, a WTI touch, model releases). Calibrated; the tail is everywhere, not just war news. converge_day removed
  from the slow job (it had also never entered: 0 candidates - likely the 1-day Gamma window filled by up/down markets before the offset cap).
- N20 UMA proposal window (11-14 c9, research/slow/uma_window.py on 1,308 15-min book snapshots 10-31..11-14, 7,814 closed markets):
  in the last 2 h before closedTime, the 19 non-sports UMA markets we recorded had the winner at ask 0.999 (17/19); the 2 cheaper ones were
  Binance-candle markets before the candle closed (not a proposal gap). Sports (2,100) are auto-resolved and the window is the live game.
  Caveat: the recorder drops most non-sports markets after their end date (19 of 1,829 seen in the window), so this is thin - but every
  market seen is at 0.999, i.e. cents at best (LESSONS 8) and bots read the oracle (LESSONS 1). Not worth a post-end recorder.
- Weather W1 ensemble model as an edge (11-13 c8, weather_score.py via Actions, 66 settled events / 726 buckets on 11-12 and 11-13):
  Brier model .0732 vs market .0635 (market better on both days); winning bucket model p .201 vs market .334. Paper positions: NO side
  127 bets, model expected 103.5 wins, market 81.0, actual 82 -> the model is overconfident, the market is right; YES 29 bets 5 won +$79,
  of which +$78 is one 6c Taipei bucket (without it +$0.8). LESSONS 9 again. weather_paper keeps logging to 11-22 (cheap), no promotion.
- lock_mv (volatility filter on lock_m, 11-13 c8): 34 / 32 -0.6%/$; its trades outside lock_x 22 / 20 -6.4% (17 end-times). Its good
  part is lock_x.
- Touch ladders, taker (N17, 11-13, hit_census.py: 352 weekly + 156 monthly stock/commodity 'hit (HIGH/LOW)' events 2026-04..11-06, 4,592
  rungs with hourly last prices, crypto not reached in the time budget): touch YES is RICH - at start + 24 h YES priced 0.27 resolved
  0.17, 0.43 -> 0.35; dip touches (LOW) worst (YES 0.1-0.5 -47%/$, HIGH -25%). NO on YES 0.30-0.50: +9.4%/$ at +2c + fee (1,052 rungs,
  283 events, 19/28 weeks positive), +4.3% at +5c; at mid-life +0.7%. But the real NO ask on these ladders in their first 72 h is NO
  mid + 13c (median, 36 young-paper rungs, week of 11-09) and last prices overstate NO edges (mention census +15% -> negative at Kalshi
  asks). At +13c the edge is gone; the week of 11-09 (-$168 on 36 rungs) is one of the 9/28 losing weeks. Kept as maker idea N17b.
- Sports favourite-longshot bias (11-13): the 15-min books said pre-game favourites 0.60-0.90 won above their ask (+2..+10%/$, ~340
  markets, 2 weeks; NBA 15/15). 5 months of history (hist_prices.py, 8,871 moneylines with prices, Jun-Nov): leagues where every game
  has big volume are CALIBRATED at 3 h before the start - MLB won 60.7% at price 60.5%, NHL 62.9/63.0, NFL 68.2/67.1, esports 70.0/70.2;
  after +0.5c and the fee, majors + esports: favourite -2.0%/$ (n 629), underdog -7.2%. The 'favourites lose' gap in other leagues
  (-4 pts, n 3,999) grows with FINAL volume (-2.5 / -3.6 / -5.8 pts by tercile; inside MLB +7.9 -> -4.3) = selection, not an edge.
  No pre-game drift either (buy 24/12/6 h before, sell before the start: -1.4..-6.8%). Tracker removed.
- Mention markets NO as a taker (N8/N14, 11-13, kalshi_mentions.py: Kalshi hourly candles with the real yes bid/ask, 473 mention
  series, 9,623 settled markets / 494 events): YES is only 0-6 pts rich at the MID (e.g. mid 0.35 said 0.33, mid 0.47 said 0.42-0.43)
  and the spread is 3-9c, so NO bought at 1 - yes_bid loses in EVERY band: -0.1..-13.7%/$ 3 h before, -0.7..-23% 24 h before (events
  positive 41-208 of 187-262). The Polymarket census +14.6% was last-trade prices (LESSONS 3). mention_paper kept only as a spread log.
  Possible maker version (sell YES at the ask into retail buyers) untested, low prior (adverse selection from people who know the script).
- W2 recount (11-14 c11, all 20,625 sameday rows): 7,797 dead-bucket rows; after the 11-13 09:10 fix 2 of 3,537 have a YES bid >= 1c (Munich
  5C at 10:13 local bid 10c, LA 64-65F at 01:13 local bid 1.7c); the 20 pre-fix rows (and the 22 listed in weather_score.json) are all in
  local hours 00-10, i.e. the old clock bug carrying the previous day's obs. W2 stays DEAD; the open 'two scripts disagree' item is closed.
- Weather W2 same-day dead buckets (11-13, data/weather/sameday.jsonl after the obsTime fix, 1,705 rows / 719 dead-bucket rows):
  0 with a YES bid >= 1c, 0 with a NO ask <= 0.985 - bots clear them. The one pre-fix case (London 7C bid 6.5c, resolved NO) was a one-off.
- Websocket-speed lock_m / lock_b replay / 15m-only (11-13, server lockm.jsonl 11-11 13h..11-13 15h, 389 window-trades at 0.1 s): split by
  whether the paper bot was running in the window's last minute - bot running: 137 trades on 95 end-times (1.4 each), 92.6% won, -0.3%/$ at
  0.1 s, -0.9% at 1 s, -6.4% at 2 s (rx, cap 0.97, 5m); bn the same (+1.3 / -2.1%); 15m 16 trades +3.4%. Bot stopped (our hourly hook, one
  slot per hour drifting ~5 min/h): 252 trades on 40 end-times (4.8 each), +14..+20%/$, and the count barely falls from R 0.1 s to 2 s
  (184 -> 179) - cheap asks that 'persist' are a frozen recording. Where replay and paper both traded (61 windows) prices agreed (0.929 vs
  0.924) and P&L was +1.3%. The heavy replay in the hook (650 MB, 927 MiB box) made the recorder fall behind (LESSONS 14). Hook step removed;
  lag_check server job measures recording lag by minute.
- Time-of-day / dip buying of slow favourites (N15, 11-13, tod_asks.py, 1,261 book snapshots, 192 tokens / 189 events): asks lowest 04-05 UTC
  but only -0.13c vs the day median (max-min 0.22c; placebo p95 0.08c); weekends not cheaper; 1c dips: ask +0.97c and bid +0.21c over the dip
  ask 24 h later (70 events). Cents (LESSONS 8); kept only as an entry rule idea (N15b).
- lock_m cool-down after a loss (N9, 11-13, paper lock_m 133 trades / 8 losses on 7 end-times): no clustering - trades within 30 min after a
  loss 3/4 -5.7%, within 60 min 11/12 +9.1% vs rest +0.2%; losses share an end-time only once (2 trades). Nothing to skip on.
- Earnings beat base rate (N6, 11-13, 470 closed 'beat quarterly earnings?' markets, 2025-09..2026-03, earnings_beat_census.py): the
  market already prices the ~73% beat rate - D-1 avg price 0.734 vs YES 0.737, Brier .156 vs base rate .194. YES all -2.2%/$ at +2c,
  YES 0.40-0.80 -10.2% (calibration 0.7-0.8 band: 0.75 priced, 0.67 won), YES 0.80-0.95 +0.6% (= 0 after fee), 2026 half -7.6%. NO 0.80-0.97
  +15% on 7 cases only. Lesson 13.
- Box-office preview momentum (11-12, 134 films): buy the direction of the Thu 22 -> Fri 18 UTC move at Fri 18 + 2c: +4.7%/$ on
  111 films, but a placebo with no news (Wed 22 -> Thu 18) gives +8.4%, entry at Fri 16/20/23 UTC +1.9/0.0/-3.7%, newest period -4.5%;
  move vs residual corr 0.07. Hourly-price noise, not under-reaction. The Fri 18 -> Sat 18 move: -13%/$ (overshoot, not drift).
- Maker on a lock (11-12, local 11-08..11-10, exact K, prints by receive time): rest a bid 0.90-0.97 on the locked side
  while z >= 2.5: fills come only from sellers who know better - filled windows won 48-67%, -28..-38%/$.
- Nested windows (11-12): a 5m and a 15m window ending the same second resolve on the same TWAP, so Up(lower K) +
  Down(higher K) pays >= $1. Riskless (asks + fees < $1) in 9 of 463 pairs, 3-32 shares, cents each; at fixed times the
  pair is fairly priced (-1..-3% = spread + fees).
- After the end (11-12): books and trades go on ~30 s past the end, when the final TWAP is already known, but no
  winner ask under 0.99 after end + 2 s in 7 h of recordings.
- Flow filter for locks (server flow_v3, 239 windows, 11-11 18h..11-12): flow toward Up -> outcome 8.3 pts BELOW the mid
  (n 36), toward Down -1.6 (n 42): the local +4.2 / -6.1 did not replicate.
- Late favourite at the ask, server sample (flow_v3): -31%..+5%/$ by band; the only positive cell (0.90-0.95 at 20 s,
  n 14) is noise next to its neighbours.
- Earlier lock entries 1-4 min before the end (replay, 11-12): z >= 3 at 60-140 s -0.2%/$, z >= 2.5 at 140-240 s 0.0%,
  z >= 3.5 anywhere 60-240 s -17%.
- Late favourite at the ask, no model (local recordings, 11-12): buy the side whose best ask is 0.60-0.95 at 20/40/60 s
  before the end: -36%..+0.1%/$ (cheap asks that survive late are cheap for a reason). The mid-based +10 pts was the spread.
- Weather fair value from a 2-day-old deterministic forecast (11-01): Brier .199 vs market .164. Known-outcome weather after the day's max (11-02): bots, winner at $1.00 in 99%.
- Date-ladder arbitrage (11-02, 468 ladders; 11-11 census again): cents.
- Big sparse ridge (11-02, 39k features, 1M rows): +1.5c val / -0.4c lockbox on fair rows - no robust edge.
- 5m: dog, fav, exact, pairs (rare), sweeper (~0 after fees), maker replays, copy-trading, flow-filtered MM.
- 5m window-start mispricing (exact K, 2,000 windows): the market beats the model even at rem 270-300 s (Brier 0.219 vs
  0.221); trading the gap -6.5..-10.7%/$.
- Ridge / logistic-ridge with 45 features: log loss 0.326 vs market 0.325; error not predictable (test R^2 -0.14).
- Cross-asset (BTC leads alts): coefficient 0.02; rule -11..-26%/$.
- Parity maker (15m/5m pairs): one leg fills in 45%, -$380 on 554 pairs.
- Jump chaser: 38% win, -23%/$.
- Spike fade (slow markets): 96 24-h exits -17.6%.
- Longshot NO (YES 2-10c): fairly priced (~0 except +0.75% in the last week).
- Endgame after the end date: 0.97-0.995 +0.17%/position.
