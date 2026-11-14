"""Dry run of the follow-the-winning-wallets paper tracker for a few minutes with its state in /tmp (nothing is saved to the repo):
does the feed parse, how many fills / pages / crossings per poll, what do the positions look like."""
import os, runpy, json, glob
os.environ.update(RUN_MIN="6", BF_DIR="/tmp/bf_probe", BF_CACHE="/tmp/bf_probe_cache.json")
runpy.run_path(os.path.join(os.path.dirname(__file__), "follow_paper.py"), run_name="__main__")
for f in sorted(glob.glob("/tmp/bf_probe/*")):
    L = open(f).read().split("\n")
    print(f"\n== {f}: {len(L)} lines, {os.path.getsize(f)} bytes")
    print("\n".join(x[:700] for x in L[:60]))
