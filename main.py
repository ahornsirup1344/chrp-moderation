import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COGS_DIR = os.path.join(BASE_DIR, "cogs")

async def load_cogs():
    if not os.path.exists(COGS_DIR):
        print(f"Ordner {COGS_DIR} existiert nicht! Bitte erstelle ihn.")
        return

    for root, dirs, files in os.walk(COGS_DIR):
        for filename in files:
            if filename.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, filename), BASE_DIR)
                cog_name = rel_path.replace(os.sep, ".")[:-3]  # .py entfernen
                try:
                    await bot.load_extension(cog_name)
                    print(f"Cog geladen: {cog_name}")
                except Exception as e:
                    print(f"Fehler beim Laden von {cog_name}: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} ist online!")
    await load_cogs()
    try:
        await bot.tree.sync()
        print("Slash-Commands erfolgreich synchronisiert.")
    except Exception as e:
        print(f"Fehler beim Synchronisieren: {e}")

bot.run(os.environ.get("DISCORD_BOT_TOKEN"))