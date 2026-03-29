#!/usr/bin/env python3
"""
Benchmark: 1 run de cada codec (libx264, libx265, libvpx-vp9) em serial
em m5.large e c5.large para medir tempos reais com metodologia correta:
  - Input: wget do S3 (sem SFTP upload local)
  - Output: stat apenas (sem download local)
  - Timing: provisioning + sleep(30) + SSH + s3_download + encode
"""
import time, boto3, paramiko
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# S3 pre-signed URL para o vídeo completo
S3_BUCKET = "brenovasconcelos"
S3_KEY    = "full_video/video_repetido_10min.mp4"
REGION    = "us-east-1"

AWS_CONFIG = {
    "key_name":        "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "local_key_path":  "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

# (label, instance_type, ami_id, arch, threads)
INSTANCES = [
    ("m5.large",  "m5.large",  "ami-06c7c20c67513469a", "x86_64", 5),
    ("c5.large",  "c5.large",  "ami-06c7c20c67513469a", "x86_64", 5),
    ("m7g.large", "m7g.large", "ami-0976d56fa61f42304", "arm64",  5),
    ("c7g.large", "c7g.large", "ami-0976d56fa61f42304", "arm64",  5),
]

CODECS = [
    ("libx264",    "-c:v libx264   -preset slow -b:v 2M"),
    ("libx265",    "-c:v libx265   -preset slow -b:v 2M"),
    ("libvpx-vp9", "-c:v libvpx-vp9 -b:v 2M"),
]

THREADS = 5

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def run_remote(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    rc = stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode(), rc

def benchmark_one(inst_label, inst_type, ami_id, codec_name, codec_flags, s3_url):
    ctx = f"{inst_label}/{codec_name}"
    ec2 = boto3.client('ec2', region_name=REGION)
    instance_id = None
    ssh = None
    result = {"inst": inst_label, "codec": codec_name, "status": "error"}
    try:
        t0 = time.time()

        # 1. Launch
        log(f"[{ctx}] Launching...")
        resp = ec2.run_instances(
            ImageId=ami_id, InstanceType=inst_type,
            KeyName=AWS_CONFIG["key_name"],
            SecurityGroups=AWS_CONFIG["security_groups"],
            MinCount=1, MaxCount=1)
        instance_id = resp['Instances'][0]['InstanceId']
        ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        public_ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
        t_provisioned = time.time()
        log(f"[{ctx}] Running ({t_provisioned-t0:.1f}s). IP: {public_ip}")

        # 2. Sleep
        time.sleep(30)

        # 3. SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(public_ip, username="ubuntu", key_filename=AWS_CONFIG["local_key_path"])
        t_ssh = time.time()
        log(f"[{ctx}] SSH OK ({t_ssh-t0:.1f}s)")

        # 4. S3 download
        wget_cmd = f"wget -q '{s3_url}' -O /home/ubuntu/input.mp4 && echo OK"
        out, _, rc = run_remote(ssh, wget_cmd)
        t_downloaded = time.time()
        if rc != 0 or "OK" not in out:
            raise RuntimeError(f"wget failed")
        log(f"[{ctx}] S3 download done ({t_downloaded-t0:.1f}s)")

        # 5. Encode
        cmd = f"ffmpeg -i /home/ubuntu/input.mp4 {codec_flags} -threads {THREADS} -y /home/ubuntu/output.mp4 2>&1"
        log(f"[{ctx}] Encoding...")
        out, _, rc = run_remote(ssh, cmd)
        t_encoded = time.time()
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed: {out[-200:]}")
        log(f"[{ctx}] Encode done ({t_encoded-t0:.1f}s)")

        # 6. Verify output
        out, _, rc = run_remote(ssh, "stat -c %s /home/ubuntu/output.mp4")
        output_size = int(out.strip()) if rc == 0 else -1

        t_total = time.time() - t0
        result = {
            "inst": inst_label, "codec": codec_name, "status": "ok",
            "total_s":       round(t_total, 2),
            "provision_s":   round(t_provisioned - t0, 2),
            "ssh_s":         round(t_ssh - t_provisioned - 30, 2),
            "s3_dl_s":       round(t_downloaded - t_ssh, 2),
            "encode_s":      round(t_encoded - t_downloaded, 2),
            "output_bytes":  output_size,
        }
        log(f"[{ctx}] DONE — total={t_total:.1f}s  encode={result['encode_s']:.1f}s")

    except Exception as e:
        log(f"[{ctx}] ERROR: {e}")
        result["error"] = str(e)
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log(f"[{ctx}] Instance terminated.")
    return result

def main():
    log("=== Serial encoding benchmark — 1 run per (instance, codec) ===")
    log(f"Instances: {[i[0] for i in INSTANCES]}")
    log(f"Codecs: {[c[0] for c in CODECS]}")

    # Generate pre-signed URLs (valid 2h)
    s3 = boto3.client('s3', region_name=REGION)
    s3_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': S3_KEY},
        ExpiresIn=7200)
    log(f"S3 URL generated (2h validity)")

    # Run all combos in parallel (4 instances × 3 codecs = 12 concurrent)
    jobs = []
    for inst_label, inst_type, ami_id, arch, threads in INSTANCES:
        for codec_name, codec_flags in CODECS:
            jobs.append((inst_label, inst_type, ami_id, codec_name, codec_flags, s3_url))

    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futures = [ex.submit(benchmark_one, *j) for j in jobs]
        for f in futures:
            results.append(f.result())

    # Summary table
    print("\n" + "="*75)
    print(f"{'Instance':<12} {'Codec':<12} {'Total':>8} {'Provision':>10} {'S3 DL':>7} {'Encode':>8}")
    print("-"*75)
    for r in sorted(results, key=lambda x: (x['inst'], x['codec'])):
        if r['status'] == 'ok':
            print(f"{r['inst']:<12} {r['codec']:<12} {r['total_s']:>7.1f}s {r['provision_s']:>9.1f}s {r['s3_dl_s']:>6.1f}s {r['encode_s']:>7.1f}s")
        else:
            print(f"{r['inst']:<12} {r['codec']:<12}   ERROR: {r.get('error','?')}")
    print("="*75)

if __name__ == "__main__":
    main()
