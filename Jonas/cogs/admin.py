from discord.ext import commands

from permissions import is_owner_or_admin


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clear")
    @is_owner_or_admin()
    async def cmd_clear(self, ctx: commands.Context, amount: int = 10):
        """Deletes the given number of recent messages in this channel (default 10, max 100)."""
        amount = max(1, min(amount, 100))
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message itself
        confirmation = await ctx.send(f"✅ Deleted {len(deleted) - 1} messages.")
        await confirmation.delete(delay=3)

    @commands.command(name="clearall")
    @is_owner_or_admin()
    async def cmd_clear_all(self, ctx: commands.Context):
        """Deletes every message in this channel (pages through full history, no limit)."""
        deleted = await ctx.channel.purge(limit=None)
        confirmation = await ctx.send(f"✅ Deleted {len(deleted)} messages (entire channel history).")
        await confirmation.delete(delay=3)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
