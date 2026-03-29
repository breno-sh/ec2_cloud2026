# Plano de Correções — "The EC2 Sweet Spot" (cloud2026)

Status: [ ] pendente | [x] concluído | [-] descartado/não aplicável

---

## PRIORIDADE 1 — CRÍTICOS (bloqueantes para aceitação)

| # | Issue | Localização | Status | Notas |
|---|-------|-------------|--------|-------|
| C1 | **1.1** Abstract mistura dois experimentos distintos (speedup 1.28× é M-family intra, custo 89.4% é cross-family t3 vs m5) | Abstract | [x] | Adicionado "cross-family comparison" + "wall-clock speedup"; comentário LaTeX corrigido para atribuir 1.28× ao t3.micro vs m5.4xlarge |
| C2 | **2.1** Welch's t-test aplicado a dados não-normais (ARM Graviton CV>50%) | §III Metodologia | [x] | §III: adicionado critério de quando Welch's é retido; §IV.B.iii: justificativa CLT via CV<0.6%; §IV.C.iii: nota que p<10⁻²³ torna a escolha do teste irrelevante para a conclusão; ARM Graviton apontado para §V |
| C3 | **2.2** Cohen's d inválido para dados não-normais (d=8.77 M-family) | §III Metodologia | [x] | Phase 2: nota que CV<0.6% satisfaz normalidade prática → Cohen's d apropriado; Phase 3 x86: d>3 implica separação distribucional completa → Cliff's delta assintotaria ±1, tornando a escolha irrelevante; ARM Graviton já encaminhado para §V |
| C4 | **3.3** Comparação cross-codec ARM H.265 vs x86 H.264 é cientificamente inválida | §IV.D ARM Graviton | [x] | Removida comparação cross-codec; adicionada comparação within-ARM (serial vs horizontal H.265); nota explícita de que cross-codec é inválido; conclusão corrigida; dados verificados: m7g hor H.265 n=30 median=59.27s ✓, H.264 hor n=24 (design intencional) median=108.07s ✓ |
| C5 | **5.3** Tabela 1 (tab:comparative_analysis) nunca referenciada com \ref no texto | §II Related Works | [x] | Já presente na linha 214: "Table~\ref{tab:comparative_analysis} summarizes the positioning..." — sem alteração necessária |
| C6 | **8.1** Data de coleta dos preços AWS nunca declarada | §III Metodologia | [x] | Tabela tab:experimental_configurations expandida: adicionada coluna sa-east-1, ARM instances (m7g/c7g), e caption com "retrieved March 2026 via AWS Pricing API". Preços verificados via `aws pricing get-products` e conferem com paper (exceto c7g: paper usava $0.0724 vs API $0.0725 — negligível). |

---

## PRIORIDADE 2 — MAJOR (devem ser corrigidos)

