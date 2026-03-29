#!/usr/bin/env python3
"""
Phase 3 Re-run — Metodologia correta com S3.

Diferenças em relação aos scripts originais:
  - Input: instância baixa via wget de URL pré-assinada do S3 (sem SFTP upload local)
  - Output: apenas verifica que o arquivo existe na instância (sem download local)
  - Timing: wall clock de provisioning → encode completo (sem split, sem transferência local)
  - CPU check: x86 M/C families → terminate+retry se CPU errado
  - Instâncias frescas por run (nunca reutilizadas)

Uso:
  python3 phase3_rerun_s3.py --instance-type m5.large --strategy serial   --codec libx264    --runs 30
  python3 phase3_rerun_s3.py --instance-type c5.large --strategy horizontal --codec libx265  --runs 30
  python3 phase3_rerun_s3.py --instance-type m7g.large --strategy vertical  --codec libvpx-vp9 --runs 30
"""
import argparse, os, time, sys, boto3, paramiko
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ── S3 ──────────────────────────────────────────────────────────────────────
S3_BUCKET   = "brenovasconcelos"
S3_FULL_KEY = "full_video/video_repetido_10min.mp4"
S3_CHUNK_PREFIX = "h265_chunks"   # part_00.mp4 … part_09.mp4
NUM_CHUNKS  = 10
REGION      = "us-east-1"

# ── AMIs ────────────────────────────────────────────────────────────────────
AMI_X86 = "ami-06c7c20c67513469a"   # x86, ffmpeg pre-installed
AMI_ARM = "ami-0976d56fa61f42304"   # ARM Graviton3, ffmpeg pre-installed

# ── Instance configs ─────────────────────────────────────────────────────────
INSTANCE_CONFIGS = {
    # (base_type, strategy) → (effective_type, ami, threads, expected_cpu)
    # x86 M-family
    "m5.large":   {"ami": AMI_X86, "serial_threads": 5, "horiz_threads": 5, "vert_type": "m5.4xlarge", "vert_threads": 10,
                   "expected_cpu": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz"},
    "c5.large":   {"ami": AMI_X86, "serial_threads": 5, "horiz_threads": 5, "vert_type": "c5.4xlarge", "vert_threads": 10,
                   "expected_cpu": "Intel(R) Xeon(R) Platinum 8275CL CPU @ 3.00GHz"},
    # ARM
    "m7g.large":  {"ami": AMI_ARM, "serial_threads": 5, "horiz_threads": 5, "vert_type": "m7g.4xlarge", "vert_threads": 10,
                   "expected_cpu": None},
    "c7g.large":  {"ami": AMI_ARM, "serial_threads": 5, "horiz_threads": 5, "vert_type": "c7g.4xlarge", "vert_threads": 10,
                   "expected_cpu": None},
}

# ── Codec ffmpeg flags ────────────────────────────────────────────────────────
CODEC_FLAGS = {
    "libx264":    "-c:v libx264    -preset slow -b:v 2M -max_muxing_queue_size 1024",
    "libx265":    "-c:v libx265    -preset slow -b:v 2M -max_muxing_queue_size 1024",
    "libvpx-vp9": "-c:v libvpx-vp9             -b:v 2M -max_muxing_queue_size 1024",
}

AWS_KEY_NAME  = "bvasconcelos"
AWS_SG        = ["bvasconcelosGroup"]
LOCAL_KEY     = "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem"

def log(msg, ctx=None):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    prefix = f" [{ctx}]" if ctx else ""
    print(f"[{ts}]{prefix} {msg}", flush=True)

def run_remote(ssh, cmd):
    _, stdout, stderr = ssh.exec_command(cmd)
    rc = stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode(), rc

def get_cpu_model(ssh):
    out, _, _ = run_remote(ssh, "grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs")
    return out.strip()

def launch_and_verify_cpu(ec2, inst_type, ami, expected_cpu, ctx):
    """Launch instance, wait, get IP. Retry if CPU mismatch."""
    MAX_RETRIES = 5
    for attempt in range(1, MAX_RETRIES + 1):
        instance_id = None
        ssh = None
        try:
            resp = ec2.run_instances(
                ImageId=ami, InstanceType=inst_type,
                KeyName=AWS_KEY_NAME, SecurityGroups=AWS_SG,
                MinCount=1, MaxCount=1)
            instance_id = resp['Instances'][0]['InstanceId']
            ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
            public_ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
            time.sleep(30)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(public_ip, username="ubuntu", key_filename=LOCAL_KEY)

            if expected_cpu:
                cpu = get_cpu_model(ssh)
                if cpu != expected_cpu:
                    log(f"CPU mismatch (got '{cpu}', want '{expected_cpu}') — terminating & retrying (attempt {attempt})", ctx)
                    ssh.close()
                    ec2.terminate_instances(InstanceIds=[instance_id])
                    continue
                log(f"CPU OK: {cpu}", ctx)
            else:
                log(f"ARM instance — no CPU check needed", ctx)

            return instance_id, ssh, public_ip
        except Exception as e:
            if ssh:
                try: ssh.close()
                except: pass
            if instance_id:
                try: ec2.terminate_instances(InstanceIds=[instance_id])
                except: pass
            if attempt == MAX_RETRIES:
                raise
            log(f"Launch error (attempt {attempt}): {e} — retrying", ctx)
            time.sleep(5)
    raise RuntimeError(f"Failed to get correct CPU after {MAX_RETRIES} attempts")

def process_part_horizontal(part_idx, inst_type, ami, expected_cpu, codec_flags, threads, s3_chunk_url, run_idx):
    ctx = f"run{run_idx:02d}/part{part_idx:02d}"
    ec2 = boto3.client('ec2', region_name=REGION)
    instance_id, ssh = None, None
    t0 = time.time()
    try:
        instance_id, ssh, public_ip = launch_and_verify_cpu(ec2, inst_type, ami, expected_cpu, ctx)
        t_ready = time.time()

        # S3 download on instance
        out, _, rc = run_remote(ssh, f"wget -q '{s3_chunk_url}' -O /home/ubuntu/input.mp4 && echo OK")
        if rc != 0 or "OK" not in out:
            raise RuntimeError("wget chunk failed")
        t_dl = time.time()

        # Encode
        cmd = f"ffmpeg -i /home/ubuntu/input.mp4 {codec_flags} -threads {threads} -y /home/ubuntu/output.mp4 2>&1"
        out, _, rc = run_remote(ssh, cmd)
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed: {out[-300:]}")
        t_enc = time.time()

        # Verify output
        out, _, rc = run_remote(ssh, "stat -c %s /home/ubuntu/output.mp4")
        if rc != 0:
            raise RuntimeError("output file missing")

        return {
            "part": part_idx, "status": "ok",
            "total_s": t_enc - t0,
            "provision_s": t_ready - t0,
            "s3_dl_s": t_dl - t_ready,
            "encode_s": t_enc - t_dl,
        }
    except Exception as e:
        log(f"ERROR part {part_idx}: {e}", ctx)
        return {"part": part_idx, "status": "error", "error": str(e)}
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])

