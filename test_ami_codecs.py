import boto3
import time
import paramiko
from datetime import datetime

AWS_CONFIG = {
    "ami_id": "ami-06c7c20c67513469a",
    "key_name": "bvasconcelos",
    "security_groups": ["bvasconcelosGroup"],
    "region": "us-east-1",
    "local_key_path": "/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/bvasconcelos.pem",
}

def log(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}")

ec2 = boto3.client('ec2', region_name=AWS_CONFIG['region'])

log("Launching instance with custom AMI to test codec support...")
response = ec2.run_instances(
    ImageId=AWS_CONFIG['ami_id'], 
    InstanceType='t3.micro',
    KeyName=AWS_CONFIG['key_name'], 
    SecurityGroups=AWS_CONFIG['security_groups'],
    MinCount=1, MaxCount=1
)
instance_id = response['Instances'][0]['InstanceId']
log(f"Instance {instance_id} launched. Waiting for Running state...")

ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
instance = ec2.describe_instances(InstanceIds=[instance_id])
public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
log(f"Instance ready. IP: {public_ip}. Waiting 30s for SSH daemon...")
time.sleep(30)

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(public_ip, username="ubuntu", key_filename=AWS_CONFIG['local_key_path'])
log("SSH connected. Testing Codecs...")

commands = [
    ("H.264", "ffmpeg -encoders | grep libx264"),
    ("H.265 (HEVC)", "ffmpeg -encoders | grep libx265"),
    ("VP9", "ffmpeg -encoders | grep libvpx-vp9")
]

all_passed = True
for codec_name, cmd in commands:
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    output = stdout.read().decode().strip()
    if output:
        log(f"[OK] {codec_name} is supported: {output}")
    else:
        log(f"[FAILED] {codec_name} IS MISSING!")
        all_passed = False

ssh_client.close()

log("Terminating test instance...")
ec2.terminate_instances(InstanceIds=[instance_id])

if all_passed:
    log("SUCCESS: All required codecs are natively supported by the AMI!")
else:
    log("ERROR: One or more codecs are missing from the apt-get FFmpeg installation.")
