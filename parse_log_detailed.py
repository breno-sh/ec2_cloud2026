import re

log_content = ""
with open("artifacts2/phase3_scaling/n30_logs/c5_large_horizontal_opt_run_1.log", "r") as f:
    log_content = f.read()

# Let's extract the actual ffmpeg time for one of the parts.
# The script might not log ffmpeg time directly, but let's check.
import sys
for line in log_content.split('\n'):
    if "ffmpeg" in line.lower() or "compression" in line.lower() or "download" in line.lower() or "upload" in line.lower():
        print(line)
