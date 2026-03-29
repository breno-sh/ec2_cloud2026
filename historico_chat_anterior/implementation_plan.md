# Phase 3: Horizontal vs Vertical Scaling — Plano de Execução

## Objetivo

Comparar **escalabilidade horizontal** (muitas instâncias pequenas) vs **vertical** (uma instância grande) para compressão de um vídeo de 10 minutos, para as famílias M e C.

---

## Metodologia do Artigo (como foi feito na família T)

### 3 Estratégias Comparadas

| # | Estratégia | Configuração T-family | O que faz |
|---|------------|----------------------|-----------|
| 1 | **Serial (baseline)** | 1× t3.micro | Processa o vídeo de 10 min inteiro sequencialmente |
| 2 | **Horizontal** | 10× t3.micro | Divide em 10 segmentos de 1 min, processa em paralelo |
| 3 | **Vertical** | 1× t3.2xlarge | Instância poderosa processa o vídeo inteiro |

### 2 Sub-fases

| Sub-fase | Provisioning | AMI | Docker |
|----------|-------------|-----|--------|
| **3.1 — Dinâmico** | Ubuntu padrão + `apt-get install docker.io` | `ami-0a313d6098716f372` | Sim |
| **3.2 — Otimizado** | AMI customizada com FFmpeg pré-instalado | `ami-0300cfb089403fb0b` | Não (ffmpeg direto) |

> [!IMPORTANT]
> No artigo o cluster horizontal usa a **instância mais eficiente** (menor, mais barata) e a vertical usa a **instância mais poderosa** (maior). O ponto é provar que muitas instâncias baratas superam uma instância cara.

---

## Configuração para M e C Families

### Família M

| Estratégia | Instância | Qtd | Threads | CPU Esperada |
|------------|-----------|-----|---------|--------------|
| Serial (baseline) | m5.large | 1 | 5 | Intel Xeon Platinum 8259CL @ 2.50GHz |
| Horizontal | m5.large | 10 | 5 | Intel Xeon Platinum 8259CL @ 2.50GHz |
| Vertical | m5.4xlarge | 1 | 10 | Intel Xeon Platinum 8259CL @ 2.50GHz |

> [!NOTE]
> m5.large foi a mais eficiente da família M nos benchmarks Phase 2.
> m5.4xlarge é a mais rápida (0.81s H.264).

### Família C

| Estratégia | Instância | Qtd | Threads | CPU Esperada |
|------------|-----------|-----|---------|--------------|
| Serial (baseline) | c5.large | 1 | 5 | Intel Xeon Platinum 8275CL @ 3.00GHz |
| Horizontal | c5.large | 10 | 5 | Intel Xeon Platinum 8275CL @ 3.00GHz |
| Vertical | c5.4xlarge | 1 | 10 | Intel Xeon Platinum 8275CL @ 3.00GHz |

> [!NOTE]
> c5.large foi a mais eficiente da família C nos benchmarks Phase 2.
> c5.4xlarge é a mais rápida (0.76s H.264).

---

## Apenas Sub-fase 3.2 (AMI Otimizada)

> [!IMPORTANT]
> **Proposta de simplificação:** No artigo, a Sub-fase 3.1 (dinâmica) serviu para demonstrar o impacto do overhead de provisioning. Como já provamos esse ponto com a família T, **sugiro rodar apenas a Sub-fase 3.2** (AMI otimizada) para M e C. Isso economiza tempo e custo AWS.
>
> Se quiser, podemos rodar ambas sub-fases. **O que prefere?**

---

## Scripts Necessários

### Status Atual

| Script | Descrição | Status |
|--------|-----------|--------|
| `parallel_scaling_phase2.py` | Horizontal scaling (10× instâncias) | ✅ Existe, parameterizado |
| Script serial (1× menor) | Serial baseline | ❌ **Precisa ser criado** |
| Script vertical (1× maior) | Vertical scaling | ❌ **Precisa ser criado** |

Os scripts serial e vertical são simples: uma única instância processando o vídeo inteiro (serial usa a menor, vertical usa a maior). Vou criar versões parametrizadas como o `parallel_scaling_phase2.py`.

---

## Passo a Passo de Execução

### Família M (primeiro)

```
# Passo 1: Serial — 1× m5.large processando vídeo de 10 min inteiro
python3 serial_scaling_phase2.py --instance-type m5.large \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz" --threads 5

# Passo 2: Horizontal — 10× m5.large, cada uma processando 1 min
python3 parallel_scaling_phase2.py --instance-type m5.large \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz" --threads 5

# Passo 3: Vertical — 1× m5.4xlarge processando vídeo de 10 min inteiro
python3 serial_scaling_phase2.py --instance-type m5.4xlarge \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz" --threads 10
```

### Família C (depois)

```
# Passo 4: Serial — 1× c5.large
python3 serial_scaling_phase2.py --instance-type c5.large \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8275CL CPU @ 3.00GHz" --threads 5

# Passo 5: Horizontal — 10× c5.large
python3 parallel_scaling_phase2.py --instance-type c5.large \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8275CL CPU @ 3.00GHz" --threads 5

# Passo 6: Vertical — 1× c5.4xlarge
python3 serial_scaling_phase2.py --instance-type c5.4xlarge \
    --expected-cpu "Intel(R) Xeon(R) Platinum 8275CL CPU @ 3.00GHz" --threads 10
```

---

## Métricas Coletadas

Cada execução mede (via timestamps nos logs):

| Métrica | Como é calculada |
|---------|-----------------|
| **Tempo Total** | Timestamp final − timestamp inicial |
| **Setup Overhead** | Tempo até instância estar pronta + upload do vídeo |
| **Tempo Efetivo de Encoding** | Tempo de compressão real do FFmpeg |
| **Custo Total** | (tempo_total / 3600) × custo_hora × num_instâncias |
| **Custo por Minuto de Vídeo** | custo_total / 10 |

---

## Resultado Esperado

Tabela comparativa idêntica à Table 4 do artigo, para cada família:

| Métrica | Serial (1× *.large) | Horizontal (10× *.large) | Vertical (1× *.4xlarge) |
|---------|---------------------|--------------------------|-------------------------|
| Tempo Total (min) | ? | ? | ? |
| Setup Overhead (min) | ? | ? | ? |
| Tempo Encoding (min) | ? | ? | ? |
| Custo Total ($) | ? | ? | ? |
| Custo/min vídeo ($) | ? | ? | ? |

---

## Questões para Validação

1. **Rodar ambas sub-fases (3.1 + 3.2) ou apenas a 3.2 (AMI otimizada)?**
2. **Codec:** Apenas H.264 (como no artigo) ou incluir H.265/VP9?
3. **vCPU limit:** A horizontal scaling roda 10 instâncias simultâneas. m5.large = 2 vCPUs × 10 = 20 vCPUs. Seu limite está em quantos?
4. **Vídeo de 10 minutos:** O arquivo `video_10_minutos.mp4` já existe no diretório?
