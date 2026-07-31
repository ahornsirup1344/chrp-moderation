import asyncio
import os

import discord
from dotenv import load_dotenv

load_dotenv()

# Jonas (justjonas.), Owner von "[456] Squid Games | Town" — ID vom User am 2026-07-31 selbst kopiert & bestaetigt.
JONAS_USER_ID = 931300563772112926

MESSAGE = (
    "Hey Jonas! \U0001F44B Bau grad für den [456]-Bot das Dropdown-Panel (Armory/Read me) fertig, "
    "brauch aber noch 3 Sachen von dir:\n\n"
    "1. Welche Rolle darf das Dropdown benutzen (Officer/Manager/Frontman/Moderator/andere)?\n"
    "2. Ihr habt zwei Channels namens \"rules\" — welcher ist der \"Read me\" (Chain of Command/Aufgaben)? "
    "<#1453188361861857440> oder <#1530630919281443077>\n"
    "3. Wo soll das Panel gepostet werden, und passt `players-uniform` als \"Armory\"-Channel?\n\n"
    "Wär mega wenn du kurz Bescheid gibst, dann mach ich fertig \U0001F64F"
)


async def main():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            user = await client.fetch_user(JONAS_USER_ID)
            await user.send(MESSAGE)
            print(f"DM an {user} gesendet.")
        finally:
            await client.close()

    await client.start(os.environ["DISCORD_BOT_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
