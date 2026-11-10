"""Score the research-track journal (runs on the generic runner, needs Gamma): = forecast_log.py score"""
import runpy, sys
sys.argv = ["forecast_log.py", "score"]
runpy.run_path("research/slow/forecast_log.py", run_name="__main__")
