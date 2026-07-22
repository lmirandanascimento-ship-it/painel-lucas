-- ═══════════════════════════════════════════════════════════════════════════════
-- v6: Constraint UNIQUE em investimentos_escritorio.mes
-- Necessária para o upsert(..., on_conflict="mes") do "Lançar Novo Mês" funcionar
-- (sem isso, o Postgres não sabe identificar o que é "conflito" e retorna 42P10).
-- Rodar primeiro no banco de Teste (Lucas_Pessoal_TESTE), validar, depois em Produção.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── Verificar antes: não deve retornar nenhuma linha (mês duplicado) ──────────
SELECT mes, COUNT(*) FROM investimentos_escritorio GROUP BY mes HAVING COUNT(*) > 1;

-- Se a verificação acima veio vazia, siga com a constraint:
ALTER TABLE investimentos_escritorio
    ADD CONSTRAINT investimentos_escritorio_mes_key UNIQUE (mes);

-- ── Verificar depois ───────────────────────────────────────────────────────────
SELECT conname FROM pg_constraint
WHERE conrelid = 'investimentos_escritorio'::regclass AND contype = 'u';
