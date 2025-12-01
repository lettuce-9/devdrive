import discord
import time
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = 1244518794710355978

@bot.event
async def on_ready():
    await bot.load_extension("usercards2")
    await bot.load_extension("modlogs_system")
    cmds = await bot.tree.sync()
    print(f"Globally synced {len(cmds)} commands")

    print("Syncing also to guild...")
    time.sleep(1)

    print(f"Guild sync for {GUILD_ID}...")
    guild_cmds = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Guild synced {len(guild_cmds)} commands.")
    for cmd in guild_cmds:
        print(f" - {cmd.name}")

    await bot.close()

async def main():
    async with bot:
        await bot.start(token)

asyncio.run(main())
