import io
import json
import traceback
from pathlib import Path

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from settings.config import WELCOME_CHANNEL_ID

ASSETS_DIR = Path(__file__).parent.parent / "assets"
TEMPLATE_PATH = ASSETS_DIR / "welcome_template.png"
COUNTER_FILE = Path(__file__).parent.parent / "welcome_counter.json"

MAX_PLAYERS = 456  # Squid Game player cap - counter wraps back to 1 after this.

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# Coordinates measured directly off Jonas's real template (assets/welcome_template.png,
# 800x400) by scanning for the grid lines - not eyeballed.
PHOTO_BOX = (40, 95, 153, 230)
VALUE_X0 = 282
ROW_Y = [95, 128, 162, 193, 230]  # row0 "WELCOME TO" is static art, rows 1-3 are dynamic
NUMBER_CENTER = (400, 51)


def load_counter() -> int:
    try:
        if COUNTER_FILE.exists():
            return json.loads(COUNTER_FILE.read_text(encoding="utf-8")).get("count", 0)
    except Exception:
        traceback.print_exc()
    return 0


def save_counter(count: int) -> None:
    try:
        COUNTER_FILE.write_text(json.dumps({"count": count}), encoding="utf-8")
    except Exception:
        traceback.print_exc()


def next_player_number() -> int:
    count = load_counter() + 1
    if count > MAX_PLAYERS:
        count = 1
    save_counter(count)
    return count


async def build_welcome_card(member: discord.Member, player_number: int) -> discord.File:
    img = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    avatar_bytes = await member.display_avatar.replace(size=512).read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
    px0, py0, px1, py1 = PHOTO_BOX
    box_w, box_h = px1 - px0, py1 - py0
    ratio = max(box_w / avatar.width, box_h / avatar.height)
    avatar = avatar.resize((int(avatar.width * ratio), int(avatar.height * ratio)))
    left = (avatar.width - box_w) // 2
    top = (avatar.height - box_h) // 2
    avatar = avatar.crop((left, top, left + box_w, top + box_h))
    img.paste(avatar, (px0, py0))

    f_number = ImageFont.truetype(FONT_SERIF_BOLD, 34)
    number_text = f"{player_number:03d}"
    bbox = draw.textbbox((0, 0), number_text, font=f_number)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((NUMBER_CENTER[0] - tw / 2, NUMBER_CENTER[1] - th / 2 - bbox[1]), number_text, font=f_number, fill=(10, 10, 10))

    # Row 0 ("WELCOME TO / 456 SQUID GAME") is static art - only rows 1-3 get overlaid.
    f_value = ImageFont.truetype(FONT_SERIF, 17)
    values = [
        f"{member.created_at.year}                    -                    {member.joined_at.year if member.joined_at else ''}",
        str(member.id),
        member.joined_at.strftime("%m.%d.%Y") if member.joined_at else "-",
    ]
    for i, value in enumerate(values):
        ry0, ry1 = ROW_Y[i + 1], ROW_Y[i + 2]
        bbox = draw.textbbox((0, 0), value, font=f_value)
        th = bbox[3] - bbox[1]
        draw.text((VALUE_X0 + 15, ry0 + (ry1 - ry0 - th) / 2 - bbox[1]), value, font=f_value, fill=(10, 10, 10))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="welcome.png")


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not WELCOME_CHANNEL_ID:
            print("[Welcome] WELCOME_CHANNEL_ID ist nicht gesetzt - Willkommenskarte wird uebersprungen.")
            return
        channel = self.bot.get_channel(int(WELCOME_CHANNEL_ID)) or await self.bot.fetch_channel(int(WELCOME_CHANNEL_ID))
        if not channel:
            print(f"[Welcome] Kanal {WELCOME_CHANNEL_ID} nicht gefunden.")
            return
        try:
            player_number = next_player_number()
            file = await build_welcome_card(member, player_number)
            await channel.send(content=f"Welcome, {member.mention}. You are Player {player_number:03d}.", file=file)
            print(f"[Welcome] Karte fuer {member} gesendet (Player {player_number:03d}).")
        except Exception:
            print("[Welcome] Fehler beim Erstellen/Senden der Willkommenskarte:")
            traceback.print_exc()

    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def cmd_test_welcome(self, ctx: commands.Context):
        """Preview the welcome card using your own account, without consuming a real player number."""
        preview_number = load_counter() + 1
        if preview_number > MAX_PLAYERS:
            preview_number = 1
        file = await build_welcome_card(ctx.author, preview_number)
        await ctx.send(content=f"Preview (next real join would be Player {preview_number:03d}):", file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
