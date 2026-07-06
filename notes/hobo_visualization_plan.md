# Plano: Visualização dedicada do HOBO (v4.0 — Parte 5, PENDENTE)

> Documento de trabalho para retomar na próxima sessão (já em `qcs_sage`).
> É a última parte do plano da v4.0 antes de fechar a versão.

## Contexto (o que já existe)
- Banco HOBO montado por `data.build_database('HOBO', ...)` tem as colunas:
  `Sample number, Datetime, Temperature (degC), Luminosity (lux), Expedition,
  Site, Battery voltage (V), Flag, Flag_T, Flag_lux, QCS version, Source file`.
- Hoje a visualização de um banco HOBO cai nos painéis de mooring do Seaguard
  (`plot_database_panel1/2`), que **funcionam mas**: (a) não conhecem a janela
  de uso da luz (`Flag_lux`); (b) não usam escala log (a luz vai de 0 a ~17000
  lux); (c) a lista de parâmetros da janela já foi restrita a Temperatura+Luz
  (em `show_view_window`, `QCS_DatabaseView.py`).
- `getParamColors` já tem cor para `Luminosity (lux)` (âmbar claro/escuro).
- `plot_hobo_split_site(database, dataview_path)` já existe em `QCS_DataView.py`
  (versão básica: temperatura e luz por site, SEM sombreamento da janela) — é o
  ponto de partida, mas está incompleta e não é chamada por ninguém.
- Na qualificação individual, o gráfico `QCS_light_window.svg` (com baseline,
  limiar e corte) já é gerado por `view.plot_light_window` + `mark_light_cutoff`.

## Objetivo
Painéis próprios do HOBO, no fluxo do DatabaseView, que aproveitem o `Flag_lux`:
1. **Temperatura no tempo**, por site (e/ou multi-site sobreposto), com pontos
   `Flag_T >= 3` (suspeito/ruim) destacados — análogo ao Seaguard.
2. **Luz no tempo (escala log)**, por site, com a **região após o corte de
   incrustação (`Flag_lux == 3`) sombreada** — deixa visualmente claro onde a
   luz deixou de ser confiável. É o painel mais importante e o diferencial HOBO.
3. **Comparação multi-site da luz** (log) para comparar o início da incrustação
   entre sites.

## Onde plugar
- `QCS_DataView.py`: novas funções
  - `plot_hobo_temperature(database, dataViewSettings, site)`
  - `plot_hobo_light(database, dataViewSettings, site)`  ← sombreia via `Flag_lux`
  - `plot_hobo_light_multisite(database, dataViewSettings)`
  Reaproveitar `getParamColors` (luz), `getSiteColors` (multi-site),
  `fill_NaT_gap`, e o recorte por ano já usado nos painéis existentes.
- `QCS_DatabaseView.py`: a seção de painéis da janela Step 2 precisa virar
  **instrument-aware**. Quando `inputSettings['instrument'] == 'HOBO'`, mostrar
  checkboxes de painéis HOBO (Temperatura / Luz+janela / Luz multi-site) em vez
  de Panel 1/2/3 e T-S diagram; `generatePanels` roteia por instrumento.
  (Hoje `show_view_window` já ajusta `parameter_names` para HOBO; falta a troca
  dos painéis em si.)

## Decisões a confirmar com o usuário (fazer no início da próxima sessão)
1. Um painel por site, multi-site sobreposto, ou os dois?
2. **Sombrear** a região incrustada (`Flag_lux==3`) OU **pintar** os pontos
   suspeitos de outra cor? (sugestão: sombrear — é a "janela de uso").
3. Escala log para a luz — confirmar (recomendado pela faixa dinâmica).
4. Destacar `Flag_T` suspeito/ruim na temperatura, como no Seaguard?
5. T-S diagram fica indisponível para HOBO (sem salinidade) — confirmar.

## Verificação esperada
- `QCS_SelfTest.py` (28 casos) deve continuar verde após mexer no DataView.
- E2E: arquivo real em `C:\Users\LAMB\Desktop\PAB3_13set2024_1_a_24032025.xlsx`
  → qualificar (Input Type = HOBO) → no DatabaseView, Instrument = HOBO,
  apontar a pasta-mãe de saída → gerar os painéis HOBO → conferir o sombreado
  da janela de luz batendo com o corte do `QCS_light_window.svg`.
  (Os drivers de teste headless ficavam no scratchpad, que é efêmero — recriar
  se precisar; a lógica está descrita nos commits da v4.0.)

## Estado da v4.0 (branch `melhorias-v4.0`)
Commits até aqui: GUI moderna (Sun Valley/DPI/dark) → correções + QARTOD →
HOBO leitura+luz → formato de saída HOBO → unificação `build_database` →
lat/long fora das planilhas. **Falta**: esta visualização + **atualizar o
manual HTML** (defasado desde a v3.2.1). Depois: fechar a versão e abrir o PR
para `master` (nada foi enviado ao GitHub ainda).
