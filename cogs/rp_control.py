import discord
from discord.ext import commands
import traceback
import json
from pathlib import Path
from typing import Optional

from settings.config import CHANNEL_ID, TARGET_CHANNEL_ID, ROLE_ID, STATUS_CHANNEL_ID

PERSIST_FILE = Path(__file__).parent / "rp_panel.json"
CONFIG_FILE = Path("welcome_config.json")
PANEL_TITLE = "RP Steuerung"

#---------------------------------------------------------------------

def load_persist() -> dict:
    try:
        if PERSIST_FILE.exists():
            with PERSIST_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        traceback.print_exc()
    return {}


def save_persist(data: dict) -> None:
    try:
        with PERSIST_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        traceback.print_exc()

# ---------------------------
# timer
# ---------------------------
async def handle_rate_limit(channel: discord.abc.Messageable, error: discord.HTTPException):
    if error.status == 429:
        wait_seconds = getattr(error, "retry_after", 300)
        minutes, seconds = divmod(int(wait_seconds), 60)
        await channel.send(f"⏳ Rate Limit aktiv – bitte noch **{minutes}m {seconds}s** warten.")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=wait_seconds))

# ---------------------------
# Logger
# ---------------------------
async def log_action(interaction: discord.Interaction, action: str, success: bool = True, extra: str = ""):
    try:
        if not CONFIG_FILE.exists():
            print("[RPControl] Keine Config-Datei gefunden, Logs nicht möglich.")
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                cfgs = json.load(f)
            except json.JSONDecodeError:
                print("[RPControl] Config JSON fehlerhaft – Logs nicht möglich.")
                return

        guild_id = str(interaction.guild.id)
        log_channel_id = cfgs.get(guild_id, {}).get("rp_control_logs_id")

        if not log_channel_id:
            print(f"[RPControl] Kein Log-Channel für Guild {guild_id} definiert.")
            return

        log_channel = interaction.guild.get_channel(int(log_channel_id))
        if not log_channel:
            print(f"[RPControl] Log-Channel mit ID {log_channel_id} nicht gefunden.")
            return

        embed = discord.Embed(
            title="📋 RP Control Log",
            description=f"Aktion: **{action}**",
            color=discord.Color.green() if success else discord.Color.red()
        )
        embed.add_field(name="User", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        embed.add_field(name="Guild", value=f"{interaction.guild.name} ({interaction.guild.id})", inline=False)
        if extra:
            embed.add_field(name="Details", value=extra, inline=False)

        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    except Exception:
        print("[RPControl] Fehler beim Senden eines Logs:")
        traceback.print_exc()

# ---------------------------
# Hallo-Embed
# ---------------------------
class Components(discord.ui.LayoutView):
    text_display1 = discord.ui.TextDisplay(content="<@&1420492306280353823>")

    container1 = discord.ui.Container(
        discord.ui.TextDisplay(content="# Roleplay Start  <:SchweizRoleplaypng:1400144978994266143>"),
        discord.ui.TextDisplay(content="Das **CH:RP Team** eröffnet somit das Roleplay für euch!\nDer Ingame Server ist nun online.\nUnser kompetentes Team wird euch jetzt zur Seite stehen.\nMit **!mod** könnt ihr Hilfe beantragen."),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**ER:LC Server-Name:** `Schweiz Roleplay I V1 | German I DC only`\n**Code:** `schweizrp`"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**CH:RP wünscht euch ein schönes und spannendes Roleplay!**"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://cdn.discordapp.com/attachments/1398056839324635186/1416468090597806220/RP_START.png",
            ),
        ),
    )

# ---------------------------
# Tschau-Embed
# ---------------------------
class ComponentsClosed(discord.ui.LayoutView):
    text_display1 = discord.ui.TextDisplay(content="<@&1420492306280353823>")

    container1 = discord.ui.Container(
        discord.ui.TextDisplay(content="# Roleplay Ende  <:SchweizRoleplaypng:1400144978994266143>"),
        discord.ui.TextDisplay(content="Das **CH:RP Team** beendet somit das Roleplay für euch!\nDer Ingame Server ist nun geschlossen und wird nicht mehr betreut.\nWir bedanken uns bei allen Teilnehmern. \nBitte beendet euer Roleplay und verlasst danach unseren Server."),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**Der Server wird morgen wieder für euch geöffnet sein.**"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**CH:RP wünscht euch einen schönen Abend!**"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://cdn.discordapp.com/attachments/1398056839324635186/1416468050630410362/RP_STOP.png",
            ),
        ),
    )


