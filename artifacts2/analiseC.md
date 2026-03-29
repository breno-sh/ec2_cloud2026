# Análise — Família C (Compute Optimized)

## Configuração Experimental

| Instância | vCPUs | RAM | Custo/hora (USD) | CPU Esperada |
|-----------|-------|-----|------------------|--------------|
| c5.large | 2 | 4 GiB | $0.085 | Intel Xeon Platinum 8275CL @ 3.00GHz |
| c5.xlarge | 4 | 8 GiB | $0.170 | Intel Xeon Platinum 8275CL @ 3.00GHz |
| c5.2xlarge | 8 | 16 GiB | $0.340 | Intel Xeon Platinum 8275CL @ 3.00GHz |
| c5.4xlarge | 16 | 32 GiB | $0.680 | Intel Xeon Platinum 8275CL @ 3.00GHz |

**Codecs:** H.264 (libx264), H.265 (libx265), VP9 (libvpx-vp9)  
**Threads:** 1, 3, 5, 10  
**Iterações:** 30 por configuração  
**Total de execuções:** 4 instâncias × 3 codecs × 4 threads × 30 iterações = **1.440 compressões**

---

## Fórmulas Utilizadas

| Métrica | Fórmula |
|---------|---------|
| **Eficiência** | `1 / (custo_hora/3600 × tempo)` |
| **Custo Total** | `(custo_hora/3600) × tempo` |

---

## Tabela de Estatísticas Descritivas

### H.264

| Instância | Threads | Mediana (s) | Std | Min | Max | Eficiência | Custo ($) |
|-----------|---------|-------------|-----|-----|-----|------------|-----------|
| c5.large | 1 | 2.4264 | 0.0086 | 2.4173 | 2.4538 | 17,455 | $0.0000573 |
| c5.large | 3 | 2.2658 | 0.0059 | 2.2539 | 2.2793 | 18,692 | $0.0000535 |
| c5.large | **5** | **2.2563** | 0.0059 | 2.2484 | 2.2778 | **18,771** | $0.0000533 |
| c5.large | 10 | 2.2711 | 0.0064 | 2.2589 | 2.2840 | 18,649 | $0.0000536 |
| c5.xlarge | 1 | 2.3232 | 0.0109 | 2.3072 | 2.3587 | 9,115 | $0.0001097 |
| c5.xlarge | 3 | 1.3867 | 0.0080 | 1.3737 | 1.4072 | 15,272 | $0.0000655 |
| c5.xlarge | **5** | **1.3239** | 0.0073 | 1.3094 | 1.3381 | **15,996** | $0.0000625 |
| c5.xlarge | 10 | 1.3439 | 0.0074 | 1.3277 | 1.3589 | 15,757 | $0.0000635 |
| c5.2xlarge | 1 | 2.3314 | 0.0081 | 2.3216 | 2.3511 | 4,542 | $0.0002202 |
| c5.2xlarge | 3 | 1.1116 | 0.0373 | 1.0320 | 1.1685 | 9,525 | $0.0001050 |
| c5.2xlarge | 5 | 0.9277 | 0.0068 | 0.9115 | 0.9412 | 11,413 | $0.0000876 |
| c5.2xlarge | **10** | **0.8930** | 0.0054 | 0.8795 | 0.9015 | **11,857** | $0.0000843 |
| c5.4xlarge | 1 | 2.3734 | 0.0138 | 2.3527 | 2.4174 | 2,231 | $0.0004483 |
| c5.4xlarge | 3 | 1.0204 | 0.0346 | 0.9802 | 1.1293 | 5,188 | $0.0001927 |
| c5.4xlarge | 5 | 0.7893 | 0.0273 | 0.7517 | 0.8606 | 6,708 | $0.0001491 |
| c5.4xlarge | **10** | **0.7580** | 0.0134 | 0.7268 | 0.7823 | **6,984** | $0.0001432 |

### H.265

