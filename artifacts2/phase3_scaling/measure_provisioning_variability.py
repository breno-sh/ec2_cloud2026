#!/usr/bin/env python3
"""
I2-b: Provisioning variability characterization — ARM Graviton vs x86.

Launches N instances of each type, measures time from API call → SSH ready,
terminates immediately. Reports median, stdev, CV, p95 per architecture.

Usage:
    python3 measure_provisioning_variability.py

Cost estimate: ~$0.70 (100×m7g.large + 100×m5.large, ~60s each, on-demand)
"""
import time
import statistics
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import boto3
import paramiko
import os

# --- Config ---
N_PER_ARCH    = 100       # instances per architecture
BATCH_SIZE    = 10        # parallel launches per batch (controls vCPU usage)
REGION        = "us-east-1"
KEY_NAME      = "bvasconcelos"
SECURITY_GRP  = "bvasconcelosGroup"
KEY_PATH      = os.path.expanduser(
    "~/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem"
)

CONFIGS = [
    {"label": "m7g.large (ARM Graviton3)", "instance_type": "m7g.large",
     "ami": "ami-0976d56fa61f42304"},
    {"label": "m5.large  (x86 Intel)",     "instance_type": "m5.large",
     "ami": "ami-06c7c20c67513469a"},
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}", flush=True)


def measure_one(ec2, cfg, idx):
    """Launch one instance, wait for SSH, terminate. Return provisioning seconds."""
    instance_id = None
    t0 = time.time()
    try:
        resp = ec2.run_instances(
            ImageId=cfg["ami"],
            InstanceType=cfg["instance_type"],
            KeyName=KEY_NAME,
            SecurityGroups=[SECURITY_GRP],
            MinCount=1, MaxCount=1,
        )
        instance_id = resp["Instances"][0]["InstanceId"]

        # Wait until running + IP assigned
        ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
        info = ec2.describe_instances(InstanceIds=[instance_id])
        ip = info["Reservations"][0]["Instances"][0]["PublicIpAddress"]

        # Poll SSH port until accepting connections
        while True:
            try:
                s = socket.create_connection((ip, 22), timeout=3)
                s.close()
                # Give SSH daemon a moment to fully init
                time.sleep(2)
                # Try actual SSH handshake
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username="ubuntu", key_filename=KEY_PATH, timeout=5)
                ssh.close()
                break
            except Exception:
                time.sleep(2)

        elapsed = time.time() - t0
        log(f"  [{cfg['instance_type']}] #{idx:03d}: {elapsed:.1f}s")
        return elapsed

    except Exception as e:
        log(f"  [{cfg['instance_type']}] #{idx:03d}: ERROR — {e}")
        return None
    finally:
        if instance_id:
            try:
                ec2.terminate_instances(InstanceIds=[instance_id])
            except Exception:
                pass


def run_arch(cfg, n, batch_size):
    ec2 = boto3.client("ec2", region_name=REGION)
    results = []
    errors  = 0

    log(f"\n{'='*60}")
    log(f"Starting {n} measurements: {cfg['label']}")
    log(f"Batch size: {batch_size} parallel")
    log(f"{'='*60}")

    indices = list(range(1, n + 1))
    for batch_start in range(0, n, batch_size):
        batch = indices[batch_start:batch_start + batch_size]
        with ThreadPoolExecutor(max_workers=batch_size) as ex:
            futures = {ex.submit(measure_one, ec2, cfg, i): i for i in batch}
            for fut in as_completed(futures):
                val = fut.result()
                if val is not None:
                    results.append(val)
                else:
                    errors += 1

    return results, errors


def summarize(label, times):
    if len(times) < 2:
        log(f"{label}: insufficient data (n={len(times)})")
        return
    med   = statistics.median(times)
    mean  = statistics.mean(times)
    std   = statistics.stdev(times)
    cv    = std / med * 100
    times_s = sorted(times)
    p95   = times_s[int(len(times_s) * 0.95)]
    p99   = times_s[min(int(len(times_s) * 0.99), len(times_s)-1)]

    log(f"\n{'='*60}")
    log(f"RESULTS — {label}  (n={len(times)})")
    log(f"  Mean:    {mean:.1f}s")
    log(f"  Median:  {med:.1f}s")
    log(f"  Stdev:   {std:.1f}s")
    log(f"  CV:      {cv:.1f}%")
    log(f"  p95:     {p95:.1f}s")
    log(f"  p99:     {p99:.1f}s")
    log(f"  Min:     {min(times):.1f}s")
    log(f"  Max:     {max(times):.1f}s")
    log(f"{'='*60}")
    return {"label": label, "n": len(times), "median": med, "mean": mean,
            "std": std, "cv": cv, "p95": p95, "p99": p99}


def main():
    log("=== Provisioning Variability: ARM Graviton3 vs x86 ===")
    log(f"N={N_PER_ARCH} per architecture, batches of {BATCH_SIZE}")

    all_results = {}
    for cfg in CONFIGS:
        times, errors = run_arch(cfg, N_PER_ARCH, BATCH_SIZE)
        stats = summarize(cfg["label"], times)
        all_results[cfg["instance_type"]] = {"times": times, "stats": stats, "errors": errors}
        if errors:
            log(f"  WARNING: {errors} failed measurements")

    # Comparison summary
    log("\n" + "="*60)
    log("COMPARISON SUMMARY")
    log("="*60)
    arm = all_results.get("m7g.large", {}).get("stats")
    x86 = all_results.get("m5.large",  {}).get("stats")
    if arm and x86:
        log(f"{'Metric':<12} {'m7g.large (ARM)':<22} {'m5.large (x86)':<22}")
        log(f"{'Median':<12} {arm['median']:<22.1f} {x86['median']:<22.1f}")
        log(f"{'Stdev':<12} {arm['std']:<22.1f} {x86['std']:<22.1f}")
        log(f"{'CV':<12} {arm['cv']:<22.1f} {x86['cv']:<22.1f}")
        log(f"{'p95':<12} {arm['p95']:<22.1f} {x86['p95']:<22.1f}")
        log(f"{'p99':<12} {arm['p99']:<22.1f} {x86['p99']:<22.1f}")

    # Save raw times for reference
    import json
    out = {k: v["times"] for k, v in all_results.items()}
    fname = f"provisioning_times_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w") as f:
        json.dump(out, f, indent=2)
    log(f"\nRaw times saved to {fname}")


if __name__ == "__main__":
    main()
