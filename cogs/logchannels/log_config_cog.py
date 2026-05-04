import discord
from discord.ext import commands
import json
import os
from settings.config import OWNER_IDS

CONFIG_FILE = "welcome_config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("[log_config_cog] WARNING: Config JSON konnte nicht geparst werden.")
                return {}
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class LogConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_owner(self, ctx_or_interaction):
        if isinstance(ctx_or_interaction, discord.Interaction):
            return ctx_or_interaction.user.id in OWNER_IDS
        else:
            return ctx_or_interaction.author.id in OWNER_IDS

    @commands.hybrid_command(name="setlogchannel", description="Öffne ein Popup zum Setzen der Log-Kanäle")
    async def setlogchannel(self, ctx: commands.Context):
        interaction = ctx.interaction if ctx.interaction else None
        if interaction is None:
            return await ctx.send("❌ Dieser Command funktioniert nur als Slash-Command.", ephemeral=True)

        if not await self.is_owner(interaction):
            return await interaction.response.send_message("❌ Du darfst diesen Command nicht benutzen.", ephemeral=True)

        cfgs = load_config()
        guild_id = str(interaction.guild.id)
        guild_cfg = cfgs.get(guild_id, {})

        class LogChannelModal(discord.ui.Modal, title="Log-Kanäle festlegen"):
            dcmembers_field = discord.ui.TextInput(
                label="DCMembers-Logs Kanal ID",
                style=discord.TextStyle.short,
                required=False,
                max_length=25,
                placeholder="123456789012345678",
                default=str(guild_cfg.get("dcmembers_log_id", "")) if guild_cfg.get("dcmembers_log_id") else ""
            )
            joinroles_field = discord.ui.TextInput(
                label="JoinRoles-Logs Kanal ID",
                style=discord.TextStyle.short,
                required=False,
                max_length=25,
                placeholder="123456789012345678",
                default=str(guild_cfg.get("joinroles_log_id", "")) if guild_cfg.get("joinroles_log_id") else ""
            )
            rolelock_field = discord.ui.TextInput(
                label="RoleLock Logs Kanal ID",
                style=discord.TextStyle.short,
                required=False,
                max_length=25,
                placeholder="123456789012345678",
                default=str(guild_cfg.get("rolelock_logs_id", "")) if guild_cfg.get("rolelock_logs_id") else ""
            )
            rp_control_field = discord.ui.TextInput(
                label="RP Control Logs Kanal ID",
                style=discord.TextStyle.short,
                required=False,
                max_length=25,
                placeholder="123456789012345678",
                default=str(guild_cfg.get("rp_control_logs_id", "")) if guild_cfg.get("rp_control_logs_id") else ""
            )
            landauswahl_logs_field = discord.ui.TextInput(
                label="LandAuswahl Logs Kanal ID",
                style=discord.TextStyle.short,
                required=False,
                max_length=25,
                placeholder="123456789012345678",
                default=str(guild_cfg.get("landauswahl_logs_id", "")) if guild_cfg.get("landauswahl_logs_id") else ""
            )

            async def on_submit(modal_self, interaction: discord.Interaction):
                cfgs = load_config()
                guild_id = str(interaction.guild.id)
                cfgs[guild_id] = cfgs.get(guild_id, {})

                try:
                    def handle_field(field_value, key):
                        if field_value.strip():
                            cfgs[guild_id][key] = int(field_value)
                        else:
                            cfgs[guild_id].pop(key, None)

                    handle_field(modal_self.dcmembers_field.value, "dcmembers_log_id")
                    handle_field(modal_self.joinroles_field.value, "joinroles_log_id")
                    handle_field(modal_self.rolelock_field.value, "rolelock_logs_id")
                    handle_field(modal_self.rp_control_field.value, "rp_control_logs_id")
                    handle_field(modal_self.landauswahl_logs_field.value, "landauswahl_logs_id")

                    save_config(cfgs)
                    await interaction.response.send_message("✅ Log-Kanäle gespeichert!", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)

        await interaction.response.send_modal(LogChannelModal())


async def setup(bot):
    await bot.add_cog(LogConfigCog(bot))