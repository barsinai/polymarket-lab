"""Cycle 19 follow-up to riskday_census.py (N47): split the tape by what was PUBLIC at entry time, using the resolution rules read by
riskday_check.py. Tornado: resolves on the 01:00 UTC SPC Day 1 update, market ends 12:00 UTC the next day -> hb < 11 = after the final
polygon was public. Rain: NWS CLI issued next morning, market ends 19:00 UTC next day -> hb < 6 = CLI out; 6-13 = climate day over
(US local midnight ~05-08 UTC), METARs complete; 13-24 = observation day running; 24-48 = before the day.
Rows: all taker entries 0.03-0.97 (both sides), points per share after fees, event-clustered."""
import runpy, sys, io, contextlib, collections
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path("research/slow/riskday_census.py")
R, stat = g["R"], g["stat"]
for fam, cuts in (("tornado", ((1, 11), (11, 24), (24, 72))), ("rain", ((1, 6), (6, 13), (13, 24), (24, 48)))):
    F_ = [r for r in R if r["f"] == fam]
    for lo, hi in cuts:
        rows = [r for r in F_ if lo <= r["hb"] < hi]
        for name, sel in (("fav 0.60-0.97", lambda r: 0.60 <= r["p"] <= 0.97), ("mid 0.20-0.60", lambda r: 0.20 <= r["p"] < 0.60),
                          ("long 0.03-0.20", lambda r: 0.03 <= r["p"] < 0.20)):
            v = [r for r in rows if sel(r)]
            print(f"{fam:8} hb {lo:>2}-{hi:<2} {name:15}", stat(v), "avg_p", round(sum(r["p"] for r in v) / len(v), 3) if v else None)
