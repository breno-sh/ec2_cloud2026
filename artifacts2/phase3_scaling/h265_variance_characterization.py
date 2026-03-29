#!/usr/bin/env python3
"""
H.265 ARM Variance Characterization — Two parts:

PART 1 — Encoding isolation (single m7g.large instance):
  Upload all 10 video chunks, encode each with libx265 5× in place.
  Measures ONLY encoding time. Reveals content-dependent variance without
  provisioning/SFTP noise.

PART 2 — Full pipeline decomposition (n=10 horizontal runs):
  Each run launches 10 m7g.large instances (batched 5 at a time).
  Per-step timing logged: provisioning, ssh_wait, upload, encode, download.
  Shows which step is responsible for total wall-clock variance.

Usage:
    python3 h265_variance_characterization.py --part 1
    python3 h265_variance_characterization.py --part 2
    python3 h265_variance_characterization.py --part all   (default)

Cost estimate:
  Part 1: ~1 m7g.large × ~15 min → ~$0.02
  Part 2: ~10 runs × 10 m7g.large × ~3 min avg → ~$0.20
"""
import os
import sys
import time
import json
import socket
import argparse
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
import paramiko

# ─────────────────────────── Config ───────────────────────────
REGION        = "us-east-1"
INSTANCE_TYPE = "m7g.large"
AMI_ID        = "ami-0976d56fa61f42304"   # pre-built ARM AMI w/ ffmpeg
KEY_NAME      = "bvasconcelos"
SECURITY_GRPS = ["bvasconcelosGroup"]
KEY_PATH      = os.path.expanduser(
    "~/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem"
)

PARTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "video_parts_m7g_large_libx265"
)
NUM_PARTS     = 10
REPS_PART1    = 5       # encoding repetitions per chunk in Part 1
N_RUNS_PART2  = 10      # full pipeline runs in Part 2
BATCH_SIZE    = 5       # concurrent instances (×2 vCPUs = 10 vCPUs, within limit)

FFMPEG_CMD = (
    "ffmpeg -i /home/ubuntu/input.mp4 "
    "-c:v libx265 -preset slow -b:v 2M "
    "-threads 2 -y /home/ubuntu/output.mp4 2>&1"
)

S3_BUCKET  = "brenovasconcelos"
S3_PREFIX  = "h265_chunks"
S3_EXPIRY  = 7200        # pre-signed URL lifetime in seconds

SSH_TIMEOUT   = 120     # max seconds to poll for SSH before giving up


# ─────────────────────────── Logging ──────────────────────────
def log(msg, ctx=None):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    prefix = f" [{ctx}]" if ctx else ""
    print(f"[{ts}]{prefix} {msg}", flush=True)


# ─────────────────────── SSH helpers ──────────────────────────
def wait_for_ssh(ip, key_path, timeout=SSH_TIMEOUT):
    """Poll SSH port and do a real handshake. Returns seconds elapsed."""
    t0 = time.time()
    deadline = t0 + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((ip, 22), timeout=3)
            s.close()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username="ubuntu", key_filename=key_path, timeout=5)
            ssh.close()
            return time.time() - t0
        except Exception:
            time.sleep(2)
    raise TimeoutError(f"SSH on {ip} did not become ready within {timeout}s")


def open_ssh(ip, key_path):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username="ubuntu", key_filename=key_path, timeout=10)
    return ssh


def run_remote(ssh, cmd):
    """Run command, return (stdout_str, stderr_str, exit_code)."""
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode(), exit_code


