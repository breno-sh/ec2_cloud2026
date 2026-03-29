import pandas as pd
import matplotlib.pyplot as plt

tex_file = '/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/cloud2026.tex'
with open(tex_file, 'r') as f:
    lines = f.readlines()

data = []
in_table = False
for line in lines:
    if 't2.micro & 1 thread' in line:
        in_table = True
    if 'bottomrule' in line and in_table:
        in_table = False
    
    if in_table and '&' in line and 'thread' in line:
        clean_line = line.replace('\\textbf{', '').replace('}', '').replace('\\', '').strip()
        parts = [p.strip() for p in clean_line.split('&')]
        if len(parts) >= 17:
            inst = parts[0]
            threads = parts[1].replace('thread', 'thr')
            h264_time = float(parts[2])
            
            h264_cost_str = parts[6].split('|')[1].strip()
            h264_cost_str = h264_cost_str.replace('$', '')
            h264_cost = float(h264_cost_str)
            
            if inst.startswith('t'): family = 'T-Family (Burstable)'
            elif inst.startswith('m'): family = 'M-Family (General Purpose)'
            elif inst.startswith('c'): family = 'C-Family (Compute Optimized)'
            else: family = 'Other'
            
            data.append({
                'Instance': inst, 
                'Config': f"{inst} ({threads.strip()})", 
                'Family': family, 
                'Time': h264_time, 
                'Cost': h264_cost
            })

df = pd.DataFrame(data)

# Find Pareto frontier (minimize both Time and Cost)
df_sorted = df.sort_values('Time')
pareto_front = []
min_cost = float('inf')

for index, row in df_sorted.iterrows():
    if row['Cost'] <= min_cost:
        pareto_front.append(row)
        min_cost = row['Cost']

pareto_df = pd.DataFrame(pareto_front)

plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(8, 6))

colors = {'T-Family (Burstable)': '#2ca02c', 'M-Family (General Purpose)': '#ff7f0e', 'C-Family (Compute Optimized)': '#1f77b4'}
markers = {'T-Family (Burstable)': 'o', 'M-Family (General Purpose)': 's', 'C-Family (Compute Optimized)': '^'}

for family in df['Family'].unique():
    subset = df[df['Family'] == family]
    # For T-family we might want to manually specify colors to match the other graphs later, but this is fine for now
    color = colors.get(family, 'black')
    marker = markers.get(family, 'o')
    ax.scatter(subset['Time'], subset['Cost'], s=80, label=family, color=color, marker=marker, alpha=0.8, edgecolors='k', linewidth=0.5)

# Plot Pareto frontier line
ax.plot(pareto_df['Time'], pareto_df['Cost'], color='red', linestyle='--', linewidth=1.5, label='Pareto Frontier', alpha=0.8)

# Annotate Fastest
best_perf = df.loc[df['Time'].idxmin()]
ax.annotate(f"{best_perf['Config']}", 
            xy=(best_perf['Time'], best_perf['Cost']), 
            xytext=(best_perf['Time']+0.1, best_perf['Cost'] + 0.00005),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=4), 
            fontsize=9)

# Annotate Best Cost
best_cost = df.loc[df['Cost'].idxmin()]
ax.annotate(f"{best_cost['Config']}", 
            xy=(best_cost['Time'], best_cost['Cost']), 
            xytext=(best_cost['Time']+0.3, best_cost['Cost'] - 0.00002),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=4), 
            fontsize=9)

ax.set_xlabel('Execution Time (seconds) - Lower is Better', fontsize=11, fontweight='bold')
ax.set_ylabel('Total Cost (USD) - Lower is Better', fontsize=11, fontweight='bold')
ax.set_title('Cost-Performance Pareto Frontier (H.264)', fontsize=12, fontweight='bold')
ax.legend(title='Instance Family', frameon=True, shadow=True, title_fontsize='10', fontsize='9')

plt.tight_layout()
plt.savefig('/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/graphs/cost_time_scatter.pdf', dpi=300)
print('Done!')
