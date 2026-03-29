#!/usr/bin/env python3
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os

# Configuration
SCRIPT = "phase3_unified.py"
RUNS = 30
VCPU_LIMIT = 32

# The 5 remaining configurations for M3 with optimized run counts
REMAINING_EXPERIMENTS = [
    {"label": "M3: m7g.large serial libx264", "instance_type": "m7g.large", "strategy": "serial", "codec": "libx264", "cost": 2, "runs": 30},
    {"label": "M3: m7g.large serial libx265", "instance_type": "m7g.large", "strategy": "serial", "codec": "libx265", "cost": 2, "runs": 20},
    {"label": "M3: m7g.large serial libvpx-vp9", "instance_type": "m7g.large", "strategy": "serial", "codec": "libvpx-vp9", "cost": 2, "runs": 7},
    {"label": "M3: c7g.large serial libvpx-vp9", "instance_type": "c7g.large", "strategy": "serial", "codec": "libvpx-vp9", "cost": 2, "runs": 7},
    {"label": "M3: m7g.large horizontal libx264", "instance_type": "m7g.large", "strategy": "horizontal", "codec": "libx264", "cost": 20, "runs": 24},
]

class VCPUBudget:
    def __init__(self, limit):
        self.limit = limit
        self.used = 0
        self.cv = threading.Condition(threading.Lock())

    def acquire(self, cost):
        with self.cv:
            while self.used + cost > self.limit:
                self.cv.wait()
            self.used += cost
            print(f"[{datetime.now().strftime('%H:%M:%S')}] DEBUG: Budget acquired {cost} vCPUs. Used: {self.used}/{self.limit}")

    def release(self, cost):
        with self.cv:
            self.used -= cost
            print(f"[{datetime.now().strftime('%H:%M:%S')}] DEBUG: Budget released {cost} vCPUs. Used: {self.used}/{self.limit}")
            self.cv.notify_all()

def run_experiment(exp, budget):
    cost = exp["cost"]
    budget.acquire(cost)
    try:
        cmd = [
            "python3", SCRIPT,
            "--instance-type", exp["instance_type"],
            "--strategy", exp["strategy"],
            "--codec", exp["codec"],
            "--region", "us-east-1",
            "--runs", str(exp["runs"])
        ]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] RUNNING: {exp['label']}")
        
        # We don't use check=True so that other experiments can continue if one fails
        subprocess.run(cmd, check=False)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] FINISHED: {exp['label']}")
    finally:
        budget.release(cost)

def main():
    budget = VCPUBudget(VCPU_LIMIT)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting resume for final 5 configurations...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_experiment, exp, budget) for exp in REMAINING_EXPERIMENTS]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error in execution thread: {e}")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Resumption script completed.")

if __name__ == "__main__":
    main()
