import discord
from discord.ext import commands
from discord import app_commands, ui
import os
from typing import Dict
import asyncio
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import logging

load_dotenv()
from settings.config import RANK_ADMIN_IDS, LEVEL_CHANNEL_ID

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Ranks & Queue
ranks: Dict[str, dict] = {"paused": False}
xp_queue = Counter()
queue_lock = asyncio.Lock()
SAVE_INTERVAL = 5  # Sekunden


# ---------------- Supabase Funktionen ----------------

def load_ranks_from_supabase():
    global ranks
    try:
        data = supabase.table("ranks").select("*").execute()
        ranks = {"paused": False}

        for row in data.data:
            uid = str(row["user_id"])
            try:
                xp = int(row.get("xp", 0))
            except (TypeError, ValueError):
                xp = 0
            try:
                level = int(row.get("level", 1))
            except (TypeError, ValueError):
                level = 1
            try:
                messages = int(row.get("messages", 0))
            except (TypeError, ValueError):
                messages = 0

            ranks[uid] = {
                "xp": xp,
                "level": level,
                "messages": messages
            }

        print(f"[Supabase] {len(ranks) - 1} Ranks geladen")

    except Exception as e:
        print(f"[Supabase] Fehler beim Laden: {e}")

def save_rank_to_supabase(uid: str):
    uid = str(uid)
    if uid not in ranks:
        print(f"[Supabase] ⚠️ Kein Rank-Datensatz für {uid}")
        return

    data = ranks[uid].copy()
    data["user_id"] = uid
    data["updated_at"] = datetime.utcnow().isoformat()

    try:
        # Prüfen, ob Nutzer schon existiert
        exists = supabase.table("ranks").select("user_id").eq("user_id", uid).execute()
        if exists.data:
            # Update bestehender Datensatz
            supabase.table("ranks").update(data).eq("user_id", uid).execute()
        else:
            # Neuer Datensatz
            supabase.table("ranks").insert(data).execute()

        print(f"[Supabase] Gespeichert: {uid} (Level {data['level']}, XP {data['xp']})")

    except Exception as e:
        print(f"[Supabase] ❌ Fehler beim Speichern von {uid}: {e}")
# ---------------- Systemfunktionen ----------------

def is_system_paused():
    return ranks.get("paused", False)

def set_system_paused(paused: bool):
    ranks["paused"] = paused

def ensure_user(user_id):
    user_id = str(user_id)
    if user_id == "paused":
        raise ValueError("User ID 'paused' ist reserviert!")
    if user_id not in ranks:
        ranks[user_id] = {"xp":0, "level":1, "messages":0}
    else:
        ranks[user_id].setdefault("xp",0)
        ranks[user_id].setdefault("level",1)
        ranks[user_id].setdefault("messages",0)
    return user_id

async def queue_xp(user_id, xp=1):
    async with queue_lock:
        xp_queue[str(user_id)] += xp

def messages_required_for_level(level: int) -> int:
    if level <=1: return 50
    if level >=20: return 200
    return int(50 + (level-1)*(150/18))

def add_xp(user_id, xp_to_add):
    user_id = ensure_user(user_id)
    ranks[user_id]["xp"] += xp_to_add
    ranks[user_id]["messages"] += 1
    lvl = ranks[user_id]["level"]
    next_level_xp = sum(messages_required_for_level(l) for l in range(1,lvl+1))
    if ranks[user_id]["xp"] >= next_level_xp:
        ranks[user_id]["level"] += 1
    save_rank_to_supabase(user_id)
    return ranks[user_id]["xp"] >= next_level_xp

