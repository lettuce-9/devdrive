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
    print(Fore.BLUE + Style.BRIGHT + '[INFO]' + Fore.RESET + Style.RESET_ALL + ' : Embed will be sent shortly!')
    print(Fore.YELLOW + Style.BRIGHT + '[WARN]' + Fore.RESET + Style.RESET_ALL + f' : Message will be sent in #rules.')

    time.sleep(1.5)
    example_embed = Embed(
        # title='Placeholder',
        description='## Maintenance is in progress.\nCommands like this are temporarily disabled.',
        color=0x319D54# Change to any color using hex, ex. [0022FF]
        )
  
    
    # example_embed.set_author(
    #     name='author',
    # )

    # example_embed.add_field(name='Regular field title', value='Some value here')

    # example_embed.timestamp = discord.utils.utcnow()

    # example_embed.set_footer(
    #     text='latest update',
    # )

    # Get the channel (replace with the channel ID of your bot's server)
    channel = client.get_channel(1355794063349252187)  # Replace with the channel ID
    await channel.send(embed=example_embed)

client.run(token)