# Plano de Melhorias — The Cloud EC2 Sweet Spot

Gerado em: 2026-03-25
Status: Em construção — discutindo ponto a ponto

---

## [C1 + C2] Chunk sensitivity multi-resolução + comparação com managed services — CRÍTICO
*(experimento bundled — rodar junto)*

**Problemas que resolve:**
- C1: Recomendação de 60s baseada em único vídeo 320×240. Não generaliza para workloads VaaS reais.
- C2: Paper recomenda orquestração custom mas nunca confronta os baselines de mercado (Fargate, MediaConvert).

**Hipótese central (C1):**
O ótimo de chunk depende da relação entre t_enc e t_prov:
- 240p: t_enc(60s) ≈ 5s << t_prov ≈ 48s → provisioning domina → 60s ótimo
- 720p: t_enc(60s) ≈ 44–50s ≈ t_prov → crossover → ótimo pode mudar
- 1080p: t_enc(60s) >> t_prov → encoding domina → chunks maiores devem ser melhores

**Espectro de abordagens (C2):**
```
Mais controle / Mais barato          Menos controle / Mais caro
EC2 custom (paper) → Fargate → MediaConvert
   $0.002/run        $0.008/run    $0.075/run
   48s overhead       ~20s          ~0s
```

**Design do experimento:**

| Eixo | Valores |
|------|---------|
| Resolução | 320×240 (já feito), 720p, 1080p |
| Chunk sizes | {30, 60, 120}s |
| Abordagens EC2 | m5.large horizontal (n=10), m5.4xlarge vertical (n=10), m5.large serial (n=10) |
| Abordagem Fargate | 1 vCPU / 2GB, chunk ótimo c=60s (n=5) |
| Abordagem MediaConvert | Basic tier ≤30fps, n=3 (custo fixo — billing determinístico) |

**Vídeo:** Big Buck Bunny, mesmo conteúdo em 3 resoluções
- 240p: já disponível localmente
- 720p + 1080p: https://download.blender.org/peach/bigbuckbunny_movies/ (CC-BY 3.0)

**Setup necessário:**
- S3 bucket (input/output para MediaConvert e Fargate)
- IAM role para MediaConvert acessar S3
- Docker image com FFmpeg → push para ECR (para Fargate)
- ECS task definition + cluster (para Fargate)
- Phase 3.2 AMI já existente (para EC2)

**Importante — re-rodar 240p via S3:**
Os dados existentes de 240p usaram SFTP da máquina local; os novos experimentos usarão S3.
Comparar direto seria misturar metodologias. O 240p precisa ser re-rodado via S3 com os
5 pontos de chunk para ficar na mesma base metodológica que 720p e 1080p.
Os dados antigos ficam como referência histórica mas não entram na nova tabela comparativa.

**Custo estimado — sessão única bundled (C1 + C2 + I2 + M2):**

| Item | Custo |
|------|-------|
| EC2 chunk sensitivity — 5 chunks × 3 resoluções (n=10) | $5.16 |
| Fargate — c=60s × 3 resoluções (n=5) | $0.20 |
| MediaConvert — 3 resoluções × n=3 | $0.67 |
| ARM provisionamento variability — 100× m7g + 100× m5 (I2) | $0.70 |
| ARM 6 runs faltando — m7g H.264 horizontal (I2) | $0.02 |
| Setup S3 / ECR / IAM / misc | $0.50 |
| **TOTAL estimado** | **~$7.25** |
| **Com margem de segurança (2×)** | **~$14.50** |

*Nota: encoding times para 720p/1080p são estimativas escaladas do 240p medido. Variam ±50%.*

**Ganho no paper:**
- Tabela de chunk sensitivity por resolução mostrando deslocamento do ótimo
- Validação empírica do modelo T(c)
- Espectro EC2 → Fargate → MediaConvert posicionando o paper no nicho correto
- Transforma C1 de fraqueza em contribuição

**Erro factual a corrigir independentemente (custo zero):**
O paper afirma "720p" em dois lugares (Metodologia e Threats to Validity).
O vídeo real é 320×240. Corrigir no tex antes de submeter, independente de rodar experimentos.

---

## [I2] ARM com amostragem inconsistente + caracterização de variabilidade de provisionamento

**Três problemas originais:**

1. **m7g.large H.264 horizontal: n=24** — sessão interrompida, 6 runs excluídos. Footnote
   embaraçoso na tabela que um revisor vai atacar: "por que não completou os 6 runs?"
2. **H.265 serial m7g.large: n=26 / c7g.large: n=29** — artefato de log (runs misatribuídos
   entre codecs na consolidação). Os runs existem mas foram contados na coluna errada.
3. **CV > 50% no H.265 horizontal sem hipótese explicativa** — declarado no paper mas não
   justificado empiricamente.