# ─────────────────────────── PART 1 ───────────────────────────
def part1_encoding_isolation():
    log("=" * 60)
    log("PART 1 — Encoding Isolation (single m7g.large)")
    log(f"  Chunks: {NUM_PARTS}  |  Reps per chunk: {REPS_PART1}")
    log(f"  FFmpeg: {FFMPEG_CMD}")
    log("=" * 60)

    ec2 = boto3.client("ec2", region_name=REGION)
    instance_id = None
    ssh = None
    results = {}   # chunk_idx → list of encoding seconds

    try:
        # Launch instance
        log("Launching m7g.large...")
        t_api = time.time()
        resp = ec2.run_instances(
            ImageId=AMI_ID, InstanceType=INSTANCE_TYPE,
            KeyName=KEY_NAME, SecurityGroups=SECURITY_GRPS,
            MinCount=1, MaxCount=1
        )
        instance_id = resp["Instances"][0]["InstanceId"]
        ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
        ip = ec2.describe_instances(InstanceIds=[instance_id])[
            "Reservations"][0]["Instances"][0]["PublicIpAddress"]
        t_running = time.time()
        log(f"  instance_running in {t_running - t_api:.1f}s — IP: {ip}")

        ssh_wait = wait_for_ssh(ip, KEY_PATH)
        t_ssh = time.time()
        log(f"  SSH ready in {ssh_wait:.1f}s")

        ssh = open_ssh(ip, KEY_PATH)

        # Verify ffmpeg
        out, _, _ = run_remote(ssh, "ffmpeg -version 2>&1 | head -1")
        log(f"  FFmpeg: {out.strip()}")

        sftp = ssh.open_sftp()

        # Upload all chunks
        log("Uploading all 10 chunks...")
        for i in range(NUM_PARTS):
            local = os.path.join(PARTS_DIR, f"part_{i:02d}.mp4")
            sftp.put(local, f"/home/ubuntu/chunk_{i:02d}.mp4")
            log(f"  Uploaded chunk_{i:02d}.mp4")

        # Encode each chunk REPS_PART1 times
        for i in range(NUM_PARTS):
            times = []
            for rep in range(REPS_PART1):
                # Overwrite input with this chunk
                run_remote(ssh, f"cp /home/ubuntu/chunk_{i:02d}.mp4 /home/ubuntu/input.mp4")
                # Time the encoding with `time` built-in via /usr/bin/time
                timed_cmd = (
                    f"/usr/bin/time -f '%e' sh -c '"
                    + FFMPEG_CMD.replace("'", "'\\''")
                    + f"' 2>/home/ubuntu/time_out.txt; cat /home/ubuntu/time_out.txt"
                )
                # Alternative: measure on Python side
                t_enc_start = time.time()
                out, err, rc = run_remote(ssh, FFMPEG_CMD.replace("2>&1", ""))
                t_enc_end = time.time()
                enc_time = t_enc_end - t_enc_start
                if rc != 0:
                    log(f"  chunk_{i:02d} rep{rep+1}: FAILED (rc={rc})", f"P1-C{i:02d}")
                    log(f"    stderr tail: {err[-200:]}", f"P1-C{i:02d}")
                    times.append(None)
                else:
                    log(f"  chunk_{i:02d} rep{rep+1}/{REPS_PART1}: {enc_time:.1f}s", f"P1-C{i:02d}")
                    times.append(enc_time)
            results[i] = times

        sftp.close()

    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log(f"  Instance {instance_id} terminated.")

    # ── Report ──
    log("")
    log("=" * 60)
    log("PART 1 RESULTS — Per-chunk encoding time (libx265, m7g.large)")
    log(f"{'Chunk':<8} {'Times (s)':<55} {'Med':>6} {'Stdev':>7} {'CV%':>6}")
    log("-" * 85)
    all_times = []
    for i in range(NUM_PARTS):
        vals = [v for v in results[i] if v is not None]
        all_times.extend(vals)
        if len(vals) >= 2:
            med = statistics.median(vals)
            std = statistics.stdev(vals)
            cv  = std / med * 100
        elif len(vals) == 1:
            med, std, cv = vals[0], 0.0, 0.0
        else:
            med, std, cv = float("nan"), float("nan"), float("nan")
        times_str = "  ".join(f"{v:.1f}" for v in results[i] if v is not None)
        log(f"chunk_{i:02d}  {times_str:<55} {med:6.1f} {std:7.2f} {cv:6.1f}%")

    if len(all_times) >= 2:
        log("-" * 85)
        g_med = statistics.median(all_times)
        g_std = statistics.stdev(all_times)
        g_cv  = g_std / g_med * 100
        log(f"{'GLOBAL':<8} {'(all chunks × all reps)':<55} {g_med:6.1f} {g_std:7.2f} {g_cv:6.1f}%")
    log("=" * 60)

    # Save JSON
    fname = f"part1_encoding_isolation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w") as f:
        json.dump({"results": results}, f, indent=2)
    log(f"Raw data saved to {fname}")
    return results


