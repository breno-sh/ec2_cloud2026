#!/usr/bin/env python3
"""
Confirms that Part 01 fails with the original Phase 3.1 FFmpeg command.
Runs exactly 1 instance with dynamic FFmpeg install (apt), original command unchanged.
"""
import os, time, sys
from datetime import datetime
import boto3, paramiko

# --- EXACT same params as m5_large_horizontal.py ---
PART_INDEX = 1   # Part 01 is one that always fails
PART_FILE = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/phase3_scaling/video_parts_m5/part_01.mp4"
INSTANCE_TYPE = "m5.large"
CODEC = "libx264"
BITRATE = "2M"
PRESET = "slow"
THREADS = 5
FFMPEG_CMD = f"ffmpeg -i /home/ubuntu/input.mp4 -c:v {CODEC} -preset {PRESET} -b:v {BITRATE} -threads {THREADS} -y /home/ubuntu/output.mp4"

AWS_CONFIG = {
    "ami_id": "ami-0a313d6098716f372",  # Standard Ubuntu 22.04 LTS — same as original
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}", flush=True)

def run():
    log(f"=== Confirmation test: Part {PART_INDEX:02d} with ORIGINAL command ===")
    log(f"FFmpeg command: {FFMPEG_CMD}")
    log(f"AMI: {AWS_CONFIG['ami_id']} (standard Ubuntu, dynamic apt install)")

    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    instance_id, ssh_client = None, None

    try:
        log("Launching m5.large...")
        resp = ec2.run_instances(
            ImageId=AWS_CONFIG['ami_id'], InstanceType=INSTANCE_TYPE,
            KeyName=AWS_CONFIG['key_name'], SecurityGroups=AWS_CONFIG['security_groups'],
            MinCount=1, MaxCount=1
        )
        instance_id = resp['Instances'][0]['InstanceId']
        ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
        log(f"Instance ready: {instance_id} / {ip}")

        time.sleep(30)

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])
        log("SSH connected.")

        log("Installing ffmpeg via apt (exact same as original)...")
        for cmd in ["sudo apt-get update -y", "sudo apt-get install -y ffmpeg"]:
            _, stdout, _ = ssh_client.exec_command(cmd)
            stdout.channel.recv_exit_status()

        _, stdout, _ = ssh_client.exec_command("ffmpeg -version 2>&1 | head -1")
        log(f"FFmpeg version: {stdout.read().decode().strip()}")

        sftp = ssh_client.open_sftp()
        log(f"Uploading part_{PART_INDEX:02d}.mp4...")
        sftp.put(PART_FILE, "/home/ubuntu/input.mp4")
        log("Upload done. Running original FFmpeg command...")

        _, stdout, stderr = ssh_client.exec_command(FFMPEG_CMD)
        exit_status = stdout.channel.recv_exit_status()
        err_output = stderr.read().decode()

        if exit_status != 0:
            log(f"RESULT: FAILED (exit={exit_status})")
            log(f"Error tail: {err_output[-300:]}")
        else:
            log(f"RESULT: SUCCESS (exit=0) — hypothesis NOT confirmed for Part {PART_INDEX:02d}")

        sftp.close()

    finally:
        if ssh_client:
            try: ssh_client.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log(f"Instance {instance_id} terminated.")

if __name__ == "__main__":
    run()
