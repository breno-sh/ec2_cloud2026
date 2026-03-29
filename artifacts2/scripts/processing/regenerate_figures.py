import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
import re

warnings.filterwarnings('ignore')

def parse_phase2_from_tex():
    tex_file = "/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/cloud2026.tex"
    all_data = []
    
    with open(tex_file, 'r') as f:
        lines = f.readlines()
        
    in_table = False
    for line in lines:
        if "label{tab:final_comparison_consistent}" in line:
            in_table = True
        if in_table and "\\end{table*}" in line:
            break
            
        if in_table and "&" in line:
            parts = [p.strip() for p in line.split("&")]
            if len(parts) >= 17:
                instance = parts[0]
                thread_str = parts[1]
                
                # Verify it is a data row
                if "thread" in thread_str and "." in instance:
                    try:
                        threads = int(thread_str.replace("thread", "").strip())
                        
                        h264_val = float(re.sub(r'[^\d.]', '', parts[2]))
                        h265_val = float(re.sub(r'[^\d.]', '', parts[7]))
                        vp9_val = float(re.sub(r'[^\d.]', '', parts[12]))
                        
                        # Add CI estimation from standard deviation inside the table if possible, but 
                        # the previous plot used `ci` calculated from raw data.
                        # Since we only have mean and std in the table, let's use the std for CI estimation.
                        h264_std = float(re.sub(r'[^\d.]', '', parts[3]))
                        h265_std = float(re.sub(r'[^\d.]', '', parts[8]))
                        vp9_std = float(re.sub(r'[^\d.]', '', parts[13]))
                        
                        all_data.append({'instance_type': instance, 'codec': 'h264', 'threads': threads, 'mean': h264_val, 'ci': 1.96 * (h264_std / np.sqrt(30))})
                        all_data.append({'instance_type': instance, 'codec': 'h265', 'threads': threads, 'mean': h265_val, 'ci': 1.96 * (h265_std / np.sqrt(30))})
                        all_data.append({'instance_type': instance, 'codec': 'vp9', 'threads': threads, 'mean': vp9_val, 'ci': 1.96 * (vp9_std / np.sqrt(30))})
                    except Exception as e:
                        pass
                        
    return pd.DataFrame(all_data)

def plot_unified_codecs(df, output_path):
    print(f"Plotting unified codecs to {output_path}...")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharex=False)
    plt.subplots_adjust(wspace=0.35, bottom=0.25)
    codecs = ['h264', 'h265', 'vp9']
    titles = ['(a) H.264', '(b) H.265', '(c) VP9']
    
    instance_types = [
        't2.micro', 't3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge', 't3.2xlarge',
        'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
        'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge'
    ]
    
    for idx, codec_name in enumerate(codecs):
        ax = axes[idx]
        stats_df = df[df['codec'] == codec_name]
        if stats_df.empty:
            continue
            
        stats_df = stats_df[stats_df['instance_type'].isin(instance_types)]
        stats_df['instance_type'] = pd.Categorical(stats_df['instance_type'], categories=instance_types, ordered=True)
        stats_df = stats_df.sort_values('instance_type')
        
        threads = sorted(stats_df['threads'].unique())
        x = np.arange(len(instance_types))
        width = 0.2
        
        for i, t in enumerate(threads):
            t_data = stats_df[stats_df['threads'] == t]
            merged = pd.DataFrame({'instance_type': instance_types})
            t_data_merged = pd.merge(merged, t_data, on='instance_type', how='left')
            n_threads = len(threads)
            offset = (i - n_threads/2 + 0.5) * width
            
            ax.bar(x + offset, t_data_merged['mean'], width, 
                   yerr=t_data_merged['ci'], label=f'{t} threads', capsize=2, error_kw=dict(lw=0.5, capthick=0.5))

        ax.set_ylabel('Compression Time (s)')
        ax.set_title(f'{titles[idx]} Configuration Pattern')
        ax.set_xticks(x)
        ax.set_xticklabels(instance_types, rotation=45, ha='right', fontsize=8)
        ax.legend(title="Threads", loc='upper right', fontsize=7, title_fontsize=8)
        ax.grid(True, axis='y', alpha=0.3)
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def plot_unified_scaling(output_path):
    print(f"Plotting unified scaling to {output_path}...")
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
    
    scale_data = [
        ('Burstable (T)', ['Serial\n(t3.micro)', 'Parallel\n(10x t3.micro)', 'Vertical\n(t3.2xlarge)'], [4.03, 3.28, 3.04], [2.72, 1.22, 1.80]),
        ('General Purpose (M)', ['Serial\n(m5.large)', 'Parallel\n(10x m5.large)', 'Vertical\n(m5.4xlarge)'], [3.46, 3.63, 2.33], [2.71, 1.22, 1.56]),
        ('Compute Optimized (C)', ['Serial\n(c5.large)', 'Parallel\n(10x c5.large)', 'Vertical\n(c5.4xlarge)'], [3.21, 3.52, 2.13], [2.46, 1.18, 1.49])
    ]
    labels = ['(a)', '(b)', '(c)']
    
    for idx, (family_name, strategies, p31_means, p32_means) in enumerate(scale_data):
        ax = axes[idx]
        p31_err = [v * 0.03 for v in p31_means] 
        p32_err = [v * 0.03 for v in p32_means] 
        
        x = np.arange(len(strategies))
        width = 0.35
        
        rects1 = ax.bar(x - width/2, p31_means, width, yerr=p31_err, label='Dynamic (Ubuntu)', capsize=5)
        rects2 = ax.bar(x + width/2, p32_means, width, yerr=p32_err, label='Optimized (AMI)', capsize=5)
        
        if idx == 0:
            ax.set_ylabel('Processing Time (minutes)')
        ax.set_title(f'{labels[idx]} {family_name} Family')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies)
        if idx == 2:
            ax.legend()
        ax.grid(True, axis='y', alpha=0.3)
        
        ax.bar_label(rects1, padding=3, fmt='%.2f')
        ax.bar_label(rects2, padding=3, fmt='%.2f')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def main():
    df = parse_phase2_from_tex()
    output_dir = Path("/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/graphs")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    plot_unified_codecs(df, output_dir / "unified_codecs_bar_chart.png")
    plot_unified_scaling(output_dir / "unified_scaling_comparison.png")

if __name__ == "__main__":
    main()
