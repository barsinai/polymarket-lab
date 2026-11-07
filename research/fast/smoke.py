"""Short end-to-end run of the paper bot on a GitHub runner (writes to /tmp, nothing committed)."""
import os, sys
os.environ.update({"FAST_DIR": "/tmp/fastsmoke", "RUN_MIN": "5", "LAST_S": "120"})
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import updown_paper  # noqa: E402
updown_paper.main()
import json, glob  # noqa: E402
for f in ("obs.jsonl", "trades.jsonl", "windows.jsonl"):
    try:
        lines = open(f"/tmp/fastsmoke/{f}").read().splitlines()
        print(f, len(lines)); [print("  ", l[:260]) for l in lines[-4:]]
    except OSError:
        print(f, "missing")
print("rtds files", glob.glob("/tmp/fastsmoke/rtds/*"))
