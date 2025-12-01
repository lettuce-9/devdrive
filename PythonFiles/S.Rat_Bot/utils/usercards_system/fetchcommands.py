import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1244518794710355978

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)

    global_cmds = await bot.tree.fetch_commands()
    print(f"\nGlobal commands ({len(global_cmds)}):")
    for cmd in global_cmds:
        print(f" - {cmd.name}")

    if guild:
        guild_cmds = await bot.tree.fetch_commands(guild=guild)
        print(f"\nGuild commands for {guild.name} ({len(guild_cmds)}):")
        for cmd in guild_cmds:
            print(f" - {cmd.name}")
    else:
        print(f"\nCould not find guild with ID {GUILD_ID}")

    await bot.close()

async def main():
    async with bot:
        await bot.start(token)

asyncio.run(main())
