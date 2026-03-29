# Análise — Família M (General Purpose)

## Configuração Experimental

| Instância | vCPUs | RAM | Custo/hora (USD) | CPU Esperada |
|-----------|-------|-----|------------------|--------------|
| m5.large | 2 | 8 GiB | $0.096 | Intel Xeon Platinum 8259CL @ 2.50GHz |
| m5.xlarge | 4 | 16 GiB | $0.192 | Intel Xeon Platinum 8259CL @ 2.50GHz |
| m5.2xlarge | 8 | 32 GiB | $0.384 | Intel Xeon Platinum 8259CL @ 2.50GHz |
| m5.4xlarge | 16 | 64 GiB | $0.768 | Intel Xeon Platinum 8259CL @ 2.50GHz |

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
| m5.large | 1 | 2.7308 | 0.0149 | 2.7170 | 2.7642 | 13,732 | $0.0000728 |
| m5.large | 3 | 2.5365 | 0.0116 | 2.5256 | 2.5763 | 14,784 | $0.0000676 |
| m5.large | **5** | **2.5327** | 0.0114 | 2.5179 | 2.5719 | **14,807** | $0.0000675 |
| m5.large | 10 | 2.5555 | 0.0124 | 2.5366 | 2.5837 | 14,674 | $0.0000681 |
| m5.xlarge | 1 | 2.6349 | 0.0129 | 2.6099 | 2.6664 | 7,116 | $0.0001405 |
| m5.xlarge | 3 | 1.5607 | 0.0097 | 1.5419 | 1.5964 | 12,013 | $0.0000832 |
| m5.xlarge | **5** | **1.4758** | 0.0073 | 1.4631 | 1.4928 | **12,705** | $0.0000787 |
| m5.xlarge | 10 | 1.4870 | 0.0073 | 1.4761 | 1.5008 | 12,609 | $0.0000793 |
| m5.2xlarge | 1 | 2.6757 | 0.0211 | 2.6552 | 2.7270 | 3,504 | $0.0002854 |
| m5.2xlarge | 3 | 1.2808 | 0.0365 | 1.2063 | 1.3430 | 7,319 | $0.0001366 |
| m5.2xlarge | 5 | 1.0517 | 0.0080 | 1.0358 | 1.0633 | 8,914 | $0.0001122 |
| m5.2xlarge | **10** | **1.0052** | 0.0068 | 0.9865 | 1.0149 | **9,326** | $0.0001072 |
| m5.4xlarge | 1 | 2.5409 | 0.0114 | 2.5247 | 2.5717 | 1,845 | $0.0005421 |
| m5.4xlarge | 3 | 1.0937 | 0.0209 | 1.0648 | 1.1410 | 4,286 | $0.0002333 |
| m5.4xlarge | 5 | 0.8574 | 0.0316 | 0.8057 | 0.8950 | 5,467 | $0.0001829 |
| m5.4xlarge | **10** | **0.8129** | 0.0150 | 0.7782 | 0.8357 | **5,766** | $0.0001734 |

### H.265

