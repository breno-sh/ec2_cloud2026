#!/usr/bin/env python3
"""
Runs m7g_large_horizontal_libx265.py exactly 30 times, saving each run to
n30_logs/m7g_large_horizontal_libx265_run_N.log

Methodology matches run_n30.py: each run is an independent subprocess,
logs captured to individual files, no state shared between runs.
"""
import os, subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "m7g_large_horizontal_libx265.py")
LOG_DIR = os.path.join(SCRIPT_DIR, "n30_logs")
N_RUNS = 30

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

os.makedirs(LOG_DIR, exist_ok=True)

for i in range(1, N_RUNS + 1):
    log(f"--- Starting run {i}/{N_RUNS} ---")
    result = subprocess.run(["python3", SCRIPT], cwd=SCRIPT_DIR,
                            capture_output=True, text=True)
    log_file = os.path.join(LOG_DIR, f"m7g_large_horizontal_libx265_run_{i}.log")
    with open(log_file, "w") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
    if result.returncode != 0:
        log(f"ERROR on run {i} — see {log_file}")
    else:
        # Extract Total Time from log for progress tracking
        for line in result.stdout.splitlines():
            if "Total Time:" in line:
                log(f"Run {i} OK — {line.strip()}")
                break

log(f"ALL {N_RUNS} RUNS COMPLETED.")
