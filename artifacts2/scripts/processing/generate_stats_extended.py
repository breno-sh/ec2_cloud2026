#!/usr/bin/env python3
"""
Generate descriptive statistics and analysis for M-family instances.
Replicates the analysis methodology from the NOMS paper (Table III).
"""
import pandas as pd
import numpy as np
import os
from scipy import stats

BASE_DIR = "/home/breno/doutorado/ec2sweetspot_noms2"
DATA_DIR = os.path.join(BASE_DIR, "artifacts2", "experimental_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "artifacts2", "analysis_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# M-family instance configurations
csv_files = [
    'aggregated_m5_large.csv',
    'aggregated_m5_xlarge.csv',
    'aggregated_m5_2xlarge.csv',
    'aggregated_m5_4xlarge.csv',
]

# Cost per hour (USD) - us-east-1 on-demand pricing
instance_costs_per_hour = {
    'm5_large':   0.096,
    'm5_xlarge':  0.192,
    'm5_2xlarge': 0.384,
    'm5_4xlarge': 0.768,
}

all_data = {}
for file_name in csv_files:
    file_path = os.path.join(DATA_DIR, file_name)
    df = pd.read_csv(file_path)
    instance_type = file_name.replace('aggregated_', '').replace('.csv', '')
    for col in df.columns:
        parts = col.split(' ')
        if len(parts) >= 2:
            codec = parts[0]
            threads = int(parts[1])
            metric_name = f'{codec}_{threads}_threads'
            all_data[(instance_type, metric_name)] = df[col].dropna().tolist()

# Build long-format DataFrame
data_for_analysis = []
for (instance_type, metric_name), values in all_data.items():
    codec, threads_str, _ = metric_name.split('_')
    threads = int(threads_str)
    cost_per_hour = instance_costs_per_hour[instance_type]
    for value in values:
        efficiency = 1.0 / ((cost_per_hour / 3600.0) * value)
        total_cost = (cost_per_hour / 3600.0) * value
        data_for_analysis.append({
            'InstanceType': instance_type,
            'Codec': codec,
            'Threads': threads,
            'CompressionTime': value,
            'Efficiency': efficiency,
            'TotalCost': total_cost,
        })

df_analysis = pd.DataFrame(data_for_analysis)

# Descriptive statistics
desc_stats = df_analysis.groupby(['InstanceType', 'Codec', 'Threads']).agg(
    CompressionTime_Median=('CompressionTime', 'median'),
    CompressionTime_Std=('CompressionTime', 'std'),
    CompressionTime_Min=('CompressionTime', 'min'),
    CompressionTime_Max=('CompressionTime', 'max'),
    Efficiency_Median=('Efficiency', 'median'),
    TotalCost_Median=('TotalCost', 'median'),
).reset_index()

instance_order = ['m5_large', 'm5_xlarge', 'm5_2xlarge', 'm5_4xlarge']
codec_order = ['h264', 'h265', 'vp9']
desc_stats['instance_sort'] = desc_stats['InstanceType'].map({v: i for i, v in enumerate(instance_order)})
desc_stats['codec_sort'] = desc_stats['Codec'].map({v: i for i, v in enumerate(codec_order)})
desc_stats = desc_stats.sort_values(['instance_sort', 'codec_sort', 'Threads']).drop(columns=['instance_sort', 'codec_sort'])

desc_stats.to_csv(os.path.join(OUTPUT_DIR, 'descriptive_statistics_m5.csv'), index=False)

# Build the table
table_rows = []
for inst in instance_order:
    inst_display = inst.replace('_', '.')
    for threads in [1, 3, 5, 10, 16]:
        row = {'Instance': inst_display, 'Threads': f"{threads} thread"}
        found = False
        for codec in codec_order:
            mask = (desc_stats['InstanceType'] == inst) & (desc_stats['Codec'] == codec) & (desc_stats['Threads'] == threads)
            subset = desc_stats[mask]
            if not subset.empty:
                found = True
                s = subset.iloc[0]
                row[f'{codec}_median'] = s['CompressionTime_Median']
                row[f'{codec}_std'] = s['CompressionTime_Std']
                row[f'{codec}_min'] = s['CompressionTime_Min']
                row[f'{codec}_max'] = s['CompressionTime_Max']
                row[f'{codec}_eff'] = s['Efficiency_Median']
                row[f'{codec}_cost'] = s['TotalCost_Median']
        if found:
            table_rows.append(row)

# Markdown output
md_lines = []
md_lines.append("# Descriptive Statistics - M-Family Instances\n")
md_lines.append("## Compression Time (seconds), Efficiency, and Total Cost\n")
md_lines.append("| Instance Type | Threads | H.264 Median | H.264 Std | H.264 Min | H.264 Max | H.264 Eff | H.264 Cost | H.265 Median | H.265 Std | H.265 Min | H.265 Max | H.265 Eff | H.265 Cost | VP9 Median | VP9 Std | VP9 Min | VP9 Max | VP9 Eff | VP9 Cost |")
md_lines.append("|" + "|".join(["---"] * 19) + "|")

for row in table_rows:
    vals = [row['Instance'], row['Threads']]
    for codec in codec_order:
        if f"{codec}_median" in row:
            vals.extend([
                f"{row[f'{codec}_median']:.4f}",
                f"{row[f'{codec}_std']:.4f}",
                f"{row[f'{codec}_min']:.4f}",
                f"{row[f'{codec}_max']:.4f}",
                f"{row[f'{codec}_eff']:,.0f}",
                f"${row[f'{codec}_cost']:.7f}",
            ])
        else:
            vals.extend(["-", "-", "-", "-", "-", "-"])
    md_lines.append("| " + " | ".join(vals) + " |")

with open(os.path.join(OUTPUT_DIR, 'descriptive_statistics_m5.md'), 'w') as f:
    f.write("\n".join(md_lines))

stat_results = []
for (instance_type, metric_name), values in all_data.items():
    codec, threads_str, _ = metric_name.split('_')
    threads = int(threads_str)
    values_arr = np.array(values)
    
    if len(values_arr) >= 8:
        shapiro_stat, shapiro_p = stats.shapiro(values_arr)
        normal = "Yes" if shapiro_p > 0.05 else "No"
    else:
        shapiro_stat, shapiro_p = None, None
        normal = "N/A"
    
    stat_results.append({
        'Instance': instance_type.replace('_', '.'),
        'Codec': codec,
        'Threads': threads,
        'N': len(values_arr),
        'Shapiro_W': shapiro_stat,
        'Shapiro_p': shapiro_p,
        'Normal': normal,
    })

stat_df = pd.DataFrame(stat_results).sort_values(['Instance', 'Codec', 'Threads'])
stat_df.to_csv(os.path.join(OUTPUT_DIR, 'statistical_tests_m5.csv'), index=False)
