# Atualizador de Renda Fixa — Lucas Turquino

Script Python que gera um snapshot atualizado das posições de Renda Fixa
(CDB, CRI/CRA, Fundos, LCI/LCA, Tesouro Direto) puxando indicadores oficiais
do Banco Central e preços ao vivo do Tesouro Direto.

---

## Pré-requisitos (uma vez só)

Abra o **Terminal** do Mac e rode:

```bash
pip3 install python-docx
```

> O script usa apenas `python-docx` + bibliotecas-padrão do Python.
> Não precisa de `requests` nem `pandas`.

---

## Fluxo mensal recomendado

```
Dia 1 do mês
    ↓
python3 atualiza_carteira_rf.py      ← gera .docx + .json do mês
    ↓
python3 compara_snapshots_rf.py      ← gera comparativo histórico (.docx)
```

---

## 1. Gerar snapshot do mês

```bash
cd "/Users/leandro/3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
python3 atualiza_carteira_rf.py
```

O script vai:

1. Buscar **CDI** e **IPCA** acumulados (Banco Central — API SGS)
2. Buscar **PU atual** dos títulos do **Tesouro Direto** (B3)
3. Recalcular cada posição
4. Imprimir o resumo no terminal
5. Salvar `Snapshot_RF_Lucas_AAAA-MM-DD.docx` na pasta CARTEIRA LUCAS
6. Salvar `Snapshot_RF_Lucas_AAAA-MM-DD.json` na pasta CARTEIRA LUCAS ← **novo**

> O arquivo `.json` é o que alimenta o comparativo histórico.
> Guarde todos os JSONs — eles formam o histórico mês a mês.

---

## 2. Gerar comparativo histórico (delta mês a mês) — **novo**

```bash
cd "/Users/leandro/3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
python3 compara_snapshots_rf.py
```

O script lê **todos** os `Snapshot_RF_Lucas_*.json` na pasta e gera:

**`Comparativo_RF_Lucas_AAAA-MM-DD.docx`** com 4 seções:

| Seção | O que mostra |
|---|---|
| **1. Resumo Executivo** | Total atual, ganho, rentab. e variação no período |
| **2. Evolução do Total** | Tabela por data: aplicado / atual / ganho / Δ valor / Δ% |
| **3. Evolução por Classe** | Valor atual de cada classe em cada mês |
| **4. Maiores Variações** | Posições com maior variação absoluta entre o 1º e o último snapshot |

---

## Como atualizar quando mudar a carteira

Abra o arquivo `atualiza_carteira_rf.py` em qualquer editor de texto
(TextEdit, VS Code, etc.) e localize as listas:

```python
POSICOES_CDB = [...]
POSICOES_LCI_LCA = [...]
POSICOES_CRI_CRA = [...]
POSICOES_FUNDOS = [...]
POSICOES_TESOURO = [...]
```

Para cada posição:

| Campo | Significado |
|---|---|
| `nome` | Como aparece no relatório |
| `aplicacao` | Data da compra (formato `'AAAA-MM-DD'`) |
| `vencimento` | Data do vencimento |
| `tipo` | `"CDI"`, `"IPCA"` ou `"PRE"` |
| `perc_cdi` | Para CDI (ex.: `1.00` = 100% do CDI) |
| `spread_aa` | Para IPCA+ (ex.: `0.0934` = +9,34% a.a.) |
| `taxa_aa` | Para Pré (ex.: `0.1256` = 12,56% a.a.) |
| `qtd` × `pu_pago` | Para títulos com cota |
| `valor_aplicado` | Para fundos / aportes consolidados |

Adicionar uma nova posição: copie um bloco existente, edite os campos e salve.

---

## Cálculos por trás

