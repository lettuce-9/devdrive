import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1244518794710355978

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and connected to Discord!")

async def setup_hook():
    print("Loading cogs...")
    await bot.load_extension("usercards2")
    await bot.load_extension("modlogs_system")
    print("Cogs loaded.")

    print("Syncing guild commands...")
    cmds = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Synced {len(cmds)} commands to guild {GUILD_ID}")
    for cmd in cmds:
        print(f" - {cmd.name}")

bot.setup_hook = setup_hook

async def main():
    async with bot:
        await bot.start(token)

asyncio.run(main())