# ─────────────────────────── PART 2 ───────────────────────────
def process_chunk_timed(run_idx, part_index, ec2, aws_keys, s3_url):
    """Launch 1 instance, run full pipeline, return per-step timing dict or None.
    Input is fetched via wget from S3 (no SFTP upload from local machine).
    """
    ctx = f"R{run_idx:02d}-P{part_index:02d}"
    instance_id = None
    ssh = None
    timings = {}

    try:
        # ── Step 1: API call → instance_running ──
        t0 = time.time()
        resp = ec2.run_instances(
            ImageId=AMI_ID, InstanceType=INSTANCE_TYPE,
            KeyName=aws_keys["key_name"],
            SecurityGroups=aws_keys["security_groups"],
            MinCount=1, MaxCount=1
        )
        instance_id = resp["Instances"][0]["InstanceId"]
        ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
        ip = ec2.describe_instances(InstanceIds=[instance_id])[
            "Reservations"][0]["Instances"][0]["PublicIpAddress"]
        t_running = time.time()
        timings["provisioning"] = t_running - t0

        # ── Step 2: instance_running → SSH ready ──
        ssh_wait = wait_for_ssh(ip, aws_keys["local_key_path"])
        timings["ssh_wait"] = ssh_wait
        log(f"  prov={timings['provisioning']:.1f}s  ssh={timings['ssh_wait']:.1f}s", ctx)

        ssh = open_ssh(ip, aws_keys["local_key_path"])

        # ── Step 3: wget chunk from S3 (measured on remote) ──
        wget_cmd = f"wget -q '{s3_url}' -O /home/ubuntu/input.mp4 && echo OK"
        t_wget_start = time.time()
        out, err, rc = run_remote(ssh, wget_cmd)
        timings["s3_download"] = time.time() - t_wget_start
        if rc != 0 or out.strip() != "OK":
            log(f"  wget FAILED rc={rc}: {err[-200:]}", ctx)
            return None
        log(f"  s3_dl={timings['s3_download']:.1f}s", ctx)

        # ── Step 4: Encoding ──
        t_enc_start = time.time()
        out, err, rc = run_remote(ssh, FFMPEG_CMD.replace("2>&1", ""))
        timings["encode"] = time.time() - t_enc_start
        if rc != 0:
            log(f"  FFmpeg FAILED rc={rc}: {err[-200:]}", ctx)
            return None

        # ── Step 5: Verify output exists (no local download needed) ──
        t_verify_start = time.time()
        out, _, rc = run_remote(ssh, "stat -c %s /home/ubuntu/output.mp4")
        timings["verify"] = time.time() - t_verify_start
        output_bytes = int(out.strip()) if rc == 0 else 0

        timings["total"] = (timings["provisioning"] + timings["ssh_wait"]
                            + timings["s3_download"] + timings["encode"])
        log(
            f"  s3_dl={timings['s3_download']:.1f}s  "
            f"enc={timings['encode']:.1f}s  "
            f"output={output_bytes//1024}KB  "
            f"total={timings['total']:.1f}s",
            ctx
        )
        return {"run": run_idx, "part": part_index, "output_bytes": output_bytes,
                **timings}

    except Exception as e:
        log(f"  ERROR: {e}", ctx)
        return None
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if instance_id:
            try: ec2.terminate_instances(InstanceIds=[instance_id])
            except: pass


def generate_presigned_urls():
    """Generate fresh pre-signed S3 URLs for all 10 chunks."""
    s3 = boto3.client("s3", region_name=REGION)
    urls = {}
    for i in range(NUM_PARTS):
        key = f"{S3_PREFIX}/part_{i:02d}.mp4"
        urls[i] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=S3_EXPIRY,
        )
    log(f"Generated {len(urls)} pre-signed S3 URLs (valid {S3_EXPIRY}s)")
    return urls


