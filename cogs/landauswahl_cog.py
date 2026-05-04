import discord
from discord.ext import commands
import traceback
import json
import os

from settings.config import (
    LANDAUSWAHL_CHANNEL_ID,
    LANDAUSWAHL_ROLE_SWITZERLAND,
    LANDAUSWAHL_ROLE_GERMANY,
    LANDAUSWAHL_ROLE_AUSTRIA,
    LANDAUSWAHL_ALWAYS_ROLES
)

CONFIG_FILE = "welcome_config.json"


# -------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("[LandAuswahl] WARN: Config JSON konnte nicht geladen werden.")
    return {}


async def log_to_channel(bot: commands.Bot, guild: discord.Guild, description: str, success: bool = None, user: discord.User = None):
    cfgs = load_config()
    gid = str(guild.id)
    log_id = cfgs.get(gid, {}).get("landauswahl_logs_id")
    if not log_id:
        return

    color = discord.Color.light_grey()
    title = ":information_source: Info"

    if success is True:
        color = discord.Color.green()
        title = "✅ Erfolg"
    elif success is False:
        color = discord.Color.red()
        title = "❌ Fehler"

    embed = discord.Embed(title=title, description=description, color=color)
    if user:
        embed.set_footer(text=f"User: {user} | ID: {user.id}")

    try:
        channel = bot.get_channel(int(log_id)) or await bot.fetch_channel(int(log_id))
        if channel:
            await channel.send(embed=embed)
    except Exception:
        traceback.print_exc()


# -------------------------
class LandAuswahlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🇨🇭 Schweiz", style=discord.ButtonStyle.danger, custom_id="land:swiss")
    async def switzerland_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_choice(interaction, LANDAUSWAHL_ROLE_SWITZERLAND, "Schweiz")

    @discord.ui.button(label="🇩🇪 Deutschland", style=discord.ButtonStyle.secondary, custom_id="land:german")
    async def germany_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_choice(interaction, LANDAUSWAHL_ROLE_GERMANY, "Deutschland")

    @discord.ui.button(label="🇦🇹 Österreich", style=discord.ButtonStyle.success, custom_id="land:austria")
    async def austria_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_choice(interaction, LANDAUSWAHL_ROLE_AUSTRIA, "Österreich")

    async def _handle_choice(self, interaction: discord.Interaction, role_id: int, land_name: str):
        member = interaction.guild.get_member(interaction.user.id) or interaction.user
        member_role_ids = {r.id for r in getattr(member, "roles", [])}

        role_ids = {LANDAUSWAHL_ROLE_SWITZERLAND, LANDAUSWAHL_ROLE_GERMANY, LANDAUSWAHL_ROLE_AUSTRIA}

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        if member_role_ids & role_ids:
            msg = f"❌ {interaction.user.mention} besitzt bereits eine Länder-Rolle."
            await interaction.followup.send(msg, ephemeral=True)
            await log_to_channel(self.bot, interaction.guild,
                                 f"{interaction.user.mention} hat versucht `{land_name}` zu wählen, aber hatte schon eine Rolle.",
                                 success=False, user=interaction.user)
            return

        role = interaction.guild.get_role(int(role_id))
        if not role:
            msg = "❌ Rolle nicht gefunden (prüfe settings.config)."
            await interaction.followup.send(msg, ephemeral=True)
            await log_to_channel(self.bot, interaction.guild,
                                 f"{interaction.user.mention} wollte `{land_name}` wählen, aber Rolle nicht gefunden!",
                                 success=False, user=interaction.user)
            return

        try:
            always_ids = LANDAUSWAHL_ALWAYS_ROLES
            if isinstance(always_ids, int):
                always_ids = [always_ids]

            always_roles = []
            for rid in always_ids:
                r = interaction.guild.get_role(int(rid))
                if r:
                    always_roles.append(r)

            roles_to_add = [role] + always_roles
            await interaction.user.add_roles(*roles_to_add, reason="Landauswahl per Button + Immerrollen")

            msg = f"✅ Du hast **{role.name}** gewählt!"
            if always_roles:
                msg += f"\nAußerdem hast du automatisch folgende Rollen erhalten: {', '.join([r.name for r in always_roles])}"

            await interaction.followup.send(msg, ephemeral=True)
            await log_to_channel(self.bot, interaction.guild,
                                 f"{interaction.user.mention} hat erfolgreich die Rolle `{role.name}` gewählt. (Immerrollen: {[r.name for r in always_roles]})",
                                 success=True, user=interaction.user)

        except discord.Forbidden:
            msg = "❌ Ich habe keine Rechte, dir die Rolle zu geben."
            await interaction.followup.send(msg, ephemeral=True)
            await log_to_channel(self.bot, interaction.guild,
                                 f"{interaction.user.mention} konnte `{land_name}` nicht erhalten (fehlende Rechte).",
                                 success=False, user=interaction.user)
        except Exception:
            traceback.print_exc()
            msg = "❌ Fehler beim Zuweisen der Rolle."
            await interaction.followup.send(msg, ephemeral=True)
            await log_to_channel(self.bot, interaction.guild,
                                 f"Fehler beim Zuweisen von `{land_name}` an {interaction.user.mention}.",
                                 success=False, user=interaction.user)


# -------------------------
class LandAuswahlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(LandAuswahlView(self.bot))

    async def _resolve_channel(self, channel_id: int):
        try:
            ch = self.bot.get_channel(int(channel_id))
            if ch:
                return ch
            return await self.bot.fetch_channel(int(channel_id))
        except Exception:
            traceback.print_exc()
            return None

    @commands.command(name="landauswahl_send")
    async def cmd_force_send(self, ctx: commands.Context):
        """Sendet das Land-Auswahl Embed neu."""
        channel = await self._resolve_channel(LANDAUSWAHL_CHANNEL_ID)
        if not channel:
            return await ctx.send("Channel nicht gefunden.")

        view = LandAuswahlView(self.bot)

        embed = discord.Embed(
            title=":busts_in_silhouette: Schweiz Roleplay Join-Roles",
            description="Bitte wähle unten dein Land, um die passende Rolle zu erhalten. \n\n**Bitte beachte:** \n- Du kannst nur einmal eine Rolle wählen. Danach kann es nicht mehr geändert werden. \n- Es muss das richtige Land ausgewählt werden. Wenn man extra ein falsches Land nimmt, gibt dies Konsequenzen. \n- Bei Verklicken oder sonstigen Fehlern bitten wir dich, ein Ticket zu öffnen.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1398056839324635186/1398272703298928650/IMG_1171.png?ex=68d1396f&is=68cfe7ef&hm=e8a3c9b66076a4c6e5ba2c6468e121ef8d6c6e7d65c089b709ceb4a504e355bd&"
        )

        await channel.send(embed=embed, view=view)
        await ctx.send(f"✅ Embed gesendet in {channel.mention}.")
        await log_to_channel(self.bot, ctx.guild, f"Embed von {ctx.author.mention} in {channel.mention} gesendet.", success=None, user=ctx.author)


# -------------------------
async def setup(bot):
    await bot.add_cog(LandAuswahlCog(bot))