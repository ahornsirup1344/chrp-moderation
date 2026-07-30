import discord
from discord.ext import commands
import traceback

from settings.config import (
    PERSONNEL_ROLE_ID,
    ARMORY_CHANNEL_ID,
    READ_ME_CHANNEL_ID,
    PANEL_CHANNEL_ID,
    PANEL_LOG_CHANNEL_ID,
)

PANEL_TITLE = "[456] System's"
SELECT_CUSTOM_ID = "456_system:select"


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


class SystemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Armory", description="Get access to the uniform & weapons channel.", emoji="🔫", value="armory"),
            discord.SelectOption(label="Read me", description="Chain of command, duties & rules.", emoji="📖", value="readme"),
        ]
        super().__init__(
            placeholder="Select an option...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=SELECT_CUSTOM_ID,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "armory":
            channel_id = ARMORY_CHANNEL_ID
            label = "Armory"
        else:
            channel_id = READ_ME_CHANNEL_ID
            label = "Read me"

        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None

        if not channel:
            await interaction.response.send_message(
                f"❌ The `{label}` channel is not configured yet. Please contact an administrator.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ **{label}**: {channel.mention}",
            ephemeral=True,
        )
        await log_usage(
            interaction.client,
            interaction.guild,
            f"{interaction.user.mention} selected **{label}** and was redirected to {channel.mention}.",
        )


class SystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SystemSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            if interaction.guild is None:
                await interaction.response.send_message("This menu only works on the server.", ephemeral=True)
                return False

            if not PERSONNEL_ROLE_ID:
                await interaction.response.send_message(
                    "❌ This menu is not configured yet. Please contact an administrator.", ephemeral=True
                )
                return False

            member_roles = getattr(interaction.user, "roles", [])
            if not any(r.id == int(PERSONNEL_ROLE_ID) for r in member_roles):
                await interaction.response.send_message(
                    "❌ You don't have permission to use this menu.", ephemeral=True
                )
                return False

            return True
        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred while checking your permissions.", ephemeral=True)
            except Exception:
                pass
            return False


class System456Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(SystemView())

    def get_panel_embed(self) -> discord.Embed:
        return discord.Embed(
            title=PANEL_TITLE,
            description="Select an option below:\n\n🔫 **Armory** – uniform & weapons\n📖 **Read me** – chain of command & duties",
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

    @commands.command(name="456panel")
    @commands.has_permissions(administrator=True)
    async def cmd_send_panel(self, ctx: commands.Context):
        """Sends the [456] System's dropdown panel."""
        channel_id = PANEL_CHANNEL_ID or ctx.channel.id
        channel = await self._resolve_channel(channel_id)
        if not channel:
            await ctx.send("❌ Panel channel not found. Check PANEL_CHANNEL_ID in settings/config.py.")
            return

        await channel.send(embed=self.get_panel_embed(), view=SystemView())
        await ctx.send(f"✅ Panel sent in {channel.mention}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(System456Cog(bot))
