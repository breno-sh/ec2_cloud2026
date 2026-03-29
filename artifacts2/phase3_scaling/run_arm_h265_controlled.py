#!/usr/bin/env python3
"""
Orquestrador CONTROLADO para experimentos ARM H.265 faltantes.

Experimentos:
  - m7g.large serial H.265: 10 instâncias × 3 runs = 30 medições
  - c7g.large serial H.265: 10 instâncias × 3 runs = 30 medições
  - c7g.large horizontal H.265: 30 trials, max 3 simultâneos (10 inst. cada)

Pico máximo de instâncias EC2: 10 + 10 + 30 = 50
(serial e horizontal rodam em paralelo entre si)

Logs em: arm_h265_new_logs/
"""
import os, subprocess, threading, time, statistics, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
LOG_DIR       = os.path.join(SCRIPT_DIR, "arm_h265_new_logs")
SERIAL_SCRIPT = os.path.join(SCRIPT_DIR, "arm_h265_serial_3x.py")
HORIZ_SCRIPT  = os.path.join(SCRIPT_DIR, "c7g_large_horizontal_libx265.py")

os.makedirs(LOG_DIR, exist_ok=True)

lock  = threading.Lock()
state = {
    "m7g_serial": {"target": 30, "done": 0, "times": [], "errors": 0},
    "c7g_serial": {"target": 30, "done": 0, "times": [], "errors": 0},
    "c7g_horiz":  {"target": 30, "done": 0, "times": [], "errors": 0},
}

# ── Serial worker (1 instance → 3 runs) ────────────────────────
def run_serial_worker(instance_type, worker_id, exp_key):
    log_path = os.path.join(LOG_DIR, f"{exp_key}_worker_{worker_id:02d}.log")
    cmd = ["python3", SERIAL_SCRIPT,
           "--instance-type", instance_type,
           "--worker-id", str(worker_id)]
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
    with open(log_path, "w") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n"); f.write(result.stderr)

    # Parse run times from output
    times = re.findall(r'Run \d+/\d+ done: ([\d.]+)s', result.stdout)
    times = [float(t) for t in times]
    with lock:
        if result.returncode == 0 and times:
            state[exp_key]["done"]  += len(times)
            state[exp_key]["times"] += times
        else:
            state[exp_key]["errors"] += 1

# ── Horizontal worker (1 trial = 10 fresh instances) ───────────
horiz_semaphore = threading.Semaphore(3)  # max 3 concurrent trials

def run_horiz_trial(trial_idx):
    log_path = os.path.join(LOG_DIR, f"c7g_horiz_trial_{trial_idx:02d}.log")
    with horiz_semaphore:
        result = subprocess.run(
            ["python3", HORIZ_SCRIPT],
            cwd=SCRIPT_DIR, capture_output=True, text=True)
        with open(log_path, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n"); f.write(result.stderr)
        m = re.search(r'Total Time:\s+([\d.]+)s', result.stdout)
        with lock:
            if result.returncode == 0 and m:
                state["c7g_horiz"]["done"]  += 1
                state["c7g_horiz"]["times"].append(float(m.group(1)))
            else:
                state["c7g_horiz"]["errors"] += 1

# ── Launch all experiments ──────────────────────────────────────
def run_all():
    futures = []
    # Serial: 10 workers per instance type, all launched simultaneously
    with ThreadPoolExecutor(max_workers=50) as pool:
        for w in range(1, 11):
            futures.append(pool.submit(run_serial_worker, "m7g.large", w, "m7g_serial"))
            futures.append(pool.submit(run_serial_worker, "c7g.large", w, "c7g_serial"))
        for t in range(1, 31):
            futures.append(pool.submit(run_horiz_trial, t))
        for f in as_completed(futures):
            pass

def ts():
    return datetime.now().strftime('%H:%M:%S')

def fmt_stats(times):
    if len(times) < 2:
        return f"n={len(times)}"
    med = statistics.median(times)
    std = statistics.stdev(times)
    cv  = std / statistics.mean(times) * 100
    return f"n={len(times)}  med={med:.1f}s  std={std:.1f}s  CV={cv:.1f}%"

if __name__ == "__main__":
    t = threading.Thread(target=run_all, daemon=True)
    t.start()
    start = time.time()
    print(f"\n[{ts()}] Iniciado. Pico: ~50 instâncias EC2. Ctrl+C para parar.\n")

    while True:
        time.sleep(60)
        elapsed = (time.time() - start) / 60
        print(f"\n[{ts()}]  elapsed={elapsed:.0f}min  ──────────────────────────────────")
        print(f"{'Experimento':<30} {'Done':>5}/{' Tgt':<4}  {'Erros':>5}  Estatísticas")
        print("─" * 80)
        with lock:
            for key, s in state.items():
                print(f"{key:<30} {s['done']:>5}/{s['target']:<4}  {s['errors']:>5}  {fmt_stats(s['times'])}")
            all_done = all(
                s['done'] + s['errors'] >= s['target'] for s in state.values()
            )
        print("─" * 80)
        if all_done:
            print(f"\n[{ts()}] TODOS OS EXPERIMENTOS CONCLUÍDOS.")
            break

    t.join(timeout=10)
