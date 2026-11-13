"""Recording health on the server (one-off): how late does the book websocket arrive (rx - exchange ts), minute by minute,
over the last 30 h of archives? Hypothesis (11-13): while the hourly hook ran heavy replays (ulimit 650 MB on a 927 MiB box),
the recorder fell behind, so book records were stamped seconds late and a replay saw cheap asks that were already gone
(lockm.jsonl: 4.8 trades per end-time and +14..+20%/$ in hook windows vs 1.4 and ~0% when the bot was running).
Streams line by line (no JSON parse), keeps per-minute counters only."""
import glob, gzip, os, time, json
from collections import defaultdict

B = os.environ.get("BOOKWS_DIR", "/home/runner/pilot-data/bookws")
now = time.time()
files = [f for f in sorted(glob.glob(f"{B}/*.jsonl*")) if os.path.getmtime(f) > now - 31 * 3600]
mins = defaultdict(lambda: [0, 0, 0, 0, 0.0])      # minute -> n, lag>0.25, lag>0.5, lag>1, max lag
for f in files:
    op = gzip.open if f.endswith(".gz") else open
    try:
        fh = op(f, "rt")
        for line in fh:
            i = line.find('"ts":"')
            j = line.find('"rx":')
            if i < 0 or j < 0:
                continue
            try:
                ts = int(line[i + 6:line.find('"', i + 6)]) / 1000.0
                k = j + 5; e = k
                while e < len(line) and line[e] in "0123456789.":
                    e += 1
                rx = float(line[k:e])
            except ValueError:
                continue
            lag = rx - ts
            m = mins[int(rx // 60)]
            m[0] += 1; m[1] += lag > 0.25; m[2] += lag > 0.5; m[3] += lag > 1.0
            if lag > m[4]:
                m[4] = lag
    except Exception as ex:  # noqa: BLE001
        print("skip", f, ex)
bad = sorted(k for k, v in mins.items() if v[0] >= 100 and v[2] / v[0] > 0.05)
tot = sum(v[0] for v in mins.values())
print(json.dumps({"files": len(files), "minutes": len(mins), "messages": tot,
                  "share_lag_gt_0.5s": round(sum(v[2] for v in mins.values()) / max(tot, 1), 4),
                  "bad_minutes": len(bad)}))
# group bad minutes into episodes and print them (UTC), with the minute-of-hour pattern
eps = []
for k in bad:
    if eps and k - eps[-1][1] <= 2:
        eps[-1][1] = k
    else:
        eps.append([k, k])
for a, b in eps:
    w = [mins[x] for x in range(a, b + 1) if x in mins]
    n = sum(v[0] for v in w)
    print(time.strftime("%m-%d %H:%M", time.gmtime(a * 60)), "-", time.strftime("%H:%M", time.gmtime(b * 60)),
          f"msgs {n}  lag>0.5s {sum(v[2] for v in w) / max(n, 1):.0%}  lag>1s {sum(v[3] for v in w) / max(n, 1):.0%}  max {max(v[4] for v in w):.1f}s")