| # | Issue | Localização | Status | Notas |
|---|-------|-------------|--------|-------|
| M1  | **1.2** "up to 93.3%" sem qualificar que é T-family parallel | Abstract, Conclusão | [x] | Adicionado "(T-family horizontal, Phase~3.1)" no Abstract e na Conclusão; também trocado "non-negligible" por "dominant" (resolve m11 junto) |
| M2  | **1.3** Falta qualificador "cross-family" nas reduções 89.4% e 87.5% | §IV.C.ii + Abstract | [x] | Abstract já ok (C1); §IV.C.ii já tem "For cross-family comparisons" cobrindo ambos; Conclusão: adicionado "in a cross-family comparison" junto ao 89.4% |
| M3  | **1.4** Economia M-family within-family (2.3%) apresentada junto com 89.4% sem ressalva | §IV.C.ii | [x] | Adicionada ressalva explícita: "These within-family savings are marginal in absolute terms---the primary economic advantage...lies in the performance gain rather than cost reduction"; cross-family introduzido com "the contrast is far more pronounced" |
| M4  | **1.5** "within-family" para T-family (t3.micro vs t3.2xlarge) é cross-size, não within | §IV.C.iii | [x] | Substituído "T-family, within-family comparison" por "T-family cross-size comparison (10× t3.micro vs 1× t3.2xlarge, Phase 3.2)"; adicionada ressalva de que o resultado reflete size disparity (micro→2xlarge) além do benefício arquitetural |
| M5  | **1.7** Header "Median (s)" da Table 4 é ambíguo (per-segment vs total?) | tab:regional_cost | [x] | Header renomeado para "Median†(s)"; footnote adicionada: "End-to-end wall-clock time per cluster run (segmentation + provisioning + encoding + retrieval); not per-chunk." Verificado: t3.micro 73.20s = 1.22 min ✓ |
| M6  | **1.8** Conversão MB→GB errada no custo de egress ($0.0135 vs $0.0129) | §IV Phase 4 egress | [x] | Verificado: $0.0135 está CORRETO (150 MB ÷ 1000 × $0.09/GB = $0.0135, AWS usa GB decimal). O $0.0129 do plano era baseado em conversão binária incorreta. Adicionada nota explícita no texto com o cálculo completo para eliminar ambiguidade. |
| M7  | **1.10** 5-node 120s chunk mostra 2.04 min mas aritmética dá ~1.44 min; gap não explicado | §IV Phase 4 | [x] | Investigado nos logs (artifacts3/m1/logs/chunk_sensitivity_t3_120s.log): encoding=43s (vs 22s com créditos cheios) + SFTP=30s para chunks 2× maiores. Gap explicado: depleção de CPU credits + SFTP scaling. Explicação adicionada ao texto com breakdown concreto. |
| M8  | **2.3** Efficiency = 1/Total_Cost (são redundantes); paper nunca reconhece isso | §IV.B.i, Table 2 | [x] | Adicionado reconhecimento explícito: "These metrics are mathematically dual...They therefore encode the same information and will always produce identical instance rankings." Justificativa: Total_Cost = valor absoluto em USD; Efficiency = score relativo dimensionless para comparação visual. |
| M9  | **2.4** Distribuição bimodal ARM H.265 (min=328s vs median=700s) não investigada | §IV.D + Table 5 | [x] | Investigado nos logs raw: min=328.92s é artefato de parsing (VP9 run ~329s misatribuído ao H.265 por log interleaved + busca de codec por posição no arquivo). True H.265: n=26, unimodal, 699–718s. Explicação completa adicionada ao texto. c7g.large H.265 tem problema similar (stdev=190). |
| M10 | **2.5** Protocolo de hardware pinning não descrito mecanisticamente | §III Phase 1 | [x] | Investigado: TODOS os scripts apenas logam WARNING no mismatch, execution continua. phase3_unified.py tem expected_cpu como metadata mas SEM runtime check. §III corrigido: removed overclaim de "terminated and replaced"; adicionado: WARNING-only logging, high base-rate mitigation, contamination quantification (0.6/30 T-family, até 12/30 M/C-family). §IV.B.iii corrigido: removed "immediately terminated and replaced" → "flagged with WARNING, execution continued". Dupla verificação: grep confirmou zero RuntimeError em todos os scripts de experimento. VALIDAÇÃO EMPÍRICA (Março 2026): rerun CPU-verificado completo (terminate+retry, n=30×8 configs) em n30_rerun_logs/. Encoding times idênticos ao original (m5.large: 115s, m5.4xlarge: 42s, c5.4xlarge: 37s). Conclusão: contaminação de CPU não afetou resultados — dados originais do paper são válidos. |
| M11 | **2.6** Overhead SFTP atribuído sem medição direta | §IV.C.ii | [x] | Qualificado como hipótese: "hypothesized to scale with chunk size, plausibly adding ≈30s... cannot be established without direct per-phase measurement" |
| M12 | **2.7** "Analytical chunk optimization model" não deriva ótimo analítico — é análise empírica | §IV Phase 4 | [x] | Renomeado: §III "Phase 4: Chunk Size Sensitivity and Cost Analysis"; §IV "Empirical Chunk Size Sensitivity:"; conclusão atualizada |
| M13 | **2.8** VP9 "near-constant across instance types" é falso (24.7% de range); vale só para threads | §IV.B.ii | [x] | Texto já correto: "within a given instance type" + nota explícita do range 24.7% across types — sem alteração necessária |
| M14 | **3.1** RQ4 respondida só parcialmente (break-even egress vs CDN nunca calculado) | §I Intro + §IV.D | [x] | CDN break-even adicionado: CloudFront $0.00128 < compute $0.00211 → CDN justificado para qualquer repeat delivery |
| M15 | **3.2** Causalidade "provisioning eclipses speedup" para ARM H.264 não demonstrada com dados | §IV.D ARM | [x] | Breakdown quantitativo adicionado: 48s provisioning vs 6s encoding = 8× ratio; qualificado como "consistent with" + nota que direct instrumentation necessária |
| M16 | **3.4** "Strong performance" ARM H.265 contradiz CV>50% relatado logo antes | Conclusão | [x] | §IV.D: "significant domain-specific advantage" → "codec-specific parallel encoding advantages... though this advantage coexists with high operational variance (CV>50%), as detailed below" |
| M17 | **3.6** Figure 1 usa mean±CI mas Table 2 usa median; inconsistência | §IV.B.iii + Fig.1 | [x] | §IV.B.iii: corrigido "median compression time" → "mean compression time with 95% CI"; justificativa explícita para escolha de cada métrica |
| M18 | **4.3** "confirms" para recomendação não testada (ARM custom binaries) | §IV.D | [x] | Já estava correto: texto já usava "suggest" + "hypothesis warranting direct empirical validation" — sem alteração necessária |
| M19 | **4.8** "as rigidly as CPU architecture" é comparação não quantificada | §IV.D | [x] | Substituído por "primary determinant of horizontal scaling viability: the provisioning-to-encoding ratio of 8× quantified above renders the scaling strategy inviable regardless of the underlying CPU architecture" |
| M20 | **5.1** Phase 4 metodologia insuficiente; Eq.4 definida só em Results | §III Phase 4 | [x] | §III Phase 4: expandido com definições completas de T(c), todos os parâmetros (t_seg, t_prov, t_enc, t_merge, R_inst, R_egress, D_out), chunk sizes testados |
| M21 | **5.2** ARM Graviton e sa-east-1 não têm subsecção correspondente em §III | §III / §IV.D | [x] | Nova subsecção "Phase 3 Extended Evaluation: ARM Graviton and Regional Pricing" adicionada em §III |
| M22 | **6.1** Citação AWS sem data de acesso | Bibliography b_awscredits | [x] | Adicionado "[Accessed: Mar. 2026]" ao bibitem{awscredits} |
| M23 | **6.2** Nenhuma citação sobre ARM Graviton 3 ou NEON SIMD em codecs | §II + §IV.D | [x] | Adicionados: bibitem{awsgrav3} (AWS Graviton3), bibitem{neonvideo} (x265 docs); citados em §IV.B.iii e §IV.D |
| M24 | **6.5** b19 é dissertação não publicada, potencialmente auto-citação em blinded review | Bibliography | [x] | b19 substituído por Ben-Yehuda et al. (2013) "Deconstructing Amazon EC2 Spot Instance Pricing", ACM TEAC, doi:10.1145/2509413.2509416 |
| M25 | **6.6** Docker container overhead não citado; não está claro se incluso no setup overhead | §III + Appendix | [x] | Adicionado bibitem{dockercoldstart} (Felter et al. ISPASS 2015); §III esclarece que container image pré-instalada no AMI (<1s overhead); §V Threats explicita distinção entre AMI overhead e Docker pull |
| M26 | **7.1** Appendix diz 19 instance types mas paper usa 17 (15 x86 + 2 ARM) | Appendix | [x] | Corrigido para 16 (14 x86 = 6T+4M+4C, + 2 ARM m7g+c7g) com breakdown explícito |
| M27 | **7.2** Appendix diz "2.800 executions" mas design implica 5.400 (15×4×3×30) | Appendix | [x] | Corrigido para "over 5,700" com breakdown por fase: Ph2=5040, Ph3=540, ARM=240, Ph4=270, sa-east-1=90 |
| M28 | **7.3** AMI IDs são region-specific; sa-east-1 não tem AMI; risco de des-anonimização | Appendix | [x] | AMI IDs atualizados com nota region-specific; sa-east-1 instruído a usar AMI equivalente via AWS catalog; custom AMI documentada como necessitando rebuild para outras regiões |
| M29 | **7.4** Experimentos ARM e sa-east-1 ausentes da documentação do Appendix | Appendix | [x] | Adicionada subsecção "Extended Evaluations" no Appendix com ARM (phase3_scaling/arm_graviton/) e sa-east-1 (phase3_scaling/sa_east_1/) |
| M30 | **8.2** T-family burst credit surcharge não validado empiricamente ($0.0167 possível vs $0.00211) | §V Threats | [x] | §V Internal Validity: cálculo teórico upper-bound ($0.0061 para 10 instâncias), reconhecido que billing statements não foram auditados → ameaça de validade explícita |
| M31 | **8.3** Generalização de chunk size para outros comprimentos/tipos de vídeo não discutida | §V Threats | [x] | §V External Validity: parágrafo "Workload Representativeness and Chunk Size Generalizability" adicionado |
| M32 | **8.4** Condições de rede (AZ placement, bandwidth SFTP) não caracterizadas | §V Threats | [x] | §V External Validity: parágrafo "Network Conditions and Transfer Overhead" adicionado |
| M33 | **8.5** Homogeneidade ARM válida só para regiões testadas | §V Threats | [x] | §V External Validity: parágrafo "ARM Graviton Homogeneity Scope" adicionado — validado só em us-east-1 |
| M34 | **9.1** b19 pode des-anonimizar autores (UFPE + tópico relacionado) | Bibliography | [x] | Resolvido junto com M24 — b19 substituído |
| M35 | **9.2** Tempo de encoding Phase 2 (30s) escalado para Phase 3 (600s) é inconsistente com Table 3 | §IV.C / §IV.B | [x] | §IV.C: parágrafo explicando que Phase 2 mede raw encoding (2.5s/30s) enquanto Phase 3 mede end-to-end pipeline (73s); encoding portion ~6s é consistente com Phase 2 scaled |

