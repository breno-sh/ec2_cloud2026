#!/usr/bin/env python3
"""
ARM H.265 serial: lança 1 instância, faz upload do vídeo UMA vez,
roda ffmpeg 3x medindo só o tempo do encode (sem provisioning).
Consistente com metodologia do phase3_unified (encoding+transfer only).

Usage: python3 arm_h265_serial_3x.py --instance-type m7g.large --worker-id 1
"""
import os, time, sys, argparse
from datetime import datetime
import boto3, paramiko

INPUT_VIDEO = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts/test_videos/video_repetido_10min.mp4"
CODEC   = "libx265"
BITRATE = "2M"
PRESET  = "slow"
THREADS = 5
N_RUNS  = 3

AWS_CONFIG = {
    "ami_id": "ami-0976d56fa61f42304",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}", flush=True)

def run(instance_type, worker_id):
    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    instance_id, ssh_client = None, None
    results = []

    log(f"[W{worker_id}] Launching {instance_type}...")
    try:
        resp = ec2.run_instances(
            ImageId=AWS_CONFIG['ami_id'], InstanceType=instance_type,
            KeyName=AWS_CONFIG['key_name'], SecurityGroups=AWS_CONFIG['security_groups'],
            MinCount=1, MaxCount=1)
        instance_id = resp['Instances'][0]['InstanceId']
        ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
        log(f"[W{worker_id}] Ready at {ip}, sleeping 30s...")
        time.sleep(30)

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])

        sftp = ssh_client.open_sftp()
        log(f"[W{worker_id}] Uploading video (once)...")
        sftp.put(INPUT_VIDEO, "/home/ubuntu/input.mp4")
        log(f"[W{worker_id}] Upload done. Starting {N_RUNS} encodes...")

        for i in range(1, N_RUNS + 1):
            cmd = (f"ffmpeg -i /home/ubuntu/input.mp4 "
                   f"-c:v {CODEC} -preset {PRESET} -b:v {BITRATE} "
                   f"-threads {THREADS} -max_muxing_queue_size 1024 -y /home/ubuntu/output.mp4")
            t0 = time.time()
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            elapsed = time.time() - t0
            if exit_status != 0:
                log(f"[W{worker_id}] Run {i} FAILED: {stderr.read().decode()[-200:]}")
                continue
            results.append(elapsed)
            log(f"[W{worker_id}] Run {i}/{N_RUNS} done: {elapsed:.2f}s")

        sftp.close()

        log(f"[W{worker_id}] === RESULTS — {instance_type} Serial H.265 (worker {worker_id}) ===")
        for idx, t in enumerate(results, 1):
            log(f"[W{worker_id}]   Run {idx}: {t:.4f}s")
        log(f"[W{worker_id}] === END ===")

    except Exception as e:
        log(f"[W{worker_id}] ERROR: {e}")
    finally:
        if ssh_client:
            try: ssh_client.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log(f"[W{worker_id}] Instance terminated.")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-type", required=True)
    parser.add_argument("--worker-id", type=int, default=1)
    args = parser.parse_args()
    run(args.instance_type, args.worker_id)
