#!/bin/bash

SESSION="chrp-bot"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# .env erstellen falls nicht vorhanden
if [ ! -f ".env" ]; then
    echo "Kein .env gefunden. Bitte Discord Bot Token eingeben:"
    read -rp "DISCORD_BOT_TOKEN: " TOKEN
    echo "DISCORD_BOT_TOKEN=$TOKEN" > .env
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
    echo "Session '$SESSION' läuft bereits. Nutze: screen -r $SESSION"
    exit 1
fi

screen -dmS "$SESSION" bash -c "cd '$DIR' && venv/bin/python main.py; exec bash"
echo ""
echo "Bot gestartet in Screen-Session '$SESSION'."
echo "Verbinden mit: screen -r $SESSION"
echo "Trennen mit:   Ctrl+A dann D"
