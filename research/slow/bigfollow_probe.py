"""Dry run of the big-order follow paper tracker for a few minutes with its state in /tmp (nothing is saved to the repo):
does the feed parse, how many fills / pages / crossings per poll, what do the triggers look like."""
import os, runpy, json, glob
os.environ.update(RUN_MIN="6", BF_DIR="/tmp/bf_probe", BF_CACHE="/tmp/bf_probe_cache.json")
runpy.run_path(os.path.join(os.path.dirname(__file__), "big_follow_paper.py"), run_name="__main__")
for f in sorted(glob.glob("/tmp/bf_probe/*")):
    L = open(f).read().split("\n")
    print(f"\n== {f}: {len(L)} lines")
    print("\n".join(x[:900] for x in L[:25]))
c = json.load(open("/tmp/bf_probe_cache.json"))
print("\ncache: events", len(c["e"]), "markets", len(c["m"]))
print("event tags sample:", json.dumps(dict(list(c["e"].items())[:25]))[:3000])
