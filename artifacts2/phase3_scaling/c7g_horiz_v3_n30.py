#!/usr/bin/env python3
"""
c7g.large horizontal H.265 — 6 grupos × 10 instâncias × 5 rounds = 30 medições.

Fluxo:
  1. Lança 60 instâncias (paralelo)
  2. Conecta SSH (paralelo)
  3. Upload em batches de 10, 30s entre batches (evita saturação de banda)
  4. 5 rounds de encode: todos os 60 encodam simultaneamente
     Medição por round = max(tempo de cada grupo de 10)
  5. Termina todas as instâncias

Logs em: arm_h265_v3_logs/
"""
import os, time, threading, statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3, paramiko

INPUT_VIDEO    = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts/test_videos/video_repetido_10min.mp4"
PARTS_DIR      = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling/video_parts_c7g_large_libx265"
LOG_DIR        = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling/arm_h265_v3_logs"
INSTANCE_TYPE  = "c7g.large"
N_GROUPS       = 6
N_PER_GROUP    = 10        # = NUM_PARTS (cada instância recebe 1 chunk)
N_ROUNDS       = 5
UPLOAD_BATCH   = 10        # instâncias por vez no upload
UPLOAD_PAUSE   = 30        # segundos entre batches de upload
CODEC, BITRATE, PRESET, THREADS = "libx265", "2M", "slow", 5

AWS_CONFIG = {
    "ami_id": "ami-0976d56fa61f42304",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

os.makedirs(LOG_DIR, exist_ok=True)
print_lock = threading.Lock()

def log(msg, ctx=""):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    prefix = f" [{ctx}]" if ctx else ""
    with print_lock:
        print(f"[{ts}]{prefix} {msg}", flush=True)

# ── Phase 1+2: launch + connect ─────────────────────────────────────────────
def launch_and_connect(group_id, part_id, global_idx):
    ctx = f"G{group_id}P{part_id:02d}"
    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    resp = ec2.run_instances(
        ImageId=AWS_CONFIG['ami_id'], InstanceType=INSTANCE_TYPE,
        KeyName=AWS_CONFIG['key_name'], SecurityGroups=AWS_CONFIG['security_groups'],
        MinCount=1, MaxCount=1)
    iid = resp['Instances'][0]['InstanceId']
    ec2.get_waiter('instance_running').wait(InstanceIds=[iid])
    ip = ec2.describe_instances(InstanceIds=[iid])['Reservations'][0]['Instances'][0]['PublicIpAddress']
    log(f"Ready {ip}", ctx)
    time.sleep(30)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])
    return group_id, part_id, global_idx, iid, ssh

# ── Phase 3: upload one instance ────────────────────────────────────────────
def upload_one(group_id, part_id, ssh):
    ctx = f"G{group_id}P{part_id:02d}"
    log("Uploading...", ctx)
    sftp = ssh.open_sftp()
    sftp.put(f"{PARTS_DIR}/part_{part_id:02d}.mp4", "/home/ubuntu/input.mp4")
    sftp.close()
    log("Upload done.", ctx)

# ── Phase 4: one encode run ─────────────────────────────────────────────────
def run_encode(group_id, part_id, ssh):
    cmd = (f"ffmpeg -i /home/ubuntu/input.mp4 "
           f"-c:v {CODEC} -preset {PRESET} -b:v {BITRATE} "
           f"-threads {THREADS} -max_muxing_queue_size 1024 -y /home/ubuntu/output.mp4")
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode()[-100:]
        log(f"FFmpeg ERROR: {err}", f"G{group_id}P{part_id:02d}")
        return False
    return True

