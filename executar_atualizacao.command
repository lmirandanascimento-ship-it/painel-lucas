#!/bin/bash
cd "/Users/leandro/3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
echo "======================================================"
echo "  CARTEIRA LUCAS — Atualização Completa"
echo "======================================================"
echo ""
echo "  [1/4] Atualizando Renda Fixa..."
python3 atualiza_carteira_rf.py
echo ""
echo "  [2/4] Atualizando Renda Variável..."
python3 atualiza_carteira_rv.py
echo ""
echo "  [3/4] Gerando Dashboard..."
python3 gerar_dashboard.py
echo ""
echo "  [4/4] Enviando dados para o Supabase (painel web)..."
python3 push_to_supabase.py
echo ""
echo "======================================================"
echo "  Atualização concluída!"
echo "======================================================"
