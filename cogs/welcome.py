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
                print("[welcome.py] WARNING: Config JSON konnte nicht geparst werden.")
                return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_owner(self, ctx_or_interaction):
        if isinstance(ctx_or_interaction, discord.Interaction):
            return ctx_or_interaction.user.id in OWNER_IDS
        else:
            return ctx_or_interaction.author.id in OWNER_IDS

    async def _resolve_channel(self, guild: discord.Guild, channel_id):
        if not channel_id:
            return None
        try:
            cid = int(channel_id)
        except Exception:
            return None

        ch = guild.get_channel(cid)
        if ch:
            return ch
        ch = self.bot.get_channel(cid)
        if ch:
            return ch
        try:
            return await self.bot.fetch_channel(cid)
        except Exception as e:
            print(f"[WelcomeCog] fetch_channel({cid}) fehlgeschlagen: {e}")
            return None

    # --- Member Join ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfgs = load_config()
        guild_id = str(member.guild.id)
        cfg = cfgs.get(guild_id)
        if not cfg:
            return

        # Konfiguration
        channel_id = cfg.get("channel_id")
        message = cfg.get("message")
        title = cfg.get("embed_title", "👋 Willkommen!")
        color_hex = cfg.get("color", "")
        image_url = cfg.get("image", "")
        dcmembers_log_id = cfg.get("dcmembers_log_id")
        joinroles_log_id = cfg.get("joinroles_log_id")

        welcome_channel = await self._resolve_channel(member.guild, channel_id)
        dcmembers_log_channel = await self._resolve_channel(member.guild, dcmembers_log_id)
        joinroles_log_channel = await self._resolve_channel(member.guild, joinroles_log_id)

        # --- Willkommensnachricht ---
        if welcome_channel and message:
            color = discord.Color.green()
            if isinstance(color_hex, str) and color_hex.startswith("#"):
                try:
                    color = discord.Color(int(color_hex[1:], 16))
                except Exception:
                    pass

            embed = discord.Embed(
                title=title,
                description=message.replace("{user}", member.mention),
                color=color
            )
            embed.set_author(
                name=member.guild.name,
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            if image_url:
                try:
                    embed.set_image(url=image_url)
                except Exception:
                    pass

            try:
                await welcome_channel.send(embed=embed)
            except Exception as e:
                print(f"[WelcomeCog] Fehler beim Senden der Willkommensnachricht: {e}")

        # --- DC Members Log (Join) ---
        if dcmembers_log_channel:
            try:
                log_embed = discord.Embed(
                    title="👤 Neuer User beigetreten",
                    description=f"{member.mention} ist dem Server beigetreten.",
                    color=discord.Color.blue()
                )
                log_embed.add_field(
                    name="`Mitgliederstand`",
                    value=f"`{member.guild.member_count} Mitglieder`",
                    inline=False
                )
                log_embed.set_thumbnail(url=member.display_avatar.url)
                await dcmembers_log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[WelcomeCog] Fehler beim Senden des Join-Logs: {e}")

        # --- Join Rollen vergeben ---
        join_roles = cfg.get("join_roles", [])
        for role_id in join_roles:
            role = member.guild.get_role(int(role_id)) if role_id else None
            if role:
                try:
                    await member.add_roles(role, reason="Auto Join Role")
                    if joinroles_log_channel:
                        embed = discord.Embed(
                            title="✅ Rolle vergeben",
                            description=f"{role.mention} wurde erfolgreich an {member.mention} vergeben.",
                            color=discord.Color.green()
                        )
                        await joinroles_log_channel.send(embed=embed)
                except Exception as e:
                    print(f"[WelcomeCog] Fehler beim Vergeben der Rolle {role}: {e}")
                    if joinroles_log_channel:
                        embed = discord.Embed(
                            title="❌ Fehler beim Rollen vergeben",
                            description=f"Konnte {role.mention} nicht an {member.mention} vergeben.\nFehler: `{e}`",
                            color=discord.Color.red()
                        )
                        await joinroles_log_channel.send(embed=embed)

    # --- Member Leave ---
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfgs = load_config()
        guild_id = str(member.guild.id)
        cfg = cfgs.get(guild_id)
        if not cfg:
            return

        dcmembers_log_id = cfg.get("dcmembers_log_id")
        dcmembers_log_channel = await self._resolve_channel(member.guild, dcmembers_log_id)

        if dcmembers_log_channel:
            try:
                embed = discord.Embed(
                    title="🚪 User hat den Server verlassen",
                    description=f"{member.mention} hat den Server verlassen.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="`Mitgliederstand`",
                    value=f"`{member.guild.member_count} Mitglieder`",
                    inline=False
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await dcmembers_log_channel.send(embed=embed)
            except Exception as e:
                print(f"[WelcomeCog] Fehler beim Senden des Leave-Logs: {e}")

    # --- Commands ---
    @commands.hybrid_command(name="setwelcomechannel", description="Setze den Kanal für die Willkommensnachricht")
    async def setwelcomechannel(self, ctx: commands.Context, channel: discord.TextChannel):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ Du darfst diesen Command nicht benutzen.", ephemeral=True)

        cfgs = load_config()
        guild_id = str(ctx.guild.id)
        cfgs[guild_id] = cfgs.get(guild_id, {})
        cfgs[guild_id]["channel_id"] = channel.id
        save_config(cfgs)
        await ctx.send(f"✅ Willkommenskanal wurde auf {channel.mention} gesetzt.", ephemeral=True)

    @commands.hybrid_command(name="setwelcomemessage", description="Öffne ein Popup zum Setzen der Willkommensnachricht")
    async def setwelcomemessage(self, ctx: commands.Context):
        interaction = ctx.interaction
        if interaction is None:
            return await ctx.send("❌ Dieser Command funktioniert nur als Slash-Command.", ephemeral=True)

        if not await self.is_owner(interaction):
            return await interaction.response.send_message("❌ Du darfst diesen Command nicht benutzen.", ephemeral=True)

        class WelcomeMessageModal(discord.ui.Modal, title="Willkommensnachricht festlegen"):
            title_field = discord.ui.TextInput(
                label="Titel",
                style=discord.TextStyle.short,
                required=True,
                max_length=256,
                placeholder="z.B. Willkommen auf dem Server!"
            )
            description_field = discord.ui.TextInput(
                label="Text",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=2000,
                placeholder="Hallo {user}, schön dass du da bist!"
            )
            color_field = discord.ui.TextInput(
                label="Farbe (Hex, optional)",
                style=discord.TextStyle.short,
                required=False,
                max_length=7,
                placeholder="#00ff00"
            )
            image_field = discord.ui.TextInput(
                label="Bild (Link, optional)",
                style=discord.TextStyle.short,
                required=False,
                max_length=500,
                placeholder="https://example.com/image.png"
            )

            async def on_submit(modal_self, interaction: discord.Interaction):
                cfgs = load_config()
                guild_id = str(interaction.guild.id)
                cfgs[guild_id] = cfgs.get(guild_id, {})
                cfgs[guild_id]["embed_title"] = modal_self.title_field.value
                cfgs[guild_id]["message"] = modal_self.description_field.value
                cfgs[guild_id]["color"] = modal_self.color_field.value if modal_self.color_field.value else ""
                cfgs[guild_id]["image"] = modal_self.image_field.value if modal_self.image_field.value else ""
                save_config(cfgs)
                await interaction.response.send_message("✅ Embed-Willkommensnachricht gespeichert!", ephemeral=True)

        await interaction.response.send_modal(WelcomeMessageModal())

    @commands.hybrid_command(name="setjoinroles", description="Lege die Rollen fest, die neue Member automatisch bekommen sollen")
    async def setjoinroles(self, ctx: commands.Context, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ Du darfst diesen Command nicht benutzen.", ephemeral=True)

        roles = [r for r in [role1, role2, role3] if r is not None]
        cfgs = load_config()
        guild_id = str(ctx.guild.id)
        cfgs[guild_id] = cfgs.get(guild_id, {})
        cfgs[guild_id]["join_roles"] = [role.id for role in roles]
        save_config(cfgs)

        await ctx.send(f"✅ Neue Join-Rollen gespeichert: {', '.join([role.mention for role in roles])}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))