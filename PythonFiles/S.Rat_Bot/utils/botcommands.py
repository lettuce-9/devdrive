import discord
from discord import Embed
from discord.ext import commands
import os
from dotenv import load_dotenv
import random

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
VERSION = ("Alpha v1.1.2") # note: update 2nd digit every major release and 3rd digit every minor release

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

class LinkToBotStatus(discord.ui.View):
    def __init__(self, cog, target: discord.Member, url: str):
        super().__init__()
        self.cog = cog
        self.target = target

        self.add_item(discord.ui.Button(
            label="Bot Status Website", 
            style=discord.ButtonStyle.link, 
            url="https://stats.uptimerobot.com/BaYUBaKb0y/800642392"
        ))

@bot.event
async def on_ready():
    print(f"{bot.user} is connected to Discord")
    channel_id = 1244518794710355981
    channel = bot.get_channel(channel_id)
    embed = discord.Embed(
        description=f"### ⚠️ **{bot.user} is in debug. Text commands are __temporarily enabled.__**\nVersion : **`{VERSION}`**",
        color=0x00FFAA
    )
    embedview = LinkToBotStatus(cog=None, target=None, url="https://stats.uptimerobot.com/BaYUBaKb0y/800642392")
    await channel.send(embed=embed, view=embedview)


@bot.command(help="Lists all available commands.")
async def commands(ctx):
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

    command_list = [
        f'`!{cmd.name}` - {cmd.help or "*No description*"}'
        for cmd in bot.commands if not cmd.hidden
    ]

    embed = discord.Embed(
        title="Available Commands",
        description="\n".join(command_list),
        color=0x00FFAA
    )
    await ctx.send(embed=embed)

@bot.command(help="Send a image")
async def stare(ctx):
    await ctx.send(file=discord.File("images/meauw.png"))
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

@bot.command(help="Send a image")
async def gubby(ctx):
    await ctx.send(file=discord.File("images/gubby.png"))
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

@bot.command(help="Send a image")
async def checkit(ctx):
    await ctx.send(file=discord.File("images/checkit.png"))
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

@bot.command(help="Send a image")
async def jumpscare(ctx):
    await ctx.send(file=discord.File("images/jumpscare.png"))
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

@bot.command(help="Send a image")
async def oyes(ctx):
    await ctx.send(file=discord.File("images/oyes.png"))
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)

@bot.command(help="Show current bot version")
async def version(ctx):
    embed = discord.Embed(
        description=f"**{bot.user}'s version :** **`{VERSION}`**",
        color=0xFFFFC5
    )
    await ctx.send(embed=embed)

quotes = [
    "“gng theres actually someone who loves me... the voices in my head ❤”\n–HelloCube", # quote 1
    "“I like tickling feet”\n –Kosu", # quote 2
    "“sussy the fish”\n –Haz", # quote 3
    "“cartride into 17 pregnant hyenas”\n –???", # quote 4
    "“mewo~ I am a femboy~~”\n –HelloCube", # quote 5
    "“leak his feet pics”\n –Kosu", # quote 6
    "“im emo now bro, i color my goat dark color”\n –Jeb", # quote 7
    "“they better put the freaky emotion in inside out 3”\n –Mosu", # quote 8
    "“kosu with homeless chance skin”\n –Kane", # quote 9
    "“who wanna play freaksaken 👅👅👅👅👅👅👅👅”\n –Drip", # quote 10
    "“ew you like that fucking obese piece of shit”\n –Mosu", # quote 11
    "“kaki actually wants her toes to be tickled and licked 💔”\n –Jed", # quote 12
    "“Miku feet hangout better”\n –Heavenly", # quote 13
    "“dih means d - dreaded i - inclusive h - human”\n –kosu", # quote 14
    "“freak mode… engage!”\n –Mosu", # quote 15
    "“why tf is there a fish nicknamed big daddy <:ufarted:1366362019632123995> <:ufarted:1366362019632123995> ”\n –Physics", # quote 16
    "“I ate 5 sanghai”\n –Kaki", # quote 17
    "“I like licking people’s toes”\n –Mosu", # quote 18
    "“i am going to tickle yo toes”\n –Physics", # quote 19
    "-# Replying to Kaki : I clean it with soap while suzi scrubs it\n“i lick it too”\n –Kosu", # quote 20
    "“ts all we have gng”\n –Lettuce", # quote 21
    "“ill tickle ur feet pls”\n –Drip", # quote 22
    "“It was physics he wants to gobble ur toes”\n –Cel", # quote 23
    "“Physics x kosu”\n –Heavenly", # quote 24
    "“i wanna eat lettuce”\n –Physics", # quote 25
    "“i wanna become a drug lord”\n –Heavenly", # quote 26
    "“i checked and i didnt wash my ass”\n –Physics", # quote 27
    "“you said something along the lines of “i am gonna send this flower to my crush” and then sends a picture of you holding a sunflower from roblox grow a garden”\n –Physics", # quote 28
    "“WERE GONNA PUT OUR TOES IN YOUR MOUTH IF U DONT GIVE HAZ 4K”\n –Drip", # quote 29
    "“damn cel\nyou laugh so loud”\n –Kosu" # quote 30
]

@bot.command(help="Get random quotes from the server.")
async def randquote(ctx):
#    embed = discord.Embed(
#        description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#        color=0x8B0000
#    )
#    await ctx.send(embed=embed, ephemeral=True)
    quote = random.choice(quotes)
    embed = Embed(
        description=f"*{quote}*",
        color=0x0099FF  
    )
    await ctx.send(embed=embed)


@bot.command()
async def randpercent(ctx):
#    embed = discord.Embed(
#    description=f"## Maintenance is in progress.\nCommands like this are temporarily disabled.",
#    color=0x8B0000
#)
#    await ctx.send(embed=embed, ephemeral=True)
    chosen = random.randint (0, 100)
    embed = Embed(
        description=f"{chosen}%",
        color=0x0099FF  
    )
    await ctx.send(embed=embed)

bot.run(token)
