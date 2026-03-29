import glob
import re
import os
import csv

files = glob.glob("phase3_unified_*.log")
results = []

# Pricing for sa-east-1 ( São Paulo)
PRICING = {
    "m5.large": 0.138,
    "c5.large": 0.122,
    "m5.4xlarge": 1.106,
    "c5.4xlarge": 0.978
}

for f in files:
    content = open(f).read()
    # Find all AGGREGATE RESULTS in case there are multiple in one log
    blocks = content.split("AGGREGATE RESULTS")
    if len(blocks) > 1:
        for block in blocks[1:]:
            # Extract metadata
            inst_match = re.search(r"Instance:\s+(\S+)", block)
            strat_match = re.search(r"Strategy:\s+(\S+)", block)
            codec_match = re.search(r"Codec:\s+(\S+)", block)
            runs_match = re.search(r"(\d+)/30 successful runs", block)
            mean_match = re.search(r"Mean:\s+([\d.]+)s", block)
            median_match = re.search(r"Median:\s+([\d.]+)s", block)
            stdev_match = re.search(r"Stdev:\s+([\d.]+)s", block)
            
            if inst_match and strat_match and codec_match:
                inst = inst_match.group(1)
                results.append({
                    "Codec": codec_match.group(1),
                    "Instance": inst,
                    "Strategy": strat_match.group(1),
                    "Runs": runs_match.group(1) if runs_match else "30",
                    "Mean": mean_match.group(1) if mean_match else "0",
                    "Median": median_match.group(1) if median_match else "0",
                    "Stdev": stdev_match.group(1) if stdev_match else "0",
                    "Cost_per_hour": PRICING.get(inst, 0)
                })

# Calculate specific metrics for Phase 3 (Cost per operation)
for r in results:
    mean_time = float(r["Mean"])
    cost_h = float(r["Cost_per_hour"])
    if r["Strategy"] == "horizontal":
        # Horizontal uses 10 instances
        r["Total_Cost"] = (cost_h * 10) * (mean_time / 3600.0)
    else:
        r["Total_Cost"] = cost_h * (mean_time / 3600.0)

# Sort
results.sort(key=lambda x: (x["Codec"], x["Instance"], x["Strategy"]))

# Write CSV
with open("m2_results_sa_east_1.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

# Print Summary
print(f"{'Codec':<12} {'Instance':<12} {'Strategy':<12} {'Mean':<10} {'Cost ($)':<10}")
print("-" * 60)
for r in results:
    print(f"{r['Codec']:<12} {r['Instance']:<12} {r['Strategy']:<12} {r['Mean']:<10} {r['Total_Cost']:<10.5f}")
