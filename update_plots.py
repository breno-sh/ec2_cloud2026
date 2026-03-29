import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

def load_performance_data():
    all_data = []
    
    data_dirs = [
        Path("/home/breno/doutorado/ec2sweetspot_noms2/artifacts/experimental_data"),
        Path("/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/experimental_data")
    ]
    
    for d_dir in data_dirs:
        if d_dir.exists():
            for file_path in d_dir.glob("aggregated_*.csv"):
                df = pd.read_csv(file_path)
                instance_type = file_path.name.replace('aggregated_', '').replace('.csv', '').replace('_', '.')
                
                for col in df.columns:
                    parts = col.split()
                    if len(parts) >= 2:
                        codec = parts[0]
                        try:
                            threads = int(parts[1])
                        except:
                            continue
                            
                        for value in df[col].dropna():
                            all_data.append({
                                'instance_type': instance_type,
                                'codec': codec,
                                'threads': threads,
                                'compression_time': value
                            })
                            
    return pd.DataFrame(all_data)

def plot_unified_codecs(df, output_path):
    print(f"Plotting unified codecs to {output_path}...")
    fig, axes = plt.subplots(3, 1, figsize=(6, 12), sharex=False)
    plt.subplots_adjust(hspace=0.4, bottom=0.1)
    codecs = ['h264', 'h265', 'vp9']
    titles = ['(a) H.264', '(b) H.265', '(c) VP9']
    
    instance_types = [
        't2.micro', 't3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge', 't3.2xlarge',
        'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
        'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge'
    ]
    
    for idx, codec_name in enumerate(codecs):
        ax = axes[idx]
        subset = df[df['codec'] == codec_name]
        if subset.empty:
            continue
            
        stats_df = subset.groupby(['instance_type', 'threads'])['compression_time'].agg(['mean', 'std', 'count']).reset_index()
        stats_df['se'] = stats_df['std'] / np.sqrt(stats_df['count'])
        stats_df['ci'] = 1.96 * stats_df['se']

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
    df = load_performance_data()
    output_dir = Path("/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/graphs")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    plot_unified_codecs(df, output_dir / "unified_codecs_bar_chart.png")
    plot_unified_scaling(output_dir / "unified_scaling_comparison.png")

if __name__ == "__main__":
    main()