def part2_pipeline_decomposition():
    log("=" * 60)
    log("PART 2 — Full Pipeline Decomposition (H.265 horizontal)")
    log(f"  Runs: {N_RUNS_PART2}  |  10 × m7g.large per run  |  batch={BATCH_SIZE}")
    log(f"  Input: wget from S3 (no SFTP upload)")
    log("=" * 60)

    presigned_urls = generate_presigned_urls()

    aws_keys = {
        "key_name": KEY_NAME,
        "security_groups": SECURITY_GRPS,
        "local_key_path": KEY_PATH,
    }

    all_records = []

    for run_idx in range(1, N_RUNS_PART2 + 1):
        log(f"\n--- Run {run_idx}/{N_RUNS_PART2} ---")
        ec2 = boto3.client("ec2", region_name=REGION)
        run_records = []
        run_start = time.time()

        # Process in batches to stay within vCPU limit
        for batch_start in range(0, NUM_PARTS, BATCH_SIZE):
            batch = list(range(batch_start, min(batch_start + BATCH_SIZE, NUM_PARTS)))
            log(f"  Batch parts {batch[0]:02d}–{batch[-1]:02d} ({len(batch)} concurrent)")
            with ThreadPoolExecutor(max_workers=len(batch)) as ex:
                futures = {
                    ex.submit(process_chunk_timed, run_idx, p, ec2, aws_keys,
                              presigned_urls[p]): p
                    for p in batch
                }
                for fut in as_completed(futures):
                    rec = fut.result()
                    if rec:
                        run_records.append(rec)
                    else:
                        log(f"  Part {futures[fut]:02d} failed — skipped")

        run_wall = time.time() - run_start
        valid = [r for r in run_records if r]
        log(f"  Run {run_idx} wall={run_wall:.1f}s  valid_parts={len(valid)}/10")
        all_records.extend(valid)

    # ── Analysis ──
    log("")
    log("=" * 60)
    log("PART 2 RESULTS — Per-step variance breakdown")
    log("=" * 60)

    steps = ["provisioning", "ssh_wait", "s3_download", "encode", "total"]
    print(f"\n{'Step':<14} {'N':>4}  {'Med':>7}  {'Mean':>7}  {'Std':>7}  {'CV%':>6}  {'p95':>7}  {'Min':>7}  {'Max':>7}")
    print("-" * 75)

    for step in steps:
        vals = [r[step] for r in all_records if step in r and r[step] is not None]
        if len(vals) < 2:
            print(f"{step:<14} {'—':>4}")
            continue
        n   = len(vals)
        med = statistics.median(vals)
        mu  = statistics.mean(vals)
        std = statistics.stdev(vals)
        cv  = std / med * 100
        sv  = sorted(vals)
        p95 = sv[int(n * 0.95)]
        print(f"{step:<14} {n:4d}  {med:7.1f}  {mu:7.1f}  {std:7.2f}  {cv:6.1f}%  {p95:7.1f}  {min(vals):7.1f}  {max(vals):7.1f}")

    # Per-chunk encoding variance
    log("")
    log("Per-chunk encoding variance (Part 2):")
    print(f"\n{'Chunk':<8} {'N':>4}  {'Med':>7}  {'Std':>7}  {'CV%':>6}  {'Min':>7}  {'Max':>7}")
    print("-" * 55)
    for p in range(NUM_PARTS):
        vals = [r["encode"] for r in all_records if r["part"] == p and "encode" in r]
        if len(vals) < 2:
            print(f"chunk_{p:02d} {len(vals):4d}")
            continue
        med = statistics.median(vals)
        std = statistics.stdev(vals)
        cv  = std / med * 100
        print(f"chunk_{p:02d} {len(vals):4d}  {med:7.1f}  {std:7.2f}  {cv:6.1f}%  {min(vals):7.1f}  {max(vals):7.1f}")

    # Per-run total time
    log("")
    log("Per-run total wall-clock (longest part per run):")
    run_totals = {}
    for r in all_records:
        ri = r["run"]
        run_totals.setdefault(ri, []).append(r["total"])
    print(f"\n{'Run':<6}  {'N parts':>8}  {'Max total':>10}  {'Bottleneck step':>16}")
    for ri in sorted(run_totals):
        parts = [r for r in all_records if r["run"] == ri]
        max_part = max(parts, key=lambda x: x["total"])
        bottleneck = max(
            ["provisioning", "ssh_wait", "s3_download", "encode"],
            key=lambda s: max_part.get(s, 0)
        )
        print(f"Run {ri:<3}  {len(parts):8d}  {max_part['total']:10.1f}s  {bottleneck:>16}  (part {max_part['part']:02d})")

    # Save JSON
    fname = f"part2_pipeline_decomposition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w") as f:
        json.dump(all_records, f, indent=2)
    log(f"\nRaw data saved to {fname}")
    return all_records


# ─────────────────────────── Main ─────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["1", "2", "all"], default="all",
                        help="Which part to run (default: all)")
    args = parser.parse_args()

    if args.part in ("1", "all"):
        part1_encoding_isolation()

    if args.part in ("2", "all"):
        part2_pipeline_decomposition()


if __name__ == "__main__":
    # Tee stdout to log file
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, data):
            for f in self.files:
                f.write(data)
                f.flush()
        def flush(self):
            for f in self.files: f.flush()

    log_fname = f"h265_variance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_fname, "w") as lf:
        tee = Tee(sys.__stdout__, lf)
        sys.stdout = sys.stderr = tee
        try:
            main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\nLog saved to {log_fname}")
