# [456] System's – Deployment Notes

Standalone Discord bot in this folder. Only feature so far: a dropdown panel
with two options (**Armory**, **Read me**) that redirects a specific
personnel role to the correct channel.

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

| Constant              | What to put there                                              |
|-----------------------|------------------------------------------------------------------|
| `PANEL_CHANNEL_ID`    | Channel where the `!456panel` dropdown message should be posted |
| `PERSONNEL_ROLE_ID`   | Role allowed to use the dropdown ("bestimmtes Personal")        |
| `ARMORY_CHANNEL_ID`   | Channel with uniform & weapons info (Armory)                    |
| `READ_ME_CHANNEL_ID`  | Channel with chain of command / duties & rules (Read me)        |
| `PANEL_LOG_CHANNEL_ID`| Optional: channel to log who used the panel. Leave `0` to disable |

## 4. Send the panel

In the panel channel (or any channel, if `PANEL_CHANNEL_ID` is set), run:

```
!456panel
```

(Requires Administrator permission. The panel is a persistent component,
so it keeps working after bot restarts without needing to be re-sent.)
