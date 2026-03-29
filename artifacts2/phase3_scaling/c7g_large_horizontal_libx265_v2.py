#!/usr/bin/env python3
"""
Phase 3.2 OPTIMIZED v2 — Horizontal: 10× c7g.large with custom AMI (ARM Graviton3).
Codec: libx265 (H.265/HEVC) — fresh instances per run.

v2: uploads to all 10 instances happen in parallel, but encoding only starts
    after ALL 10 uploads are complete (barrier). Downloads are sequential.
Flow: launch (parallel) → SSH connect (parallel) → upload all (parallel)
      → barrier → encode all (parallel) → download (sequential)
"""
import os, time, sys, subprocess, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3, paramiko

INPUT_VIDEO = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts/test_videos/video_repetido_10min.mp4"
INSTANCE_TYPE = "c7g.large"
THREADS = 5
CODEC = "libx265"
BITRATE = "2M"
PRESET = "slow"
NUM_PARTS = 10

PARTS_DIR      = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling/video_parts_c7g_large_libx265"
COMPRESSED_DIR = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling/compressed_c7g_large_libx265_v2"

AWS_CONFIG = {
    "ami_id": "ami-0976d56fa61f42304",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

download_lock = threading.Lock()  # sequential downloads to avoid bandwidth issues

def log(msg, context=None):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    context_info = f" [{context}]" if context else ""
    print(f"[{timestamp}]{context_info} {msg}", flush=True)

def split_video():
    log("Starting video split...", "Setup")
    os.makedirs(PARTS_DIR, exist_ok=True)
    os.makedirs(COMPRESSED_DIR, exist_ok=True)
    if not os.path.exists(INPUT_VIDEO):
        log(f"ERROR: Video not found at {INPUT_VIDEO}", "Setup"); return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", INPUT_VIDEO],
        capture_output=True, text=True)
    duration = float(result.stdout.strip())
    part_duration = duration / NUM_PARTS
    log(f"Video: {duration:.1f}s → {NUM_PARTS} parts of {part_duration:.1f}s", "Setup")
    for i in range(NUM_PARTS):
        out = f"{PARTS_DIR}/part_{i:02d}.mp4"
        if not os.path.exists(out):
            subprocess.run(["ffmpeg", "-y", "-i", INPUT_VIDEO,
                "-ss", str(i * part_duration), "-t", str(part_duration),
                "-c", "copy", out],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("Video split complete.", "Setup")
    return True

def launch_and_connect(part_index):
    """Phase 1+2: launch instance and establish SSH connection."""
    context = f"Part {part_index:02d}"
    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    log(f"Launching {INSTANCE_TYPE}...", context)
    response = ec2.run_instances(
        ImageId=AWS_CONFIG['ami_id'], InstanceType=INSTANCE_TYPE,
        KeyName=AWS_CONFIG['key_name'], SecurityGroups=AWS_CONFIG['security_groups'],
        MinCount=1, MaxCount=1)
    instance_id = response['Instances'][0]['InstanceId']
    ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    public_ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
    log(f"Instance ready. IP: {public_ip}", context)
    time.sleep(30)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(public_ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])
    _, stdout, _ = ssh.exec_command("uname -m")
    log(f"CPU: {stdout.read().decode().strip()}", context)
    return part_index, instance_id, ssh

def upload_part(part_index, ssh):
    """Phase 3: upload chunk (parallel across all instances)."""
    context = f"Part {part_index:02d}"
    log("Uploading segment...", context)
    sftp = ssh.open_sftp()
    sftp.put(f"{PARTS_DIR}/part_{part_index:02d}.mp4", "/home/ubuntu/input.mp4")
    sftp.close()
    log("Upload done.", context)

