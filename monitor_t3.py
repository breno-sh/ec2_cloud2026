import time
import os
import sys

log_file = "artifacts2/phase3_scaling/run_t3_n45_master.out"
target_string = "ALL T-FAMILY N=45 RUNS COMPLETED"

print(f"Monitoring {log_file} for completion...")

while True:
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            content = f.read()
            if target_string in content:
                print("\n[SUCCESS] Execution finished! The N=45 T-Family tests have concluded.")
                sys.exit(0)
    time.sleep(30)
