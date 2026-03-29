import glob

files = glob.glob("artifacts2/phase3_scaling/*_opt.py")
for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    # Force replacement of ANY instance of CUSTOM_AMI with the official baked image
    content = content.replace('CUSTOM_AMI', '"ami-06c7c20c67513469a"')
    
    # Also fix the dictionary if the user didn't have quotes
    content = content.replace('"ami_id": ami-06c7c20c67513469a', '"ami_id": "ami-06c7c20c67513469a"')

    with open(f, "w") as file:
        file.write(content)
print("Purged CUSTOM_AMI from ALL scripts universally.")
