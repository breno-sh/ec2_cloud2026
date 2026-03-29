#!/usr/bin/env python3
"""
ARM Graviton Re-run: 4 configs with CV > 20%
=============================================
Re-runs ALL 4 ARM configurations that showed CV > 20% in Table V,
all configs in parallel for maximum speed.

Configs:
  1. c7g.large serial H.264      (CV=55.4%)  — 30 runs × 1 instance
  2. c7g.large horizontal VP9    (CV=43.0%)  — 30 runs × 10 instances
  3. m7g.large horizontal VP9    (CV=26.0%)  — 30 runs × 10 instances
  4. m7g.large horizontal H.264  (CV=19.7%)  — 30 runs × 10 instances

Estimated time: ~20-25 min (all configs run simultaneously)
Estimated cost: ~$5-8

Usage:
    python3 arm_rerun_high_cv.py
    python3 arm_rerun_high_cv.py --dry-run
    python3 arm_rerun_high_cv.py --configs c7g_large_serial_h264,m7g_large_horizontal_h264
"""

import os
import sys
import time
import threading
import subprocess
import argparse
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import boto3
import paramiko

# ============================================================================
# Configuration
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AWS_CONFIG = {
    "key_name":        "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region":          "us-east-1",
    "local_key_path":  "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

INPUT_VIDEO = (
    "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms"
    "/artifacts/test_videos/video_repetido_10min.mp4"
)

ARM_AMI = "ami-0976d56fa61f42304"  # Ubuntu 22.04 ARM64 + ffmpeg pre-installed

LOG_DIR = os.path.join(BASE_DIR, "arm_rerun_highcv_logs")

# vCPU budget: 400 max (account limit 436, keep margin)
VCPU_LIMIT = 380
vcpu_sem = threading.Semaphore(VCPU_LIMIT)

# SFTP upload semaphore: limit concurrent uploads to avoid saturating local bandwidth
# 10 simultaneous uploads is safe for most connections
SFTP_CONCURRENCY = 10
sftp_sem = threading.Semaphore(SFTP_CONCURRENCY)

# Per-config concurrency for horizontal runs (3 concurrent = 30 instances per config)
HORIZONTAL_CONCURRENCY = 3

N_RUNS = 30
NUM_PARTS = 10
THREADS = 5

CONFIGS = [
    {
        "name":          "c7g_large_serial_h264",
        "instance_type": "c7g.large",
        "strategy":      "serial",
        "codec":         "libx264",
        "preset":        "slow",
        "vcpus":         2,
    },
    {
        "name":          "c7g_large_horizontal_vp9",
        "instance_type": "c7g.large",
        "strategy":      "horizontal",
        "codec":         "libvpx-vp9",
        "preset":        "slow",
        "vcpus":         2,
    },
    {
        "name":          "m7g_large_horizontal_vp9",
        "instance_type": "m7g.large",
        "strategy":      "horizontal",
        "codec":         "libvpx-vp9",
        "preset":        "slow",
        "vcpus":         2,
    },
    {
        "name":          "m7g_large_horizontal_h264",
        "instance_type": "m7g.large",
        "strategy":      "horizontal",
        "codec":         "libx264",
        "preset":        "slow",
        "vcpus":         2,
    },
]

# ============================================================================
# Logging
# ============================================================================

_print_lock = threading.Lock()

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def make_logger(log_path):
    lock = threading.Lock()
    def _log(msg, context=""):
        line = f"[{ts()}]" + (f" [{context}]" if context else "") + f" {msg}"
        with lock:
            with open(log_path, "a") as f:
                f.write(line + "\n")
        with _print_lock:
            print(line)
    return _log

# ============================================================================
# AWS helpers
# ============================================================================

def launch_instance(ec2, instance_type, log_fn, context=""):
    response = ec2.run_instances(
        ImageId=ARM_AMI,
        InstanceType=instance_type,
        KeyName=AWS_CONFIG["key_name"],
        SecurityGroups=AWS_CONFIG["security_groups"],
        MinCount=1, MaxCount=1,
    )
    iid = response["Instances"][0]["InstanceId"]
    log_fn(f"Instance {iid} launched, waiting...", context)
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    desc = ec2.describe_instances(InstanceIds=[iid])
    ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    log_fn(f"Instance ready. IP: {ip}", context)
    return iid, ip


def ssh_connect(ip, retries=10, delay=5):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for attempt in range(retries):
        try:
            ssh.connect(ip, username="ubuntu",
                        key_filename=AWS_CONFIG["local_key_path"], timeout=15)
            return ssh
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def build_ffmpeg_cmd(codec, preset, threads):
    return (
        f"ffmpeg -i /home/ubuntu/input.mp4 "
        f"-c:v {codec} -preset {preset} -b:v 2M "
        f"-threads {threads} -max_muxing_queue_size 1024 "
        f"-y /home/ubuntu/output.mp4"
    )


def acquire_vcpus(n):
    for _ in range(n):
        vcpu_sem.acquire()

def release_vcpus(n):
    for _ in range(n):
        vcpu_sem.release()

# ============================================================================
# Strategy: Serial (1 instance, 1 full-video encode per run)
# ============================================================================

def run_serial(cfg, run_id, log_path):
    log_fn = make_logger(log_path)
    ec2 = boto3.client("ec2", region_name=AWS_CONFIG["region"])
    ctx = f"{cfg['instance_type']}-Serial-R{run_id:02d}"
    vcpus = cfg["vcpus"]

    log_fn(f"=== Serial {cfg['instance_type']} {cfg['codec']} Run {run_id} ===", ctx)

    iid = None
    ssh = None
    try:
        acquire_vcpus(vcpus)
        total_start = time.time()

        iid, ip = launch_instance(ec2, cfg["instance_type"], log_fn, ctx)
        time.sleep(25)  # wait for sshd
        ssh = ssh_connect(ip)
        log_fn("SSH connected.", ctx)

        # Verify ARM
        _, stdout, _ = ssh.exec_command("uname -m")
        stdout.channel.recv_exit_status()
        arch = stdout.read().decode().strip()
        log_fn(f"Architecture: {arch}", ctx)

        # Upload full video (throttled to avoid saturating local bandwidth)
        sftp = ssh.open_sftp()
        log_fn("Waiting for SFTP slot...", ctx)
        sftp_sem.acquire()
        try:
            log_fn("Uploading 10-min video...", ctx)
            sftp.put(INPUT_VIDEO, "/home/ubuntu/input.mp4")
            log_fn("Upload complete.", ctx)
        finally:
            sftp_sem.release()

        setup_time = time.time() - total_start
        log_fn(f"SETUP TIME: {setup_time:.2f}s", ctx)

        # Encode
        cmd = build_ffmpeg_cmd(cfg["codec"], cfg["preset"], THREADS)
        log_fn(f"Running: {cmd}", ctx)
        enc_start = time.time()
        _, stdout, stderr = ssh.exec_command(cmd)
        rc = stdout.channel.recv_exit_status()
        enc_time = time.time() - enc_start
        if rc != 0:
            err = stderr.read().decode()[-300:]
            raise RuntimeError(f"ffmpeg exit {rc}: {err}")
        log_fn(f"ENCODING TIME: {enc_time:.2f}s", ctx)

        sftp.close()
        total_time = time.time() - total_start

        log_fn("=" * 60, ctx)
        log_fn(f"RESULTS — {cfg['instance_type']} Serial {cfg['codec']}", ctx)
        log_fn(f"  Total Time:    {total_time:.2f}s ({total_time/60:.2f} min)", ctx)
        log_fn(f"  Setup Time:    {setup_time:.2f}s ({setup_time/60:.2f} min)", ctx)
        log_fn(f"  Encoding Time: {enc_time:.2f}s ({enc_time/60:.2f} min)", ctx)
        log_fn(f"  Setup %:       {100*setup_time/total_time:.1f}%", ctx)
        log_fn("=" * 60, ctx)
        return total_time

    except Exception as e:
        log_fn(f"ERROR: {e}", ctx)
        raise
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if iid:
            ec2.terminate_instances(InstanceIds=[iid])
            log_fn("Instance terminated.", ctx)
        release_vcpus(vcpus)

# ============================================================================
# Strategy: Horizontal (10 instances per run, 1 chunk each)
# ============================================================================

def _process_part(part_index, cfg, parts_dir, log_fn, run_id):
    """Process one video chunk on a fresh ARM instance."""
    ec2 = boto3.client("ec2", region_name=AWS_CONFIG["region"])
    ctx = f"R{run_id:02d}-P{part_index:02d}"
    vcpus = cfg["vcpus"]
    iid = None
    ssh = None

    try:
        acquire_vcpus(vcpus)
        t_start = time.time()

        iid, ip = launch_instance(ec2, cfg["instance_type"], log_fn, ctx)
        time.sleep(25)
        ssh = ssh_connect(ip)
        log_fn("SSH connected.", ctx)

        # Upload chunk (throttled to avoid saturating local bandwidth)
        sftp = ssh.open_sftp()
        part_file = os.path.join(parts_dir, f"part_{part_index:02d}.mp4")
        log_fn("Waiting for SFTP slot...", ctx)
        sftp_sem.acquire()
        try:
            log_fn("Uploading segment...", ctx)
            sftp.put(part_file, "/home/ubuntu/input.mp4")
        finally:
            sftp_sem.release()

        # Encode
        cmd = build_ffmpeg_cmd(cfg["codec"], cfg["preset"], THREADS)
        log_fn("Running compression...", ctx)
        _, stdout, stderr = ssh.exec_command(cmd)
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            err = stderr.read().decode()[-300:]
            raise RuntimeError(f"ffmpeg exit {rc}: {err}")

        sftp.close()
        elapsed = time.time() - t_start
        log_fn(f"Done! ({elapsed:.1f}s)", ctx)
        return elapsed

    except Exception as e:
        log_fn(f"ERROR: {e}", ctx)
        raise
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if iid:
            ec2.terminate_instances(InstanceIds=[iid])
            log_fn("Instance terminated.", ctx)
        release_vcpus(vcpus)


def run_horizontal(cfg, run_id, log_path):
    """Run one full horizontal cluster (10 instances)."""
    log_fn = make_logger(log_path)
    ctx = f"{cfg['instance_type']}-Horiz-{cfg['codec']}-R{run_id:02d}"

    # Reuse pre-split video parts
    codec_dir_name = cfg["codec"]  # libx264 or libvpx-vp9
    inst_prefix = cfg["instance_type"].replace(".", "_")  # c7g_large or m7g_large
    parts_dir = os.path.join(BASE_DIR, f"video_parts_{inst_prefix}_{codec_dir_name}")

    # If parts don't exist for this exact combo, use any existing parts (they're codec-copy splits)
    if not os.path.isdir(parts_dir):
        # Try alternate paths
        for alt_codec in ["libx264", "libx265", "libvpx-vp9"]:
            alt = os.path.join(BASE_DIR, f"video_parts_{inst_prefix}_{alt_codec}")
            if os.path.isdir(alt):
                parts_dir = alt
                break
        else:
            # Create parts from scratch
            parts_dir = os.path.join(BASE_DIR, f"video_parts_{cfg['name']}")
            os.makedirs(parts_dir, exist_ok=True)
            log_fn("Splitting video...", ctx)
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", INPUT_VIDEO],
                capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            part_dur = duration / NUM_PARTS
            for i in range(NUM_PARTS):
                subprocess.run(
                    ["ffmpeg", "-y", "-i", INPUT_VIDEO,
                     "-ss", str(i * part_dur), "-t", str(part_dur),
                     "-c", "copy", os.path.join(parts_dir, f"part_{i:02d}.mp4")],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    log_fn(f"=== Horizontal {cfg['instance_type']} {cfg['codec']} Run {run_id} ===", ctx)
    log_fn(f"Parts dir: {parts_dir}", ctx)

    total_start = time.time()

    # Launch all 10 parts in parallel
    with ThreadPoolExecutor(max_workers=NUM_PARTS) as executor:
        futures = [
            executor.submit(_process_part, i, cfg, parts_dir, log_fn, run_id)
            for i in range(NUM_PARTS)
        ]
        for f in futures:
            f.result()  # re-raise exceptions

    total_time = time.time() - total_start

    log_fn("=" * 60, ctx)
    log_fn(f"RESULTS — {NUM_PARTS}x {cfg['instance_type']} Horizontal {cfg['codec']}", ctx)
    log_fn(f"  Total Time:    {total_time:.2f}s ({total_time/60:.2f} min)", ctx)
    log_fn("=" * 60, ctx)
    return total_time

# ============================================================================
# Config runner
# ============================================================================

def run_config(cfg, horiz_concurrency=HORIZONTAL_CONCURRENCY):
    """Run all 30 iterations of a single config."""
    name = cfg["name"]
    strategy = cfg["strategy"]
    runner = run_serial if strategy == "serial" else run_horizontal

    print(f"\n[{ts()}] >>> Starting config: {name} ({N_RUNS} runs)")

    # Check for already-completed runs
    existing = set()
    if os.path.isdir(LOG_DIR):
        for fn in os.listdir(LOG_DIR):
            m = re.match(rf"{re.escape(name)}_run_(\d+)\.log", fn)
            if m:
                path = os.path.join(LOG_DIR, fn)
                with open(path) as fh:
                    if "RESULTS" in fh.read():
                        existing.add(int(m.group(1)))

    run_ids = [i for i in range(1, N_RUNS + 1) if i not in existing]
    if not run_ids:
        print(f"  [{name}] All {N_RUNS} runs already complete. Skipping.")
        return

    print(f"  [{name}] Running {len(run_ids)} (skipping {len(existing)} existing)")

    if strategy == "serial":
        # All serial runs in parallel (30 instances at once)
        max_workers = len(run_ids)
    else:
        # Horizontal: limit concurrent cluster runs
        max_workers = horiz_concurrency

    success = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for run_id in run_ids:
            log_path = os.path.join(LOG_DIR, f"{name}_run_{run_id}.log")
            f = executor.submit(runner, cfg, run_id, log_path)
            futures[f] = run_id

        for f in futures:
            rid = futures[f]
            try:
                elapsed = f.result()
                with _print_lock:
                    print(f"  [{name}] run {rid:02d} done: {elapsed:.1f}s")
                success += 1
            except Exception as e:
                with _print_lock:
                    print(f"  [{name}] run {rid:02d} FAILED: {e}")
                failed += 1

    print(f"  [{name}] Completed {success}/{len(run_ids)} (failed: {failed})")

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--configs", default="",
                        help="Comma-separated config names (default: all 4)")
    parser.add_argument("--concurrency", type=int, default=HORIZONTAL_CONCURRENCY,
                        help=f"Max concurrent horizontal runs per config (default: {HORIZONTAL_CONCURRENCY})")
    args = parser.parse_args()

    horiz_concurrency = args.concurrency

    os.makedirs(LOG_DIR, exist_ok=True)

    # Filter configs
    if args.configs:
        selected = [s.strip() for s in args.configs.split(",")]
        configs = [c for c in CONFIGS if c["name"] in selected]
    else:
        configs = CONFIGS

    if not configs:
        print(f"No matching configs. Available: {[c['name'] for c in CONFIGS]}")
        sys.exit(1)

    # Estimate
    serial_count = sum(1 for c in configs if c["strategy"] == "serial") * N_RUNS
    horiz_count = sum(1 for c in configs if c["strategy"] == "horizontal") * N_RUNS
    total_instances = serial_count + horiz_count * NUM_PARTS
    peak_vcpus = (serial_count * 2) + (len([c for c in configs if c["strategy"] == "horizontal"]) * horiz_concurrency * NUM_PARTS * 2)

    print(f"\n{'='*70}")
    print(f"ARM Graviton Re-run: High-CV Configs (CV > 20%)")
    print(f"{'='*70}")
    print(f"Configs       : {[c['name'] for c in configs]}")
    print(f"Total runs    : {(serial_count + horiz_count)} ({serial_count} serial + {horiz_count} horizontal)")
    print(f"Total launches: ~{total_instances} instances")
    print(f"Peak vCPUs    : ~{peak_vcpus} (limit: {VCPU_LIMIT})")
    print(f"Horiz concurr.: {horiz_concurrency} runs/config")
    print(f"Log dir       : {LOG_DIR}")
    print(f"{'='*70}\n")

    if args.dry_run:
        print("[DRY RUN] Would launch above. Exiting.")
        return

    # Verify prerequisites
    if not os.path.exists(INPUT_VIDEO):
        print(f"ERROR: Video not found: {INPUT_VIDEO}")
        sys.exit(1)
    if not os.path.exists(AWS_CONFIG["local_key_path"]):
        print(f"ERROR: PEM key not found: {AWS_CONFIG['local_key_path']}")
        sys.exit(1)

    global_start = time.time()

    # Run ALL configs in parallel (this is the key optimization)
    with ThreadPoolExecutor(max_workers=len(configs)) as executor:
        futures = {executor.submit(run_config, c, horiz_concurrency): c["name"] for c in configs}
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"\n[FATAL] Config {futures[f]} raised: {e}")

    total = time.time() - global_start
    print(f"\n{'='*70}")
    print(f"ALL CONFIGS FINISHED in {total:.1f}s ({total/60:.1f} min)")
    print(f"Logs: {LOG_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
