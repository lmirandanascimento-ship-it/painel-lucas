-- ═══════════════════════════════════════════════════════════════════════════════
-- setup_supabase_v3.sql
-- Tabelas para gestão de Empréstimos Concedidos pelo Lucas
-- Rodar no Supabase → SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── 1. Devedores ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS devedores (
    id          SERIAL PRIMARY KEY,
    nome        TEXT NOT NULL,
    categoria   TEXT,
    contato     TEXT,
    ativo       BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE devedores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_all_devedores" ON devedores;
CREATE POLICY "auth_all_devedores" ON devedores
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── 2. Empréstimos Concedidos ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emprestimos_concedidos (
    id               SERIAL PRIMARY KEY,
    devedor_id       INTEGER REFERENCES devedores(id) ON DELETE CASCADE,
    titulo           TEXT NOT NULL,
    data_emprestimo  DATE,
    valor_original   NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldo_devedor    NUMERIC(12,2) NOT NULL DEFAULT 0,
    taxa_juros       NUMERIC(8,6)  DEFAULT 0,
    parcela_juros    NUMERIC(12,2) DEFAULT 0,
    recorrencia      TEXT          DEFAULT 'Mensal',
    dia_vencimento   INTEGER,
    status           TEXT          DEFAULT 'ativo',
    observacao       TEXT,
    created_at       TIMESTAMPTZ   DEFAULT NOW()
);

ALTER TABLE emprestimos_concedidos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_all_emp_concedidos" ON emprestimos_concedidos;
CREATE POLICY "auth_all_emp_concedidos" ON emprestimos_concedidos
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── 3. Pagamentos Recebidos ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pagamentos_recebidos (
    id              SERIAL PRIMARY KEY,
    emprestimo_id   INTEGER REFERENCES emprestimos_concedidos(id) ON DELETE CASCADE,
    data_pagamento  DATE          NOT NULL,
    valor_pago      NUMERIC(12,2) NOT NULL,
    juros           NUMERIC(12,2) DEFAULT 0,
    amortizacao     NUMERIC(12,2) DEFAULT 0,
    saldo_antes     NUMERIC(12,2),
    saldo_depois    NUMERIC(12,2),
    observacao      TEXT,
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);

ALTER TABLE pagamentos_recebidos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_all_pagamentos" ON pagamentos_recebidos;
CREATE POLICY "auth_all_pagamentos" ON pagamentos_recebidos
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── 4. Coluna histórico na tabela de empréstimos tomados (se não existir) ─────
ALTER TABLE emprestimos
    ADD COLUMN IF NOT EXISTS historico_pagamentos JSONB DEFAULT '[]';

-- ═══════════════════════════════════════════════════════════════════════════════
-- Verificar criação
-- ═══════════════════════════════════════════════════════════════════════════════
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('devedores','emprestimos_concedidos','pagamentos_recebidos','emprestimos')
ORDER BY table_name;
