import time
import os

log_file = "artifacts2/phase3_scaling/run_n30_opt_master.out"
target_string = "ALL 45 ITERATIONS OF PHASE 3 COMPLETED."

print(f"Monitoring {log_file} for completion...")

while True:
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            if target_string in content:
                print("Found completion string! Exiting.")
                break
    time.sleep(10)