---

## PRIORIDADE 3 — MINOR (melhorias de qualidade)

| # | Issue | Localização | Status | Notas |
|---|-------|-------------|--------|-------|
| m1  | **1.6** Rounding discrepancy: c5.4xlarge efficiency 4,662 vs 4,663 | Table 2 | [x] | Tabela e texto já consistentes (4,662 em ambos); discrepância era do reviewer vs paper, não interna |
| m2  | **1.9** Cross-family comparison requer justificativa de comparabilidade (burstable vs sustained) | §IV.C.ii | [x] | §IV.C.ii: parágrafo adicionado justificando comparabilidade — dentro do burst window (60s chunk), t3.micro entrega 100% vCPU comparável a non-burstable |
| m3  | **3.5** n=30 não justificado por análise de poder estatístico | §II Related Works | [x] | §III: adicionada justificativa: CV<0.6% → power analysis requer <10 observações para 5% effect; n=30 excede este threshold |
| m4  | **3.7** Experimento VP9 usa defaults; não deixa claro que tiling está fora do escopo | §IV.B.ii | [x] | §IV.B.ii: "spatial tiling (which is outside the scope of this study and was not configured in any experiment)" + "under default libvpx-vp9 settings" |
| m5  | **4.1** RQs em run-on sentence; difícil de parsear | §I Intro | [x] | RQs reformatadas como lista numerada com bold labels (RQ1-RQ4) |
| m6  | **4.2** "Intriguingly", "most striking anomaly" — linguagem editorial inadequada | §IV.D | [x] | Não encontrado no texto atual — já removido em edição anterior |
| m7  | **4.4** Em-dash parenthetical quebra fluxo de leitura | §IV.D | [-] | Não identificado especificamente; múltiplos em-dashes no texto são necessários para a estrutura — item descartado |
| m8  | **4.5** "orchestrational" não é palavra; deve ser "orchestration" | §IV.D | [x] | Corrigido: "orchestrational overhead" → "orchestration overhead" |
| m9  | **4.6** "strangles" — verbo coloquial inadequado para IEEE | §IV.E | [x] | Corrigido: "strangles" → "may severely limit" |
| m10 | **4.7** "alter" muito vago; substituir por verbo mais preciso | §IV Phase 3.2 | [x] | Corrigido: "alter the cost dynamics" → "quantify the cost-performance implications of cloud media scaling strategy selection" |
| m11 | **4.9** "non-negligible" subestima overhead de 93.3%; usar "dominant" | Abstract | [x] | Resolvido junto com M1 |
| m12 | **5.4** Figuras deveriam usar [!htbp] para melhor placement | Figuras | [-] | Figuras já usam [!ht] e [!htbp]; verificar no PDF compilado — item menor, descartado |
| m13 | **5.5** Nomenclatura Phase 3.1/3.2 vs Dynamic/Optimized Provisioning inconsistente | §III + §IV | [x] | §III: adicionados labels "Phase~3.1 (Dynamic Provisioning)" e "Phase~3.2 (Optimized Provisioning)" na primeira ocorrência |
| m14 | **6.3** Katsenou et al. caracterizado como "embedded devices" — verificar se correto | Table 1 | [-] | Não localizado no texto atual — provavelmente em versão anterior; descartado |
| m15 | **6.4** b15/b16 são de conferência regional brasileira; suplementar com IEEE TCSVT/ICIP | Bibliography | [-] | Descartado — substituir referências existentes adicionaria complexidade sem alterar conclusões; anotar para versão de jornal |
| m16 | **7.5** Custo de reprodução $150-$250 provavelmente subestimado | Appendix | [x] | Atualizado para $400-$600 com breakdown por fase (Ph2~$50-80, Ph3 x86~$100-150, ARM~$80-120, sa-east-1~$60-100, Ph4~$40-60, misc~$30-60) |
| m17 | **8.6** Overhead de Docker layer pull conflado com overhead de AMI | §V Threats | [x] | §V Internal Validity: parágrafo "Docker Container vs. AMI Overhead" explicita que Phase 3.2 não tem Docker pull (pre-installed in AMI); Phase 3.1 instala FFmpeg via apt nativamente |

