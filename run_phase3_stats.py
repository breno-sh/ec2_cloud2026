import os
import pandas as pd
import numpy as np
import scipy.stats as stats

def analyze(name, file1_path, file2_path, time_col='Total_Execute_Time_s'):
    if not os.path.exists(file1_path) or not os.path.exists(file2_path):
        print(f"Skipping {name} due to missing data")
        if not os.path.exists(file1_path): print(f"Missing: {file1_path}")
        if not os.path.exists(file2_path): print(f"Missing: {file2_path}")
        return
        
    df1 = pd.read_csv(file1_path)
    df2 = pd.read_csv(file2_path)
    
    # Check column names if time_col not present (e.g. might be Total_Time_s)
    if time_col not in df1.columns:
        print(f"Columns in {file1_path}: {list(df1.columns)}")
        time_col = [c for c in df1.columns if 'Time' in c and 'Total' in c][0]
        
    times1 = df1[time_col].dropna().values
    times2 = df2[time_col].dropna().values
    
    print(f"\n--- {name} ---")
    print(f"Hori: N={len(times1)}, Mean={np.mean(times1):.4f}, Std={np.std(times1, ddof=1):.4f} (seconds)")
    print(f"Vert: N={len(times2)}, Mean={np.mean(times2):.4f}, Std={np.std(times2, ddof=1):.4f} (seconds)")
    
    # Shapiro-Wilk
    _, p_shapiro1 = stats.shapiro(times1)
    _, p_shapiro2 = stats.shapiro(times2)
    print(f"Shapiro-Wilk Hori: p = {p_shapiro1:.4f} ({'Normal' if p_shapiro1 > 0.05 else 'Not Normal'})")
    print(f"Shapiro-Wilk Vert: p = {p_shapiro2:.4f} ({'Normal' if p_shapiro2 > 0.05 else 'Not Normal'})")
    
    # Levene's Test
    stat_levene, p_levene = stats.levene(times1, times2)
    print(f"Levene Test: p = {p_levene:.4f} ({'Equal Variances' if p_levene > 0.05 else 'Unequal Variances'})")
    
    # Welch's t-test (unequal variances assumed)
    stat_t, p_t = stats.ttest_ind(times1, times2, equal_var=False)
    print(f"Welch's t-test: p = {p_t:.4e}")
    
    # Cohen's d
    m1, m2 = np.mean(times1), np.mean(times2)
    n1, n2 = len(times1), len(times2)
    v1, v2 = np.var(times1, ddof=1), np.var(times2, ddof=1)
    pooled_sd = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    d = (m1 - m2) / pooled_sd
    print(f"Cohen's d: {abs(d):.4f}")

base_dir = "/home/breno/doutorado/ec2sweetspot_noms2/"
a2_parsed = base_dir + "artifacts2/phase3_scaling/n30_parsed/"
a1_parsed = base_dir + "artifacts/phase3_scaling/n30_parsed/"

analyze("M-Family Phase 3", 
        a2_parsed + "horizontal_m5_opt_10x.csv", 
        a2_parsed + "vertical_m5_opt_1x.csv")
        
analyze("C-Family Phase 3", 
        a2_parsed + "horizontal_c5_opt_10x.csv", 
        a2_parsed + "vertical_c5_opt_1x.csv")
        
analyze("T-Family Phase 3", 
        a2_parsed + "horizontal_t3_opt_10x.csv", 
        a2_parsed + "vertical_t3_opt_1x.csv")