| Classe | Como o valor atual é calculado | IR |
|---|---|---|
| **CDB / Fundo CDI** | `aplicado × Π (1 + CDI_dia × % CDI)` | Regressivo (15–22,5%) |
| **CDB Pré** | `aplicado × (1 + taxa)^anos` | Regressivo |
| **LCI / LCA pós** | mesmo fator de CDI | **Isento (PF)** |
| **LCI / LCA IPCA+** | `aplicado × IPCA_acum × (1+spread)^anos` | **Isento (PF)** |
| **CRI / CRA IPCA+** | `aplicado × IPCA_acum × (1+spread)^anos` | **Isento (PF)** |
| **CRI / CRA Pré** | `aplicado × (1+taxa)^anos` | **Isento (PF)** |
| **Tesouro Direto** | `qtd × PU atual da B3` (líquido de IR) | Regressivo |

---

## Limitações importantes

- **CRI / CRA**: o cálculo é **estimativa de carregamento na curva contratada**.
  Não é marcação a mercado real (que pode divergir).
- **Fundos**: apenas aproximação por % do CDI. O valor real depende da cota
  do dia e da taxa de administração efetiva.
- **IPCA**: divulgado pelo IBGE com defasagem de ~1 mês — meses recentes podem
  não estar disponíveis na série; o script ignora os ausentes.
- **Tesouro Direto**: a API retorna preço em horário de mercado (dia útil).
  Em finais de semana / feriados pode trazer o último valor disponível.
- O script **não** aplica IOF (relevante apenas em resgates < 30 dias).

---

## Solução de problemas

| Erro | O que fazer |
|---|---|
| `ModuleNotFoundError: docx` | Rodar `pip3 install python-docx` |
| `Falha ao buscar série BCB ...` | Sem internet ou API do BCB fora do ar — tente novamente |
| `PU atual não encontrado` (Tesouro) | Verificar internet; se persistir, definir `pu_atual_manual` na posição |
| `Nenhum arquivo .json encontrado` | Rodar `atualiza_carteira_rf.py` pelo menos uma vez antes do comparativo |
| Permissão para salvar | O script tem fallback: salva no diretório atual se a pasta padrão não existir |

---

## Onde fica cada arquivo

```
CARTEIRA LUCAS/
├── Aplicações Lucas.xlsx                    ← planilha original
├── Aplicações Lucas.numbers                 ← original Numbers
├── atualiza_carteira_rf.py                  ← script de snapshot mensal
├── compara_snapshots_rf.py                  ← script de comparativo histórico (novo)
├── agendar_atualizacao.sh                   ← agendamento via launchd (macOS)
├── Avaliacao_Carteira_Lucas_Turquino.docx   ← análise inicial consolidada
├── Snapshot_RF_Lucas_AAAA-MM-DD.docx        ← snapshot do mês (gerado a cada execução)
├── Snapshot_RF_Lucas_AAAA-MM-DD.json        ← dados numéricos do snapshot (novo)
└── Comparativo_RF_Lucas_AAAA-MM-DD.docx     ← histórico mês a mês (novo)
```

---

## API do Tesouro Direto — automação de PUs (novo)

A partir desta versão, o script busca PUs automaticamente em duas fontes públicas,
sem necessidade de chave de API:

| Prioridade | Fonte | URL |
|---|---|---|
| 1 | **Manual** | `pu_atual_manual` na posição (sobrescreve tudo) |
| 2 | **AA40 API** | `aposenteaos40.org/fire-dash/includes/api_tesouro.php` |
| 3 | **B3/Tesouro** | `tesourodireto.com.br/json/…/treasurybondsinfo.json` (fallback) |

### Posições do Lucas e cobertura