# ── Phase 5: terminate ───────────────────────────────────────────────────────
def terminate(iid, ssh):
    try: ssh.close()
    except: pass
    boto3.client('ec2', region_name=AWS_CONFIG['region']).terminate_instances(InstanceIds=[iid])

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    total_start = time.time()
    log(f"Starting: {N_GROUPS} groups × {N_PER_GROUP} instances × {N_ROUNDS} rounds = {N_GROUPS*N_ROUNDS} measurements")

    # Phase 1+2: launch in batches of 10 (avoid AWS RunInstances rate limit)
    LAUNCH_BATCH = 10
    LAUNCH_PAUSE = 3   # seconds between launch batches
    log(f"Launching 60 instances in batches of {LAUNCH_BATCH}...")
    all_instances = {}
    all_tasks = [(g, p, g * N_PER_GROUP + p) for g in range(N_GROUPS) for p in range(N_PER_GROUP)]
    for batch_start in range(0, len(all_tasks), LAUNCH_BATCH):
        batch = all_tasks[batch_start:batch_start + LAUNCH_BATCH]
        log(f"Launch batch {batch_start//LAUNCH_BATCH + 1}/{len(all_tasks)//LAUNCH_BATCH} ...")
        with ThreadPoolExecutor(max_workers=LAUNCH_BATCH) as pool:
            futs = {pool.submit(launch_and_connect, g, p, idx): idx for g, p, idx in batch}
            for f in as_completed(futs):
                g, p, idx, iid, ssh = f.result()
                all_instances[idx] = (g, p, iid, ssh)
        if batch_start + LAUNCH_BATCH < len(all_tasks):
            time.sleep(LAUNCH_PAUSE)
    log(f"All 60 instances connected. Starting uploads in batches of {UPLOAD_BATCH}...")

    # Phase 3: upload in batches of 10
    all_sorted = sorted(all_instances.items())  # [(idx, (g,p,iid,ssh)), ...]
    for batch_start in range(0, len(all_sorted), UPLOAD_BATCH):
        batch = all_sorted[batch_start:batch_start + UPLOAD_BATCH]
        batch_num = batch_start // UPLOAD_BATCH + 1
        log(f"Upload batch {batch_num}/{len(all_sorted)//UPLOAD_BATCH} (instances {batch_start}–{batch_start+len(batch)-1})")
        with ThreadPoolExecutor(max_workers=UPLOAD_BATCH) as pool:
            futs = [pool.submit(upload_one, g, p, ssh) for _, (g, p, iid, ssh) in batch]
            for f in as_completed(futs): f.result()
        if batch_start + UPLOAD_BATCH < len(all_sorted):
            log(f"Batch {batch_num} done. Waiting {UPLOAD_PAUSE}s before next batch...")
            time.sleep(UPLOAD_PAUSE)

    log("All uploads complete. Starting encode rounds...")

    # Phase 4: 5 rounds — measure per group
    round_times = {g: [] for g in range(N_GROUPS)}

    for rnd in range(1, N_ROUNDS + 1):
        log(f"=== Round {rnd}/{N_ROUNDS} ===")
        group_start = {g: None for g in range(N_GROUPS)}
        group_end   = {g: None for g in range(N_GROUPS)}
        group_lock  = threading.Lock()

        def encode_and_time(idx):
            g, p, iid, ssh = all_instances[idx]
            with group_lock:
                if group_start[g] is None:
                    group_start[g] = time.time()
            ok = run_encode(g, p, ssh)
            with group_lock:
                t = time.time()
                if group_end[g] is None or t > group_end[g]:
                    group_end[g] = t
            return g, p, ok

        with ThreadPoolExecutor(max_workers=60) as pool:
            futs = [pool.submit(encode_and_time, idx) for idx in all_instances]
            for f in as_completed(futs): f.result()

        for g in range(N_GROUPS):
            if group_start[g] and group_end[g]:
                elapsed = group_end[g] - group_start[g]
                round_times[g].append(elapsed)
                log(f"  Group {g}: round {rnd} = {elapsed:.2f}s")

    # Phase 5: terminate all
    log("Terminating all instances...")
    with ThreadPoolExecutor(max_workers=60) as pool:
        for idx, (g, p, iid, ssh) in all_instances.items():
            pool.submit(terminate, iid, ssh)

    # Results
    all_times = [t for g in range(N_GROUPS) for t in round_times[g]]
    log("=" * 60)
    log(f"RESULTS — c7g.large Horizontal H.265 ({N_GROUPS}×{N_ROUNDS}={len(all_times)} measurements)")
    for g in range(N_GROUPS):
        ts = round_times[g]
        if ts:
            log(f"  Group {g}: {[f'{t:.1f}' for t in ts]}")
    if len(all_times) >= 2:
        med = statistics.median(all_times)
        std = statistics.stdev(all_times)
        cv  = std / statistics.mean(all_times) * 100
        log(f"  ALL: n={len(all_times)}  med={med:.2f}s  std={std:.2f}s  CV={cv:.1f}%")
    log(f"  Total wall-clock: {(time.time()-total_start)/60:.1f} min")
    log("=" * 60)

    # Save results
    with open(os.path.join(LOG_DIR, "results_v3.txt"), "w") as f:
        f.write(f"n={len(all_times)}\n")
        for t in all_times:
            f.write(f"{t:.4f}\n")

if __name__ == "__main__":
    main()
