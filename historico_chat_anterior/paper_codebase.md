# Paper Codebase: NOMS v4 Breakdown & Update Plan

This document maps the paragraphs of `cloud2026/noms_v4.tex` to their content and outlines the necessary updates to incorporate **M-family** and **C-family** results.

## Abstract
- **Lines 55-57:**
    - **Content:** Summarizes the study on T-family burstable instances. Mentions 40.5% speedup vs 20x cost efficiency. Highlights the Horizontal vs Vertical case study (10 instances, 1.28x speedup, 75.5% cost reduction).
    - **Update Plan:** Broaden scope from "burstable" to "diverse instance families (T, M, C)". Update the specific numbers (speedup/cost reduction) to reflect the range across all three families, or highlights the best case (C-family efficiency).

## 1. Introduction
- **Paragraph 1 (Lines 65-66):**
    - **Content:** Contextualizes cloud video processing challenges (trade-offs between capacity, scalability, cost).
    - **Update Plan:** Slight tweak to mention that these trade-offs vary significantly across instance families (General Purpose vs Compute Optimized).
- **Paragraph 2 (Lines 67-68):**
    - **Content:** Identifies the research gap: lack of cost-efficiency analysis for *burstable* instances.
    - **Update Plan:** Expand the gap to include the comparison between *Horizontal Scaling of Weak Instances* (regardless of family) vs *Vertical Scaling*. The gap is confirming if "cluster of small" beats "one big" universally.
- **Paragraph 3 (Lines 69-69):**
    - **Content:** Research Questions (RQs): (1) Cost-performance profiles? (2) Operational overheads? (3) Can optimization make small clusters viable?
    - **Update Plan:** RQs remain valid, but scope expands to M and C families.
- **Paragraph 4 (Lines 71-71):**
    - **Content:** Contributions: Challenges scaling assumptions (smaller is 20x more efficient), quantifies overhead (70%), develops AMI optimization (55% reduction), demonstrates Horizontal > Vertical (1.28x faster).
    - **Update Plan:** **CRITICAL UPDATE.** Add that this phenomenon (Horizontal > Vertical) was validated across M and C families, not just T.
- **Paragraph 5 (Lines 73-73):**
    - **Content:** Practical implications for organizations.
    - **Update Plan:** Keep as is, maybe strengthen "universality" of the finding.

## 2. Related Works
- **Paragraphs 1-6 (Lines 80-94):**
    - **Content:** Reviews literature on Video Coding complexity (VVC), Cloud Optimization (scientific workloads), Multi-cloud (PIVOT), and Benchmarking.
    - **Update Plan:** No major changes needed unless we want to cite something specific about General Purpose vs Compute Optimized comparisons.

## 3. Experimental Methodology
- **Phase 1: Processor Homogeneity (Lines 146-151):**
    - **Content:** Methodology for verifying CPU consistency in T-family (Zone 'a' vs 'f').
    - **Update Plan:** Mention that M and C families were also subject to standard processor verification (though T-family remains the detailed case study).
- **Phase 2: Benchmarks (Lines 169-188):**
    - **Content:** Docker setup, FFmpeg commands, T-family instances (`t2.micro` to `t3.2xlarge`).
    - **Update Plan:** **Add `m5` and `c5` instances** to the list of tested configurations. Update Table II specs.
- **Phase 3: Scaling Analysis (Lines 189-193):**
    - **Content:** Case study: 10x `t3.micro` vs 1x `t3.2xlarge`.
    - **Update Plan:** Explicitly state the expansion of this case study:
        -   **M-Family:** 10x `m5.large` vs 1x `m5.4xlarge`.
        -   **C-Family:** 10x `c5.large` vs 1x `c5.4xlarge`.

## 4. Experimental Results
### Phase 1: Homogeneity
- **Lines 206-213:**
    - **Content:** Results of T-family CPU variation.
    - **Update Plan:** Keep as is.

### Phase 2: Initial Benchmarks
- **Efficiency Calculation (Lines 231-246):**
    - **Content:** Definitions of Efficiency vs Total Cost.
    - **Update Plan:** No change.
- **Performance Analysis (Lines 268-269):**
    - **Content:** Introduces the big descriptive table (Table III).
    - **Update Plan:** **Significant expansion.** Need to include M and C family data in Table III (or a new Table IV).
- **Key Insights (Lines 322-308):**
    - **Content:** Analyzes T-family patterns (diminishing returns, `t3.micro` efficiency king).
    - **Update Plan:** Compare M and C. Likely finding:
        -   T-family = Best Cost Efficiency.
        -   C-family = Best Absolute Speed.
        -   M-family = Balanced.

### Phase 3: Horizontal vs Vertical
- **Overview (Lines 410-413):**
    - **Content:** Sets up the T-family battle.
    - **Update Plan:** diverse into three battles: T-Battle, M-Battle, C-Battle.
- **Two-Phase Results (Lines 415-436):**
    - **Content:**
        -   **Phase 3.1 (Dynamic):** Overhead kills performance (70% time).
        -   **Phase 3.2 (Optimized):** AMI fixes it. Horizontal wins (1.45m vs 1.85m).
    - **Update Plan:** **Add M/C Results.**
        -   **M-Family:** Horizontal (1.35m) vs Vertical (1.65m).
        -   **C-Family:** Horizontal (1.31m) vs Vertical (1.54m).
- **Validation (Lines 438-444):**
    - **Content:** Table V (Unified Case Study).
    - **Update Plan:** Add rows for M and C to Table V. This is the "money shot" of the paper.

## 5. Conclusion
- **Paragraph 1 (Lines 485-485):**
    - **Content:** Summarizes T-family findings (20x efficiency, 1.28x speedup).
    - **Update Plan:** Generalize. "We proved that Optimized Horizontal Scaling is superior across **Burstable, General Purpose, and Compute Optimized** families."
- **Paragraph 2 (Lines 487-487):**
    - **Content:** "Raw power does not correlate with economic efficiency."
    - **Update Plan:** Reinforce this with the M/C data (where even non-burstable weak instances beat the strong ones).
- **Limitations (Lines 489-489):**
    - **Content:** "Specific to AWS T-family..."
    - **Update Plan:** Remove "Specific to T-family" limitation.

---
# Actionable Checklist

1.  [ ] **Modify Abstract:** Include M/C scope.
2.  [ ] **Update Methodology:** Add `m5`/`c5` specs to Table II.
3.  [ ] **Update Phase 2 Results:** Insert M/C benchmark data (Table III update).
4.  [ ] **Update Phase 3 Results:** Add M/C "Battle" results (Horizontal vs Vertical).
5.  [ ] **Update Table V:** Add M/C rows.
6.  [ ] **Rewrite Conclusion:** Generalize findings.
