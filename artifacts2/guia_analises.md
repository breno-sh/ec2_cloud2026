# Guia de Análises — EC2 Sweet Spot

Este documento descreve o passo a passo de cada análise realizada no artigo NOMS, servindo como guia para replicação com novas famílias de instâncias (C, M, etc.).

---

## Pipeline de Processamento

```
Logs brutos (.log)
    ↓  parser_extended.py
CSVs agregados (aggregated_*.csv)
    ↓  generate_stats_extended.py
Estatísticas descritivas + Testes estatísticos
    ↓  (geração de documentos)
analiseM.md / analiseC.md
```

---

## Fase 1 — Validação de Homogeneidade de Processador

**Objetivo:** Garantir que todas as instâncias de um mesmo tipo usam o mesmo modelo de CPU.

| Passo | Ação | Detalhe |
|-------|------|---------|
| 1.1 | Lançar 100 instâncias por tipo | Distribuídas pelas zonas de disponibilidade (a-f) |
| 1.2 | Extrair modelo da CPU | `cat /proc/cpuinfo \| grep 'model name'` |
| 1.3 | Analisar distribuição | Contar ocorrências de cada modelo por zona |
| 1.4 | Selecionar zona dominante | Escolher zona com maior homogeneidade |
| 1.5 | Definir CPU esperada | Para cada tipo de instância, definir o modelo dominante |

---

## Fase 2 — Benchmarks de Performance

**Objetivo:** Medir tempo de compressão, eficiência e custo para cada combinação (Instância × Codec × Threads).

### 2.1 — Execução dos Benchmarks

| Passo | Ação | Detalhe |
|-------|------|---------|
| 2.1.1 | Lançar instância EC2 | Uma por tipo, verificar CPU esperada |
| 2.1.2 | Instalar Docker | `apt-get install docker.io` |
| 2.1.3 | Gerar Dockerfile | Contém FFmpeg + script de compressão |
| 2.1.4 | Para cada codec × threads | Build e run do container Docker |
| 2.1.5 | Repetir 30x por configuração | `for i in $(seq 1 30)` no script |
| 2.1.6 | Baixar logs | Via SFTP para máquina local |

**Codecs:** H.264 (`libx264`), H.265 (`libx265`), VP9 (`libvpx-vp9`)  
**Threads:** 1, 3, 5, 10  
**Iterações:** 30 por configuração

### 2.2 — Processamento dos Dados

| Passo | Script | Entrada → Saída |
|-------|--------|-----------------|
| 2.2.1 | `parser_extended.py` | `*.log` → `aggregated_*.csv` |
| 2.2.2 | `generate_stats_extended.py` | `aggregated_*.csv` → tabela descritiva + testes |

### 2.3 — Tabela de Estatísticas Descritivas (Tabela III do artigo)

Para cada combinação (Instância, Codec, Threads), calcular:

| Métrica | Fórmula |
|---------|---------|
| **Mediana** | `median(tempos)` |
| **Desvio Padrão** | `std(tempos)` |
| **Mínimo** | `min(tempos)` |
| **Máximo** | `max(tempos)` |
| **Eficiência** | `1 / (custo_hora/3600 × tempo_mediana)` |
| **Custo Total** | `(custo_hora/3600) × tempo_mediana` |

### 2.4 — Testes Estatísticos

| Teste | Objetivo | Condição |
|-------|----------|----------|
| **Shapiro-Wilk** | Testar normalidade dos dados | p < 0.05 → dados não-normais |
| **Levene** | Testar igualdade de variâncias | p < 0.05 → variâncias desiguais |
| **Welch's t-test** | Comparar médias entre grupos | Usado quando dados são não-normais |

### 2.5 — Análises Qualitativas (Key Insights)

| Análise | Descrição |
|---------|-----------|
| **Custo-eficiência** | Comparar instância mais barata vs mais cara |
| **Thread scaling** | Retornos decrescentes ao aumentar threads |
| **Comportamento por codec** | H.264 vs H.265 vs VP9 — características diferentes |
| **Comparação geracional** | Ex: t2.micro vs t3.micro (performance vs custo) |

### 2.6 — Visualizações

| Gráfico | Descrição | Referência no artigo |
|---------|-----------|----------------------|
| **Bar Chart** (por codec) | Mediana do tempo de compressão por instância e threads | Figuras 3, 4, 5 |
| **Heatmap** (por codec) | Eficiência: threads (eixo Y) × tipo de instância (eixo X) | Figuras 7, 8, 9 |
| **Sunburst** | Eficiência normalizada hierárquica de todas as configurações | Figura 6 |
| **Boxplot** | Dispersão do tempo de compressão por configuração | Gráficos auxiliares |

---

## Fase 3 — Horizontal vs. Vertical Scaling

**Objetivo:** Comparar cluster paralelo (10× smallest) vs instância única (1× largest).

| Passo | Ação |
|-------|------|
| 3.1 | Fase 3.1 — Provisionamento dinâmico (Ubuntu padrão) |
| 3.2 | Fase 3.2 — Provisionamento otimizado (AMI customizada) |
| 3.3 | Medir tempo total, overhead de setup, tempo efetivo de encoding |
| 3.4 | Calcular custo total, custo por minuto de vídeo |
| 3.5 | Comparar melhoria de tempo e redução de custo entre fases |
