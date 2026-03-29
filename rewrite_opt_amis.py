import glob

files = glob.glob("artifacts2/phase3_scaling/*_opt.py")
for f in files:
    with open(f, "r") as rfile:
        content = rfile.read()
    
    # Remove custom AMI loading
    content = content.replace('with open("/home/breno/doutorado/ec2sweetspot_noms/ec2sweetspot_noms/artifacts2/phase3_scaling/custom_ami_id.txt") as f:\n    CUSTOM_AMI = f.read().strip()\n', '')
    content = content.replace('    "ami_id": CUSTOM_AMI,\n', '    "ami_id": "ami-0a0e5d9c7acc336f1",  # Ubuntu 22.04 LTS\n')
    
    content = content.replace('# NO ffmpeg install needed — already in AMI!', 'log("Installing ffmpeg...", context)\n        for cmd in ["sudo apt-get update -y", "sudo apt-get install -y ffmpeg"]:\n            stdin, stdout, stderr = ssh_client.exec_command(cmd)\n            stdout.channel.recv_exit_status()\n        log("ffmpeg installed.", context)')
    content = content.replace('# NO ffmpeg install needed!', 'log("Installing ffmpeg...", context)\n        for ssh in ssh_clients:\n            for cmd in ["sudo apt-get update -y", "sudo apt-get install -y ffmpeg"]:\n                ssh.exec_command(cmd)\n        time.sleep(15)\n        log("ffmpeg installed.", context)')

    with open(f, "w") as wfile:
        wfile.write(content)
print("Rewrote AMIs and apt-get blocks.")
