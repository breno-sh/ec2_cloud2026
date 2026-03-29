# Resumo Executivo — EC2 Sweet Spot: Experimentos e Metodologia

Este documento descreve o passo a passo de cada experimento realizado no estudo EC2 Sweet Spot, incluindo os dados coletados até o momento para cada família de instâncias.

---

## Visão Geral

O estudo analisa a **custo-eficiência de instâncias AWS EC2** para compressão de vídeo, comparando diferentes famílias de instâncias, codecs e estratégias de escalonamento.

| Fase | Objetivo | Status |
|------|----------|--------|
| Fase 1 | Validação de homogeneidade de CPU | ✅ Concluída (T-family) |
| Fase 2 | Benchmarks de performance | ✅ T-family, ✅ M-family, ✅ C-family |
| Fase 3 | Horizontal vs. Vertical Scaling | ✅ Concluída (T-family) |

---

## Fase 1 — Validação de Homogeneidade de Processador

### O que é
Antes de fazer benchmarks, precisamos garantir que todas as instâncias de um mesmo tipo usam o **mesmo modelo de CPU**. Cloud providers como a AWS podem alocar CPUs diferentes para o mesmo tipo de instância, dependendo da zona de disponibilidade.

### Como funciona
1. Lançamos **100 instâncias** de cada tipo (t2.micro a t3.2xlarge)
2. Distribuímos pelas **6 zonas de disponibilidade** (us-east-1a até us-east-1f)
3. Em cada instância, executamos `cat /proc/cpuinfo` para extrair o modelo do processador
4. Analisamos a distribuição: qual % usa cada modelo de CPU?

### Resultados
- **Zona a:** 98% Intel Xeon 8259CL, 2% Intel Xeon 8175M
- **Zona f:** 74% Intel Xeon 8259CL, 26% Intel Xeon 8175M
- **Decisão:** Selecionamos a zona **a** e padronizamos na CPU dominante
- **Impacto:** Sem controle, variação de hardware causa até 15% de desvio na performance

---

## Fase 2 — Benchmarks de Performance

### O que é
Medição sistemática do **tempo de compressão de vídeo** em diferentes configurações de instância, codec e paralelismo.

### Como funciona
Para cada tipo de instância:

1. **Lançar** instância EC2 e verificar CPU esperada
2. **Instalar Docker** no host
3. Para cada **codec** (H.264, H.265, VP9):
   - Para cada **contagem de threads** (1, 3, 5, 10):
     - Gerar Dockerfile com FFmpeg configurado
     - Build + Run do container
     - Compressão é repetida **30 vezes** dentro do container
     - Tempo medido com resolução de milissegundos
     - Log baixado via SFTP
4. **Encerrar** instância

### Métricas
| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| Tempo de Compressão | Medido diretamente (s) | Quanto tempo leva para comprimir |
| Eficiência | `1 / (custo_hora/3600 × tempo)` | Performance normalizada pelo custo |
| Custo Total | `(custo_hora/3600) × tempo` | Custo monetário por operação |

### Status por Família

#### Família T (Burstable) — ✅ COMPLETA
- **Instâncias:** t2.micro, t3.micro, t3.small, t3.medium, t3.large, t3.xlarge, t3.2xlarge
- **Total:** 7 × 3 × 4 × 30 = 2.520 compressões
- **Destaque:** t3.micro com eficiência 20× maior que t3.2xlarge
- **Dados:** `artifacts/experimental_data/aggregated_t*.csv`

#### Família M (General Purpose) — ✅ COMPLETA
- **Instâncias:** m5.large, m5.xlarge, m5.2xlarge, m5.4xlarge
- **Total:** 4 × 3 × 4 × 30 = 1.440 compressões
- **Destaque:** m5.large com eficiência 2.5× maior que m5.4xlarge; m5.4xlarge 44% mais rápida que t3.2xlarge
- **Dados:** `artifacts2/experimental_data/aggregated_m5_*.csv`
- **Análise completa:** `artifacts2/analiseM.md`

