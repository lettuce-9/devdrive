import discord
import os
from discord import Embed
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_TOKEN")

table = """\
Tori = **Average: 9.38**, Combined Total: 37.5

Iza = **Average: 9.03**, Combined Total: 36.1

Kosu = **Average: 9.17**, Combined Total: 27.5

Cel = **Average: 8.48**, Combined Total: 34.0

Lettuce = **Average: 7.90**, Combined Total: 31.6

Jeb = **Average: 7.00**, Combined Total: 28

Drip = **Average: 6.00**, Combined Total: 12

Cube & Haz = **Average: 5.80**, Combined Total: 29
"""
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    example_embed = Embed(
        description=f"## S. Rats Talent Show has officialy ended!\nS. Rats Talent Show 🧀 has ended, and here are the results!\n\n-# Sorted **highest average** to **lowest.**\n{table}-# **Names that have a [Insufficient] tag at the end means that all the judges didn't rate their performances.**\n**Duration** : <t:1748674800:t> to <t:1748678880:t> **[1 hr 8 min]**",
        color=0x0099FF
    )

    channel = client.get_channel(1244528433720066079)
    if channel:
        await channel.send(f"@everyone", embed=example_embed)
    else:
        print("Channel not found")


client.run(token)