def run_horizontal(run_idx, inst_type, ami, expected_cpu, codec_flags, threads, s3_chunk_urls):
    ctx = f"run{run_idx:02d}"
    log(f"Starting horizontal run {run_idx} — launching {NUM_CHUNKS} instances", ctx)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=NUM_CHUNKS) as ex:
        futures = [
            ex.submit(process_part_horizontal,
                      i, inst_type, ami, expected_cpu, codec_flags, threads,
                      s3_chunk_urls[i], run_idx)
            for i in range(NUM_CHUNKS)
        ]
        results = [f.result() for f in futures]
    total = time.time() - t0
    errors = [r for r in results if r['status'] != 'ok']
    if errors:
        log(f"Run {run_idx} had {len(errors)} errors: {[e['error'] for e in errors]}", ctx)
        return None
    log(f"Run {run_idx} OK — Total: {total:.2f}s", ctx)
    return total

def run_single_instance(run_idx, inst_type, ami, expected_cpu, codec_flags, threads, s3_full_url, strategy):
    ctx = f"run{run_idx:02d}"
    log(f"Starting {strategy} run {run_idx}", ctx)
    ec2 = boto3.client('ec2', region_name=REGION)
    t0 = time.time()
    instance_id, ssh = None, None
    try:
        instance_id, ssh, _ = launch_and_verify_cpu(ec2, inst_type, ami, expected_cpu, ctx)
        t_ready = time.time()

        out, _, rc = run_remote(ssh, f"wget -q '{s3_full_url}' -O /home/ubuntu/input.mp4 && echo OK")
        if rc != 0 or "OK" not in out:
            raise RuntimeError("wget full video failed")
        t_dl = time.time()

        cmd = f"ffmpeg -i /home/ubuntu/input.mp4 {codec_flags} -threads {threads} -y /home/ubuntu/output.mp4 2>&1"
        out, _, rc = run_remote(ssh, cmd)
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed: {out[-300:]}")
        t_enc = time.time()

        out, _, rc = run_remote(ssh, "stat -c %s /home/ubuntu/output.mp4")
        if rc != 0:
            raise RuntimeError("output file missing")

        total = t_enc - t0
        log(f"Run {run_idx} OK — Total: {total:.2f}s  (provision: {t_ready-t0:.1f}s  s3_dl: {t_dl-t_ready:.1f}s  encode: {t_enc-t_dl:.1f}s)", ctx)
        return total
    except Exception as e:
        log(f"Run {run_idx} ERROR: {e}", ctx)
        return None
    finally:
        if ssh:
            try: ssh.close()
            except: pass
        if instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            log(f"Instance terminated.", ctx)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-type", required=True, choices=list(INSTANCE_CONFIGS.keys()))
    parser.add_argument("--strategy",      required=True, choices=["serial","horizontal","vertical"])
    parser.add_argument("--codec",         required=True, choices=list(CODEC_FLAGS.keys()))
    parser.add_argument("--runs",          type=int, default=30)
    parser.add_argument("--log-dir",       default="n30_rerun_s3_logs")
    args = parser.parse_args()

    cfg = INSTANCE_CONFIGS[args.instance_type]
    codec_flags = CODEC_FLAGS[args.codec]
    expected_cpu = cfg["expected_cpu"]

    if args.strategy == "vertical":
        inst_type = cfg["vert_type"]
        threads   = cfg["vert_threads"]
    else:
        inst_type = args.instance_type
        threads   = cfg["horiz_threads"] if args.strategy == "horizontal" else cfg["serial_threads"]

    ami = cfg["ami"]

    label = f"{args.instance_type}_{args.strategy}_{args.codec.replace('-','_').replace('/','_')}"
    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, f"{label}.log")

    log(f"=== Phase 3 Re-run (S3 methodology) ===")
    log(f"Config: {inst_type} | strategy={args.strategy} | codec={args.codec} | threads={threads} | runs={args.runs}")
    log(f"CPU check: {expected_cpu or 'N/A (ARM)'}")
    log(f"Log: {log_path}")

    # Generate S3 pre-signed URLs (valid 12h)
    s3 = boto3.client('s3', region_name=REGION)
    if args.strategy == "horizontal":
        s3_urls = [
            s3.generate_presigned_url('get_object',
                Params={'Bucket': S3_BUCKET, 'Key': f"{S3_CHUNK_PREFIX}/part_{i:02d}.mp4"},
                ExpiresIn=43200)
            for i in range(NUM_CHUNKS)
        ]
    else:
        s3_full_url = s3.generate_presigned_url('get_object',
            Params={'Bucket': S3_BUCKET, 'Key': S3_FULL_KEY},
            ExpiresIn=43200)

    times = []
    with open(log_path, "w") as logfile:
        class Tee:
            def __init__(self, *fs): self.fs = fs
            def write(self, d):
                for f in self.fs: f.write(d); f.flush()
            def flush(self):
                for f in self.fs: f.flush()
        tee = Tee(sys.__stdout__, logfile)
        sys.stdout = sys.stderr = tee
        try:
            for run_idx in range(1, args.runs + 1):
                if args.strategy == "horizontal":
                    t = run_horizontal(run_idx, inst_type, ami, expected_cpu,
                                       codec_flags, threads, s3_urls)
                else:
                    t = run_single_instance(run_idx, inst_type, ami, expected_cpu,
                                            codec_flags, threads, s3_full_url,
                                            args.strategy)
                if t is not None:
                    times.append(t)

            import statistics
            if times:
                log(f"\n{'='*60}")
                log(f"RESULTS — {inst_type} {args.strategy} {args.codec}")
                log(f"  Runs OK:  {len(times)}/{args.runs}")
                log(f"  Mean:     {statistics.mean(times):.2f}s")
                log(f"  Median:   {statistics.median(times):.2f}s")
                log(f"  Stdev:    {statistics.stdev(times):.2f}s" if len(times)>1 else "  Stdev:    N/A")
                log(f"  Min/Max:  {min(times):.2f}s / {max(times):.2f}s")
                log(f"{'='*60}")
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

if __name__ == "__main__":
    main()
