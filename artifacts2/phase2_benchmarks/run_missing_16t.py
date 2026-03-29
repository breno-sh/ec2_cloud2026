
import boto3
import paramiko
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import textwrap
import os

CONFIG = {
    "ami_id": "ami-0a313d6098716f372",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
    "compression_iterations": 30,
    "video_url": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts/test_videos/big_buck_bunny_240p_20mb.mp4",
}

instance_configs = [
    {"InstanceType": "c5.4xlarge", "vCPUs": 16, "ExpectedCPU": "Intel(R) Xeon(R) Platinum 8275CL CPU @ 3.00GHz"},
    {"InstanceType": "m5.4xlarge", "vCPUs": 16, "ExpectedCPU": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz"},
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def generate_dockerfile(codec, thread_count, iterations):
    codec_flag = {"h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9"}[codec]
    ext = "mp4" if codec in ["h264", "h265"] else "webm"
    return textwrap.dedent(f"""
        FROM ubuntu:22.04
        ENV DEBIAN_FRONTEND=noninteractive
        RUN apt-get update && apt-get install -y wget bc ffmpeg
        WORKDIR /app
        COPY original_video.mp4 /app/original_video.mp4
        RUN echo '#!/bin/bash' > /app/run.sh && \
            echo 'set -e' >> /app/run.sh && \
            echo 'ffmpeg -i /app/original_video.mp4 -t 30 -c copy /app/original_video_30.mp4' >> /app/run.sh && \
            echo 'for i in $(seq 1 {iterations}); do' >> /app/run.sh && \
            echo '  start=$(date +%s.%N)' >> /app/run.sh && \
            echo '  ffmpeg -i /app/original_video_30.mp4 -c:v {codec_flag} -crf 28 -threads {thread_count} /app/compressed_$i.{ext} 1>/dev/null 2>/dev/null' >> /app/run.sh && \
            echo '  end=$(date +%s.%N)' >> /app/run.sh && \
            echo '  duration=$(echo "$end - $start" | bc)' >> /app/run.sh && \
            echo '  echo "Compression $i ({thread_count} threads): ${{duration}} seconds"' >> /app/run.sh && \
            echo 'done' >> /app/run.sh && chmod +x /app/run.sh
        CMD ["/bin/bash", "/app/run.sh"]
    """)

def run_instance(config):
    itype = config["InstanceType"]
    ec2 = boto3.client('ec2', region_name=CONFIG['region'])
    log(f"🚀 Launching {itype} for 16-thread tests...")
    res = ec2.run_instances(
        ImageId=CONFIG['ami_id'], InstanceType=itype, KeyName=CONFIG['key_name'],
        SecurityGroups=CONFIG['security_groups'], MinCount=1, MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': f'Phase2-16T-{itype}'}]}]
    )
    iid = res['Instances'][0]['InstanceId']
    ec2.get_waiter('instance_running').wait(InstanceIds=[iid])
    public_ip = ec2.describe_instances(InstanceIds=[iid])['Reservations'][0]['Instances'][0]['PublicIpAddress']
    time.sleep(30)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(public_ip, username="ubuntu", key_filename=CONFIG['local_key_path'])
    
    sftp = ssh.open_sftp()
    sftp.put(CONFIG["video_url"], "/home/ubuntu/original_video.mp4")
    sftp.close()
    
    ssh.exec_command("sudo apt-get update && sudo apt-get install -y docker.io && sudo usermod -aG docker ubuntu && sudo chmod 666 /var/run/docker.sock")
    time.sleep(20)

    for codec in ["h264", "h265", "vp9"]:
        log(f"[{itype}] Running {codec} 16 threads...")
        log_name = f"compression_{itype}_{codec}_16thread.log"
        df = generate_dockerfile(codec, 16, CONFIG['compression_iterations'])
        stdin, stdout, stderr = ssh.exec_command(f"cat > Dockerfile << 'EOF'\n{df}\nEOF")
        stdout.channel.recv_exit_status()

        log(f"[{itype}] Building and running {codec}...")
        cmd = f"docker build -t comp . && docker run --rm comp | tee /home/ubuntu/{log_name}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Stream logs to avoid timeout and see progress
        for line in stdout:
            pass # just consume to wait
            
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
             log(f"❌ Error on {itype} {codec}")

        # Download log
        sftp = ssh.open_sftp()
        try:
            sftp.get(f"/home/ubuntu/{log_name}", f"logs/{log_name}")
            log(f"✅ Saved {log_name}")
        except:
             log(f"❌ Could not get {log_name}")
        sftp.close()

    ec2.terminate_instances(InstanceIds=[iid])
    log(f"🧹 {itype} terminated.")

def main():
    os.makedirs("logs", exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as exc:
        exc.map(run_instance, instance_configs)

if __name__ == "__main__":
    main()
