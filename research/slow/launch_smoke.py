"""Smoke test of launch_paper.py on the live public API (no orders): 6 minutes, output to data/research/launch_smoke/."""
import os, runpy
os.environ.update(LN_DIR="data/research/launch_smoke", RUN_MIN="6", POLL="120")
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_paper.py"), run_name="__main__")
