import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_TOKEN")
openrouterkey = os.getenv("OPENROUTER_API_KEY")

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

@bot.command()
async def connect(ctx):
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
        await voice_channel.connect()
        await ctx.send("hi i am here now")

    else:
        await ctx.send("huh")

bot.run(token)