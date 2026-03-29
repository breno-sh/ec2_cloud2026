#!/usr/bin/env python3
"""
Orquestrador do re-run completo Phase 3 com metodologia S3.

Roda os 29 configs contaminados × 30 runs cada.
Estratégia de paralelismo (controla instâncias simultâneas):
  - Serial e Vertical: rodam em grupos (até MAX_PARALLEL_CAMPAIGNS simultâneos)
  - Horizontal: roda 1 por vez (cada horizontal = 10 instâncias)

Uso: python3 run_all_rerun_s3.py [--dry-run] [--skip-done]
"""
import subprocess, os, sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase3_rerun_s3.py")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "n30_rerun_s3_logs")
RUNS = 30

# Todos os configs contaminados a re-rodar
# (instance_type, strategy, codec)
CONFIGS = [
    # x86 — H.265 e VP9 (H.264 já está limpo nos opt logs)
    ("m5.large",  "serial",     "libx265"),
    ("m5.large",  "serial",     "libvpx-vp9"),
    ("m5.large",  "horizontal", "libx265"),
    ("m5.large",  "horizontal", "libvpx-vp9"),
    ("m5.large",  "vertical",   "libx265"),
    ("m5.large",  "vertical",   "libvpx-vp9"),
    ("c5.large",  "serial",     "libx265"),
    ("c5.large",  "serial",     "libvpx-vp9"),
    ("c5.large",  "horizontal", "libx265"),
    ("c5.large",  "horizontal", "libvpx-vp9"),
    ("c5.large",  "vertical",   "libx265"),
    ("c5.large",  "vertical",   "libvpx-vp9"),
    # ARM — todos os 3 codecs (exceto m7g.large horizontal libx265 já feito hoje)
    ("m7g.large", "serial",     "libx264"),
    ("m7g.large", "serial",     "libx265"),
    ("m7g.large", "serial",     "libvpx-vp9"),
    ("m7g.large", "horizontal", "libx264"),
    ("m7g.large", "horizontal", "libvpx-vp9"),
    ("m7g.large", "vertical",   "libx264"),
    ("m7g.large", "vertical",   "libx265"),
    ("m7g.large", "vertical",   "libvpx-vp9"),
    ("c7g.large", "serial",     "libx264"),
    ("c7g.large", "serial",     "libx265"),
    ("c7g.large", "serial",     "libvpx-vp9"),
    ("c7g.large", "horizontal", "libx264"),
    ("c7g.large", "horizontal", "libx265"),
    ("c7g.large", "horizontal", "libvpx-vp9"),
    ("c7g.large", "vertical",   "libx264"),
    ("c7g.large", "vertical",   "libx265"),
    ("c7g.large", "vertical",   "libvpx-vp9"),
]

# Also need x86 H.264 with S3 methodology (for consistency — opt logs used SFTP)
# Comentado por enquanto — discutir com usuário se quer re-rodar esses também
# X86_H264 = [
#     ("m5.large","serial","libx264"), ("m5.large","horizontal","libx264"), ("m5.large","vertical","libx264"),
#     ("c5.large","serial","libx264"), ("c5.large","horizontal","libx264"), ("c5.large","vertical","libx264"),
# ]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def label(cfg):
    inst, strat, codec = cfg
    return f"{inst}_{strat}_{codec.replace('-','_').replace('/','_')}"

def is_done(cfg):
    log_file = os.path.join(LOG_DIR, f"{label(cfg)}.log")
    if not os.path.exists(log_file):
        return False
    content = open(log_file).read()
    return "RESULTS —" in content

def run_config(cfg, dry_run=False):
    inst, strat, codec = cfg
    lbl = label(cfg)
    log(f"START: {lbl}")
    if dry_run:
        log(f"  [DRY RUN] would run: python3 phase3_rerun_s3.py --instance-type {inst} --strategy {strat} --codec {codec} --runs {RUNS}")
        return lbl, True
    cmd = [
        "python3", SCRIPT,
        "--instance-type", inst,
        "--strategy", strat,
        "--codec", codec,
        "--runs", str(RUNS),
        "--log-dir", LOG_DIR,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"ERROR: {lbl} — exit code {result.returncode}")
        log(f"  stderr: {result.stderr[-300:]}")
        return lbl, False
    log(f"DONE: {lbl}")
    return lbl, True

def main():
    dry_run   = "--dry-run"   in sys.argv
    skip_done = "--skip-done" in sys.argv

    os.makedirs(LOG_DIR, exist_ok=True)

    # Split by strategy
    serial_cfgs   = [c for c in CONFIGS if c[1] == "serial"]
    horiz_cfgs    = [c for c in CONFIGS if c[1] == "horizontal"]
    vertical_cfgs = [c for c in CONFIGS if c[1] == "vertical"]

    if skip_done:
        serial_cfgs   = [c for c in serial_cfgs   if not is_done(c)]
        horiz_cfgs    = [c for c in horiz_cfgs    if not is_done(c)]
        vertical_cfgs = [c for c in vertical_cfgs if not is_done(c)]

    log(f"=== Phase 3 Complete Re-run (S3 methodology) ===")
    log(f"Total configs: {len(CONFIGS)} ({len(serial_cfgs)} serial, {len(horiz_cfgs)} horizontal, {len(vertical_cfgs)} vertical)")
    log(f"Runs per config: {RUNS}")
    if dry_run: log("*** DRY RUN MODE ***")

    # ── SERIAL: roda até 4 em paralelo (4 instâncias simultâneas máximo)
    if serial_cfgs:
        log(f"\n--- SERIAL ({len(serial_cfgs)} configs) — até 4 em paralelo ---")
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(run_config, c, dry_run): c for c in serial_cfgs}
            for f in as_completed(futures):
                lbl, ok = f.result()
                log(f"  {'OK' if ok else 'FAIL'}: {lbl}")

    # ── VERTICAL: roda até 4 em paralelo (instâncias 4xlarge — mais caras)
    if vertical_cfgs:
        log(f"\n--- VERTICAL ({len(vertical_cfgs)} configs) — até 4 em paralelo ---")
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(run_config, c, dry_run): c for c in vertical_cfgs}
            for f in as_completed(futures):
                lbl, ok = f.result()
                log(f"  {'OK' if ok else 'FAIL'}: {lbl}")

    # ── HORIZONTAL: roda 2 em paralelo (2×10 = 20 instâncias simultâneas)
    if horiz_cfgs:
        log(f"\n--- HORIZONTAL ({len(horiz_cfgs)} configs) — 2 em paralelo ---")
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = {ex.submit(run_config, c, dry_run): c for c in horiz_cfgs}
            for f in as_completed(futures):
                lbl, ok = f.result()
                log(f"  {'OK' if ok else 'FAIL'}: {lbl}")

    log(f"\n=== ALL DONE ===")

if __name__ == "__main__":
    main()