| Posição | Vencimento | API AA40 | Observação |
|---|---|---|---|
| IPCA+ 2040 | ago/2040 | ✅ automático | `pu_atual_manual = None` |
| IPCA+ 2050 (#1 e #2) | ago/2050 | ✅ automático | `pu_atual_manual = None` |
| NTN-B Principal 2050 | ago/2050 | ✅ automático | `pu_atual_manual = None` |
| NTN-B Principal 2060 | ago/2060 | ⚠️ manual | Título fora da lista atual do TD; atualizar mensalmente |

### Quando atualizar o NTN-B Principal 2060 manualmente

Abra `atualiza_carteira_rf.py`, localize:

```python
{"nome": "NTN-B Principal 2060",
 ...
 "pu_atual_manual": 586.03,   # ← atualizar com PU da corretora
```

Substitua o número pelo PU atual da sua corretora (use ponto, não vírgula).

### Como verificar se a API AA40 está funcionando

Cole no terminal:

```bash
curl "https://www.aposenteaos40.org/fire-dash/includes/api_tesouro.php?titulo=All"
```

Se retornar linhas CSV com preços, está OK. A AA40 é uma API comunitária sem
garantia de disponibilidade permanente — se ficar fora do ar, o script cai
automaticamente para a API B3 e depois para `pu_atual_manual`.


---

## Extensão — Renda Variável (novo)

### Pré-requisito adicional (uma vez só)

```bash
pip3 install yfinance
```

### 3. Gerar snapshot de Renda Variável

```bash
python3 atualiza_carteira_rv.py
```

Busca cotações em tempo real via **Yahoo Finance** para:

| Classe | Tickers | Cotação |
|---|---|---|
| Ações BR | MELI34, BBSE3 | BRL (B3) |
| ETF BR | COIN11 | BRL (B3) |
| ETF USA | TLT, BND, IUSB, JCPB, IAGG, IBIT, TFLO | USD → BRL |
| FII | MCCI11, PCIP11, CXCI11 | BRL (B3) |
| REITs | PSA, VICI, AMT | USD → BRL |
| Stocks | RACE (Ferrari) | USD → BRL |

Gera:
- `Snapshot_RV_Lucas_AAAA-MM-DD.docx` — relatório de RV
- `Snapshot_RV_Lucas_AAAA-MM-DD.json` — dados para histórico

### 4. Gerar Carteira Completa (RF + RV unificada)

```bash
python3 consolida_carteira.py
```

Lê os snapshots mais recentes de RF e RV e gera:

**`Carteira_Completa_Lucas_AAAA-MM-DD.docx`** com:
1. **Resumo Executivo** — totais de RF, RV e carteira consolidada
2. **Alocação por Classe** — % de cada classe no total
3. **Alocação Geográfica** — Brasil vs Internacional
4. **RF Detalhe** — posições por classe de renda fixa
5. **RV Detalhe** — posições por classe de renda variável

---

## Fluxo mensal completo (atualizado)

```
Dia 1 do mês
    ↓
python3 atualiza_carteira_rf.py      ← RF: .docx + .json
    ↓
python3 atualiza_carteira_rv.py      ← RV: .docx + .json
    ↓
python3 consolida_carteira.py        ← Carteira Completa (docx)
    ↓
python3 compara_snapshots_rf.py      ← Histórico RF (delta mês a mês)
```

---

## Onde fica cada arquivo (atualizado)

```
CARTEIRA LUCAS/
├── Aplicações Lucas.xlsx                       ← planilha original
├── Aplicações Lucas.numbers                    ← original Numbers
├── atualiza_carteira_rf.py                     ← snapshot RF mensal
├── atualiza_carteira_rv.py                     ← snapshot RV mensal (novo)
├── compara_snapshots_rf.py                     ← histórico RF mês a mês
├── consolida_carteira.py                       ← carteira completa RF+RV (novo)
├── agendar_atualizacao.sh                      ← agendamento via launchd
├── Avaliacao_Carteira_Lucas_Turquino.docx      ← análise inicial
├── Snapshot_RF_Lucas_AAAA-MM-DD.docx/.json    ← snapshot RF (mensal)
├── Snapshot_RV_Lucas_AAAA-MM-DD.docx/.json    ← snapshot RV (mensal, novo)
├── Comparativo_RF_Lucas_AAAA-MM-DD.docx       ← histórico RF
└── Carteira_Completa_Lucas_AAAA-MM-DD.docx    ← carteira consolidada (novo)
```