#### Família C (Compute Optimized) — ✅ COMPLETA
- **Instâncias:** c5.large, c5.xlarge, c5.2xlarge, c5.4xlarge
- **Total:** 4 × 3 × 4 × 30 = 1.440 compressões
- **Destaque:** c5.4xlarge@10t a mais rápida de todas (0.76s H.264); c5.large 27% mais eficiente que m5.large
- **Dados:** `artifacts2/experimental_data/aggregated_c5_*.csv`
- **Análise completa:** `artifacts2/analiseC.md`

---

## Fase 3 — Horizontal vs. Vertical Scaling

### O que é
Comparação entre usar **muitas instâncias pequenas em paralelo** vs. **uma instância grande** para processar um vídeo de 10 minutos.

### Como funciona

| Abordagem | Configuração | Estratégia |
|-----------|-------------|------------|
| **Serial (baseline)** | 1× t3.micro | Processa o vídeo inteiro sequencialmente |
| **Horizontal** | 10× t3.micro | Divide em segmentos de 1min, processa em paralelo |
| **Vertical** | 1× t3.2xlarge | Instância poderosa processa o vídeo inteiro |

### Duas Subfases

**Fase 3.1 — Provisionamento Dinâmico:** Instâncias lançadas com Ubuntu padrão, Docker instalado na hora.

**Fase 3.2 — Provisionamento Otimizado:** Instâncias lançadas com AMI customizada (Docker pré-instalado).

### Resultados (H.264)

| Métrica | Serial | Horizontal | Vertical |
|---------|--------|------------|----------|
| **Fase 3.1 — Tempo Total** | 4.03 min | 3.28 min | 3.04 min |
| **Fase 3.1 — Custo** | $0.00070 | $0.00568 | $0.01687 |
| **Fase 3.2 — Tempo Total** | 2.80 min | **1.45 min** | 1.85 min |
| **Fase 3.2 — Custo** | $0.00048 | **$0.00251** | $0.01026 |

**Conclusão:** Com AMI otimizada, horizontal scaling:
- ⚡ **1.28× mais rápido** que vertical
- 💰 **75.5% mais barato** que vertical
- 📉 Overhead de setup caiu de 70% para 67% do tempo total

---

## Principais Conclusões

1. **Instâncias menores são mais custo-eficientes** — até 20× na família T, 2.7× na C, 2.5× na M
2. **Thread scaling satura em 5 threads** — ganhos marginais além disso (padrão em C, M e T)
3. **VP9 é insensível ao hardware** — speedup < 5% em todas as famílias (T, M, C)
4. **C5 é a melhor família para performance absoluta** — 7% mais rápida que M5, 47% que T3
5. **C5 é a mais eficiente entre as de performance fixa** — 27% melhor que M5 (clock mais alto + preço menor)
6. **Horizontal scaling supera vertical** — quando overhead de setup é minimizado
7. **AMI customizada é essencial** — reduz tempo de provisioning em 55%

### Comparação Cross-Family (H.264, melhor configuração)

| Família | Instância + Config | Tempo | Eficiência | Custo/op |
|---------|-------------------|-------|------------|----------|
| **C5** | c5.4xlarge @ 10t | **0.76s** | 6,984 | $0.000143 |
| **M5** | m5.4xlarge @ 10t | 0.81s | 5,766 | $0.000173 |
| **T3** | t3.2xlarge @ 5t | 1.44s | 7,542 | $0.000133 |

---

## Scripts e Dados

| Item | Localização |
|------|-------------|
| Script de benchmark | `artifacts2/phase2_benchmarks/all_instances_phase2_extended.py` |
| Parser de logs | `artifacts2/scripts/processing/parser_extended.py` |
| Gerador de estatísticas | `artifacts2/scripts/processing/generate_stats_extended.py` |
| Dados T-family | `artifacts/experimental_data/` |
| Dados M-family | `artifacts2/experimental_data/` |
| Guia de análises | `artifacts2/guia_analises.md` |
| Análise M-family | `artifacts2/analiseM.md` |
| Análise C-family | `artifacts2/analiseC.md` (placeholder) |
