#!/usr/bin/env python3
"""Roda 12 trials adicionais de c7g.large horizontal H.265 (max 3 simultâneos)."""
import os, subprocess, threading, re, statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_DIR     = os.path.join(SCRIPT_DIR, "arm_h265_new_logs")
HORIZ_SCRIPT= os.path.join(SCRIPT_DIR, "c7g_large_horizontal_libx265.py")
N_TRIALS    = 12
START_IDX   = 31   # logs: trial_31 .. trial_42

sem   = threading.Semaphore(3)
lock  = threading.Lock()
times = []
errors= 0

def run_trial(idx):
    global errors
    log_path = os.path.join(LOG_DIR, f"c7g_horiz_trial_{idx:02d}.log")
    with sem:
        result = subprocess.run(["python3", HORIZ_SCRIPT],
                                cwd=SCRIPT_DIR, capture_output=True, text=True)
        with open(log_path, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n"); f.write(result.stderr)
        m = re.search(r'Total Time:\s+([\d.]+)s', result.stdout)
        with lock:
            if result.returncode == 0 and m:
                times.append(float(m.group(1)))
                t = float(m.group(1))
                print(f"[{datetime.now().strftime('%H:%M:%S')}] trial_{idx:02d} done: {t:.1f}s  (n={len(times)}/12)", flush=True)
            else:
                errors += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] trial_{idx:02d} ERROR", flush=True)

print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando 12 trials extras (max 3 simultâneos)...")
with ThreadPoolExecutor(max_workers=12) as pool:
    futs = [pool.submit(run_trial, START_IDX + i) for i in range(N_TRIALS)]
    for f in as_completed(futs):
        pass

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Concluído: {len(times)} ok, {errors} erros")
if len(times) >= 2:
    med = statistics.median(times)
    std = statistics.stdev(times)
    cv  = std / statistics.mean(times) * 100
    print(f"  med={med:.1f}s  std={std:.1f}s  CV={cv:.1f}%")
