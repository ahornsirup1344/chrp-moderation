import discord
from discord.ext import commands
from discord import app_commands, ui
from supabase import create_client
import os

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------ Paginierte Leaderboard-View ------------------

class LeaderboardView(ui.View):
    def __init__(self, pages):
        super().__init__(timeout=None)
        self.pages = pages
        self.current_page = 0

    @ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(label="➡️", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

# ------------------ Leaderboard Cog ------------------

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Zeigt das Level-Leaderboard des Servers")
    async def leaderboard(self, interaction: discord.Interaction):
        """Paginiertes Leaderboard mit Mentions und 15 Mitgliedern pro Seite"""

        try:
            response = supabase.table("ranks").select("*").execute()
            all_ranks = response.data
        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler beim Laden des Leaderboards: {e}", ephemeral=True)
            return

        if not all_ranks:
            await interaction.response.send_message("❌ Es sind noch keine Mitglieder im Leaderboard.", ephemeral=True)
            return

        sorted_ranks = sorted(all_ranks, key=lambda x: x.get("xp", 0), reverse=True)

        per_page = 15
        total_pages = (len(sorted_ranks) + per_page - 1) // per_page
        pages = []

        for page_num in range(total_pages):
            embed = discord.Embed(
                title="🏆 Level Leaderboard",
                description=f"Seite {page_num + 1}/{total_pages}",
                color=discord.Color.gold()
            )

            for i, data in enumerate(sorted_ranks[page_num * per_page:(page_num + 1) * per_page],
                                     start=page_num * per_page + 1):
                uid = data.get("user_id")
                if not uid:
                    continue
                try:
                    member = await interaction.guild.fetch_member(int(uid))
                    name = member.mention
                except discord.NotFound:
                    continue

                embed.add_field(
                    name=f"#{i}",
                    value=f"{name} | Level: {data['level']} | XP: {data['xp']} | Nachrichten: {data['messages']}",
                    inline=False
                )

            embed.set_footer(text="Swiss Power 🇨🇭")
            pages.append(embed)

        if not pages:
            await interaction.response.send_message("❌ Es sind noch keine Mitglieder im Leaderboard.", ephemeral=True)
            return

        view = LeaderboardView(pages)
        await interaction.response.send_message(embed=pages[0], view=view)

# ------------------ Setup ------------------

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))