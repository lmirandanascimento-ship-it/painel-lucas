# Painel Lucas — 3P Finanças

Contexto completo do projeto para o Claude Code. Leia este arquivo antes de qualquer alteração.

---

## Visão Geral

Dashboard financeiro pessoal de Lucas Miranda Nascimento, gerenciado por Leandro Nascimento (3P Finanças). Cobre:

1. **Carteira de Investimentos** — renda variável (ações, ETFs, FIIs, REITs, Stocks) e renda fixa
2. **Empréstimos Concedidos** — Lucas empresta para terceiros (Quadra, iClothes, etc.)
3. **Meus Empréstimos** — empréstimos que Lucas tomou (ainda em desenvolvimento)
4. **Escritório** (planejado) — controle financeiro das lojas do Lucas

O app é de uso interno: só Lucas e Leandro acessam.

---

## Stack Técnica

| Componente | Tecnologia |
|---|---|
| Frontend/App | Python + Streamlit ≥ 1.35 |
| Banco de dados | Supabase (PostgreSQL) |
| Hospedagem app | Streamlit Community Cloud |
| Hospedagem DB | Supabase Cloud |
| Versionamento | GitHub |
| Cotações | yfinance + brapi (BRAPI_TOKEN em app.py) |

---

## Ambientes

| Ambiente | Branch | URL | Banco Supabase |
|---|---|---|---|
| Produção | `main` | `painel-lucas.streamlit.app` | `Lucas_Pessoal` |
| Staging/Teste | `Teste` | `painel-lucas-teste.streamlit.app` | `Lucas_Pessoal_TESTE` |

**Fluxo de deploy:** sempre validar no Teste primeiro, depois `git push origin HEAD:main`.

---

## Arquivos do Projeto

```
CARTEIRA LUCAS/
├── app.py                    ← App principal (único arquivo Python do Streamlit)
├── requirements.txt          ← streamlit, supabase, pandas, plotly, requests, yfinance
├── supabase_local.py         ← NUNCA COMMITAR — contém SUPABASE_SERVICE_KEY de produção
├── supabase_local_teste.py   ← NUNCA COMMITAR — contém SUPABASE_SERVICE_KEY do staging
├── .gitignore                ← já inclui os dois arquivos acima
├── setup_supabase.sql        ← DDL histórico das tabelas
├── setup_supabase_v2.sql
├── setup_supabase_v3.sql
├── importar_quadra.py        ← script para importar Excel da Quadra/iClothes
├── popular_staging.py        ← script para popular o banco de staging
├── push_to_supabase.py       ← script genérico de push de dados
├── Posicoes_Lucas.xlsx       ← planilha mestre de posições (atualizada manualmente)
└── ... (vários Snapshots_*.docx e scripts auxiliares)
```

### CRÍTICO — Segurança
`supabase_local.py` e `supabase_local_teste.py` estão no `.gitignore` e **JAMAIS devem ser commitados**. Eles contêm a `SUPABASE_SERVICE_KEY` que dá acesso irrestrito ao banco.

---

## Banco de Dados Supabase

### Tabelas Principais

#### `devedores`
Cadastro de quem Lucas empresta dinheiro.
```sql
id, nome, cpf, telefone, categoria, observacoes, created_at
```

#### `emprestimos_concedidos`
Contratos de empréstimo (Lucas → devedor).
```sql
id, devedor_id (FK→devedores), titulo, valor_original, taxa_juros (decimal, ex: 0.02 = 2%),
dia_vencimento, data_emprestimo, status ('ativo'|'quitado'),
saldo_devedor, parcela_juros, observacoes, created_at
```

#### `pagamentos_recebidos`
Pagamentos de cada contrato.
```sql
id, emprestimo_id (FK→emprestimos_concedidos), data_pagamento, valor_pago,
juros, amortizacao, saldo_depois, observacao, created_at
```
- `amortizacao = valor_pago` (amortização pura — juros são separados)
- `saldo_depois` pode ser NULL para pagamentos importados (calculado retroativamente)
- Apenas o ÚLTIMO pagamento (maior data) tem botões EDITAR/EXCLUIR

#### `posicoes` (investimentos)
Posições da carteira de investimentos.
```sql
id, ticker, nome, classe, quantidade, preco_medio, valor_atual,
data_atualizacao, tipo ('RV'|'RF'), ...
```

---

## Estrutura do app.py

### Constantes e Cores
```python
VERDE        = "#1A4731"   # verde escuro (cor principal)
VERDE2       = "#2D6A4F"   # verde médio
OURO         = "#B8860B"   # dourado (destaques)
CAPITAL_BASE = 684_160.69
BRAPI_TOKEN  = "o1ikT8zCSyqQUkNYz224ho"
```

### Autenticação
Login simples via `st.session_state["autenticado"]`. Senha hardcoded (uso interno). Sem biblioteca de auth.

### Cache
Funções de carregamento com `@st.cache_data(ttl=300)`:
- `load_emprestimos_concedidos()` — sem parâmetros, usa `sb` global
- `load_pagamentos_recebidos(emprestimo_id=None)` — opcional filtro por contrato
- `load_devedores()`

Após operações de escrita (save/delete), sempre chamar:
```python
load_emprestimos_concedidos.clear()
load_pagamentos_recebidos.clear()
st.rerun()
```

### Abas Principais
```
📊 Resumo | 📈 Investimentos | 💼 Empréstimos | 🏦 Escritório
```

Dentro de **Empréstimos**:
```
🏦 Empréstimos Concedidos | 💳 Meus Empréstimos
```

### Função _conteudo_devedor(dev_id, dev_nome)
Função central para a aba Empréstimos Concedidos. Renderiza:
1. KPIs do devedor
2. Cards de Contratos Ativos (grid 2 colunas, com barra de progresso de amortização)
3. Formulário de novo pagamento
4. Expander com histórico de pagamentos por contrato

