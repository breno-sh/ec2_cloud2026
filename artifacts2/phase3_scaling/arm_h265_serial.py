#!/usr/bin/env python3
"""
Phase 3.2 OPTIMIZED — Serial: 1× ARM instance, full 10-min video, codec=libx265.
Usage: python3 arm_h265_serial.py --instance-type m7g.large
"""
import os, time, sys, argparse
from datetime import datetime
import boto3, paramiko

INPUT_VIDEO = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts/test_videos/video_repetido_10min.mp4"
CODEC    = "libx265"
BITRATE  = "2M"
PRESET   = "slow"
THREADS  = 5

AWS_CONFIG = {
    "ami_id": "ami-0976d56fa61f42304",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

def log(msg, context=None):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    prefix = f" [{context}]" if context else ""
    print(f"[{timestamp}]{prefix} {msg}", flush=True)

def run(instance_type):
    ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])
    instance_id, ssh_client = None, None
    log(f"=== ARM H.265 Serial: 1x {instance_type} ===")
    if not os.path.exists(INPUT_VIDEO):
        log(f"ERROR: Video not found: {INPUT_VIDEO}"); return
    total_start = time.time()
    try:
        log(f"Launching {instance_type}...", instance_type)
        response = ec2.run_instances(
            ImageId=AWS_CONFIG['ami_id'], InstanceType=instance_type,
            KeyName=AWS_CONFIG['key_name'], SecurityGroups=AWS_CONFIG['security_groups'],
            MinCount=1, MaxCount=1)
        instance_id = response['Instances'][0]['InstanceId']
        ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        instance = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
        log(f"Instance ready. IP: {public_ip}", instance_type)
        time.sleep(30)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])
        log(f"SSH connected.", instance_type)
        sftp = ssh_client.open_sftp()
        try:
            log("Uploading full video...", instance_type)
            sftp.put(INPUT_VIDEO, "/home/ubuntu/input.mp4")
            cmd = (f"ffmpeg -i /home/ubuntu/input.mp4 "
                   f"-c:v {CODEC} -preset {PRESET} -b:v {BITRATE} "
                   f"-threads {THREADS} -max_muxing_queue_size 1024 -y /home/ubuntu/output.mp4")
            log("Running H.265 encoding...", instance_type)
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.read().decode()[-300:]}")
            log("Encoding complete. Downloading output...", instance_type)
            out_dir = f"/tmp/arm_serial_{instance_type.replace('.','_')}"
            os.makedirs(out_dir, exist_ok=True)
            sftp.get("/home/ubuntu/output.mp4", f"{out_dir}/output_{int(total_start)}.mp4")
        finally:
            sftp.close()
        total_time = time.time() - total_start
        log("=" * 60)
        log(f"RESULTS — 1x {instance_type} Serial H.265 OPTIMIZED")
        log(f"  Total Time:    {total_time:.2f}s ({total_time/60:.2f} min)")
        log("=" * 60)
    except Exception as e:
        log(f"ERROR: {e}", instance_type)
        raise
    finally:
        if ssh_client:
            try: ssh_client.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log("Instance terminated.", instance_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-type", required=True)
    args = parser.parse_args()
    run(args.instance_type)
