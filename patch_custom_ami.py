import glob

files = glob.glob("artifacts2/phase3_scaling/*_opt.py")
for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    # Remove the manual ffmpeg install block
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if 'log("Installing ffmpeg...", context)' in line:
            skip = True
            continue
        if skip and 'log("ffmpeg installed.", context)' in line:
            skip = False
            continue
        if skip:
            continue
        new_lines.append(line)
        
    content = '\n'.join(new_lines)
    
    # Inject the new Custom AMI ID replacing the official Ubuntu ID
    content = content.replace("ami-0a0e5d9c7acc336f1", "ami-06c7c20c67513469a")
    content = content.replace("ami-0a19e2d694753754b", "ami-06c7c20c67513469a")
    
    # Restore the log syntax to confirm it is the pre-installed AMI
    content = content.replace('log(f"AMI: {AWS_CONFIG[\'ami_id\']}")', 'log(f"AMI: {AWS_CONFIG[\'ami_id\']} (ffmpeg pre-installed)")')
    
    with open(f, "w") as file:
        file.write(content)
print("Updated all scripts safely to use ami-06c7c20c67513469a")
