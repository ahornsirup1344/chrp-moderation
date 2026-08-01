# ---------- KONFIG ----------
# IDs unten am 2026-08-01 per list_ids.py aus dem Server "[456] Squid Games | Town"
# (Guild 1452809192959119455) ausgelesen und per Namensabgleich zugeordnet.

# --- [456] System's Panel ---
PANEL_CHANNEL_ID = 1530780174835126435   # #staff-directory (Kategorie "GAME STAFF")
PANEL_LOG_CHANNEL_ID = 0                 # optional: Log-Kanal fuer Panel-Nutzung, 0 = deaktiviert

# --- Welcome-Karte ---
WELCOME_CHANNEL_ID = 1452809194284777504  # #welcome (Kategorie "Entrance")

# Hierarchie von Waiter bis Frontman. "Personal"-Status wird direkt daraus
# abgeleitet: wer eine der role_id unten besitzt, darf das Panel benutzen.
#
# role_id           = Discord-Rollen-ID dieser Position
# rules_channel_id  = "<rolle>-assignments" Channel in der RULES-Kategorie
# locker_channel_id = "<rolle>-equipment" Channel in der Locker-Kategorie
#
# TODO Waiter: Rolle existiert (1530626022926717078), aber es gibt noch keine
#   waiter-assignments/waiters-equipment Channels -> Platzhalter 0.
# TODO Servant: servant-assignments (1530781723825143950) und
#   servants-equipment (1530781474507456594) existieren, aber keine passende
#   Rolle wurde gefunden -> fehlt hier komplett, role_id noch unbekannt.
HIERARCHY = [
    {"name": "Waiter",   "role_id": 1530626022926717078, "rules_channel_id": 0, "locker_channel_id": 0},
    {"name": "Worker",   "role_id": 1530625650602279012, "rules_channel_id": 1530780266140799066, "locker_channel_id": 1460067788965023806},
    {"name": "Soldier",  "role_id": 1530625013315801088, "rules_channel_id": 1530780224613257257, "locker_channel_id": 1530779500181459086},
    {"name": "Officer",  "role_id": 1530624403333841206, "rules_channel_id": 1530780782069813308, "locker_channel_id": 1530779832324198440},
    {"name": "Manager",  "role_id": 1530625488282718219, "rules_channel_id": 1530780566872653974, "locker_channel_id": 1530782572278190141},
    {"name": "Frontman", "role_id": 1530624562725785701, "rules_channel_id": 1530782194673516814, "locker_channel_id": 1530781391615164506},
]
# ---------------------------
