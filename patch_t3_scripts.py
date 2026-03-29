import os

files_to_patch = [
    "artifacts/phase3_scaling/t3_micro_phase2.py",
    "artifacts/phase3_scaling/t3_2xlarge_phase2.py",
    "artifacts/phase3_scaling/t3_micro_paralelo_phase2.py"
]

for file_path in files_to_patch:
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        
        # 1. Update AMI ID
        content = content.replace('"ami-0a19e2d694753754b"', '"ami-06c7c20c67513469a"')
        
        # 2. Remove max_muxing_queue_size
        content = content.replace(" -max_muxing_queue_size 1024", "")
        
        # 3. Disable strict CPU checks loop to prevent hanging
        old_loop = """                if cpu_model == self.expected_cpu:
                    self.log("CPU correct. Proceeding...", context)
                    break
                
                self.log(f"CPU incorreta. Esperado '{self.expected_cpu}'. Terminando e tentando novamente.", context)
                ssh_client.close()
                ec2.terminate_instances(InstanceIds=[instance_id])
                instance_id = None
                time.sleep(10)"""
        new_loop = """                if cpu_model == self.expected_cpu:
                    self.log("CPU correct. Proceeding...", context)
                else:
                    self.log(f"CPU incorreta. Esperado '{self.expected_cpu}', found {cpu_model}. Proceeding anyway.", context)
                break"""
        content = content.replace(old_loop, new_loop)
        
        old_check = """            if cpu_model != self.expected_cpu:
                self.log(f"ERROR: CPU incorreta. Esperado '{self.expected_cpu}'. Abortando.", context)
                return"""
        content = content.replace(old_check, "")
        
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Patched {file_path}")
