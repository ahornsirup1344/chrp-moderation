# [456] System's – Deployment Notes

Standalone Discord bot in this folder. Only feature so far: a dropdown panel
with two options (**Aufgaben & Regeln**, **Locker**) that redirects each
staff member to the channel pair matching their rank in the hierarchy
(Waiter through Frontman).

## 1. Create the Discord application

1. Go to the Discord Developer Portal and create a new application.
2. Set the bot's username to **`[456] System's`**.
3. Under "Bot", enable the following Privileged Gateway Intents:
   - `SERVER MEMBERS INTENT`
   - `MESSAGE CONTENT INTENT`
4. Copy the bot token.
5. Invite the bot to the server: https://discord.gg/GVkxKw64Qg
   (OAuth2 URL Generator → scopes `bot` + `applications.commands`,
   permissions: `View Channels`, `Send Messages`, `Embed Links`).

## 2. Set up the environment

```bash
cd Jonas
./start.sh
```

`start.sh` will ask for `DISCORD_BOT_TOKEN` and create `.env` on first run.

## 3. Fill in the real Discord IDs (TODO — pending)

Once the bot has joined the server, enable Developer Mode in Discord
(User Settings → Advanced) and right-click to "Copy ID" for each of the
following. Then edit `Jonas/settings/config.py` and replace the `0`
placeholders:

| Constant                | What to put there                                                |
|--------------------------|------------------------------------------------------------------|
| `PANEL_CHANNEL_ID`      | Channel where the `!456panel` dropdown message should be posted  |
| `PANEL_LOG_CHANNEL_ID`  | Optional: channel to log who used the panel. Leave `0` to disable |
| `HIERARCHY[i]["role_id"]` | Discord role ID for that rank (Waiter, ..., Officer, Manager, Frontman) |
| `HIERARCHY[i]["rules_channel_id"]` | That rank's `<rank>-assignments` channel in the duties/rules category |
| `HIERARCHY[i]["locker_channel_id"]` | That rank's `<rank>-assignments` channel in the locker (uniform/weapons) category |

"Personnel" isn't a separate role — anyone holding one of the `role_id`
values in `HIERARCHY` is automatically allowed to use the panel, and gets
routed to the channel pair for their own rank. Add more ranks by appending
another row to `HIERARCHY` in `settings/config.py`, no code change needed.

## 4. Panel auto-refresh

Once `PANEL_CHANNEL_ID` is set, the bot posts the panel automatically on
every startup — no manual command needed. On each start it:

1. Looks up the last sent panel message (saved in `Jonas/cogs/panel_456.json`).
2. If found, edits it in place (embed + dropdown refreshed).
3. If it was deleted, searches the channel history for an existing bot
   panel message and refreshes that instead.
4. Otherwise sends a brand-new panel message and saves its ID.

The dropdown itself is a persistent component (`custom_id`-based), so it
keeps working across restarts without needing to be resent.

If you ever want to force a fresh panel message manually (e.g. to move it
to the bottom of the channel), run `!456panel` (requires Administrator
permission) — it sends a new message and updates the saved reference.
