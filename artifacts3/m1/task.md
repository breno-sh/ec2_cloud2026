# EC2 Sweet Spot Project — 5 Melhorias

- [x] Entender estrutura do artigo e scripts existentes
- [x] Identificar dados mais recentes (CSVs de 11/Mar, analysis_output de 7/Mar)
- [x] Revisar scripts de Fase 3 existentes para avaliar reuso
- [x] Elaborar plano de implementação detalhado para as 5 melhorias
- [x] Obter aprovação do usuário

### Phase 3 Experiment Execution
- [x] Run Smoke Tests (Melhoria 1, 2, 3)
- [x] Execute Melhoria 1 batch (H.265/VP9 on M/C families)
- [/] Execute Melhoria 2 batch (Regional Validation - sa-east-1 on M/C families)
- [ ] Execute Melhoria 3 batch (ARM Graviton - M/C variants)
- [x] Executar Melhoria 4 (modelo analítico de chunk)
- [x] Executar Melhoria 5 (estimativa de custos de rede)
- [x] Criar script unificado phase3_unified.py (Melhorias 1+2+3)
- [x] Criar script orquestrador run_all_experiments.py

### AWS Prerequisites
- [x] Copy AMIs to sa-east-1 (ami-0653a33fe2919af93, ami-0ecbc0dab130caeda)
- [x] Create KeyPair and Security Group in sa-east-1
- [x] Clean up duplicate AMIs/Snapshots in sa-east-1
- [x] Terminate orphaned instances from interrupted runs
- [x] Check T-family throttling (Confirmed: t3.micro at 0.0 credits)
- [x] Executar testes com o orquestrador (Opcional - aguardando comando do usuário)
- [ ] Integrar resultados no LaTeX
