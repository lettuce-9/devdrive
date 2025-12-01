# main.py

import discord
from discord.ext import tasks, commands
import os
import asyncio
from keep_alive import keep_alive
import internalroute
keep_alive()

token=os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = 1244518794710355978
VC_CHANNEL_ID = 1378020189676769403
GENERAL_ID = 1244518794710355981

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    guild = bot.get_guild(GUILD_ID)
    general = await bot.fetch_channel(GENERAL_ID)
    await general.send(f'`Raw Permissions Integer : {guild.me.guild_permissions.value}`')
    await asyncio.sleep(0.25)
    update_member_count.start()



@tasks.loop(minutes=1)  # update every 60s
async def update_member_count():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Guild not found.")
        return

    non_bot_members = [m for m in guild.members if not m.bot]
    count = len(non_bot_members)

    channel = guild.get_channel(VC_CHANNEL_ID)
    if channel: 
        new_name = f"Members: {count}"
        if channel.name != new_name:
            await channel.edit(name=new_name)
            print(f"Channel name updated to: {new_name}")
    else:
        print("Channel not found.")

bot.run(token)
