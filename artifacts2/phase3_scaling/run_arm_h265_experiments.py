#!/usr/bin/env python3
"""
Orquestrador: roda experimentos ARM H.265 faltantes em paralelo.
  - c7g.large horizontal: 30 runs, 3 workers simultâneos
  - m7g.large serial: 4 runs (suplementa n=26 → n=30)
  - c7g.large serial: 1 run  (suplementa n=29 → n=30)
Logs em: arm_h265_new_logs/
"""
import os, subprocess, threading, time, statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_DIR      = os.path.join(SCRIPT_DIR, "arm_h265_new_logs")
HORIZ_SCRIPT = os.path.join(SCRIPT_DIR, "c7g_large_horizontal_libx265.py")
SERIAL_SCRIPT= os.path.join(SCRIPT_DIR, "arm_h265_serial.py")

os.makedirs(LOG_DIR, exist_ok=True)

# ── shared state ────────────────────────────────────────────────
lock  = threading.Lock()
state = {
    "c7g_horiz":  {"target": 30, "done": 0, "times": [], "errors": 0, "running": 0},
    "m7g_serial": {"target":  4, "done": 0, "times": [], "errors": 0, "running": 0},
    "c7g_serial": {"target":  1, "done": 0, "times": [], "errors": 0, "running": 0},
}

def ts():
    return datetime.now().strftime('%H:%M:%S')

def run_one(exp_key, run_idx, cmd, log_path):
    with lock:
        state[exp_key]["running"] += 1
    t0 = time.time()
    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        elapsed = time.time() - t0
        with open(log_path, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n"); f.write(result.stderr)
        # extract Total Time from log
        total_time = None
        for line in result.stdout.splitlines():
            if "Total Time:" in line:
                import re
                m = re.search(r'Total Time:\s+([\d.]+)s', line)
                if m:
                    total_time = float(m.group(1))
                break
        with lock:
            state[exp_key]["running"] -= 1
            if result.returncode == 0 and total_time:
                state[exp_key]["done"] += 1
                state[exp_key]["times"].append(total_time)
            else:
                state[exp_key]["errors"] += 1
    except Exception as e:
        with lock:
            state[exp_key]["running"] -= 1
            state[exp_key]["errors"] += 1

def make_jobs():
    jobs = []
    # c7g horizontal: 30 runs
    for i in range(1, 31):
        log_path = os.path.join(LOG_DIR, f"c7g_large_horizontal_libx265_run_{i}.log")
        jobs.append(("c7g_horiz", i,
                     ["python3", HORIZ_SCRIPT],
                     log_path))
    # m7g serial: 4 runs
    for i in range(1, 5):
        log_path = os.path.join(LOG_DIR, f"m7g_large_serial_h265_run_{i}.log")
        jobs.append(("m7g_serial", i,
                     ["python3", SERIAL_SCRIPT, "--instance-type", "m7g.large"],
                     log_path))
    # c7g serial: 1 run
    log_path = os.path.join(LOG_DIR, "c7g_large_serial_h265_run_1.log")
    jobs.append(("c7g_serial", 1,
                 ["python3", SERIAL_SCRIPT, "--instance-type", "c7g.large"],
                 log_path))
    return jobs

def run_experiments():
    jobs = make_jobs()
    # c7g horizontal: up to 3 concurrent; serial jobs: 5 concurrent (fast to finish)
    # Use a single pool of 8 workers: 3 horiz + 5 serial in parallel
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_one, key, idx, cmd, lp) for key, idx, cmd, lp in jobs]
        for f in as_completed(futures):
            pass  # results tracked via shared state

if __name__ == "__main__":
    # Start experiments in background thread
    t = threading.Thread(target=run_experiments, daemon=True)
    t.start()

    start_time = time.time()
    print(f"\n[{ts()}] Experimentos iniciados. Atualizando a cada 60s. Ctrl+C para parar.\n")

    def fmt_stats(times):
        if not times:
            return "—"
        med = statistics.median(times)
        std = statistics.stdev(times) if len(times) > 1 else 0
        cv  = (std / statistics.mean(times) * 100) if times else 0
        return f"med={med:.0f}s  std={std:.1f}s  CV={cv:.1f}%"

    while True:
        time.sleep(60)
        elapsed = time.time() - start_time
        print(f"\n[{ts()}] ── Status (elapsed: {elapsed/60:.0f} min) ──────────────────")
        print(f"{'Experimento':<30} {'Done':>5} {'Target':>7} {'Running':>8} {'Errors':>7}  Estatísticas")
        print("─" * 90)
        with lock:
            for key, s in state.items():
                stats = fmt_stats(s["times"])
                print(f"{key:<30} {s['done']:>5}/{s['target']:<5}  {s['running']:>6}  {s['errors']:>6}  {stats}")
        print("─" * 90)
        # check if done
        with lock:
            all_done = all(s["done"] >= s["target"] or (s["done"] + s["errors"] >= s["target"]) for s in state.values())
        if all_done:
            print(f"\n[{ts()}] TODOS OS EXPERIMENTOS CONCLUÍDOS.")
            break

    t.join(timeout=5)
