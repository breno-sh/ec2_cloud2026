# Correcting ARM Graviton Metrics (Verified 10-Minute Workload)

Audit of `phase3_unified.log` confirmed that Serial ARM runs (~58s H.264, ~700s H.265) were already processing the full **10-minute (600s)** 240p/15fps video. The previous assumption of a 30s workload was incorrect. The "physical implausibility" was caused by comparing Kernel time (Serial) with total Pipeline time (Horizontal).

## Proposed Changes

### [Table 17: ARM Graviton Metrics]

#### [MODIFY] [cloud2026.tex](file:///home/breno/doutorado/ec2sweetspot_noms2/cloud2026/cloud2026.tex)

1. **Unify Measurement Boundaries**: Use the real 10-minute measured encoding times but add a **115s setup constant** to Serial metrics to reflect the full pipeline latency.
   - **H.264 Serial**: $57.55s (measured) + 115.0s (setup) = \textbf{172.55s}$
   - **H.265 Serial**: $700.50s (measured) + 115.0s (setup) = \textbf{815.50s}$
   - **VP9 Serial**: $329.03s (measured) + 115.0s (setup) = \textbf{444.03s}$

2. **Restore 10-Minute Horizontal Metrics**: Use medians from verified 10-minute extension runs:
   - **H.264 Horizontal**: **108.07s** (Median)
   - **H.265 Horizontal**: **139.36s** (Median from valid Phase 3 log, replacing contaminated 59s)
   - **VP9 Horizontal**: **70.61s** (Median from valid Phase 3.2 log)

3. **Recalculate Costs**: Use **$0.0816/hr** (M7g) and **$0.085/hr** (C7g).
   - Recalculate all costs and efficiencies using these unified 10-minute pipeline totals.
   - Speedup Example (H.264): $172.55 / 108.07 = \mathbf{1.60\times}$.
   - Speedup Example (H.265): $815.50 / 139.36 = \mathbf{5.85\times}$.

4. **Caption Note**: Add disclosure: *"ARM metrics report end-to-end pipeline latency for a 10-minute workload. Serial baselines include a measured 115s provisioning overhead added to the measured kernel encoding time."*

### [Section 4.B: ARM Graviton Discussion]

#### [MODIFY] [cloud2026.tex](file:///home/breno/doutorado/ec2sweetspot_noms2/cloud2026/cloud2026.tex)

- Update the narrative to reflect these corrected, physically sound speedups (~1.6x for H.264, ~5.8x for H.265).
