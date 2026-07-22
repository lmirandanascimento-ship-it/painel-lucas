-- ═══════════════════════════════════════════════════════════════════════════════
-- LIMPEZA DE DADOS DE EMPRÉSTIMOS — BANCO DE TESTE (Lucas_Pessoal_TESTE)
--
-- ⚠️  RODAR SOMENTE NO PROJETO Lucas_Pessoal_TESTE. NÃO usar no banco de Produção
--     (Lucas_Pessoal) sem revisão específica — os dados de produção são reais.
--
-- Apaga todos os registros de:
--   - devedores               (cadastro de quem toma empréstimo do Lucas)
--   - emprestimos_concedidos  (contratos — apagado em cascata via devedor_id)
--   - pagamentos_recebidos    (pagamentos — apagado em cascata via emprestimo_id)
--   - emprestimos             ("Meus Empréstimos": dívidas que o Lucas tomou de terceiros)
--
-- NÃO afeta: carteira_snapshots, carteira_rv_posicoes, carteira_historico,
--            investimentos_escritorio (dados de investimentos, intocados).
-- ═══════════════════════════════════════════════════════════════════════════════

TRUNCATE TABLE devedores RESTART IDENTITY CASCADE;
-- CASCADE também limpa emprestimos_concedidos e pagamentos_recebidos
-- (FKs devedor_id e emprestimo_id têm ON DELETE CASCADE)

TRUNCATE TABLE emprestimos RESTART IDENTITY CASCADE;
-- "Meus Empréstimos" — tabela independente, sem relação com devedores

-- ── Verificar que ficou tudo zerado ───────────────────────────────────────────
SELECT 'devedores' AS tabela, COUNT(*) FROM devedores
UNION ALL
SELECT 'emprestimos_concedidos', COUNT(*) FROM emprestimos_concedidos
UNION ALL
SELECT 'pagamentos_recebidos', COUNT(*) FROM pagamentos_recebidos
UNION ALL
SELECT 'emprestimos', COUNT(*) FROM emprestimos;