class RPControlView(discord.ui.View):
    def __init__(self, cog: "RPControl"):
        super().__init__(timeout=None)
        self.cog = cog

    def get_status_embed(self) -> discord.Embed:
        status = "✅ Offen" if self.cog.is_open else "❌ Geschlossen"
        desc = f"Aktueller Status: **{status}**"
        return discord.Embed(
            title=PANEL_TITLE,
            description=desc,
            color=discord.Color.blue()
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            if interaction.guild is None:
                await interaction.response.send_message("Dieser Button funktioniert nur auf dem Server.", ephemeral=True)
                return False
            user_roles = getattr(interaction.user, "roles", [])
            if not any(r.id == ROLE_ID for r in user_roles):
                await interaction.response.send_message("❌ Du hast keine Berechtigung, diesen Button zu benutzen!", ephemeral=True)
                return False
            return True
        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("Fehler bei der Berechtigungsprüfung.", ephemeral=True)
            except Exception:
                pass
            return False

    @discord.ui.button(label="RP öffnen", style=discord.ButtonStyle.success, custom_id="rp_open_v1")
    async def open_rp(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.cog.is_open:
                await interaction.response.send_message("⚠️ RP ist bereits offen!", ephemeral=True)
                return

            self.cog.is_open = True
            await interaction.response.edit_message(embed=self.get_status_embed(), view=self)

            status_channel = interaction.guild.get_channel(STATUS_CHANNEL_ID)
            if status_channel:
                try:
                    if status_channel.name != "𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🟢":
                        await status_channel.edit(name="𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🟢")
                        await log_action(interaction, "Status-Channel geändert", extra="🟢 Offen")
                except discord.HTTPException as e:
                    await handle_rate_limit(interaction.channel, e)
                except Exception:
                    traceback.print_exc()
                    await log_action(interaction, "Fehler beim Status-Channel ändern", success=False)

            channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
            if channel:
                try:
                    file = discord.File("Banner Schweiz Roleplay.png", filename="Banner Schweiz Roleplay.png")
                    await channel.send(view=Components(), file=file)
                    await log_action(interaction, "Startnachricht gesendet")
                except Exception:
                    traceback.print_exc()
                    await log_action(interaction, "Fehler beim Senden der Startnachricht", success=False)

            await log_action(interaction, "RP geöffnet")

        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("Fehler beim Öffnen (siehe Konsole).", ephemeral=True)
            except Exception:
                pass
            await log_action(interaction, "RP öffnen fehlgeschlagen", success=False)

    @discord.ui.button(label="RP schließen", style=discord.ButtonStyle.danger, custom_id="rp_close_v1")
    async def close_rp(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self.cog.is_open:
                await interaction.response.send_message("⚠️ RP ist bereits geschlossen!", ephemeral=True)
                return

            self.cog.is_open = False
            await interaction.response.edit_message(embed=self.get_status_embed(), view=self)

            status_channel = interaction.guild.get_channel(STATUS_CHANNEL_ID)
            if status_channel:
                try:
                    if status_channel.name != "𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🔴":
                        await status_channel.edit(name="𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🔴")
                        await log_action(interaction, "Status-Channel geändert", extra="🔴 Geschlossen")
                except discord.HTTPException as e:
                    await handle_rate_limit(interaction.channel, e)
                except Exception:
                    traceback.print_exc()
                    await log_action(interaction, "Fehler beim Status-Channel ändern", success=False)

            channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
            if channel:
                try:
                    file = discord.File("Banner Schweiz Roleplay.png", filename="Banner Schweiz Roleplay.png")
                    await channel.send(view=ComponentsClosed(), file=file)
                    await log_action(interaction, "Stopnachricht gesendet")
                except Exception:
                    traceback.print_exc()
                    await log_action(interaction, "Fehler beim Senden der Stopnachricht", success=False)

            await log_action(interaction, "RP geschlossen")

        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("Fehler beim Schließen (siehe Konsole).", ephemeral=True)
            except Exception:
                pass
            await log_action(interaction, "RP schließen fehlgeschlagen", success=False)


class RPControl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_open: bool = False
        self.view = RPControlView(self)

    async def cog_load(self):
        try:
            self.bot.add_view(self.view)
        except Exception:
            print("[RPControl] Fehler beim Registrieren der persistent View:")
            traceback.print_exc()

        try:
            self.bot.loop.create_task(self._ensure_panel_task())
        except Exception:
            print("[RPControl] Fehler beim Starten des Ensure-Panel-Tasks:")
            traceback.print_exc()

    async def _ensure_panel_task(self):
        await self.bot.wait_until_ready()

        try:
            status_channel = self.bot.get_channel(STATUS_CHANNEL_ID)
            if status_channel and status_channel.name != "𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🔴":
                await status_channel.edit(name="𝗥𝗼𝗹𝗲𝗽𝗹𝗮𝘆 𝗦𝘁𝗮𝘁𝘂𝘀: 🔴")
        except Exception:
            traceback.print_exc()

        try:
            channel = self.bot.get_channel(CHANNEL_ID)
            if channel is None:
                print(f"[RPControl] Kanal mit ID {CHANNEL_ID} nicht gefunden. Prüfe die ID und ob der Bot auf dem Guild ist.")
                return

            data = load_persist()
            saved_message_id: Optional[int] = data.get("message_id")

            if saved_message_id:
                try:
                    msg = await channel.fetch_message(saved_message_id)
                    if msg and msg.author == self.bot.user:
                        await msg.edit(embed=self.view.get_status_embed(), view=self.view)
                        print("[RPControl] Panel via gespeicherter message_id gefunden und aktualisiert.")
                        return
                    else:
                        print("[RPControl] Gespeicherte message_id gehört nicht dem Bot oder Nachricht fehlt.")
                except discord.NotFound:
                    print("[RPControl] Gespeicherte message_id nicht gefunden (gelöscht).")
                except discord.Forbidden:
                    print("[RPControl] Erlaubnisfehler: Keine Rechte, gespeicherte Nachricht zu holen/editieren.")
                except Exception:
                    print("[RPControl] Fehler beim Abrufen der gespeicherten Nachricht:")
                    traceback.print_exc()

            try:
                async for message in channel.history(limit=200):
                    if message.author != self.bot.user:
                        continue
                    if message.embeds and getattr(message.embeds[0], "title", "") == PANEL_TITLE:
                        await message.edit(embed=self.view.get_status_embed(), view=self.view)
                        save_persist({"message_id": message.id})
                        print("[RPControl] Bestehendes Panel in History gefunden & aktualisiert.")
                        return
                    if getattr(message, "components", None):
                        await message.edit(embed=self.view.get_status_embed(), view=self.view)
                        save_persist({"message_id": message.id})
                        print("[RPControl] Bot-Nachricht mit Komponenten gefunden & aktualisiert.")
                        return
            except discord.Forbidden:
                print("[RPControl] Keine Rechte, Nachrichtenverlauf zu lesen.")
            except Exception:
                print("[RPControl] Fehler beim Durchsuchen der History:")
                traceback.print_exc()

            try:
                msg = await channel.send(embed=self.view.get_status_embed(), view=self.view)
                save_persist({"message_id": msg.id})
                print("[RPControl] Neues Panel gesendet und message_id gespeichert.")
            except discord.Forbidden:
                print("[RPControl] Keine Rechte, um Nachrichten zu senden.")
            except Exception:
                print("[RPControl] Fehler beim Senden des neuen Panels:")
                traceback.print_exc()

        except Exception:
            print("[RPControl] Unbekannter Fehler im Ensure-Panel-Task:")
            traceback.print_exc()


async def setup(bot: commands.Bot):
    await bot.add_cog(RPControl(bot))