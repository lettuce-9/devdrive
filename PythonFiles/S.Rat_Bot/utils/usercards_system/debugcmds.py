import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="d.", intents=intents)

token = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1244518794710355978

@bot.event
async def on_ready():
    print("Debug commands ready.")

@bot.command()
@commands.is_owner()
async def resync(ctx):
    load_msg = await ctx.send("<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **\n```\nNo logs yet...\n```")

    try:
        await bot.load_extension("usercards2")
    except commands.errors.ExtensionAlreadyLoaded:
        await bot.reload_extension("usercards2")
    
    try:
        await bot.load_extension("modlogs_system")
    except commands.errors.ExtensionAlreadyLoaded:
        await bot.reload_extension("modlogs_system")


    synced_global = await bot.tree.sync()
    await load_msg.edit(content=f"<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nAttempting to guild sync...\n```")

    synced_guild = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await load_msg.edit(content=f"<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\n```")
    await load_msg.edit(content=f"<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\nAttempting to close cogs...\n```")

    try:
        await bot.unload_extension("usercards2")
        await bot.unload_extension("modlogs_system")
        await load_msg.edit(content=f"<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\nClosed cogs successfully.\n```")
    except Exception as exc:
        await load_msg.edit(content=f"<a:loadinganim:1393847961397497958> Syncing commands...\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\nFailed to close cogs : {exc}\n```")
        await asyncio.sleep(0.25)
        await load_msg.edit(content=f"<:sts_info:1402277598171627551> <:sts_no:1402277277672276068> Failed to resync commands : **`{exc}`**\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\nFailed to close cogs : {exc}\n```")
        return

    await asyncio.sleep(0.5)

    await load_msg.edit(content=f"<:sts_yes:1402277268398542940> ***Successfully resynced slash commands.***\n\n**Logs : **```\nGlobally synced {len(synced_global)} commands.\nGuild synced {len(synced_guild)} commands to {GUILD_ID}.\nClosed cogs successfully.\n```")

bot.run(token)
