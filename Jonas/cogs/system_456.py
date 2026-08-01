import discord
from discord.ext import commands
import json
import traceback
from pathlib import Path
from typing import Optional

from settings.config import (
    HIERARCHY,
    PANEL_CHANNEL_ID,
    PANEL_LOG_CHANNEL_ID,
)

PANEL_TITLE = "[456] System's"
SELECT_CUSTOM_ID = "456_system:select"
PERSIST_FILE = Path(__file__).parent / "panel_456.json"


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


async def log_usage(bot: commands.Bot, guild: discord.Guild, description: str):
    if not PANEL_LOG_CHANNEL_ID:
        return
    try:
        channel = bot.get_channel(int(PANEL_LOG_CHANNEL_ID)) or await bot.fetch_channel(int(PANEL_LOG_CHANNEL_ID))
        if channel:
            embed = discord.Embed(description=description, color=discord.Color.blurple())
            await channel.send(embed=embed)
    except Exception:
        traceback.print_exc()


def find_tier(member: discord.Member) -> Optional[dict]:
    """Returns the HIERARCHY entry matching the member's rank role, or None if they hold none."""
    member_role_ids = {r.id for r in getattr(member, "roles", [])}
    for tier in HIERARCHY:
        if tier["role_id"] and tier["role_id"] in member_role_ids:
            return tier
    return None


class SystemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Aufgaben & Regeln", description="Befehlskette, Aufgaben & Regeln.", emoji="📖", value="rules"),
            discord.SelectOption(label="Locker", description="Uniform & Waffen für deine Position.", emoji="🔫", value="locker"),
        ]
        super().__init__(
            placeholder="Wähle eine Option...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=SELECT_CUSTOM_ID,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        tier = find_tier(interaction.user)

        # interaction_check already guarantees a tier exists, but stay defensive.
        if not tier:
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, dieses Menü zu benutzen.", ephemeral=True,
            )
            return

        if choice == "rules":
            channel_id = tier["rules_channel_id"]
            label = "Aufgaben & Regeln"
        else:
            channel_id = tier["locker_channel_id"]
            label = "Locker"

        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None

        if not channel:
            await interaction.response.send_message(
                f"❌ Der `{label}`-Channel für **{tier['name']}** ist noch nicht eingerichtet. Bitte wende dich an einen Administrator.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ **{label}** ({tier['name']}): {channel.mention}",
            ephemeral=True,
        )
        await log_usage(
            interaction.client,
            interaction.guild,
            f"{interaction.user.mention} ({tier['name']}) hat **{label}** ausgewählt und wurde zu {channel.mention} weitergeleitet.",
        )


class SystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SystemSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            if interaction.guild is None:
                await interaction.response.send_message("Dieses Menü funktioniert nur auf dem Server.", ephemeral=True)
                return False

            if not any(tier["role_id"] for tier in HIERARCHY):
                await interaction.response.send_message(
                    "❌ Dieses Menü ist noch nicht eingerichtet. Bitte wende dich an einen Administrator.", ephemeral=True
                )
                return False

            if find_tier(interaction.user) is None:
                await interaction.response.send_message(
                    "❌ Du hast keine Berechtigung, dieses Menü zu benutzen.", ephemeral=True
                )
                return False

            return True
        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("Beim Prüfen deiner Berechtigung ist ein Fehler aufgetreten.", ephemeral=True)
            except Exception:
                pass
            return False


class System456Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(SystemView())

    async def cog_load(self):
        self.bot.loop.create_task(self._ensure_panel_task())

    def get_panel_embed(self) -> discord.Embed:
        return discord.Embed(
            title=PANEL_TITLE,
            description="Wähle eine Option:\n\n📖 **Aufgaben & Regeln** – Befehlskette & Aufgaben\n🔫 **Locker** – Uniform & Waffen für deine Position",
            color=discord.Color.dark_red(),
        )

    async def _resolve_channel(self, channel_id: int):
        try:
            ch = self.bot.get_channel(int(channel_id))
            if ch:
                return ch
            return await self.bot.fetch_channel(int(channel_id))
        except Exception:
            traceback.print_exc()
            return None

    async def _ensure_panel_task(self):
        """Automatically (re)sends or refreshes the panel on every bot start, no manual command needed."""
        await self.bot.wait_until_ready()

        if not PANEL_CHANNEL_ID:
            print("[System456] PANEL_CHANNEL_ID ist nicht gesetzt – automatisches Panel wird uebersprungen.")
            return

        channel = await self._resolve_channel(PANEL_CHANNEL_ID)
        if not channel:
            print(f"[System456] Panel-Kanal {PANEL_CHANNEL_ID} nicht gefunden.")
            return

        data = load_persist()
        saved_message_id: Optional[int] = data.get("message_id")

        if saved_message_id:
            try:
                msg = await channel.fetch_message(saved_message_id)
                if msg and msg.author == self.bot.user:
                    await msg.edit(embed=self.get_panel_embed(), view=SystemView())
                    print("[System456] Panel via gespeicherter message_id gefunden und aktualisiert.")
                    return
            except discord.NotFound:
                print("[System456] Gespeicherte message_id nicht gefunden (geloescht) – sende neues Panel.")
            except discord.Forbidden:
                print("[System456] Keine Rechte, gespeicherte Panel-Nachricht zu holen/editieren.")
            except Exception:
                print("[System456] Fehler beim Abrufen der gespeicherten Panel-Nachricht:")
                traceback.print_exc()

        try:
            async for message in channel.history(limit=200):
                if message.author == self.bot.user and message.components:
                    await message.edit(embed=self.get_panel_embed(), view=SystemView())
                    save_persist({"message_id": message.id})
                    print("[System456] Bestehendes Panel in History gefunden & aktualisiert.")
                    return
        except discord.Forbidden:
            print("[System456] Keine Rechte, Nachrichtenverlauf zu lesen.")
        except Exception:
            print("[System456] Fehler beim Durchsuchen der History:")
            traceback.print_exc()

        try:
            msg = await channel.send(embed=self.get_panel_embed(), view=SystemView())
            save_persist({"message_id": msg.id})
            print("[System456] Neues Panel gesendet und message_id gespeichert.")
        except discord.Forbidden:
            print("[System456] Keine Rechte, um Nachrichten zu senden.")
        except Exception:
            print("[System456] Fehler beim Senden des neuen Panels:")
            traceback.print_exc()

    @commands.command(name="456panel")
    @commands.has_permissions(administrator=True)
    async def cmd_send_panel(self, ctx: commands.Context):
        """Manually (re)sends the [456] System's dropdown panel and updates the saved reference."""
        channel_id = PANEL_CHANNEL_ID or ctx.channel.id
        channel = await self._resolve_channel(channel_id)
        if not channel:
            await ctx.send("❌ Panel-Channel nicht gefunden. PANEL_CHANNEL_ID in settings/config.py prüfen.")
            return

        msg = await channel.send(embed=self.get_panel_embed(), view=SystemView())
        save_persist({"message_id": msg.id})
        await ctx.send(f"✅ Panel gesendet in {channel.mention}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(System456Cog(bot))
