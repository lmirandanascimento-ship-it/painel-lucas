-- ============================================================
-- PASSO 1 — CRIAR AS TABELAS
-- Cole e execute no SQL Editor do Supabase
-- ============================================================

-- Extensão para gerar UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Tabela: Investimentos do Escritório ─────────────────────
CREATE TABLE IF NOT EXISTS investimentos_escritorio (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    mes           DATE        NOT NULL,
    tipo          VARCHAR(30) NOT NULL,          -- 'Saldo Inicial', 'Aporte', 'Retirada'
    valor         DECIMAL(15,2) DEFAULT 0,       -- valor do aporte/retirada
    saldo_anterior DECIMAL(15,2) DEFAULT 0,
    rendimento    DECIMAL(15,2) DEFAULT 0,
    saldo_final   DECIMAL(15,2) DEFAULT 0,
    taxa_mensal   DECIMAL(6,4)  DEFAULT 0.01,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tabela: Empréstimos ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS emprestimos (
    id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    credor           VARCHAR(100) NOT NULL,
    titulo           VARCHAR(150) NOT NULL,
    data_emprestimo  DATE,
    valor_originario DECIMAL(15,2) NOT NULL,
    saldo_devedor    DECIMAL(15,2) NOT NULL,
    taxa_juros       DECIMAL(8,6)  NOT NULL,    -- mensal, ex: 0.02 = 2% a.m.
    parcela_juros    DECIMAL(15,2) DEFAULT 0,
    recorrencia      VARCHAR(50),
    status           VARCHAR(20)  DEFAULT 'ativo',  -- 'ativo' ou 'quitado'
    observacao       TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Segurança RLS (Row Level Security) ─────────────────────
ALTER TABLE investimentos_escritorio ENABLE ROW LEVEL SECURITY;
ALTER TABLE emprestimos              ENABLE ROW LEVEL SECURITY;

-- Usuários autenticados podem LER os dados
CREATE POLICY "leitura_autenticada_inv" ON investimentos_escritorio
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "leitura_autenticada_emp" ON emprestimos
    FOR SELECT TO authenticated USING (true);

-- Admin (service role) pode tudo — necessário para inserir dados abaixo
CREATE POLICY "admin_all_inv" ON investimentos_escritorio
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "admin_all_emp" ON emprestimos
    FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ============================================================
-- PASSO 2 — INSERIR OS DADOS INICIAIS
-- (execute logo após o Passo 1)
-- ============================================================

-- Investimentos do Escritório (fev-jun/2026)
INSERT INTO investimentos_escritorio
    (mes, tipo, valor, saldo_anterior, rendimento, saldo_final, taxa_mensal)
VALUES
    ('2026-02-01', 'Saldo Inicial',   0.00,      0.00,       0.00,     159772.76, 0.0100),
    ('2026-03-01', 'Aporte',      42190.50,  159772.76,   1597.73,   203561.00, 0.0100),
    ('2026-04-01', 'Aporte',      35000.00,  203561.00,   2035.61,   240596.61, 0.0100),
    ('2026-05-01', 'Aporte',      29900.00,  240596.61,   2405.97,   272902.58, 0.0100),
    ('2026-06-01', 'Aporte',      26605.00,  272902.58,   2729.03,   302236.60, 0.0100);


-- Empréstimos ativos (posição jun/2026)
INSERT INTO emprestimos
    (credor, titulo, data_emprestimo, valor_originario, saldo_devedor, taxa_juros, parcela_juros, recorrencia, status)
VALUES
-- ── Sr. Carmino ──────────────────────────────────────────────────────────
    ('Sr. Carmino',    'CC Sr. Carmino',           '2022-09-23', 120734.14,  91316.06, 0.006000, 547.90,  'Mensal', 'ativo'),

-- ── Nomã ─────────────────────────────────────────────────────────────────
    ('Nomã',           'Emp. 12',                  '2025-04-16', 100000.00,  94438.20, 0.011325, 1133.26, 'Mensal', 'ativo'),
    ('Nomã',           'Emp. Nomã Terraço',        '2026-06-05',   2000.00,   2000.00, 0.012000,   24.00, 'Mensal', 'ativo'),

-- ── iClothes / Quadra ────────────────────────────────────────────────────
    ('iClothes/Quadra','Emp. Quadra 1',            NULL,          30000.00,  22845.00, 0.020000,  456.90, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 2',            '2024-03-15',  40000.00,  40000.00, 0.020000,  800.00, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 3',            '2024-03-22',  22435.00,  22435.00, 0.020000,  448.70, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 4',            '2024-04-18',  30000.00,  20980.00, 0.020000,  419.60, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 5',            '2024-04-24',  20000.00,  20000.00, 0.020000,  400.00, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 7',            '2024-06-06',  10000.00,  10000.00, 0.020000,  200.00, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 9',            '2024-09-05',  40000.00,  40000.00, 0.020000,  800.00, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. Quadra 10',           '2024-09-12',  40000.00,  40000.00, 0.020000,  800.00, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. iClothes 1',          NULL,          28265.57,  28265.57, 0.018000,  508.78, 'Mensal', 'ativo'),
    ('iClothes/Quadra','Emp. iClothes 2',          '2023-03-08',  30000.00,  28210.00, 0.020000,  564.20, 'Mensal', 'ativo');
