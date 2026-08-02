from discord.ext import commands

from settings.config import BOT_OWNER_ID


def is_owner_or_admin():
    """Allows the bot owner (by user ID, regardless of server role) or anyone
    with the Administrator permission on this server - nobody else."""

    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id == BOT_OWNER_ID:
            return True
        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)
