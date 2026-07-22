-- ═══════════════════════════════════════════════════════════════════════════════
-- v7: Corrige RLS de gravação em investimentos_escritorio e emprestimos
--
-- Essas duas tabelas só tinham política de SELECT para "authenticated" (a role
-- usada pelo login do app) e ALL apenas para "service_role" (que o app não usa).
-- Resultado: qualquer INSERT/UPDATE/DELETE feito pelo app nessas tabelas falha
-- com "42501 — new row violates row-level security policy".
--
-- Isso afeta: 🏢 Escritório (Lançar/Editar Mês) e 💳 Meus Empréstimos (Registrar
-- Pagamento, Editar, Excluir, Marcar como Quitado, Cadastrar Novo Empréstimo).
--
-- Rodar primeiro no banco de Teste (Lucas_Pessoal_TESTE), validar, depois em
-- Produção (Lucas_Pessoal) — produção provavelmente tem o mesmo problema.
-- ═══════════════════════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "auth_all_investimentos_escritorio" ON investimentos_escritorio;
CREATE POLICY "auth_all_investimentos_escritorio" ON investimentos_escritorio
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "auth_all_emprestimos" ON emprestimos;
CREATE POLICY "auth_all_emprestimos" ON emprestimos
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── Verificar ────────────────────────────────────────────────────────────────
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename IN ('investimentos_escritorio', 'emprestimos')
ORDER BY tablename, policyname;
