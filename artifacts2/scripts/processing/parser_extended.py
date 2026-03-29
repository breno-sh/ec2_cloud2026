#!/usr/bin/env python3
"""
Adapted parser for M-family and C-family instances.
Reads logs from artifacts2/phase2_benchmarks/logs/ and generates aggregated CSVs.
"""
import os
import re
import pandas as pd

# Use absolute paths
BASE_DIR = "/home/breno/doutorado/ec2sweetspot_noms2/"

# Point to the correct log directory
log_dir = os.path.join(BASE_DIR, "artifacts2", "phase2_benchmarks", "logs")

# Output directory for generated CSVs
output_dir = os.path.join(BASE_DIR, "artifacts2", "experimental_data")
os.makedirs(output_dir, exist_ok=True)

# Regex for filename: captures instance type, codec, thread count
file_pattern = re.compile(r"compression_(.+?)_(h264|h265|vp9)_(\d+)thread\.log")
line_pattern = re.compile(r"Compression \d+ \(\d+ threads\): ([\d\.]+) seconds")

results = {}

print(f"📂 Scanning log directory: {log_dir}")
for filename in sorted(os.listdir(log_dir)):
    match = file_pattern.match(filename)
    if not match:
        continue

    instance_type, codec, threads = match.groups()
    key = f"{codec} {threads} thread"
    filepath = os.path.join(log_dir, filename)

    count = 0
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            duration_match = line_pattern.search(line)
            if duration_match:
                duration = float(duration_match.group(1))
                results.setdefault(instance_type, {}).setdefault(key, []).append(duration)
                count += 1
    
    print(f"  ✅ Parsed {filename}: {count} data points")

# Generate one CSV per instance type
for instance_type, data in sorted(results.items()):
    max_len = max(len(v) for v in data.values())
    for k in data:
        data[k] += [None] * (max_len - len(data[k]))

    # Sort columns by codec and thread count
    ordered_keys = sorted(data.keys(), key=lambda k: (k.split()[0], int(k.split()[1])))
    df = pd.DataFrame({k: data[k] for k in ordered_keys})

    out_csv = os.path.join(output_dir, f"aggregated_{instance_type.replace('.', '_')}.csv")
    df.to_csv(out_csv, index=False)
    print(f"✅ CSV generated: {out_csv} with {len(df)} rows and {len(df.columns)} columns")

if not results:
    print("⚠️ No data found. Check log files in", log_dir)
else:
    print(f"\n🎉 Done! Generated {len(results)} CSV files in {output_dir}")
