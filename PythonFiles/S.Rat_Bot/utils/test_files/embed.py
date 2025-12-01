import discord
import time
from discord import Embed
from colorama import init, Fore, Style
import os
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_TOKEN")

# Create an instance of a client
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    
    print(Fore.BLUE + Style.BRIGHT + '[INFO]' + Fore.RESET + Style.RESET_ALL + f' : Logged in as {client.user}')
    time.sleep(0.5)
    print(f'Embed will be sent shortly!')
    print(Fore.YELLOW + Style.BRIGHT + '[WARN]' + Fore.RESET + Style.RESET_ALL + ' : This message will be sent in #Staff-Discussion.')

    time.sleep(1.5)
    # Create an embed object
    cleancard_embed = Embed(
        description="-# **USER CARD WARN EXAMPLE**\n## USER CARD\nUser ID : [`{user.id}`]\nUser : [`<@{user.id}>`]\n\n* ***Active Warns*** : [Nothing to see here...]\n***Moderator*** : `<@{mod_user_ID}>`\n  * ***Moderator Note*** : [Nothing to see here...]\n- ***Warn expiration (if any)*** : [Nothing to see here...]\n\n",
        color=0x0099FF
        )
    
    warned_embed = Embed(
    description="-# **___USER CARD WARN EXAMPLE___**\n## USER CARD\nUser : <@1377979264946671728>\nUser ID : 1377979264946671728\n\n***Active Warns*** : [Warn 1]\n***Moderator*** : <@945608534010241024>\n***Moderator Note*** : [Spammed in <#1244518794710355981>]\n***Warn expiration (if any)*** : <t:1751099700:R>, <t:1751099700:f>",
    color=0x0099FF
    )
    
    channel = client.get_channel(1369978345931935795)  # Replace with the channel ID
    await channel.send(embed=cleancard_embed)
    await channel.send(embed=warned_embed)

client.run(token)