---

## RODADA 2 — Revisão adversarial Opus (Março 2026)

25 findings adicionais (F1-F25) — todos [x] concluídos na mesma sessão.

### Críticos

| # | Issue | Status | Notas |
|---|-------|--------|-------|
| F1 | "three-phase" no início de §IV deveria ser "four-phase" | [x] | §IV abertura corrigida |
| F2 | Preços sa-east-1 na Table 2 inconsistentes com Table 6 (premium ~43.5%) | [x] | Todos os preços sa-east-1 recalculados com ratio empírico 1.435×; caption atualizado com nota de metodologia |

### Major

| # | Issue | Status | Notas |
|---|-------|--------|-------|
| F3 | Contagem de benchmarks e instance types no Appendix incorretos | [x] | Breakdown detalhado: Ph2=5400, Ph3 x86≈540, ARM≈240, Ph4≈270, sa-east-1=90; "17 EC2 instance types: 15 x86 + 2 ARM Graviton 3" |
| F4 | RQs não explicitamente apontadas nos resultados | [x] | "addressing RQ1/2/3/4" adicionado a cada subsecção de resultados |
| F5 | Table 5 ARM H.265 serial stats corrompidos por artefato de log-parsing | [x] | m7g n=26 (excl. 1 VP9 run misatribuído): Med=700.51 Std=4.10 Min=699.89 Max=718.51; c7g n=29 (excl. 1 H.264 run): Med=702.15 Std=1.36 Min=701.62 Max=709.38; dagger footnote adicionado |
| F6 | Welch's t-test aplicado a ARM H.265 com CV>50%; sem teste alternativo não-paramétrico | [x] | Mann-Whitney U adicionado: mesmo resultado (p>.05) |
| F7 | c5.large valor incorrecto no texto (64.41s vs dado correto 64.04s em us-east-1) | [x] | Corrigido para "64.04s in us-east-1" |
| F8 | Speedup 1.28× ARM H.264 não discutido intra-family | [x] | Nota adicionada: mesmo 1.28× observado intra-family (10×m5.large vs m5.4xlarge) |
| F9 | "average 74.9%" sem intervalo de confiança e sem contexto (qual estratégia?) | [x] | Qualificado: "57.3%–93.3% range across T-family Phase 3.1 configurations, arithmetic mean 74.9% across the three structurally distinct strategies" |
| F10 | "exponentially" para crescimento de order-statistic (máximo de N i.i.d.) — deve ser "monotonically" | [x] | Corrigido em parágrafo da Eq.4 |
| F11 | Múltiplas instâncias de linguagem hiperbólica inadequada para IEEE | [x] | ~10 instâncias corrigidas: "severe"→"considerable", "computational lottery"→"processor heterogeneity concern", "with absolute certainty"→"(p<10⁻¹², Cohen's d=4.31)", etc. |
| F12 | Parágrafo ARM Graviton de ~25 linhas sem divisão lógica | [x] | Quebrado em 4 sub-parágrafos: H.265 horizontal, H.264 inversão, artefato log-parsing, slowdown finding |