**Solução para cada problema:**

| Problema | Solução | Custo |
|---|---|---|
| n=24 H.264 horizontal | Rodar 6 runs adicionais com m7g.large | ~$0.02 |
| n=26/29 H.265 serial | Bootstrap CI nos dados existentes (n suficiente) | $0 |
| CV > 50% sem explicação | Experimento de caracterização de provisionamento (ver abaixo) | ~$0.70 |

---

**Experimento de caracterização de variabilidade de provisionamento (novo — análogo ao Phase 1)**

*Motivação:* O CV > 50% no H.265 horizontal (m7g.large, c7g.large) sugere que a barreira
de sincronização do cluster (espera pelo nó mais lento) está sendo dominada por variabilidade
de provisioning, não pelo encoder. O H.265 horizontal mostra mediana 59s mas max 225s —
exatamente o padrão de long-tail de provisionamento, não de encoding.

*Design:*
- Lançar 100 instâncias m7g.large uma a uma com a Phase 3.2 AMI (pré-construída)
- Marcar t_start = chamada boto3 / t_ready = SSH respondendo
- Repetir com 100 instâncias m5.large (controle x86 — mesma AMI)
- Calcular: mediana, std, CV, min, max, p95 para cada arquitetura
- Comparar as duas distribuições

*Resultado esperado:* CV de provisionamento Graviton >> x86, confirmando que
provisioning long-tail — e não variabilidade do encoder — é o culpado.

*Texto a adicionar no paper:*
> "To investigate the source of CV > 50% in Graviton horizontal clusters, we conducted
> a dedicated provisioning latency characterization (n=100 per architecture). Graviton 3
> provisioning time exhibited [X]× higher CV than x86 (CV: [Y]% vs [Z]%), confirming
> that provisioning long-tail variance — not encoder non-determinism — is the dominant
> source of execution time variability in ARM horizontal deployments."

*Custo:*
- 100 × m7g.large × ~2 min: ~$0.34
- 100 × m5.large × ~2 min (controle): ~$0.32
- **Total: ~$0.70**

*Observação:* Esse resultado também tem valor para C1+C2 — explica por que Fargate
com containers ARM pode exibir o mesmo comportamento de variabilidade.

---

**Bundling com C1+C2:** Rodar tudo na mesma sessão AWS:
- Setup de infraestrutura (S3, ECR, IAM) já necessário para C1+C2 serve para I2 também
- Os 6 runs faltantes do H.264 horizontal podem ser rodados junto

---

## [I3] Rebalancear hierarquia cross-family vs intra-família — custo zero

**O problema:**
O headline do paper é a comparação cross-family (10× t3.micro vs m5.4xlarge → 89,4% de
redução de custo). Mas essa comparação mistura famílias com billing models diferentes
(créditos de CPU, SLAs distintos), o que a torna metodologicamente mais fraca.

A comparação intra-família (10× m5.large vs m5.4xlarge → 1,28× speedup, mesma família,
mesmo billing model) é mais sólida, mas atualmente aparece como nota de rodapé.

**A tensão:**
- Cross-family: 89,4% de redução de custo — headline impactante, mas billing diferente
- Intra-família: 1,28× de speedup sem aumento de custo — menos dramático, mas inexpugnável

Trocar o headline enfraquece o impacto. Manter só o cross-family expõe a metodologia.

**Solução: rebalancear, não trocar**

1. Manter cross-family como resultado de alto impacto — mas qualificado explicitamente:
   workload episódico dentro da janela de burst, créditos não se acumulam.
2. Elevar intra-família de "nota" para "validação estrutural": o mesmo padrão se repete
   sem depender de créditos de CPU, confirmando que o resultado é arquitetural.
3. Conclusão reframeada: "horizontal scaling vence vertical independentemente da família —
   o resultado mais conservador (intra-família) ainda mostra 1,28× sem aumento de custo."

**Onde mudar no tex:**
- Seção Phase 3 Results: adicionar parágrafo explicitando a hierarquia de evidências
- Discussion: qualificar o cross-family com o pressuposto de burst window
- Abstract e Conclusion: mencionar intra-família antes de cross-family como "validação"

**Custo:** $0 — só reescrita de texto, sem experimentos novos.

---

## [M2] Curva T(c) com apenas 3 pontos — bundlado com C1+C2

**O problema:**
A análise de chunk sensitivity usa só c ∈ {30, 60, 120}s. Com 3 pontos não dá para
caracterizar a curvatura de T(c) com confiança — o "ótimo de 60s" pode ser acidente
de amostragem. Um revisor pode pedir mais pontos.

**Solução: bundlar com C1+C2, rodar 5 pontos nas 3 resoluções**

