# 📊 Evolução do Tempo de Espera por Mês – Streamlit App

Este aplicativo interativo desenvolvido com [Streamlit](https://streamlit.io/) permite visualizar a **evolução do tempo de espera para agendamentos médicos ao longo dos meses**, com a possibilidade de **filtrar por especialidade e por unidade solicitante**.

O gráfico mostra:
- **Mediana do tempo de espera**
- **1º e 3º quartis**
- **Faixa interquartil sombreada**
- Todos os meses exibidos no eixo X
- Valores arredondados e apresentados em número inteiro

---

## ✅ Funcionalidades

- Upload de arquivo `.csv` ou `.xlsx`
- Filtros múltiplos por:
  - Especialidade
  - Unidade Solicitante
- Gráfico de linha com:
  - Faixas entre quartis
  - Hover unificado com ordenação semântica
- Responsivo e amigável para uso local ou na web

---

## 📁 Estrutura dos dados esperados

O arquivo de entrada deve conter as seguintes colunas:

| Coluna                | Tipo           | Exemplo              |
|-----------------------|----------------|-----------------------|
| `data_solicitacao`    | Data (`YYYY-MM-DD`) | `2024-01-15`    |
| `tempo_espera_dias`   | Numérico (int ou float) | `12`        |
| `Especialidade`       | Texto          | `Cardiologia`         |
| `Unidade Solicitante` | Texto          | `UBS Central`         |

---

## 🚀 Como executar localmente

1. **Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
