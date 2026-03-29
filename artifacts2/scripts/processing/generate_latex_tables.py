prices = {
    "t3.micro": 0.0104,
    "t3.2xlarge": 0.3328,
    "m5.large": 0.0960,
    "m5.4xlarge": 0.7680,
    "c5.large": 0.0850,
    "c5.4xlarge": 0.6800
}

# The empirical "Total Time" from Phase 3.1 and Phase 3.2 logs
tot = {
    "t": {"p1ser": 4.03, "p1par": 3.28, "p1ver": 3.04, "p2ser": 2.72, "p2par": 1.22, "p2ver": 1.80},
    "m": {"p1ser": 3.46, "p1par": 3.63, "p1ver": 2.33, "p2ser": 2.71, "p2par": 1.22, "p2ver": 1.56},
    "c": {"p1ser": 3.21, "p1par": 3.52, "p1ver": 2.13, "p2ser": 2.46, "p2par": 1.18, "p2ver": 1.49}
}

# Constant algorithmic Encoding Time (using Phase 3.2 clean data as ground truth)
enc = {
    "t": {"ser": 1.72, "par": 0.22, "ver": 0.79},
    "m": {"ser": 1.71, "par": 0.26, "ver": 0.59},
    "c": {"ser": 1.48, "par": 0.24, "ver": 0.52}
}

for fam, fname in [("t", "Burstable (T)"), ("m", "General Purpose (M)"), ("c", "Compute Optimized (C)")]:
    print(f"% ================= {fname} ==================")
    print(rf"			\midrule")
    # For Phase 3.1 & 3.2 format
    
    inst = {}
    if fam == "t":
        inst = {"ser": ("t3.micro", 1), "par": ("t3.micro", 10), "ver": ("t3.2xlarge", 1)}
    elif fam == "m":
        inst = {"ser": ("m5.large", 1), "par": ("m5.large", 10), "ver": ("m5.4xlarge", 1)}
    elif fam == "c":
        inst = {"ser": ("c5.large", 1), "par": ("c5.large", 10), "ver": ("c5.4xlarge", 1)}

    p1ser_t = tot[fam]["p1ser"]; p1par_t = tot[fam]["p1par"]; p1ver_t = tot[fam]["p1ver"]
    p2ser_t = tot[fam]["p2ser"]; p2par_t = tot[fam]["p2par"]; p2ver_t = tot[fam]["p2ver"]

    row_tot = rf"			Total Time (min) & {p1ser_t:.2f} & {p2ser_t:.2f} & {p1par_t:.2f} & {p2par_t:.2f} & {p1ver_t:.2f} & {p2ver_t:.2f} \\"
    
    row_set = rf"			Setup Overhead (min) & {p1ser_t - enc[fam]['ser']:.2f} & {p2ser_t - enc[fam]['ser']:.2f} & {p1par_t - enc[fam]['par']:.2f} & {p2par_t - enc[fam]['par']:.2f} & {p1ver_t - enc[fam]['ver']:.2f} & {p2ver_t - enc[fam]['ver']:.2f} \\"
    
    row_setp = rf"			Setup Overhead (\%) & {(p1ser_t - enc[fam]['ser'])/p1ser_t * 100:.1f}\% & {(p2ser_t - enc[fam]['ser'])/p2ser_t * 100:.1f}\% & {(p1par_t - enc[fam]['par'])/p1par_t * 100:.1f}\% & {(p2par_t - enc[fam]['par'])/p2par_t * 100:.1f}\% & {(p1ver_t - enc[fam]['ver'])/p1ver_t * 100:.1f}\% & {(p2ver_t - enc[fam]['ver'])/p2ver_t * 100:.1f}\% \\"
    
    row_enc = rf"			Effective Encoding Time (min) & {enc[fam]['ser']:.2f} & {enc[fam]['ser']:.2f} & {enc[fam]['par']:.2f} & {enc[fam]['par']:.2f} & {enc[fam]['ver']:.2f} & {enc[fam]['ver']:.2f} \\"
    
    c1ser = prices[inst["ser"][0]] / 60 * p1ser_t * inst["ser"][1]
    c2ser = prices[inst["ser"][0]] / 60 * p2ser_t * inst["ser"][1]
    
    c1par = prices[inst["par"][0]] / 60 * p1par_t * inst["par"][1]
    c2par = prices[inst["par"][0]] / 60 * p2par_t * inst["par"][1]
    
    c1ver = prices[inst["ver"][0]] / 60 * p1ver_t * inst["ver"][1]
    c2ver = prices[inst["ver"][0]] / 60 * p2ver_t * inst["ver"][1]

    row_cost = rf"			Total Cost (USD) & \${c1ser:.5f} & \${c2ser:.5f} & \${c1par:.5f} & \${c2par:.5f} & \${c1ver:.5f} & \${c2ver:.5f} \\"
    row_costm = rf"			Cost per Minute Video & \${c1ser/10:.6f} & \${c2ser/10:.6f} & \${c1par/10:.6f} & \${c2par/10:.6f} & \${c1ver/10:.6f} & \${c2ver/10:.6f} \\"

    row_speedup = rf"			Speedup (vs Serial) & 1.00$\times$ & 1.00$\times$ & {p1ser_t/p1par_t:.2f}$\times$ & {p2ser_t/p2par_t:.2f}$\times$ & {p1ser_t/p1ver_t:.2f}$\times$ & {p2ser_t/p2ver_t:.2f}$\times$ \\"
    row_cfactor = rf"			Cost Factor (vs Serial) & 1.0$\times$ & 1.0$\times$ & {c1par/c1ser:.1f}$\times$ & {c2par/c2ser:.1f}$\times$ & {c1ver/c1ser:.1f}$\times$ & {c2ver/c2ser:.1f}$\times$ \\"
    
    print(row_tot)
    print(row_set)
    print(row_setp)
    print(row_enc)
    print(r"			\midrule")
    print(row_cost)
    print(row_costm)
    print(r"			\midrule")
    print(row_speedup)
    print(row_cfactor)
