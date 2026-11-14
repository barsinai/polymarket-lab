"""Read-only look at how Polymarket combos (parlays, RFQ-priced) are exposed: SDK source lines that mention combo / rfq,
the hosts and paths they use, and whether any combo data (eligible markets, executed combo trades, quotes) is public without keys.
No keys, no orders, no quote requests."""
import os, re, subprocess, sys, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "polymarket-client"], check=False)
import importlib
try:
    import polymarket
except Exception as e:  # noqa: BLE001
    print("import failed", e); sys.exit(0)
d = os.path.dirname(polymarket.__file__)
print("polymarket-client", getattr(polymarket, "__version__", "?"), d)
files = []
for root, _, fs in os.walk(d):
    for f in fs:
        if f.endswith(".py"):
            files.append(os.path.join(root, f))
print(len(files), "files")
pat = re.compile(r"combo|rfq|parlay", re.I)
hosts = set(); shown = 0
for f in sorted(files):
    try:
        src = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:  # noqa: BLE001
        continue
    for h in re.findall(r"https?://[A-Za-z0-9./_\-{}:]+", src):
        hosts.add(h)
    lines = src.split("\n")
    hit = [i for i, ln in enumerate(lines) if pat.search(ln)]
    if hit and shown < 420:
        print(f"\n=== {os.path.relpath(f, d)} ({len(hit)} lines mention combo/rfq)")
        for i in hit[:60]:
            ln = lines[i].strip()
            if ln.startswith("#") and len(ln) > 160:
                ln = ln[:160]
            print(f"  {i + 1:5}: {ln[:210]}"); shown += 1
print("\nhosts in the SDK:", sorted(hosts)[:80])