| Instância | Threads | Mediana (s) | Std | Min | Max | Eficiência | Custo ($) |
|-----------|---------|-------------|-----|-----|-----|------------|-----------|
| c5.large | 1 | 3.5668 | 0.0099 | 3.5504 | 3.5938 | 11,874 | $0.0000842 |
| c5.large | 3 | 3.4772 | 0.0096 | 3.4567 | 3.4938 | 12,180 | $0.0000821 |
| c5.large | **5** | **3.4647** | 0.0102 | 3.4496 | 3.4932 | **12,224** | $0.0000818 |
| c5.large | 10 | 3.4831 | 0.0088 | 3.4699 | 3.5023 | 12,160 | $0.0000822 |
| c5.xlarge | 1 | 2.5090 | 0.0130 | 2.4890 | 2.5399 | 8,440 | $0.0001185 |
| c5.xlarge | 3 | 2.2492 | 0.0119 | 2.2114 | 2.2700 | 9,415 | $0.0001062 |
| c5.xlarge | 5 | 2.1886 | 0.0118 | 2.1648 | 2.2218 | 9,676 | $0.0001033 |
| c5.xlarge | **10** | **2.1726** | 0.0112 | 2.1500 | 2.1927 | **9,747** | $0.0001026 |
| c5.2xlarge | 1 | 2.2265 | 0.0170 | 2.1966 | 2.2680 | 4,755 | $0.0002103 |
| c5.2xlarge | 3 | 1.8667 | 0.0085 | 1.8518 | 1.8813 | 5,672 | $0.0001763 |
| c5.2xlarge | 5 | 1.7768 | 0.0090 | 1.7603 | 1.7962 | 5,959 | $0.0001678 |
| c5.2xlarge | **10** | **1.7532** | 0.0097 | 1.7297 | 1.7703 | **6,039** | $0.0001656 |
| c5.4xlarge | 1 | 2.1613 | 0.0201 | 2.1237 | 2.1912 | 2,449 | $0.0004082 |
| c5.4xlarge | 3 | 1.7751 | 0.0091 | 1.7594 | 1.7922 | 2,982 | $0.0003353 |
| c5.4xlarge | 5 | 1.6849 | 0.0094 | 1.6712 | 1.7134 | 3,142 | $0.0003183 |
| c5.4xlarge | **10** | **1.6497** | 0.0089 | 1.6302 | 1.6644 | **3,209** | $0.0003116 |

### VP9

| Instância | Threads | Mediana (s) | Std | Min | Max | Eficiência | Custo ($) |
|-----------|---------|-------------|-----|-----|-----|------------|-----------|
| c5.large | 1 | 21.5388 | 0.0445 | 21.4690 | 21.6547 | 1,966 | $0.0005086 |
| c5.large | 3 | 21.5031 | 0.0365 | 21.4485 | 21.6002 | 1,970 | $0.0005077 |
| c5.large | **5** | **21.4941** | 0.0218 | 21.4585 | 21.5410 | **1,970** | $0.0005075 |
| c5.large | 10 | 21.4986 | 0.0278 | 21.4313 | 21.5496 | 1,970 | $0.0005076 |
| c5.xlarge | 1 | 21.3942 | 0.0273 | 21.3475 | 21.4441 | 990 | $0.0010103 |
| c5.xlarge | 3 | 21.4176 | 0.0355 | 21.3758 | 21.5283 | 989 | $0.0010114 |
| c5.xlarge | 5 | 21.4243 | 0.0317 | 21.3625 | 21.4869 | 988 | $0.0010117 |
| c5.xlarge | 10 | 21.4406 | 0.0426 | 21.3706 | 21.5589 | 988 | $0.0010125 |
| c5.2xlarge | 1 | 21.3316 | 0.0331 | 21.2782 | 21.4166 | 496 | $0.0020147 |
| c5.2xlarge | 3 | 21.3393 | 0.0443 | 21.2860 | 21.4756 | 496 | $0.0020154 |
| c5.2xlarge | **5** | **21.3316** | 0.0524 | 21.2674 | 21.4682 | **496** | $0.0020146 |
| c5.2xlarge | 10 | 21.3535 | 0.0499 | 21.2709 | 21.4559 | 496 | $0.0020167 |
| c5.4xlarge | 1 | 21.5403 | 0.0650 | 21.4764 | 21.6968 | 246 | $0.0040687 |
| c5.4xlarge | 3 | 21.5925 | 0.0508 | 21.4812 | 21.6985 | 245 | $0.0040786 |
| c5.4xlarge | 5 | 21.5660 | 0.0404 | 21.4918 | 21.6357 | 245 | $0.0040736 |
| c5.4xlarge | 10 | 21.5845 | 0.0535 | 21.4757 | 21.6795 | 245 | $0.0040771 |

---

## Testes Estatísticos

### Shapiro-Wilk (Normalidade)

