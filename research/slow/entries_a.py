"""tape_entries.py for group a (see that file)."""
import os, runpy
os.environ["GROUP"] = "a"
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tape_entries.py"), run_name="__main__")
