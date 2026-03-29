#!/usr/bin/env python3
import os
import re
import statistics
import csv

LOG_DIR = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling"
OUTPUT_CSV = "m3_graviton_results_consolidated.csv"

# The M1, M2, and M3 Configurations
MATRICES = [
    # M3 (ARM)
    {"inst": "m7g.large", "strat": "serial", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "m7g.large", "strat": "horizontal", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "m7g.large", "strat": "vertical", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c7g.large", "strat": "serial", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c7g.large", "strat": "horizontal", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c7g.large", "strat": "vertical", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    # M1 & M2 (x86)
    {"inst": "m5.large", "strat": "serial", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "m5.large", "strat": "horizontal", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "m5.large", "strat": "vertical", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c5.large", "strat": "serial", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c5.large", "strat": "horizontal", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
    {"inst": "c5.large", "strat": "vertical", "codecs": ["libx264", "libx265", "libvpx-vp9"]},
]

# Effective types used in logs for Vertical (they show as 4xlarge)
EFFECTIVE_MAP = {
    "m7g.large serial": "m7g.large",
    "m7g.large horizontal": "m7g.large",
    "m7g.large vertical": "m7g.4xlarge",
    "c7g.large serial": "c7g.large",
    "c7g.large horizontal": "c7g.large",
    "c7g.large vertical": "c7g.4xlarge",
}

def consolidate():
    # Final data storage: {(inst, strat, codec): list_of_durations}
    raw_data = {}
    
    # Initialize keys
    for entry in MATRICES:
        for codec in entry["codecs"]:
            raw_data[(entry["inst"], entry["strat"], codec)] = []

    logs = sorted([f for f in os.listdir(LOG_DIR) if f.startswith("phase3_unified_202603")])

    for f in logs:
        path = os.path.join(LOG_DIR, f)
        try:
            with open(path, 'r', errors='ignore') as log_file:
                content = log_file.read()
                
                # We need to correctly associate "Done: XXs" lines with their config.
                # Strategy: Split by config headers or context prefixes.
                
                # Handle Serial: Look for lines with [inst-Serial] Done: XXs
                serial_dones = re.finditer(r"\[(\S+)-Serial\] Done: (\d+\.\d+)s", content)
                for sd in serial_dones:
                    inst_ctx, duration = sd.groups()
                    # We still need the codec from context. 
                    # In serial logs, the Codec is printed near the start of the Phase Header.
                    # Or we look for the "Running: ffmpeg ... -c:v <codec>" line immediately preceding.
                    pre_text = content[:sd.start()]
                    codec_m = re.findall(r"Running: ffmpeg.*? -c:v (\S+)", pre_text)
                    if codec_m:
                        codec = codec_m[-1]
                        key = (inst_ctx, "serial", codec)
                        if key in raw_data:
                            raw_data[key].append(float(duration))

                # Handle Horizontal/Vertical:
                # These use "Horizontal Run X completed in YY.YYs"
                phase_chunks = re.split(r"=== Phase 3.2 (\S+): (?:1x|10x) (\S+) ===", content)
                for i in range(1, len(phase_chunks), 3):
                    strat = phase_chunks[i].lower()
                    inst = phase_chunks[i+1]
                    body = phase_chunks[i+2] if i+2 < len(phase_chunks) else ""
                    
                    codec_m = re.search(r"Codec: (\S+)", body[:200])
                    if codec_m:
                        codec = codec_m.group(1)
                        if (inst, strat, codec) in raw_data:
                            durations = re.findall(r"Run \d+ completed in (\d+\.\d+)s", body)
                            for d in durations:
                                raw_data[(inst, strat, codec)].append(float(d))
        except Exception:
            pass

    # Print results
    print(f"\n{'='*80}")
    print(f"{'Instance':<15} | {'Strategy':<12} | {'Codec':<12} | {'Runs':<5} | {'Mean':<8} | {'Median':<8}")
    print(f"{'-'*80}")
    
    final_rows = []
    
    for (inst, strat, codec), durations in sorted(raw_data.items()):
        # Filter duplicates and cap at 30
        # Interleaved logs might cause us to read the same line multiple times if regex is loose.
        # But here we are more specific.
        
        # In case of overlapping logs, we'll use a set of values or just cap.
        # Since durations have high precision, duplicates are unlikely unless it's the exact same run.
        unique_durations = durations if len(durations) <= 30 else durations[:30]
        
        if len(unique_durations) > 0:
            mean = statistics.mean(unique_durations)
            median = statistics.median(unique_durations)
            stdev = statistics.stdev(unique_durations) if len(unique_durations) > 1 else 0
            
            print(f"{inst:<15} | {strat:<12} | {codec:<12} | {len(unique_durations):<5} | {mean:>7.2f}s | {median:>7.2f}s")
            final_rows.append([inst, strat, codec, len(unique_durations), round(mean, 2), round(median, 2), round(stdev, 2)])
        else:
            print(f"{inst:<15} | {strat:<12} | {codec:<12} | {0:<5} | {'MISSING':>7} | {'MISSING':>7}")

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Instance", "Strategy", "Codec", "Runs", "Mean", "Median", "Stdev"])
        writer.writerows(final_rows)
    
    print(f"{'='*80}")
    print(f"Results saved to {OUTPUT_CSV}")

    # Export Raw Runs
    RAW_CSV = "m3_graviton_raw_runs.csv"
    with open(RAW_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Instance", "Strategy", "Codec", "Run_ID", "Time_Seconds"])
        for (inst, strat, codec), durations in sorted(raw_data.items()):
            unique_durations = durations if len(durations) <= 30 else durations[:30]
            for run_id, d in enumerate(unique_durations, start=1):
                writer.writerow([inst, strat, codec, run_id, d])
    print(f"Raw disaggregated runs saved to {RAW_CSV}")

    print("\nLATEX TABLE ROWS FOR ARM:")
    COSTS = {"m7g.large": 0.0816, "c7g.large": 0.0724}
    for inst in ["t2.micro", "t3.micro", "m5.large", "c5.large", "m7g.large", "c7g.large"]:
        if inst not in COSTS: continue
        for strat in ["horizontal", "serial"]:
            c_hr = COSTS[inst]
            c_sec = c_hr / 3600.0
            row = f"{inst} & {strat} "
            for codec in ["libx264", "libx265", "libvpx-vp9"]:
                key = (inst, strat, codec)
                if key in raw_data and len(raw_data[key]) > 0:
                    durs = raw_data[key]
                    med = statistics.median(durs)
                    std = statistics.stdev(durs) if len(durs) > 1 else 0
                    mi = min(durs)
                    ma = max(durs)
                    tc = c_sec * med
                    eff = 1.0 / (tc * med) if tc > 0 else 0
                    row += f"& {med:.4f} & {std:.4f} & {mi:.4f} & {ma:.4f} & {int(eff):,} | {tc:.7f} "
                else:
                    row += "& - & - & - & - & - "
            print(row + "\\\\")

    print("\nSTATISTICAL ANALYSIS:")
    try:
        from scipy import stats
        import math
        import numpy as np
        
        def cohend(d1, d2):
            n1, n2 = len(d1), len(d2)
            s1, s2 = np.var(d1, ddof=1), np.var(d2, ddof=1)
            s = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
            u1, u2 = np.mean(d1), np.mean(d2)
            return (u1 - u2) / s

        def run_test(label, dist1, dist2):
            if len(dist1) < 3 or len(dist2) < 3: return
            _, p_shapiro1 = stats.shapiro(dist1)
            _, p_shapiro2 = stats.shapiro(dist2)
            _, p_levene = stats.levene(dist1, dist2)
            _, p_ttest = stats.ttest_ind(dist1, dist2, equal_var=(p_levene >= 0.05))
            d = cohend(dist1, dist2)
            print(f"Test: {label}")
            print(f"  Shapiro p-vals: {p_shapiro1:.4f}, {p_shapiro2:.4f}")
            print(f"  Levene p-val: {p_levene:.4f}")
            print(f"  Welch/T-Test p-val: {p_ttest:.2e} | Cohen's d: {abs(d):.2f}\n")

        print("--- H.265 (HEVC) COMPARISON ---")
        d1 = raw_data.get(("m7g.large", "horizontal", "libx265"), [])
        d2 = raw_data.get(("c7g.large", "horizontal", "libx265"), [])
        run_test("m7g.large vs c7g.large (H.265 horizontal)", d1, d2)

        print("--- H.264 (AVC) COMPARISON ---")
        d3 = raw_data.get(("m7g.large", "serial", "libx264"), [])
        d4 = raw_data.get(("m7g.large", "horizontal", "libx264"), [])
        run_test("m7g.large Serial vs Horizontal (H.264)", d3, d4)
        
    except ImportError:
        print("scipy or numpy not installed, skipping stats.")

if __name__ == "__main__":
    consolidate()