c ∈ {30, 45, 60, 90, 120}s em 240p, 720p e 1080p — a curva fica bem caracterizada
empiricamente e permite ajustar um modelo paramétrico mostrando o mínimo analítico.

**Nota importante sobre o 240p:**
Os dados existentes de chunk sensitivity (240p, c={30,60,120}s) usaram SFTP da máquina
local. Os novos experimentos usarão S3. Comparar direto seria misturar metodologias.
O 240p precisa ser **re-rodado via S3** com os 5 pontos de chunk para ficar na mesma
base metodológica que 720p e 1080p. Dados antigos ficam como referência histórica.

**Custo:** ~$0,89 para o 240p re-rodado + incremento marginal nos 5 pontos das outras
resoluções — já embutido no custo total da sessão bundled.

---

## [M1] Modelo de egress pressupõe entrega direta — custo zero

**O problema:**
O paper calcula egress a $0,09/GB (saída direta EC2 → internet, us-east-1) e conclui que
"once compute is optimized, egress becomes the dominant cost driver."

Pipelines VaaS reais usam S3 + CloudFront CDN:
- EC2 → S3 (intra-região): grátis
- S3 → CloudFront: grátis
- CloudFront → usuário: $0,0085/GB (vs $0,09/GB direto)

Para 100 MB de output H.264:
- Direto: $0,009 → 4× o compute ($0,00211) → **egress domina**
- Via CDN: $0,00085 → 0,4× o compute → **compute ainda domina**

A conclusão do paper se inverte para o cenário CDN.

**Como tratar:**
Não é fraqueza — é oportunidade de cobrir dois cenários:
> "Under direct internet egress, data transfer costs 4× the optimized compute cost, making
> egress the binding constraint. Operators using S3-to-CloudFront delivery reduce egress
> ~10×, restoring compute as the dominant cost driver and amplifying the value of the
> provisioning optimizations described in this work."

Posiciona o paper como guia de decisão para ambos os cenários e reforça a importância
de otimizar compute independentemente da arquitetura de entrega.

**Onde mudar:** seção de egress cost + nota na Discussion. ~1 parágrafo.
**Custo:** $0.

---

## [I1] Conflação de SFTP no wall-clock — LIMITAÇÃO QUE SUBESTIMA O ACHADO

**Contexto completo (auditado nos scripts em 2026-03-25):**

Phase 1/2 — método de transferência:
- O vídeo é baixado DENTRO do Docker container via `wget` direto da internet (sample-videos.com
  ou blender.org). O SFTP só é usado para baixar logs de volta para a máquina local.
- **Phase 1/2 não tem nenhum upload de vídeo da máquina local. Dados completamente limpos.**
- Scripts relevantes: `EC2SWEETSPOT/manus/script_threads_todos.py`,
  `ec2sweetspot_noms/artifacts2/phase2_benchmarks/all_instances_phase2_extended.py`

Phase 3 — método de transferência:
- Vídeo dividido em chunks LOCALMENTE com ffmpeg
- Cada chunk enviado via `sftp.put()` para cada instância EC2 em paralelo
- Resultado comprimido baixado via `sftp.get()` de cada instância
- Com 10 instâncias paralelas: 10 uploads simultâneos da máquina local = banda local saturada
- Scripts relevantes: `artifacts2/phase3_scaling/*_horizontal*.py`

**A consequência crítica — por que isso é boa notícia:**

O gargalo de banda local prejudicou o resultado horizontal, não o vertical:
- Vertical: 1 upload do vídeo completo (150 MB) → sequencial, usa a banda bem
- Horizontal: 10 uploads simultâneos de chunks (10 × 15 MB) → contendo banda, ficou artificialmente mais lento

E mesmo assim o horizontal foi mais rápido que o vertical no Phase 3.2.

**Conclusão: a limitação subestima a vantagem do horizontal.** Com S3 como intermediário
(transferência intra-região a ~10 Gbps, sem depender da banda local), o horizontal seria
ainda mais rápido do que o medido. O achado central do paper é conservador — mais robusto
do que aparenta.

**O que fazer no paper:** Declarar como limitação na Discussion, com o framing correto:
"Transfer overhead was conducted via SFTP from the orchestrating host, subject to local
bandwidth constraints. This systematically penalizes horizontal configurations (10 concurrent
transfers) relative to vertical (1 transfer), suggesting the reported speedup advantages
are conservative lower bounds. Future work should use S3-mediated transfer to isolate
encoding performance from network topology."

**O que fazer nos novos experimentos (C1+C2):** Usar S3 como intermediário — instâncias
baixam o chunk do S3 diretamente (intra-região), encoda, e sobem o resultado de volta ao S3.
Isso já é necessário para Fargate e MediaConvert de qualquer forma, então o setup é o mesmo.
Custo adicional: negligível (S3 intra-região não cobra por transfer).
