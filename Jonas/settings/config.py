# ---------- KONFIG ----------
# WICHTIG: Alle IDs unten sind Platzhalter (0) und muessen nach dem Deployen
# ersetzt werden. Siehe DEPLOYMENT.md im Jonas-Ordner fuer eine Anleitung.

# --- [456] System's Panel ---
PANEL_CHANNEL_ID = 0     # Kanal, in dem das Dropdown-Panel gepostet wird
PANEL_LOG_CHANNEL_ID = 0 # optional: Log-Kanal fuer Panel-Nutzung, 0 = deaktiviert

# Hierarchie von Waiter bis Frontman. "Personal"-Status wird direkt daraus
# abgeleitet: wer eine der role_id unten besitzt, darf das Panel benutzen.
#
# role_id           = Discord-Rollen-ID dieser Position
# rules_channel_id  = "<rolle>-assignments" Channel in der Aufgaben&Regeln-Kategorie
# locker_channel_id = "<rolle>-assignments" Channel in der Locker-Kategorie (Uniform & Waffen)
#
# Weitere Stufen (z.B. Waiter, Soldier) einfach als weitere Zeile ergaenzen,
# gleiches Muster.
HIERARCHY = [
    {"name": "Officer",  "role_id": 0, "rules_channel_id": 0, "locker_channel_id": 0},
    {"name": "Manager",  "role_id": 0, "rules_channel_id": 0, "locker_channel_id": 0},
    {"name": "Frontman", "role_id": 0, "rules_channel_id": 0, "locker_channel_id": 0},
]
# ---------------------------