| Instância | Threads | Mediana (s) | Std | Min | Max | Eficiência | Custo ($) |
|-----------|---------|-------------|-----|-----|-----|------------|-----------|
| m5.large | 1 | 4.0685 | 0.0187 | 4.0518 | 4.1222 | 9,217 | $0.0001085 |
| m5.large | 3 | 3.9610 | 0.0187 | 3.9467 | 4.0125 | 9,467 | $0.0001056 |
| m5.large | **5** | **3.9551** | 0.0207 | 3.9312 | 4.0078 | **9,481** | $0.0001055 |
| m5.large | 10 | 3.9679 | 0.0212 | 3.9463 | 4.0373 | 9,451 | $0.0001058 |
| m5.xlarge | 1 | 2.8782 | 0.0163 | 2.8511 | 2.9194 | 6,514 | $0.0001535 |
| m5.xlarge | 3 | 2.5594 | 0.0133 | 2.5421 | 2.5893 | 7,326 | $0.0001365 |
| m5.xlarge | 5 | 2.5133 | 0.0441 | 2.4862 | 2.7398 | 7,460 | $0.0001340 |
| m5.xlarge | **10** | **2.4958** | 0.0118 | 2.4658 | 2.5150 | **7,513** | $0.0001331 |
| m5.2xlarge | 1 | 2.5651 | 0.0166 | 2.5394 | 2.5970 | 3,655 | $0.0002736 |
| m5.2xlarge | 3 | 2.1468 | 0.0118 | 2.1254 | 2.1820 | 4,367 | $0.0002290 |
| m5.2xlarge | 5 | 2.0389 | 0.0120 | 2.0188 | 2.0651 | 4,598 | $0.0002175 |
| m5.2xlarge | **10** | **2.0102** | 0.0121 | 1.9918 | 2.0304 | **4,664** | $0.0002144 |
| m5.4xlarge | 1 | 2.3425 | 0.0265 | 2.3018 | 2.3927 | 2,001 | $0.0004997 |
| m5.4xlarge | 3 | 1.9347 | 0.0129 | 1.9068 | 1.9570 | 2,423 | $0.0004127 |
| m5.4xlarge | 5 | 1.8410 | 0.0105 | 1.8197 | 1.8554 | 2,546 | $0.0003928 |
| m5.4xlarge | **10** | **1.8069** | 0.0135 | 1.7769 | 1.8334 | **2,594** | $0.0003855 |

### VP9

| Instância | Threads | Mediana (s) | Std | Min | Max | Eficiência | Custo ($) |
|-----------|---------|-------------|-----|-----|-----|------------|-----------|
| m5.large | 1 | 24.4904 | 0.0345 | 24.4368 | 24.5605 | 1,531 | $0.0006531 |
| m5.large | 3 | 24.4925 | 0.0410 | 24.4261 | 24.5986 | 1,531 | $0.0006531 |
| m5.large | 5 | 24.4926 | 0.0408 | 24.4350 | 24.6025 | 1,531 | $0.0006531 |
| m5.large | 10 | 24.4897 | 0.0394 | 24.4255 | 24.5746 | 1,531 | $0.0006531 |
| m5.xlarge | 1 | 24.4088 | 0.0342 | 24.3345 | 24.4787 | 768 | $0.0013018 |
| m5.xlarge | 3 | 24.3949 | 0.0519 | 24.3026 | 24.5084 | 769 | $0.0013011 |
| m5.xlarge | 5 | 24.3916 | 0.0615 | 24.2748 | 24.5351 | 769 | $0.0013009 |
| m5.xlarge | 10 | 24.4501 | 0.0517 | 24.3552 | 24.5619 | 767 | $0.0013040 |
| m5.2xlarge | 1 | 24.4169 | 0.0618 | 24.3344 | 24.5881 | 384 | $0.0026045 |
| m5.2xlarge | 3 | 24.4580 | 0.0570 | 24.3252 | 24.5486 | 383 | $0.0026089 |
| m5.2xlarge | 5 | 24.4628 | 0.0679 | 24.3349 | 24.6309 | 383 | $0.0026094 |
| m5.2xlarge | 10 | 24.4896 | 0.0679 | 24.3659 | 24.6345 | 383 | $0.0026122 |
| m5.4xlarge | 1 | 23.5256 | 0.4407 | 23.3837 | 24.5062 | 199 | $0.0050188 |
| m5.4xlarge | 3 | 24.3499 | 0.4209 | 23.4619 | 24.5735 | 193 | $0.0051946 |
| m5.4xlarge | **5** | **23.4499** | 0.0628 | 23.3883 | 23.5833 | **200** | $0.0050026 |
| m5.4xlarge | 10 | 23.5025 | 0.0517 | 23.3804 | 23.5943 | 199 | $0.0050139 |

---

## Testes Estatísticos

### Shapiro-Wilk (Normalidade)

