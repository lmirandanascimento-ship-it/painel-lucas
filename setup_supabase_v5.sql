-- ═══════════════════════════════════════════════════════════════════════════════
-- v5: Pagamento somente de juros (não abate o saldo devedor)
-- Rodar no SQL Editor do Supabase — primeiro no banco de Teste (Lucas_Pessoal_TESTE),
-- validar no app, depois no banco de Produção (Lucas_Pessoal).
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE pagamentos_recebidos
    ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'amortizacao';

ALTER TABLE pagamentos_recebidos
    DROP CONSTRAINT IF EXISTS pagamentos_recebidos_tipo_check;
ALTER TABLE pagamentos_recebidos
    ADD CONSTRAINT pagamentos_recebidos_tipo_check CHECK (tipo IN ('amortizacao', 'juros'));

-- ── Verificar ────────────────────────────────────────────────────────────────
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pagamentos_recebidos' AND column_name = 'tipo';
