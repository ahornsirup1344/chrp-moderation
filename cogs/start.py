import discord
from discord.ext import commands
import asyncio
import json
import os
import traceback

IDENTIFIER = "CHRP_REGELWERK_V1"
JSON_FILE = "regelwerk_msg.json"  # speichert die Nachricht-ID


def save_message_id(msg_id: int):
    data = {"message_id": msg_id}
    with open(JSON_FILE, "w") as f:
        json.dump(data, f)


def load_message_id():
    if not os.path.exists(JSON_FILE):
        return None
    with open(JSON_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("message_id")
        except Exception:
            return None


class Components(discord.ui.LayoutView):
    container1 = discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(content=f"{IDENTIFIER}\n# <:SchweizRoleplaypng:1400144978994266143> Schweiz Roleplay Regelwerk"),
            discord.ui.TextDisplay(content="Hier findest du das Regelwerk von Schweiz Roleplay. Dieses zählt auf dem ganzen Server und ist stehts einzuhalten."),
            accessory=discord.ui.Thumbnail(
                media="https://cdn.discordapp.com/attachments/1398056839324635186/1398272703298928650/IMG_1171.png?ex=68d28aef&is=68d1396f&hm=16aa73141bae5c8c7c9daaac06e7d4db380eca4c83d3261900a16e141c390a37&",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="## 📜 Discord-Regelwerk"),
        discord.ui.TextDisplay(content="Ein qualitatives und hochwertiges Roleplay ist uns wichtig. Um dies zu gewährleisten, haben wir folgend unsere Regeln festgehalten. Wir bitten alle Mitglieder, diese einzuhalten."),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(content="### 1. Respekt & Umgang\n- Ein respektvoller und freundlicher Umgang ist pflicht.\n- Es werden keine Beleidigungen, Diskriminierungen, Provokationen und ähnliches geduldet.\n- Das Runtermachen wegen eines speziellen Dialektes (Schweizerdeutsch, Österreichisches Deutsch oder Hochdeutsch) wird hier nicht tolleriert."),
        discord.ui.TextDisplay(content="### 2. Sicherheit\n- Gebe keine persönlichen Daten an andere weiter.\n- Das weitergeben von fremden Daten ist verboten.\n- Du trägst für alles, was du postest, die Verantwortung."),
        discord.ui.TextDisplay(content="### 3. Kanäle & Voicechats\n- Nutze die passenden Kanäle für deine Nachrichten, damit alles schön geordnet bleibt.\n- Das Aufnehmen der Stimmen in Voice Chats ist während des Roleplays erlaubt.\n- Spam, das verschicken von Links, die nichts mit Schweiz Roleplay zu tun haben oder das Pingen von @everyone/@here ist nicht erlaubt."),
        discord.ui.TextDisplay(content="### 4. Unangemessene Inhalte\n- Illegale, extremistische, pronografische oder gewaltverherrlichende Inhalte sind strengstens verboten.\n- Emojis, Reaktionen oder sonstige Sachen müssen angemessenen Inhalt zeigen."),
        discord.ui.TextDisplay(content="### 5. Rechtliches\n- Die Discord ToS sind stehts einzuhalten.\n- Die Roblox ToS sind stehts einzuhalten.\n- Das Serverteam übernimmt keine Haftung für geteilte Inhalte. \n Alle Daten, die uns gegeben werden, dürfen ohne Nachfrage verwendet werden. Dies bezieht sich vorallem auf die Roleplay Bots."),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**⚠️Hinweise**\n- Mit dem Joinen des Discord-/ Roblox-Servers akzeptierst du automatisch das Regelwerk.\n- Sei dir bewusst, dass Verstösse gegen das Regelwerk mit Timeouts, Kicks oder sogar permanenten Bans bestraft werden.\n- Das Regelwerk kann zu jeder Zeit vom <@&1395167813387423795> oder vom <@&1395176653466112050> geändert werden.\n\n**Schweiz Roleplay wünscht ein schönes Roleplay!**"),
        discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://cdn.discordapp.com/attachments/1398056839324635186/1411735792585539645/Banner_Schweiz_Roleplay.png",
            ),
        ),
    )

    action_row1 = discord.ui.ActionRow(
        discord.ui.Button(
            url="https://docs.google.com/document/d/1OzWza0T1MkJYaOucr0rzORd3lAgRYmPVNxd5UnbV288/edit?usp=sharing",
            style=discord.ButtonStyle.link,
            label="Roleplay Regelwerk"
        ),
        discord.ui.Button(
            url="https://docs.google.com/document/d/1yHAMT0ren0EnFC3hK_msuQLCysDWsuUGXGIAFOYBAR0/edit?usp=sharing",
            style=discord.ButtonStyle.link,
            label="Frak Regelwerk"
        ),
    )


class HalloCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1395167052729290783  # <-- DEIN TEXT-CHANNEL
        print("✅ HalloCog geladen")

    async def cog_load(self):
        self.bot.loop.create_task(self.delayed_start())

    async def delayed_start(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)
        print("🔄 Prüfe Regelwerk-Nachricht...")
        await self.send_or_update()

    async def send_or_update(self):
        try:
            channel = await self.bot.fetch_channel(self.channel_id)
            print(f"✅ Channel gefunden: {channel.name}")
        except Exception as e:
            print(f"❌ Channel konnte nicht geladen werden: {e}")
            return

        msg_id = load_message_id()
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(view=Components())
                print(f"♻️ Regelwerk aktualisiert (message id: {msg.id})")
                return
            except discord.NotFound:
                print("Alte Nachricht wurde gelöscht, sende neue")
            except Exception as e:
                print("❗Fehler beim Aktualisieren der Nachricht:", e)
                traceback.print_exc()

        # Wenn keine Nachricht existiert oder sie gelöscht wurde → senden
        try:
            sent = await channel.send(view=Components())
            save_message_id(sent.id)
            print(f"📌 Regelwerk gesendet (message id: {sent.id})")
        except Exception as e:
            print("❗Fehler beim Senden:", e)
            traceback.print_exc()


async def setup(bot: commands.Bot):
    await bot.add_cog(HalloCog(bot))