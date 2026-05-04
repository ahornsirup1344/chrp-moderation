#!/bin/bash

SESSION="chrp-bot"
DIR="$(cd "$(dirname "$0")" && pwd)"

if screen -list | grep -q "$SESSION"; then
    echo "Session '$SESSION' läuft bereits. Nutze: screen -r $SESSION"
    exit 1
fi

cd "$DIR"

if [ ! -f ".env" ]; then
    echo "FEHLER: .env Datei fehlt! Bitte zuerst .env erstellen."
    exit 1
fi

if [ ! -d "venv" ] && [ ! -d "myenv" ]; then
    echo "Kein venv gefunden, installiere Abhängigkeiten global..."
    pip install -r requirements.txt
fi

PYTHON="python3"
if [ -d "venv" ]; then
    PYTHON="venv/bin/python"
elif [ -d "myenv" ]; then
    PYTHON="myenv/bin/python"
fi

screen -dmS "$SESSION" bash -c "cd '$DIR' && $PYTHON main.py; exec bash"
echo "Bot gestartet in Screen-Session '$SESSION'."
echo "Verbinden mit: screen -r $SESSION"
echo "Trennen mit:   Ctrl+A dann D"