def get_progress_bar(current, maximum, length=20):
    filled = min(length, max(0,int(length*current//maximum)))
    return "🟥"*filled + "⬜"*(length-filled)

# ---------------- Admin UI ----------------

class RankAdminDropdown(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Level eines Users setzen", value="set_level"),
            discord.SelectOption(label="Level eines Users erhöhen", value="add_level"),
            discord.SelectOption(label="XP eines Users setzen", value="set_xp"),
            discord.SelectOption(label="System zurücksetzen", value="reset"),
            discord.SelectOption(label="Level-System pausieren/fortsetzen", value="toggle_pause"),
        ]
        super().__init__(placeholder="Wähle eine Aktion...", options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "reset":
            ranks.clear()
            ranks["paused"] = False
            # Lösche alle Einträge in Supabase
            supabase.table("ranks").delete().neq("user_id","").execute()
            await interaction.response.send_message("✅ Das Rank-System wurde zurückgesetzt.", ephemeral=True)
            return
        if value == "toggle_pause":
            current = is_system_paused()
            set_system_paused(not current)
            status = "pausiert" if not current else "fortgesetzt"
            await interaction.response.send_message(f"✅ Das Level-System wurde {status}.", ephemeral=True)
            return
        await interaction.response.send_modal(RankAdminModal(value))

class RankAdminModal(ui.Modal):
    def __init__(self, action):
        super().__init__(title=f"Rank Verwaltung: {action}")
        self.action = action
        self.user_id = ui.TextInput(label="User ID", required=True, placeholder="123456789012345678")
        self.value = ui.TextInput(label="Wert (Level oder XP)", required=False, placeholder="z.B. 5")
        self.add_item(self.user_id)
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
        except:
            return await interaction.response.send_message("❌ Ungültige User ID.", ephemeral=True)
        uid = ensure_user(uid)
        if self.action == "set_level":
            ranks[str(uid)]["level"] = int(self.value.value)
        elif self.action == "add_level":
            ranks[str(uid)]["level"] += int(self.value.value)
        elif self.action == "set_xp":
            ranks[str(uid)]["xp"] = int(self.value.value)
        save_rank_to_supabase(str(uid))
        await interaction.response.send_message(f"✅ Aktion {self.action} für <@{uid}> durchgeführt.", ephemeral=True)

class RankAdminView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RankAdminDropdown())

# ---------------- Rank System Cog ----------------

class RankSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.batch_save_loop())
        load_ranks_from_supabase()

    async def batch_save_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(SAVE_INTERVAL)
            async with queue_lock:
                if not xp_queue:
                    continue
                for uid, xp in xp_queue.items():
                    add_xp(uid, xp)
                xp_queue.clear()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if is_system_paused(): return
        leveled_up = add_xp(message.author.id,1)
        if leveled_up:
            channel = self.bot.get_channel(LEVEL_CHANNEL_ID)
            text = f"🎉 {message.author.mention} ist jetzt Level {ranks[str(message.author.id)]['level']}!"
            if channel: await channel.send(text)
            else: await message.channel.send(text)

    @app_commands.command(name="rank", description="Zeigt deinen aktuellen Level und Fortschritt")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user

        uid = ensure_user(member.id)
        data = ranks[uid]

        # Safety: XP, Level und Messages immer als int
        level = int(data.get("level", 1))
        xp = int(data.get("xp", 0))
        messages = int(data.get("messages", 0))

        # Level-Berechnung
        prev_xp = sum(messages_required_for_level(l) for l in range(1, level))
        next_xp = sum(messages_required_for_level(l) for l in range(1, level + 1))
        xp_into = xp - prev_xp
        xp_needed = next_xp - prev_xp
        progress = get_progress_bar(xp_into, xp_needed, 20)

        # Sicheres Sortieren (wandelt XP zu int)
        def safe_xp(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0

        sorted_ranks = sorted(
            ((u, d) for u, d in ranks.items() if isinstance(d, dict)),
            key=lambda x: safe_xp(x[1].get("xp", 0)),
            reverse=True
        )

        rank_pos = next((i for i, (u, _) in enumerate(sorted_ranks, start=1) if u == uid), None)

        # Embed erstellen
        embed = discord.Embed(
            title=f"🇨🇭 Rangkarte für {member.name}",
            description=f"**Server Rang:** #{rank_pos}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📈 Level", value=f"{level}", inline=True)
        embed.add_field(name="⭐ XP", value=f"{xp_into}/{xp_needed}", inline=True)
        embed.add_field(name="💬 Nachrichten", value=f"{messages}", inline=True)
        embed.add_field(
            name="📊 Fortschritt",
            value=f"{progress}\nNoch **{xp_needed - xp_into} XP** bis Level {level + 1}",
            inline=False
        )
        embed.set_footer(text="Swiss Power 🇨🇭")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rankadmin", description="Verwalte das Rank-System")
    async def rankadmin(self, interaction: discord.Interaction):
        if interaction.user.id not in RANK_ADMIN_IDS:
            return await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        view = RankAdminView()
        await interaction.response.send_message("⚙️ Wähle eine Aktion:", view=view, ephemeral=True)

# ---------------- Setup ----------------

async def setup(bot):
    await bot.add_cog(RankSystem(bot))
