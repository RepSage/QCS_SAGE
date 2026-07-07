# QCS — Quality Control System (SAGE)

Ferramenta de qualificação e visualização de dados físico-químicos oceanográficos
(perfis e fundeios), desenvolvida para os dados do projeto SAGE.

## Como rodar

O programa roda diretamente pelos scripts Python, usando o Python do Anaconda. Há dois
atalhos prontos na pasta principal (dois cliques para abrir):

- **`QCS - Qualificacao de Dados.bat`** — ferramenta de qualificação (`sourceCode/QCS_Main.py`).
- **`QCS - Visualizacao de Dados.bat`** — ferramenta de visualização (`sourceCode/QCS_DatabaseView.py`).

Uma janela de terminal abre junto e mostra o progresso; ela fecha sozinha ao encerrar o
programa (só permanece aberta se ocorrer um erro).

## Dependências

Python (Anaconda) com os pacotes listados em [`sourceCode/requirements.txt`](sourceCode/requirements.txt):
`numpy`, `pandas`, `matplotlib`, `scipy`, `openpyxl` e `gsw`. Para instalar:

```
python -m pip install -r sourceCode/requirements.txt
```

## Estrutura

- `sourceCode/` — código-fonte:
  - `QCS_Main.py` — ferramenta de qualificação (interface + pipeline de testes de QC).
  - `QCS_DatabaseView.py` — ferramenta de visualização de banco de dados.
  - `QCS_DataHandler.py` — leitura, conversão e formatação de dados; constante `QCS_VERSION`.
  - `QCS_DataView.py` — geração de gráficos e painéis.
  - `QCS_Tests.py` — testes de controle de qualidade.
  - `QCS_SelfTest.py` — autotestes com dados sintéticos (`python QCS_SelfTest.py`).
  - `qcs_user_settings.json` — preferências do usuário (geradas automaticamente).
- `changelog/` — histórico de mudanças, um arquivo por versão.
- `Quality Control System (SAGE) - User Manual.html` — user manual.

## Versão

A versão é definida em um único lugar: `QCS_VERSION`, em `sourceCode/QCS_DataHandler.py`.