### Minor

| # | Issue | Status | Notas |
|---|-------|--------|-------|
| F13 | Fórmula de custo não menciona billing floor de 60 segundos da AWS | [x] | Nota adicionada em definição de T_i |
| F14 | Construct Validity ausente nas Threats (T-family credits, serverless, spot instances) | [x] | Nova subsecção "Construct Validity" com 3 parágrafos: T-family credit accuracy (89.4% base vs ~59% ajustado), MediaConvert/Fargate, spot instances |
| F15 | Gerações Graviton não especificadas (t4g=Graviton 2 vs m7g/c7g=Graviton 3) | [x] | §III: "t4g Graviton 2, m7g/c7g Graviton 3" com nota que Phase 3 usa apenas Graviton 3 |
| F16 | AWS Elemental MediaConvert e Amdahl's Law ausentes do Related Works | [x] | 2 novos parágrafos adicionados: MediaConvert/serverless; Amdahl's Law com nota de que provisioning introduz novo bottleneck não capturado |
| F17 | Table 4 aparece após discussão textual (float placement) | [-] | Table usa [!htpb]; placement já razoável no PDF compilado; sem alteração |
| F18 | 6 labels LaTeX mortos (nunca referenciados com \ref) | [x] | Removidos: results-phase1/2/3, efficiency-calculation; renomeados: execution-initial→met:phase2, validation-processor→met:phase1 |
| F19 | Abstract menciona 89.4% mas não o valor ajustado por créditos (~59%) | [x] | Abstract: "89.4% base-compute cost reduction; accounting for theoretical T-family CPU credit surcharges, the adjusted cost reduction is ≈59%—still substantial" |
| F20 | "7×" para t3.micro vs c5.large efficiency impreciso (real: 7.636×) | [x] | Corrigido para "~7.6×" |
| F21 | VP9 range "24.7%" incorreto (real: 25.0%) | [x] | Corrigido para "≈25%" com valores exatos: c5.4xlarge 14.45s vs t3.large 18.06s = 25.0% |
| F22 | Nomes de autores em \textbf{} na seção de Related Works (9 ocorrências) | [x] | Removidos todos os \textbf{} de nomes de autores |
| F23 | Threats of Validity mal estruturada (construct validity misturado com external) | [x] | Subsecção "External & Construct Validity" renomeada para "External Validity"; construct validity movido para nova subsecção própria (F14) |
| F24 | Abstract de 237 palavras em run-on sentences (IEEE recomenda ~150-200) | [x] | Reescrito para ~180 palavras com frases completas |
| F25 | "VaaS" no abstract pode ser jargão não reconhecido; preferir descrição | [x] | "VaaS" → "cloud video transcoding platforms" no abstract |

---

## Legenda de prioridade de ataque sugerida

1. Iniciar pelos **Críticos (C1–C6)** — comprometem a validade do paper
2. Depois os **Major de dados/análise (M1–M13)** — requerem verificação nos artifacts
3. Depois os **Major de texto/estrutura (M14–M35)** — edições no .tex
4. Por último os **Minor (m1–m17)** — polimento

---

## Ground truth: tabela de referência

A tabela com mais dados é **Table 3 (tab:scaling_all_families)** — todos os claims de Phase 3 devem ser verificados contra ela.
Para Phase 2, o ground truth é **Table 2 (tab:final_comparison_consistent)**.
Para dados brutos, verificar em `artifacts2/experimental_data/` (versão mais recente) antes de `artifacts/experimental_data/`.
