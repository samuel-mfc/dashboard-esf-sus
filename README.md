# Dashboard de Regulação Assistencial — MIRA (e-SUS Regulação)

Protótipo em **Streamlit** para análise de solicitações de regulação assistencial,
baseado no **Modelo de Informação da Regulação Assistencial (MIRA)** proposto pelo
Ministério da Saúde.

## Funcionalidades
- 📥 Upload de base de dados (CSV/Parquet) ou uso de dados simulados
- 📊 KPIs: fila atual, agendadas, realizadas, canceladas/devolvidas, tempo mediano e P90 até agendar, taxa de cancelamento
- 📈 Gráficos: backlog por mês, funil de solicitações, boxplot de tempo de espera por prioridade, ranking das maiores filas por especialidade
- 📋 Tabelas: métricas por prioridade e amostra de solicitações detalhadas

## Colunas mínimas esperadas
- `id_solicitacao`
- `data_solicitacao`
- `especialidade`
- `prioridade` (ex.: P1, P2, P3, P4)
- `situacao` (Aguardando, Agendado, Realizado, Cancelado, Devolvido)
- `data_agendamento`
- `data_realizacao`
- `unidade_origem`
- `servico_destino`

### Opcionais
- `procedimento`, `equipe_origem`, `central_regulacao`, `municipio_destino`, `canal`, `cns_paciente`

## Como rodar localmente
```bash
pip install -r requirements.txt
streamlit run app_regulacao.py
