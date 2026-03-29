#!/usr/bin/env python3
"""Re-run c7g.large horizontal H.265 com upload serializado (v2). 30 trials, max 2 simultâneos."""
import os, subprocess, threading, re, statistics, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_DIR      = os.path.join(SCRIPT_DIR, "arm_h265_v2_logs")
HORIZ_SCRIPT = os.path.join(SCRIPT_DIR, "c7g_large_horizontal_libx265_v2.py")
N_TRIALS     = 30

os.makedirs(LOG_DIR, exist_ok=True)

sem   = threading.Semaphore(2)   # max 2 trials simultâneos = max 2 uploads concorrentes
lock  = threading.Lock()
times = []
errors = 0

def run_trial(idx):
    global errors
    log_path = os.path.join(LOG_DIR, f"c7g_horiz_v2_trial_{idx:02d}.log")
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
                t = float(m.group(1))
                times.append(t)
                ts = datetime.now().strftime('%H:%M:%S')
                med = statistics.median(times)
                cv  = statistics.stdev(times)/statistics.mean(times)*100 if len(times)>1 else 0
                print(f"[{ts}] trial_{idx:02d} ✓  {t:.1f}s  | n={len(times)}/30  med={med:.0f}s  CV={cv:.1f}%", flush=True)
            else:
                errors += 1
                ts = datetime.now().strftime('%H:%M:%S')
                print(f"[{ts}] trial_{idx:02d} ✗  ERROR (rc={result.returncode})", flush=True)

print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando 30 trials v2 (max 2 simultâneos, uploads sequenciais)...")
with ThreadPoolExecutor(max_workers=N_TRIALS) as pool:
    futs = [pool.submit(run_trial, i+1) for i in range(N_TRIALS)]
    for f in as_completed(futs): f.result()

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Concluído: {len(times)} ok, {errors} erros")
if len(times) >= 2:
    med = statistics.median(times)
    std = statistics.stdev(times)
    cv  = std / statistics.mean(times) * 100
    print(f"  med={med:.1f}s  std={std:.1f}s  CV={cv:.1f}%")
