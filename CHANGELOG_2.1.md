# QCS — Correções de debug

## 1. BUG PRINCIPAL — Escala fixa não funcionava nos perfis (Panel 3)
**Arquivo:** `QCS_DataView.py` · função `plot_database_panel3` · ~linha 757

Dentro do laço dos eixos secundários (`twiny`), a fixação de escala fazia:

```python
ax1.set_xlim(scaleSettings[parameter_names[i-1]]['min'],
             scaleSettings[parameter_names[-1]]['max'])   # <-- errado
```

Dois erros na mesma linha:
- **Eixo errado:** aplicava em `ax1` (o 1º eixo) em vez de `ax` (o eixo `twiny` recém-criado).
  Resultado: os eixos secundários nunca recebiam a escala fixa (continuavam em autoescala),
  e o 1º eixo era sobrescrito a cada iteração.
- **Índice errado no max:** usava `parameter_names[-1]` (último parâmetro) em vez de
  `parameter_names[i-1]` (parâmetro atual) — misturava o min de um parâmetro com o max de outro.

**Correção:**
```python
ax.set_xlim(scaleSettings[parameter_names[i-1]]['min'],
            scaleSettings[parameter_names[i-1]]['max'])
```

Comprovação (dados sintéticos, faixas fixas propositalmente fora dos dados):

| Eixo | Antes (bugado) | Depois (corrigido) | Esperado |
|------|----------------|--------------------|----------|
| Temperatura | (30, 50) ← valores da salinidade | (5, 10) | (5, 10) |
| Salinidade  | (32.8, 37.0) ← autoescala | (30, 50) | (30, 50) |

Observação: perfis com **um único parâmetro** já funcionavam (usam a linha ~703, que estava
correta); o problema só aparecia com **2+ parâmetros** no mesmo perfil. Os painéis de fundeio
(Panel 1 e Panel 2) já estavam corretos e foram validados.

## 2. Robustez — escala parcialmente preenchida quebrava o painel inteiro
**Arquivo:** `QCS_DataView.py` · Panels 1, 2 e 3

`saveDataViewSettings` só grava um parâmetro em `scaleSettings` quando **min E max** estão
preenchidos. Se um parâmetro selecionado ficasse sem min/max, o acesso direto
`scaleSettings[parametro]` lançava `KeyError` e derrubava a geração do painel todo
(virava "ERROR generating Panel X" no log).

**Correção:** todas as aplicações de escala fixa agora checam a presença da chave antes de usar,
ex.:
```python
if dataViewSettings['fixedScale'] and parameter_names[0] in dataViewSettings['scaleSettings']:
    ...
```
Parâmetros sem faixa definida simplesmente ficam em autoescala, em vez de abortar o painel.

## 3. Portabilidade — ícones nunca carregavam fora da máquina de origem
**Arquivos:** `QCS_DatabaseView.py` (2 ocorrências) e `QCS_Main.py` (3 ocorrências)

As chamadas passavam um caminho **absoluto fixo** para `resource_path`:
```python
resource_path(r"C:\Users\JoaoCardoso\QCS_SAGE_v2.0\sourceCode\qcsMainIcon.ico")
```
Como `resource_path` faz `os.path.join(base, caminho)` e o 2º argumento era absoluto, o join
ignorava o `base` (incl. o `_MEIPASS` do PyInstaller). Fora da máquina original o arquivo não
existia → caía no `try/except` → janelas sem ícone (silenciosamente).

**Correção:** passar só o nome relativo, que é como o `--add-data` empacota:
```python
resource_path("qcsMainIcon.ico")
```

---

## Itens recomendados (NÃO alterados — para sua avaliação)

- **Regex em strings comuns** (`'\d'`, `'\('`, `'\s'` etc.) em `QCS_Main.py` e `QCS_DataHandler.py`:
  funcionam no Python 3.8 do projeto, mas geram `SyntaxWarning` em Python ≥3.12 e devem virar erro
  no futuro. Recomendo prefixar com `r''` (ex.: `r'\d{1,3}'`). São mecânicas, mas preferi não tocar
  em dezenas de linhas sem seu aval.
- **Código morto:** `plot_database_panel2_DEPRECATED` em `QCS_DataView.py` não é mais chamado
  (a versão ativa é `plot_database_panel2`). Pode ser removido quando for conveniente.

## Verificação
Os três arquivos compilam (`py_compile`) e as fixações de escala de Panel 1 (fundeio) e Panel 3
(perfil) foram validadas com dados sintéticos. Quebras de linha (CRLF) preservadas.