def start_encode(part_index, ssh):
    """Phase 4: fire encode command (non-blocking)."""
    cmd = (f"ffmpeg -i /home/ubuntu/input.mp4 "
           f"-c:v {CODEC} -preset {PRESET} -b:v {BITRATE} "
           f"-threads {THREADS} -max_muxing_queue_size 1024 -y /home/ubuntu/output.mp4")
    log("Encoding started.", f"Part {part_index:02d}")
    _, stdout, stderr = ssh.exec_command(cmd)
    return stdout, stderr

def wait_and_download(part_index, instance_id, ssh, stdout_ch, stderr_ch):
    """Phase 5+6: wait for encode, download result sequentially."""
    context = f"Part {part_index:02d}"
    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    exit_status = stdout_ch.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr_ch.read().decode()[-200:]
        log(f"ERROR: FFmpeg failed: {err}", context)
        ssh.close()
        ec2.terminate_instances(InstanceIds=[instance_id])
        log("Instance terminated.", context)
        return False
    with download_lock:
        log("Downloading result...", context)
        sftp = ssh.open_sftp()
        sftp.get("/home/ubuntu/output.mp4",
                 f"{COMPRESSED_DIR}/part_{part_index:02d}_compressed.mp4")
        sftp.close()
    log("Done!", context)
    ssh.close()
    ec2.terminate_instances(InstanceIds=[instance_id])
    log("Instance terminated.", context)
    return True

def run():
    log(f"=== Phase 3.2 OPTIMIZED v2 Horizontal: {NUM_PARTS}x {INSTANCE_TYPE} ===")
    log(f"AMI: {AWS_CONFIG['ami_id']} | Codec: {CODEC} | Threads: {THREADS} | Upload: parallel+barrier")
    total_start = time.time()

    if not split_video(): return
    split_end = time.time()

    # Phase 1+2: launch all instances in parallel
    instances = {}
    with ThreadPoolExecutor(max_workers=NUM_PARTS) as pool:
        futs = {pool.submit(launch_and_connect, i): i for i in range(NUM_PARTS)}
        for f in as_completed(futs):
            part_index, instance_id, ssh = f.result()
            instances[part_index] = (instance_id, ssh)
    log("All instances ready. Starting parallel uploads...", "Summary")

    # Phase 3: upload all chunks in parallel
    upload_start = time.time()
    with ThreadPoolExecutor(max_workers=NUM_PARTS) as pool:
        futs = [pool.submit(upload_part, i, instances[i][1]) for i in range(NUM_PARTS)]
        for f in as_completed(futs): f.result()
    upload_end = time.time()
    log(f"All uploads done in {upload_end - upload_start:.1f}s — BARRIER PASSED. Starting encodes...", "Summary")

    # Phase 4: start all encodes simultaneously (barrier enforced above)
    parallel_start = time.time()
    encode_handles = {}
    for i in range(NUM_PARTS):
        stdout_ch, stderr_ch = start_encode(i, instances[i][1])
        encode_handles[i] = (stdout_ch, stderr_ch)

    # Phase 5+6: wait + download sequentially
    with ThreadPoolExecutor(max_workers=NUM_PARTS) as pool:
        futs = [pool.submit(wait_and_download, i, instances[i][0], instances[i][1],
                            encode_handles[i][0], encode_handles[i][1])
                for i in range(NUM_PARTS)]
        results = [f.result() for f in as_completed(futs)]
    parallel_end = time.time()

    total_time = parallel_end - total_start
    log("=" * 60)
    log(f"RESULTS — {NUM_PARTS}x {INSTANCE_TYPE} Horizontal OPTIMIZED v2")
    log(f"  Total Time:    {total_time:.2f}s ({total_time/60:.2f} min)")
    log(f"  Split Time:    {split_end - total_start:.2f}s")
    log(f"  Upload Time:   {upload_end - upload_start:.2f}s (parallel, barrier)")
    log(f"  Parallel Time: {parallel_end - parallel_start:.2f}s ({(parallel_end - parallel_start)/60:.2f} min)")
    log(f"  Parts OK:      {sum(results)}/{NUM_PARTS}")
    log("=" * 60)

if __name__ == "__main__":
    run()
