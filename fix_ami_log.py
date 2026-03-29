import glob

files = glob.glob("artifacts2/phase3_scaling/*_opt.py")
for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    content = content.replace('log(f"AMI: {CUSTOM_AMI} (ffmpeg pre-installed)")', 'log(f"AMI: {AWS_CONFIG[\'ami_id\']}")')
    content = content.replace('log(f"AMI: {CUSTOM_AMI}")', 'log(f"AMI: {AWS_CONFIG[\'ami_id\']}")')
    
    with open(f, "w") as file:
        file.write(content)
print("Log statements fixed.")