---

## Padrões de Código Importantes

### Formatação BRL
```python
def brl(v, sign=False) -> str:          # float → "R$ 1.234,56"
def brl_input(v: float) -> str:          # float → "1.234,56" (para text_input)
def parse_brl(s: str) -> float:          # "1.234,56" → 1234.56 (com try/except interno)
```

### Botões EDITAR/EXCLUIR (histórico de pagamentos)
Abordagem atual (funcional): `st.button()` nativo + CSS `:has()` com IDs únicos por `pag_id`.

Apenas o ÚLTIMO pagamento de cada contrato ativo tem botões (`is_ultimo = pag_id == ultimo_pag_id`).

```python
# ORDEM CRÍTICA: button ANTES do markdown (senão o botão aparece abaixo do texto)
if rc[6].button("EDITAR", key=f"btn_ed_{pag_id}", use_container_width=True):
    st.session_state[ed_key] = True
    st.rerun()
rc[6].markdown(
    f'<style>'
    # Usa "stColumn" (Streamlit 1.28+) E "column" (fallback versões antigas)
    f'div[data-testid="stColumn"]:has(#em{pag_id}) button,'
    f'div[data-testid="column"]:has(#em{pag_id}) button'
    f'{{background:#1d4ed8!important;color:#fff!important;...}}'
    f'</style>'
    f'<span id="em{pag_id}"></span>',
    unsafe_allow_html=True,
)
# EXCLUIR — vermelho (#dc2626), mesma lógica com #dm{pag_id}
```

**Por que essa abordagem (histórico de tentativas):**
- `<a href>` → Streamlit intercepta e abre em nova aba
- `<form method="get">` → page reload, perde session state (login some)
- `components.html()` → CSP bloqueia `window.parent` no Streamlit Cloud
- CSS inline `color:#fff!important` → stripped pelo Emotion CSS do Streamlit
- SVG `fill="#ffffff"` → imune ao color!important (propriedade diferente) — funcionou visualmente mas o form causava reload
- `<style>` block com `!important` → válido e não é stripped pelo Streamlit

### Grid do Histórico de Pagamentos
```python
_GCOLS = "1.4fr 1.4fr 1.1fr 1.4fr 1.5fr 2.0fr 0.85fr 0.85fr"
# Colunas: Data | Valor Pago | Juros | Amortização | Saldo Após | Obs | EDITAR | EXCLUIR
rc = st.columns([1.4, 1.4, 1.1, 1.4, 1.5, 2.0, 0.85, 0.85])
```

### Problema do git index.lock
O filesystem tem um bug de `unlink()` (retorna "Operation not permitted"). Solução via `mv` (rename):
```bash
mv .git/index.lock .git/index.lock.bak_$(date +%s%N)
mv .git/HEAD.lock .git/HEAD.lock.bak_$(date +%s%N)
```
Fazer isso ANTES e DEPOIS de cada comando git (add, commit). O push pode ser feito normalmente depois.

---

## Fluxo de Dados — Empréstimos Concedidos

### Registrar Pagamento
1. Usuário seleciona contrato ativo + preenche formulário
2. `amortizacao = valor_pago` (sempre — sistema de amortização pura)
3. `novo_saldo = max(0, valor_original - soma_todas_amortizacoes)`
4. `novo_juros = novo_saldo * taxa_juros`
5. Atualiza `pagamentos_recebidos` + `emprestimos_concedidos` (saldo + status)
6. Se `novo_saldo == 0` → status = 'quitado'

### Editar/Excluir Pagamento
- Apenas o pagamento mais recente pode ser editado/excluído
- Após operação: recalcula saldo de todos os pagamentos do contrato
- `saldo_depois` do pagamento editado = novo saldo do contrato

---

## Estado Atual (julho 2026)

### ✅ Funcionando no Teste (branch Teste)
- Login e autenticação
- Dashboard de investimentos com cotações em tempo real
- Aba Empréstimos Concedidos completa:
  - Cards de contratos ativos com barra de progresso
  - Formulário de novo pagamento
  - Histórico por contrato com EDITAR/EXCLUIR funcionais
  - Cards de contratos quitados

### 🔄 Pendente (Teste → Main)
- Validar Teste e fazer `git push origin HEAD:main`

### 📋 Próximas Features (por prioridade)
1. **EDITAR/EXCLUIR em "Meus Empréstimos"** — mesma lógica do Empréstimos Concedidos
2. **Importar Tabela Emp. Nomã Recebíveis.xlsx** — script de importação pendente
3. **Área de admin para upload de PDFs/Excel** — upload no app → Supabase automaticamente
4. **Controle de investimentos mais robusto** — importação de extratos de corretora
5. **Módulo Escritório** — controle financeiro das lojas do Lucas

---

## Como Rodar Localmente

```bash
cd "3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
pip install -r requirements.txt
streamlit run app.py
```

O app.py detecta automaticamente qual arquivo de credenciais usar (staging ou produção) com base nos arquivos `supabase_local_teste.py` e `supabase_local.py`.

---

## Contexto do Cliente

- **Leandro Nascimento** (lmiranda.nascimento@gmail.com) — desenvolvedor, sócio 3P Finanças
- **Lucas Miranda Nascimento** — cliente, usuário final do dashboard
- Dados chegam em PDF ou Excel (extratos de corretora, planilhas de lojas)
- Objetivo futuro: área de admin no app para upload direto
- Migração planejada: Streamlit → Next.js + Vercel (mesmo Supabase) quando o projeto crescer
- Cold start do Streamlit Community Cloud (gratuito) é limitação conhecida e aceita por ora
