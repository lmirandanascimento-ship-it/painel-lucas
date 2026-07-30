-- ═══════════════════════════════════════════════════════════════════════════════
-- v9: Coluna juros_sobre_saldo em emprestimos_concedidos
--
-- Modo de cálculo alternativo pro pagamento tipo "amortizacao": em vez de
-- amortização pura (100% do valor pago abate o saldo), deduz juros = taxa_juros
-- × saldo devedor atual, e só o restante abate o saldo. Usado no contrato
-- "CC Sr. Carmino" (0,6% a.m. sobre o saldo) — os demais contratos continuam
-- com amortização pura (default false).
--
-- Rodar primeiro no banco de Teste (Lucas_Pessoal_TESTE), validar, depois em
-- Produção (Lucas_Pessoal).
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE emprestimos_concedidos
    ADD COLUMN IF NOT EXISTS juros_sobre_saldo BOOLEAN NOT NULL DEFAULT false;

UPDATE emprestimos_concedidos SET juros_sobre_saldo = true
WHERE titulo = 'CC Sr. Carmino';

-- ── Verificar ────────────────────────────────────────────────────────────────
SELECT id, titulo, taxa_juros, juros_sobre_saldo FROM emprestimos_concedidos
WHERE juros_sobre_saldo = true;
