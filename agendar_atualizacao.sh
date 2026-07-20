#!/bin/bash
# ============================================================
# Configura execução automática mensal do atualizador de RF
# Sistema: macOS (launchd)
# Frequência padrão: dia 1 de cada mês, 09h00
# ============================================================
# COMO USAR:
#   1. Abra o Terminal
#   2. cd "/Users/leandro/3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
#   3. chmod +x agendar_atualizacao.sh    (só na 1ª vez)
#   4. ./agendar_atualizacao.sh
#
# Pronto. O Mac vai rodar o script todo mês sozinho.
# Se o Mac estiver desligado/dormindo na hora, o launchd
# executa assim que acordar.
# ============================================================

set -e

PYTHON_PATH=$(which python3 || true)
SCRIPT_DIR="/Users/leandro/3P Finanças/Planejamento Lucas/CARTEIRA LUCAS"
SCRIPT_PATH="$SCRIPT_DIR/atualiza_carteira_rf.py"
PLIST_LABEL="com.leandro.atualiza-carteira-rf"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

# ---------- Validações ----------
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ python3 não encontrado no PATH. Instale o Python primeiro."
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Script não encontrado em: $SCRIPT_PATH"
    echo "   Verifique se o arquivo atualiza_carteira_rf.py está na pasta CARTEIRA LUCAS."
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

# ---------- Gera o plist ----------
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_PATH</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <!-- Roda dia 1 de cada mês às 09:00 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <!-- Se o Mac estiver dormindo, roda quando acordar -->
    <key>RunAtLoad</key>
    <false/>

    <!-- Logs para debug -->
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/.atualiza_carteira_rf.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/.atualiza_carteira_rf.err</string>
</dict>
</plist>
PLIST

# ---------- Carrega no launchd ----------
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# ---------- Confirma ----------
echo
echo "  ✅ Agendamento configurado com sucesso!"
echo
echo "  📂 Script:     $SCRIPT_PATH"
echo "  🐍 Python:     $PYTHON_PATH"
echo "  📅 Frequência: dia 1 de cada mês, 09h00"
echo "  📝 Logs:       $SCRIPT_DIR/.atualiza_carteira_rf.log"
echo "                 $SCRIPT_DIR/.atualiza_carteira_rf.err"
echo
echo "  COMANDOS ÚTEIS (cole no Terminal):"
echo
echo "  • Verificar se está agendado:"
echo "      launchctl list | grep $PLIST_LABEL"
echo
echo "  • Executar AGORA (forçar — útil para testar):"
echo "      launchctl start $PLIST_LABEL"
echo
echo "  • Ver o último log:"
echo "      cat \"$SCRIPT_DIR/.atualiza_carteira_rf.log\""
echo
echo "  • Desativar o agendamento:"
echo "      launchctl unload \"$PLIST_PATH\""
echo "      rm \"$PLIST_PATH\""
echo
echo "  • Mudar a frequência (ex.: rodar dia 15 às 18h):"
echo "      Edite \"$PLIST_PATH\" e ajuste Day/Hour/Minute,"
echo "      depois rode novamente este script."
echo
