-- ═══════════════════════════════════════════════════════════════════════════════
-- setup_supabase_v4.sql
-- Documentos anexados (PDF/CSV/XLSX) aos devedores de Empréstimos Concedidos
-- Rodar no Supabase → SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── 1. Metadados dos arquivos ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documentos_emprestimos (
    id             SERIAL PRIMARY KEY,
    devedor_id     INTEGER REFERENCES devedores(id) ON DELETE CASCADE,
    emprestimo_id  INTEGER REFERENCES emprestimos_concedidos(id) ON DELETE SET NULL,
    nome_arquivo   TEXT NOT NULL,
    storage_path   TEXT NOT NULL,
    tipo_arquivo   TEXT,
    tamanho_bytes  BIGINT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE documentos_emprestimos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_all_documentos_emprestimos" ON documentos_emprestimos;
CREATE POLICY "auth_all_documentos_emprestimos" ON documentos_emprestimos
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ── 2. Bucket de storage (privado — acesso via signed URL) ───────────────────
INSERT INTO storage.buckets (id, name, public)
VALUES ('documentos-emprestimos', 'documentos-emprestimos', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "auth_all_documentos_emprestimos_storage" ON storage.objects;
CREATE POLICY "auth_all_documentos_emprestimos_storage" ON storage.objects
    FOR ALL TO authenticated
    USING (bucket_id = 'documentos-emprestimos')
    WITH CHECK (bucket_id = 'documentos-emprestimos');

-- ═══════════════════════════════════════════════════════════════════════════════
-- Verificar criação
-- ═══════════════════════════════════════════════════════════════════════════════
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'documentos_emprestimos';

SELECT id, name, public FROM storage.buckets
WHERE id = 'documentos-emprestimos';
