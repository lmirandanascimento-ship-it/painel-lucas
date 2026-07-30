-- ═══════════════════════════════════════════════════════════════════════════════
-- v8: Tabela renda_fixa_compras — data de aplicação e taxa contratada por título
--
-- Guarda o dado que falta pro app calcular rentabilidade líquida de verdade pra
-- Tesouro Direto (IR regressivo + custódia B3) e trazer a valor presente CDB e
-- CRI/CRA. "nome" casa por texto com o campo "nome" das posições no snapshot
-- (carteira_snapshots, tipo "RF") — sem formulário no app por enquanto, populada
-- manualmente via script.
--
-- Rodar primeiro no banco de Teste (Lucas_Pessoal_TESTE), validar, depois em
-- Produção (Lucas_Pessoal).
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS renda_fixa_compras (
    id                 SERIAL PRIMARY KEY,
    nome               TEXT NOT NULL,
    classe             TEXT NOT NULL,
    data_aplicacao     DATE NOT NULL,
    taxa_contratada_aa NUMERIC(8,6),
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE renda_fixa_compras ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_all_renda_fixa_compras" ON renda_fixa_compras;
CREATE POLICY "auth_all_renda_fixa_compras" ON renda_fixa_compras
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── Verificar ────────────────────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables WHERE table_name = 'renda_fixa_compras';
