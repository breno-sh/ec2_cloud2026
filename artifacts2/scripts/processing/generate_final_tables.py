#!/usr/bin/env python3
"""
Generate final tables for NOMS paper:
1. Benchmark results for all 8 instances (M & C families).
2. Weak vs Strong scaling comparison (Phase 3 results).
"""
import pandas as pd
import numpy as np
import os
import sys

BASE_DIR = "/home/breno/doutorado/ec2sweetspot_noms2"
DATA_DIR = os.path.join(BASE_DIR, "artifacts2", "experimental_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "artifacts2", "analysis_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Benchmark Data (Phase 2)
# ------------------------------------------------------------------
csv_files = [
    'aggregated_m5_large.csv', 'aggregated_m5_xlarge.csv', 'aggregated_m5_2xlarge.csv', 'aggregated_m5_4xlarge.csv',
    'aggregated_c5_large.csv', 'aggregated_c5_xlarge.csv', 'aggregated_c5_2xlarge.csv', 'aggregated_c5_4xlarge.csv',
]

# Cost per hour (USD) - us-east-1 on-demand
instance_costs_per_hour = {
    'm5_large':   0.096, 'm5_xlarge':  0.192, 'm5_2xlarge': 0.384, 'm5_4xlarge': 0.768,
    'c5_large':   0.085, 'c5_xlarge':  0.170, 'c5_2xlarge': 0.340, 'c5_4xlarge': 0.680,
}

all_data = []

print("Reading benchmark data...")
for file_name in csv_files:
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"WARNING: File not found: {file_path}")
        continue
        
    df = pd.read_csv(file_path)
    instance_type = file_name.replace('aggregated_', '').replace('.csv', '')
    cost_per_hour = instance_costs_per_hour.get(instance_type, 0)
    
    for col in df.columns:
        parts = col.split(' ')
        codec = parts[0]
        threads = int(parts[1])
        values = df[col].dropna().tolist()
        
        for val in values:
            cost = (cost_per_hour / 3600.0) * val
            efficiency = 1.0 / cost if cost > 0 else 0
            
            all_data.append({
                'Instance': instance_type,
                'Codec': codec,
                'Threads': threads,
                'Time': val,
                'Cost': cost,
                'Efficiency': efficiency
            })

df = pd.DataFrame(all_data)

# Aggregation matches TeX table structure:
# Instance | Thread | Median | Std | Min | Max | Efficiency | Cost
agg = df.groupby(['Instance', 'Codec', 'Threads']).agg(
    Time_Median=('Time', 'median'),
    Time_Std=('Time', 'std'),
    Time_Min=('Time', 'min'),
    Time_Max=('Time', 'max'),
    Efficiency_Median=('Efficiency', 'median'), # Median of efficency values
    Cost_Median=('Cost', 'median')
).reset_index()

# Sort order
inst_order = ['m5_large', 'm5_xlarge', 'm5_2xlarge', 'm5_4xlarge',
              'c5_large', 'c5_xlarge', 'c5_2xlarge', 'c5_4xlarge']
agg['inst_sort'] = agg['Instance'].map({v: i for i, v in enumerate(inst_order)})
agg = agg.sort_values(['inst_sort', 'Threads'])

# Generate Markdown Table 1 (Benchmark)
# Structure: Instance | Threads | H.264 stats | H.265 stats | VP9 stats
print("\nGenerating Table 1 (Benchmarks)...")
table1_lines = []
header = "| Instance | Threads | H.264 Median | H.264 Std | H.264 Min | H.264 Max | H.264 Eff | H.264 Cost | H.265 Median | H.265 Std | H.265 Min | H.265 Max | H.265 Eff | H.265 Cost | VP9 Median | VP9 Std | VP9 Min | VP9 Max | VP9 Eff | VP9 Cost |"
table1_lines.append(header)
table1_lines.append("|" + "|".join(["---"] * 20) + "|")

for inst in inst_order:
    for th in [1, 3, 5, 10, 16]:
        row_str = f"| {inst.replace('_', '.')} | {th} |"
        for codec in ['h264', 'h265', 'vp9']:
            row = agg[(agg['Instance'] == inst) & (agg['Threads'] == th) & (agg['Codec'] == codec)]
            if not row.empty:
                r = row.iloc[0]
                row_str += f" {r['Time_Median']:.4f} | {r['Time_Std']:.4f} | {r['Time_Min']:.4f} | {r['Time_Max']:.4f} | {r['Efficiency_Median']:,.0f} | ${r['Cost_Median']:.7f} |"
            else:
                row_str += " - | - | - | - | - | - |"
        table1_lines.append(row_str)

# 2. Phase 3 Comparison Table (Weak vs Strong)
# ------------------------------------------------------------------
# Data hardcoded based on previous Phase 3 execution results
# 1x Weak (Serial), 10x Weak (Horizontal), 1x Strong (Vertical)
# OPTIMIZED (Phase 3.2) values used as they are the final result
print("\nGenerating Table 2 (Weak vs Strong)...")

phase3_data = [
    # Family, Type, Strategy, Time (min), Avg Cost (est)
    # Scaled Cost calc:
    # m5.large = $0.096/hr. 2.90 min -> (0.096/60)*2.90 = $0.00464
    # 10x m5.large = 10 * (0.096/60)*2.39 = $0.03824 (Wait, 10 instances running for 2.39 min? Actually cost is per-second billing per instance. 
    # Horizontal Time 2.39 min is wall clock. Total compute time is roughly 10 x 2.39? 
    # Let's use the walkthrough cost calc logic if possible, or simple estimates)
    # m5.4xlarge = $0.768/hr. 1.65 min -> (0.768/60)*1.65 = $0.02112
    # Let's just output Time for now as requested.
    
    # M-Family
    ("M (m5)", "1x Weak (m5.large)",    "Serial",     2.90),
    ("M (m5)", "10x Weak (m5.large)",   "Horizontal", 1.35),
    ("M (m5)", "1x Strong (m5.4xlarge)","Vertical",   1.65),

    # C-Family
    ("C (c5)", "1x Weak (c5.large)",    "Serial",     2.64),
    ("C (c5)", "10x Weak (c5.large)",   "Horizontal", 1.31),
    ("C (c5)", "1x Strong (c5.4xlarge)","Vertical",   1.54),
]

table2_lines = []
table2_lines.append("| Família | Configuração | Estratégia | Tempo Total (min) | Speedup vs Serial |")
table2_lines.append("| :--- | :--- | :--- | :--- | :--- |")

base_m = 2.90
base_c = 2.64

for row in phase3_data:
    fam, conf, strat, time_val = row
    if "M" in fam: base = base_m
    else: base = base_c
    
    speedup = base / time_val
    table2_lines.append(f"| {fam} | {conf} | {strat} | {time_val:.2f} | {speedup:.2f}x |")

# Output to MD file
with open(os.path.join(OUTPUT_DIR, 'final_tables_noms.md'), 'w') as f:
    f.write("# Final Tables for NOMS Paper\n\n")
    f.write("## Table 1: Benchmark Results (8 Instance Types)\n")
    f.write("\n".join(table1_lines))
    f.write("\n\n## Table 2: Scaling Comparison (Weak vs Strong)\n")
    f.write("\n".join(table2_lines))

print(f"\nTables saved to {os.path.join(OUTPUT_DIR, 'final_tables_noms.md')}")