| Resultado | Quantidade | Percentual |
|-----------|------------|------------|
| Não-normal (p < 0.05) | 13 | 27.1% |
| Normal (p ≥ 0.05) | 35 | 72.9% |
| **Total** | **48** | **100%** |

**Conclusão:** Maioria das distribuições é normal (72.9%), mas o uso da mediana e Welch's t-test continua sendo recomendado por robustez.

---

## Principais Descobertas (Key Insights)

### 1. Desempenho Absoluto (Performance)

| Codec | Mais Rápido | Mais Lento | Speedup |
|-------|-------------|------------|---------|
| H.264 | c5.4xlarge @ 10t = **0.76s** | c5.large @ 1t = 2.43s | **3.20×** |
| H.265 | c5.4xlarge @ 10t = **1.65s** | c5.large @ 1t = 3.57s | **2.16×** |
| VP9 | c5.2xlarge @ 5t = **21.33s** | c5.4xlarge @ 3t = 21.59s | **1.01×** |

**Observação:** VP9 é completamente insensível ao tipo de instância — speedup de apenas 1%, confirmando o padrão observado nas famílias T e M. O VP9 é fundamentalmente limitado por processamento sequencial.

### 2. Custo-Eficiência

| Métrica | c5.large | c5.4xlarge | Razão |
|---------|----------|------------|-------|
| Tempo (H.264, 10t) | 2.27s | 0.76s | 3.0× mais rápido |
| Custo por operação | $0.0000536 | $0.0001432 | 2.7× mais caro |
| Eficiência | 18,649 | 6,984 | **2.7× mais eficiente** |

> A **c5.large** é 2.7× mais custo-eficiente que a c5.4xlarge. Padrão idêntico ao das famílias T e M.

### 3. Thread Scaling (Retornos Decrescentes)

| Instância | H.264 1t → 5t | H.264 5t → 10t | Ganho marginal |
|-----------|----------------|-----------------|----------------|
| c5.large | 2.43s → 2.26s (7.0%) | 2.26s → 2.27s (**-0.7%**) | Saturou em 5t |
| c5.xlarge | 2.32s → 1.32s (43.0%) | 1.32s → 1.34s (**-1.5%**) | Saturou em 5t |
| c5.2xlarge | 2.33s → 0.93s (60.1%) | 0.93s → 0.89s (3.7%) | Ganho mínimo |
| c5.4xlarge | 2.37s → 0.79s (66.7%) | 0.79s → 0.76s (3.9%) | Ganho mínimo |

> Padrão idêntico ao da família M: saturação entre 5-10 threads. Instâncias com mais vCPUs escalam melhor (c5.4xlarge ganha 66.7% com 5 threads).

### 4. Comparação Cross-Family (C5 vs M5 vs T3)

| Métrica (H.264, melhor config) | T3 (t3.2xlarge@5t) | M5 (m5.4xlarge@10t) | C5 (c5.4xlarge@10t) |
|--------------------------------|---------------------|----------------------|----------------------|
| **Tempo** | 1.44s | 0.81s | **0.76s** |
| **Eficiência** | 7,542 | 5,766 | **6,984** |
| **Custo** | $0.000133 | $0.000173 | **$0.000143** |
| **Custo/hora** | $0.3328 | $0.768 | $0.680 |

> **C5 é a melhor família para performance absoluta** — 7% mais rápida que M5 e 47% mais rápida que T3. Além disso, a C5 é **21% mais eficiente que a M5** graças ao preço 11.5% menor e clock 20% mais alto.

### 5. Eficiência por Família (c5.large vs m5.large vs t3.micro)

| Métrica (H.264, 5t) | t3.micro@1t | m5.large@5t | c5.large@5t |
|----------------------|-------------|-------------|-------------|
| **Tempo** | 4.44s | 2.53s | 2.26s |
| **Eficiência** | 77,900 | 14,807 | **18,771** |
| **Custo** | $0.0000128 | $0.0000675 | **$0.0000533** |

> Em eficiência pura, **t3.micro** ainda domina (por ser extremamente barata), mas entre instâncias de performance fixa, **c5.large supera m5.large em 27%**.

---

## Dados Gerados

| Arquivo | Localização |
|---------|-------------|
| CSVs agregados | `artifacts2/experimental_data/aggregated_c5_*.csv` |
| Estatísticas descritivas (CSV) | `artifacts2/analysis_output/descriptive_statistics_c5.csv` |
| Testes estatísticos | `artifacts2/analysis_output/statistical_tests_c5.csv` |
