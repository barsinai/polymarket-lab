"""Cycle 49, N107 out-of-sample pull for the herd-follow rule (N106's HERD arm, found by looking -> lesson 22 needs a second period).
Runs on GitHub Actions via run_script.yml (read-only public trade tape, no orders): pulls groups a, b, c for the last 2 weeks of closed
markets into entries_<g>_oos1 (the canonical 12-week tapes are NOT touched), then scores the rule fixed in c49 ONLY on markets that end
after the newest end in the canonical tape (never seen):
  market with >= 31 first entries, finished; share = YES cost share of the first 30 entrants; HERD if >= 0.80 or <= 0.20;
  follow = first majority-direction entry after the 30th, scored at its a300 (0.05-0.95), >= 1 h left, fee rate * p(1-p).
  Prints all / a300 0.70-0.92 / share >= 0.9, unit = event, bootstrap 1,000; BASE (any market, first entry after the 30th with a300
  0.70-0.92) as the control.
PASS (-> forward paper tracker) if HERD all >= +2 pts with >= 100 events and HERD_B - BASE >= +2; else DEAD."""
import os, sys, json, gzip, struct, collections, random, datetime as dt, runpy, subprocess, time
T_ALL = time.time()
for g in ("" if os.environ.get("SKIP_PULL") else "abc"):
    env = dict(os.environ, GROUP=g, WEEKS="2", OUT_TAG="_oos1", T_MAX="950")
    subprocess.run([sys.executable, "-u", "research/slow/tape_entries.py"], env=env, check=False)
    print(f"group {g} pulled, {time.time() - T_ALL:.0f}s", flush=True)

ROW = struct.Struct("<IIIhfffHHHIB"); B = "data/research/"; random.seed(107); R = []
for g in "abc":
    try:
        old = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); new = json.load(gzip.open(f"{B}entries_{g}_oos1_meta.json.gz"))
    except FileNotFoundError:
        print("missing", g); continue
    cut = max(m[4] for m in old["markets"]); MK = new["markets"]
    at = dt.datetime.strptime(new["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}_oos1.bin.gz").read()):
        if cut < MK[mi][4] < at: ent[mi].append((t, C, a300, fl))
    for mi, E in ent.items():
        if len(E) < 31: continue
        m = MK[mi]; E.sort(); head = E[:30]; tot = sum(e[1] for e in head)
        if tot <= 0: continue
        share = sum(e[1] for e in head if e[3] & 1) / tot; herd = share >= 0.8 or share <= 0.2; maj = 1 if share >= 0.5 else 0
        def add(arm, e):
            t, C, a300, fl = e; p = a300 / 1e4
            if m[4] - t < 3600 or not 0.05 <= p <= 0.95: return
            R.append(dict(e=f"{g}:{m[1]}", g=g, arm=arm, s=max(share, 1 - share), p=p,
                          f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
        b = next((e for e in E[30:] if 7000 <= e[2] <= 9200), None)
        if b: add("BASE", b)
        if herd:
            h = next((e for e in E[30:] if (e[3] & 1) == maj and e[2] > 0), None)
            if h:
                add("HERD", h)
                if 7000 <= h[2] <= 9200: add("HERD_B", h)


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)])


out = {a: stat([r for r in R if r["arm"] == a]) for a in ("HERD", "HERD_B", "BASE")}
out["HERD share>=0.9"] = stat([r for r in R if r["arm"] == "HERD" and r["s"] >= 0.9])
for g in "abc": out[f"HERD group {g}"] = stat([r for r in R if r["arm"] == "HERD" and r["g"] == g])
H, HB, BA = out["HERD"], out["HERD_B"], out["BASE"]
ok = H.get("events", 0) >= 100 and H["pts"] >= 2 and HB.get("pts") is not None and BA.get("pts") is not None and HB["pts"] - BA["pts"] >= 2
out["verdict"] = "PASS" if ok else "DEAD"
json.dump(out, open(f"{B}herd_oos_report.json", "w"), indent=1)
print(json.dumps(out, indent=1))
