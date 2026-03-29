import sys
import re

def parse_md_table(filepath):
    # ret dict[codec][instance][thread] = { 'median':..., 'std':..., 'min':..., 'max':..., 'eff':..., 'cost':... }
    data = {'H.264': {}, 'H.265': {}, 'VP9': {}}
    
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('| ') and not line.startswith('| Instance Type') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')][1:-1]
                if len(parts) >= 20:
                    inst = parts[0].replace('**', '')
                    threads = parts[1].replace('**', '').replace(' thread', '')
                    
                    for i, codec in enumerate(['H.264', 'H.265', 'VP9']):
                        offset = 2 + i * 6
                        med = parts[offset].replace('**', '')
                        std = parts[offset+1]
                        min_v = parts[offset+2]
                        max_v = parts[offset+3]
                        eff = parts[offset+4].replace('**', '')
                        cost_str = parts[offset+5].replace('$', '').strip()
                        
                        if cost_str and cost_str != '-':
                            cost = f"{float(cost_str):.7f}"
                        else:
                            cost = '-'
                            
                        if inst not in data[codec]:
                            data[codec][inst] = {}
                        
                        if med and med != '-':
                            data[codec][inst][threads] = {
                                'med': med, 'std': std, 'min': min_v, 'max': max_v, 'eff': eff, 'cost': cost
                            }
    return data

data_str_m = parse_md_table('/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/analysis_output/descriptive_statistics_m5.md')
data_str_c = parse_md_table('/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/analysis_output/descriptive_statistics_c5.md')

combined_data = {'H.264': {}, 'H.265': {}, 'VP9': {}}
for codec in ['H.264', 'H.265', 'VP9']:
    combined_data[codec].update(data_str_m[codec])
    combined_data[codec].update(data_str_c[codec])

def format_bold(val, is_min):
    return f"\\textbf{{{val}}}" if is_min else val

instances_order = [
    'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
    'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge'
]
threads_order = ['1', '3', '5', '10', '16']

output_lines = []
for inst in instances_order:
    # find min median and max eff across threads for each codec
    min_med = {'H.264': float('inf'), 'H.265': float('inf'), 'VP9': float('inf')}
    max_eff = {'H.264': 0, 'H.265': 0, 'VP9': 0}
    
    for thr in threads_order:
        for codec in ['H.264', 'H.265', 'VP9']:
            if thr in combined_data[codec].get(inst, {}):
                med_val = float(combined_data[codec][inst][thr]['med'])
                eff_val = float(combined_data[codec][inst][thr]['eff'].replace(',', ''))
                if med_val < min_med[codec]:
                    min_med[codec] = med_val
                if eff_val > max_eff[codec]:
                    max_eff[codec] = eff_val

    for thr in threads_order:
        if thr not in combined_data['H.264'].get(inst, {}):
            continue
            
        row_str = f"\t\t\t{inst} & {thr} thread"
        
        for codec in ['H.264', 'H.265', 'VP9']:
            d = combined_data[codec][inst][thr]
            
            med_val = float(d['med'])
            eff_val = float(d['eff'].replace(',', ''))
            
            is_min_med = (med_val == min_med[codec])
            is_max_eff = (eff_val == max_eff[codec])
            
            med_str = format_bold(f"{med_val:.4f}", is_min_med)
            eff_str = format_bold(d['eff'], is_max_eff)
            
            row_str += f" & {med_str} & {float(d['std']):.4f} & {float(d['min']):.4f} & {float(d['max']):.4f} & {eff_str} | {d['cost']}"
            
        row_str += " \\\\"
        output_lines.append(row_str)

tex_file = '/home/breno/doutorado/ec2sweetspot_noms2/cloud2026/cloud2026.tex'
with open(tex_file, 'r') as f:
    tex_content = f.read()

# Replace the specific M and C section
start_marker = "\\midrule\n\t\t\tm5.large"
end_marker = "\t\t\t\t\\bottomrule"

start_idx = tex_content.find(start_marker)
end_idx = tex_content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_section = "\\midrule\n"
    for line in output_lines:
        new_section += line + "\n"
        if '4xlarge & 10 thread' in line and 'm5' in line:
            pass # keep waiting for 16
        elif 'm5.4xlarge & 16 thread' in line:
            new_section += "\t\t\t\\midrule\n"
            
    # Remove the last midrule
    new_section = new_section.replace("\\midrule\n\t\t\t\\midrule\n", "\\midrule\n").strip()
    
    # Fix the C starts
    new_section = new_section.replace("c5.large & 1 thread", "\\midrule\n\t\t\tc5.large & 1 thread")
    
    updated_content = tex_content[:start_idx] + new_section + "\n" + tex_content[end_idx:]
    with open(tex_file, 'w') as f:
        f.write(updated_content)
    print("Updated successfully!")
else:
    print("Could not find markers.")
