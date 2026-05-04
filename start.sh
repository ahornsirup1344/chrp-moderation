#!/bin/bash

SESSION="chrp-bot"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# .env erstellen falls nicht vorhanden
if [ ! -f ".env" ]; then
    echo "=== .env Setup ==="
    read -rp "DISCORD_BOT_TOKEN: " V1
    read -rp "ERLC_SERVER_KEY: " V2
    read -rp "SUPABASE_URL: " V3
    read -rp "SUPABASE_KEY: " V4
    read -rp "VERIFICATION_CHANNEL_ID: " V5
    read -rp "ADD_ROLE_IDS: " V6
    read -rp "REMOVE_ROLE_IDS: " V7
    read -rp "CODE_TTL_SECONDS (Standard: 600): " V8
    V8=${V8:-600}
    read -rp "VERIFY_LOG_CHANNEL_ID: " V9

    cat > .env <<EOF
DISCORD_BOT_TOKEN=$V1
ERLC_SERVER_KEY=$V2
SUPABASE_URL=$V3
SUPABASE_KEY=$V4
VERIFICATION_CHANNEL_ID=$V5
ADD_ROLE_IDS=$V6
REMOVE_ROLE_IDS=$V7
CODE_TTL_SECONDS=$V8
VERIFY_LOG_CHANNEL_ID=$V9
EOF
    echo ".env wurde erstellt."
fi

# venv erstellen falls nicht vorhanden
if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

# Requirements installieren
echo "Installiere Requirements..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "Requirements installiert."

# Screen-Session prüfen
if screen -list | grep -q "$SESSION"; then
    if [ "$STY" = "${SESSION}" ] || echo "$STY" | grep -q "$SESSION"; then
        echo "Du bist bereits in der Session '$SESSION'."
        exit 0
    fi
    echo "Session '$SESSION' läuft bereits — wird neu gestartet..."
    screen -X -S "$SESSION" quit
    sleep 1
fi

screen -dmS "$SESSION" bash -c "cd '$DIR' && venv/bin/python main.py; exec bash"
echo ""
echo "Bot gestartet in Screen-Session '$SESSION'."
echo "Verbinden mit: screen -r $SESSION"
echo "Trennen mit:   Ctrl+A dann D"
