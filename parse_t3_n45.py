import glob
import re
from datetime import datetime
import csv

log_dir = "artifacts2/phase3_scaling/n30_logs"
csv_file = "artifacts2/phase3_scaling/n30_parsed/averages_n30.csv"

# Load existing M and C family data so we don't overwrite it
existing_data = []
with open(csv_file, "r") as f:
    reader = csv.reader(f)
    for row in reader:
        if not row[0].startswith("t3_"): # Drop the old t3 data from phase 2
            existing_data.append(row)

# Parse the new T family logs
t3_archs = ["t3_micro_phase2", "t3_2xlarge_phase2", "t3_micro_paralelo_phase2"]

for arch in t3_archs:
    logs = glob.glob(f"{log_dir}/{arch}_run_*.log")
    
    total_time_sum = 0
    clean_runs = 0
    
    for log in logs:
        with open(log, "r") as f:
            content = f.read()
            
        start_match = re.search(r"Log start:\s+(.+)", content)
        end_match = re.search(r"Log end:\s+(.+)", content)
        
        if start_match and end_match:
            try:
                # Log start: Fri Feb 27 15:23:57 2026
                fmt = "%a %b %d %H:%M:%S %Y"
                start_dt = datetime.strptime(start_match.group(1).strip(), fmt)
                end_dt = datetime.strptime(end_match.group(1).strip(), fmt)
                
                delta_sec = (end_dt - start_dt).total_seconds()
                total_time_sum += delta_sec
                clean_runs += 1
            except ValueError:
                pass

    if clean_runs > 0:
        avg_total = total_time_sum / clean_runs
        # The T3 total times include setup + encoding.
        # From earlier tables, Setup was approx 58s (Parallel) or 94s (Serial).
        # We will split the delta proportionally for the parser CSV format.
        # But wait! Phase 3.2 AMI setup time is identical across all families (1.57min = 94s? No, AMI setup is just EC2 API + SSH boot).
        # We will approximate setup time from the timestamps if possible, or just inject total.
        pass

