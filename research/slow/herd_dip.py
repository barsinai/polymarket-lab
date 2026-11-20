"""Cycle 50, N108 (adjacent to N107): in a one-sided market, follow the herd only on a PULLBACK.
Why the crowd could be wrong: N107 says a lopsided first crowd (>= 80% of the first 30 entrants' $ one way) is right more often than
its price says. If the herd is right, a later dip against it (the price for the herd side falls below what the herd paid) is the
stubborn minority or a forced seller pushing a correct favourite cheaper - a better entry than the next herd-way print at any price.
Exposed to 2 (a dip that survives can be news the herd missed), 22 (N107 itself was found by looking), 24, 11, 15.
Rules fixed BEFORE looking: same HERD markets as N106/N107 (finished, >= 31 first entries, share >= 0.80 or <= 0.20). vwap = majority-
direction cost / shares over the first 30 entries. DIP = the first majority-direction entry after the 30th whose a300 <= vwap - 0.03;
HERD = the first majority-direction entry after the 30th (N107 arm, the comparison). Scored at a300 (0.05-0.95), >= 1 h left, fee
rate * p(1-p). Unit = event, bootstrap 1,000, halves by end date. Run on the canonical tapes a + b + c AND on the unseen oos1 markets
(condition id not in the canonical tape, c50 fix).
DECISION: forward paper arm only if canonical DIP - HERD >= +1.5 pts with >= 200 events, both halves DIP >= +2, and OOS DIP >= +2."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB"); B = "data/research/"; random.seed(108); R = []
for tape in ("canon", "oos"):
    for g in "abc":
        old = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz"))
        if tape == "canon":
            meta, path, keep = old, f"{B}entries_{g}.bin.gz", None
        else:
            meta, path, keep = json.load(gzip.open(f"{B}entries_{g}_oos1_meta.json.gz")), f"{B}entries_{g}_oos1.bin.gz", {m[0] for m in old["markets"]}
        MK = meta["markets"]; at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
        ent = collections.defaultdict(list)
        for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(path).read()):
            if MK[mi][4] < at and (keep is None or MK[mi][0] not in keep): ent[mi].append((t, C, S, a300, fl))
        for mi, E in ent.items():
            if len(E) < 31: continue
            m = MK[mi]; E.sort(); head = E[:30]; tot = sum(e[1] for e in head)
            if tot <= 0: continue
            share = sum(e[1] for e in head if e[4] & 1) / tot
            if not (share >= 0.8 or share <= 0.2): continue
            maj = 1 if share >= 0.8 else 0
            mc = sum(e[1] for e in head if (e[4] & 1) == maj); ms = sum(e[2] for e in head if (e[4] & 1) == maj)
            if ms <= 0: continue
            vwap = mc / ms
            for arm, pick in (("HERD", lambda e: True), ("DIP", lambda e: e[3] / 1e4 <= vwap - 0.03)):
                nx = next((e for e in E[30:] if (e[4] & 1) == maj and e[3] > 0 and pick(e)), None)
                if not nx: continue
                p = nx[3] / 1e4
                if m[4] - nx[0] < 3600 or not 0.05 <= p <= 0.95: continue
                R.append(dict(tape=tape, e=f"{g}:{m[1]}", arm=arm, end=m[4], p=p, f=(1 if nx[4] & 2 else 0) - p - m[7] * p * (1 - p)))


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)], avg_p=round(sum(r["p"] for r in rr) / len(rr), 3))


out = {}
for tape in ("canon", "oos"):
    for arm in ("HERD", "DIP"):
        rr = [r for r in R if r["tape"] == tape and r["arm"] == arm]
        if not rr: continue
        med = sorted(r["end"] for r in rr)[len(rr) // 2]
        out[f"{tape} {arm}"] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]))
c = lambda k, s="all": out.get(k, {}).get(s, {}).get("pts", -99)
ok = (out.get("canon DIP", {}).get("all", {}).get("events", 0) >= 200 and c("canon DIP") - c("canon HERD") >= 1.5
      and c("canon DIP", "older") >= 2 and c("canon DIP", "newer") >= 2 and c("oos DIP") >= 2)
out["verdict"] = "PAPER" if ok else "DEAD"
json.dump(out, open(f"{B}herd_dip_report.json", "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v))
