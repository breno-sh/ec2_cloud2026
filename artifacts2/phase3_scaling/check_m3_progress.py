#!/usr/bin/env python3
import os
import re
import sys

LOG_DIR = "/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling"
TOTAL_CONFIGS = 18
TARGET_RUNS = 30

def check_progress():
    logs = sorted([f for f in os.listdir(LOG_DIR) if f.startswith("phase3_unified_20260316") or f.startswith("phase3_unified_20260317")])
    
    completed = set()
    # latest_runs will map (inst, strat, codec) -> max_run
    latest_runs = {}

    for f in logs:
        path = os.path.join(LOG_DIR, f)
        try:
            with open(path, 'r', errors='ignore') as log_file:
                content = log_file.read()
                
                # 1. Identify completed configs via AGGREGATE RESULTS
                # Handle cases with and without timestamps
                agg_blocks = re.findall(r"AGGREGATE RESULTS.*?Instance:\s+(\S+).*?Strategy:\s+(\S+).*?Codec:\s+(\S+)", content, re.DOTALL)
                for inst, strat, codec in agg_blocks:
                    completed.add(f"{inst} {strat} {codec}")
                
                # 2. Context-aware parsing for active runs
                
                # First, check for the "--- [Prefix] Run X/Y ---" format
                # Using a very permissive regex for the run markers
                run_matches = re.finditer(r"(?:\[(.*?)\])?\s+---\s+(?:Horizontal\s+|Vertical\s+)?Run\s+(\d+)/(\d+)\s+---", content)
                for rm in run_matches:
                    ctx, run_num, total_runs = rm.groups()
                    run_num = int(run_num)
                    
                    # If we have a context like [m7g.large-Serial], use it
                    if ctx and "-" in ctx:
                        inst, strat = ctx.split("-", 1)
                        # We still need the codec. Look ahead for the next ffmpeg command with same context
                        search_limit = content.find("---", rm.end())
                        if search_limit == -1: search_limit = len(content)
                        codec_m = re.search(rf"\[{re.escape(ctx)}\]\s+Running: ffmpeg.*? -c:v (\S+)", content[rm.end():rm.end()+500])
                        if codec_m:
                            codec = codec_m.group(1)
                            config_id = f"{inst} {strat.lower()} {codec}"
                            if config_id not in latest_runs or run_num > latest_runs[config_id][0]:
                                latest_runs[config_id] = (run_num, int(total_runs))

                # Also handle the Phase-block split for Horizontal/Vertical
                phase_blocks = re.split(r"=== Phase 3.2 (\S+): (?:1x|10x) (\S+) ===", content)
                for i in range(1, len(phase_blocks), 3):
                    strat = phase_blocks[i]
                    inst = phase_blocks[i+1]
                    body = phase_blocks[i+2] if i+2 < len(phase_blocks) else ""
                    
                    codec_m = re.search(r"Codec: (\S+)", body[:200])
                    if codec_m:
                        codec = codec_m.group(1)
                        config_id = f"{inst} {strat.lower()} {codec}"
                        # Flexible run count
                        run_info = re.findall(r"Run (\d+)/(\d+)", body)
                        if run_info:
                            max_run = max(int(r[0]) for r in run_info)
                            total_r = int(run_info[0][1])
                            if config_id not in latest_runs or max_run > latest_runs[config_id][0]:
                                latest_runs[config_id] = (max_run, total_r)

        except Exception:
            pass

    completed_list = sorted(list(completed))
    active_configs = {c: r for c, r in latest_runs.items() if c not in completed}

    print(f"\n{'='*50}")
    print(f" EXPERIMENT PROGRESS: MELHORIA 3 (ARM GRAVITON)")
    print(f"{'='*50}")
    
    print(f"\nCOMPLETED CONFIGURATIONS ({len(completed_list)}/{TOTAL_CONFIGS}):")
    for c in completed_list:
        print(f"  [X] {c}")
        
    print(f"\nACTIVE / PARTIAL CONFIGURATIONS:")
    for c in sorted(active_configs.keys()):
        run_num, total_r = active_configs[c]
        print(f"  [/] {c} (Run {run_num}/{total_r})")

    # Overall completion metric
    done_runs = len(completed_list) * TARGET_RUNS + sum(r[0] for r in active_configs.values())
    total_possible_runs = TOTAL_CONFIGS * TARGET_RUNS
    percent = (done_runs / total_possible_runs) * 100
    
    print(f"\nOVERALL COMPLETION: {percent:.2f}%")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    check_progress()