| Resultado | Quantidade | Percentual |
|-----------|------------|------------|
| Não-normal (p < 0.05) | 16 | 33.3% |
| Normal (p ≥ 0.05) | 32 | 66.7% |
| **Total** | **48** | **100%** |

**Conclusão:** Uma porção significativa das distribuições não segue distribuição normal, justificando o uso da **mediana** como medida central e do **Welch's t-test** para comparações.

---

## Principais Descobertas (Key Insights)

### 1. Desempenho Absoluto (Performance)

| Codec | Mais Rápido | Mais Lento | Speedup |
|-------|-------------|------------|---------|
| H.264 | m5.4xlarge @ 10t = **0.81s** | m5.large @ 1t = 2.73s | **3.36×** |
| H.265 | m5.4xlarge @ 10t = **1.81s** | m5.large @ 1t = 4.07s | **2.25×** |
| VP9 | m5.4xlarge @ 5t = **23.45s** | m5.large @ 5t = 24.49s | **1.04×** |

**Observação:** VP9 mostra sensibilidade mínima ao tamanho da instância — o speedup é de apenas 4%, indicando que o VP9 é fundamentalmente limitado por um gargalo sequencial que instâncias maiores não resolvem.

### 2. Custo-Eficiência

| Métrica | m5.large | m5.4xlarge | Razão |
|---------|----------|------------|-------|
| Tempo (H.264, 10t) | 2.56s | 0.81s | 3.2× mais rápido |
| Custo por operação | $0.0000681 | $0.0001734 | 2.5× mais caro |
| Eficiência | 14,674 | 5,766 | **2.5× mais eficiente** |

> A **m5.large** é 2.5× mais custo-eficiente que a m5.4xlarge, mesmo sendo 3.2× mais lenta. Isso confirma o padrão observado na família T: instâncias menores dominam em eficiência.

### 3. Thread Scaling (Retornos Decrescentes)

| Instância | H.264 1t → 5t | H.264 5t → 10t | Ganho marginal |
|-----------|----------------|-----------------|----------------|
| m5.large | 2.73s → 2.53s (7.3%) | 2.53s → 2.56s (**-1.2%**) | Saturou em 5t |
| m5.xlarge | 2.63s → 1.48s (43.7%) | 1.48s → 1.49s (**-0.8%**) | Saturou em 5t |
| m5.2xlarge | 2.68s → 1.05s (60.7%) | 1.05s → 1.01s (3.8%) | Ganho mínimo |
| m5.4xlarge | 2.54s → 0.86s (66.1%) | 0.86s → 0.81s (5.8%) | Ganho mínimo |

> Instâncias com mais vCPUs se beneficiam mais de multi-threading (m5.4xlarge ganha 66% com 5 threads). Mas **todas saturam entre 5-10 threads**, confirmando a Lei de Amdahl no contexto de compressão de vídeo.

### 4. Comparação com Família T (Cross-Family)

| Métrica (H.264, melhor config) | T-family (t3.2xlarge@5t) | M-family (m5.4xlarge@10t) |
|--------------------------------|--------------------------|---------------------------|
| Tempo | 1.44s | **0.81s** |
| Eficiência | 7,542 | 5,766 |
| Custo | $0.000133 | $0.000173 |

> A **m5.4xlarge** é 44% mais rápida que a t3.2xlarge, mas 30% menos eficiente. Isso se deve ao custo 2.3× mais alto da família M vs T. Para workloads onde tempo absoluto importa, a família M é superior. Para eficiência de custo, a família T continua dominante.

---

## Dados Gerados

| Arquivo | Localização |
|---------|-------------|
| CSVs agregados | `artifacts2/experimental_data/aggregated_m5_*.csv` |
| Estatísticas descritivas (CSV) | `artifacts2/analysis_output/descriptive_statistics_m5.csv` |
| Estatísticas descritivas (MD) | `artifacts2/analysis_output/descriptive_statistics_m5.md` |
| Testes estatísticos | `artifacts2/analysis_output/statistical_tests_m5.csv` |
