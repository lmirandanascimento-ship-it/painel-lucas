-- ============================================================
-- SETUP SUPABASE v2 — Carteira Lucas (novas tabelas)
-- Cole e execute no SQL Editor do Supabase
-- ============================================================

-- ── Snapshots completos (RV e RF em JSONB) ───────────────────
CREATE TABLE IF NOT EXISTS carteira_snapshots (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    data            DATE        NOT NULL,
    tipo            VARCHAR(5)  NOT NULL,          -- 'RV' ou 'RF'
    dados           JSONB       NOT NULL,
    usd_brl         DECIMAL(10,4),
    total_investido DECIMAL(15,2),
    total_atual     DECIMAL(15,2),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(data, tipo)
);

-- ── Posições RV (para cotações ao vivo no Streamlit) ─────────
CREATE TABLE IF NOT EXISTS carteira_rv_posicoes (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    data_snapshot       DATE        NOT NULL,
    classe              VARCHAR(50) NOT NULL,
    ticker              VARCHAR(20) NOT NULL,
    nome                VARCHAR(100),
    setor               VARCHAR(100),
    qtd                 DECIMAL(15,4)  DEFAULT 0,
    preco_pago          DECIMAL(15,6)  DEFAULT 0,
    moeda               VARCHAR(5)     DEFAULT 'BRL',
    valor_investido_brl DECIMAL(15,2)  DEFAULT 0,
    created_at          TIMESTAMPTZ    DEFAULT NOW()
);

-- ── Histórico consolidado ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS carteira_historico (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    data            DATE        NOT NULL UNIQUE,
    total_atual     DECIMAL(15,2),
    total_investido DECIMAL(15,2),
    total_ganho     DECIMAL(15,2),
    total_rentab    DECIMAL(10,6),
    rv_atual        DECIMAL(15,2),
    rf_atual        DECIMAL(15,2),
    nacional        DECIMAL(15,2),
    internacional   DECIMAL(15,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── RLS ──────────────────────────────────────────────────────
ALTER TABLE carteira_snapshots   ENABLE ROW LEVEL SECURITY;
ALTER TABLE carteira_rv_posicoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE carteira_historico   ENABLE ROW LEVEL SECURITY;

-- Leitura: qualquer usuário autenticado
CREATE POLICY "leitura_snaps"   ON carteira_snapshots   FOR SELECT TO authenticated USING (true);
CREATE POLICY "leitura_rv_pos"  ON carteira_rv_posicoes FOR SELECT TO authenticated USING (true);
CREATE POLICY "leitura_hist"    ON carteira_historico   FOR SELECT TO authenticated USING (true);

-- Escrita: usuários autenticados (o script local autentica com email/senha)
CREATE POLICY "escrita_snaps"   ON carteira_snapshots   FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "escrita_rv_pos"  ON carteira_rv_posicoes FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "escrita_hist"    ON carteira_historico   FOR ALL TO authenticated USING (true) WITH CHECK (true);
