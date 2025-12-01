import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)
token = os.getenv("DISCORD_TOKEN")

emojis = {
    "first": {
        "empty": "<:empty1:1409150275922694175>",
        "quarter": "<:quarter1:1409150409439842414>",
        "half": "<:half1:1409150337213796454>",
        "threequarters": "<:threequarters1:1409150440146337892>",
        "full": "<:full1:1409150310542348391>",
    },
    "middle": {
        "empty": "<:empty2:1409150296663396363>",
        "quarter": "<:quarter2:1409150419854426266>",
        "half": "<:half2:1409150351134953480>",
        "threequarters": "<:threequarters2:1409150451458375721>",
        "full": "<:full2:1409150318884950188>",
    },
    "last": {
        "empty": "<:empty3:1409150302283894925>",
        "quarter": "<:quarter3:1409150429560049664>",
        "half": "<:half3:1409150397989388400>",
        "threequarters": "<:threequarters3:1409150461248016415>",
        "full": "<:full3:1409150327789457540>",
    }
}

def build_progress_bar(current, total, length=10):
    percent = current / total
    filled_segments = percent * length
    bar = ""

    for i in range(length):
        if i == 0:
            set_type = "first"
        elif i == length - 1:
            set_type = "last"
        else:
            set_type = "middle"

        if filled_segments >= i + 1:
            bar += emojis[set_type]["full"]
        elif filled_segments > i:
            fraction = filled_segments - i
            if fraction >= 0.75:
                bar += emojis[set_type]["threequarters"]
            elif fraction >= 0.5:
                bar += emojis[set_type]["half"]
            elif fraction >= 0.25:
                bar += emojis[set_type]["quarter"]
            else:
                bar += emojis[set_type]["empty"]
        else:
            bar += emojis[set_type]["empty"]

    return bar

@bot.command()
async def testProgressBar(ctx):
    current_time = 75  # seconds
    total_time = 300   # seconds
    bar = build_progress_bar(current_time, total_time)

    embed = discord.Embed(title="Test Progress Bar", color=discord.Color.blue())
    embed.add_field(name="Progress", value=bar, inline=False)
    embed.set_footer(text=f"{current_time}s / {total_time}s")

    await ctx.send(embed=embed)

@bot.command()
async def test1(ctx):
    embed = discord.Embed(
        description="Placeholder\n\n**`0:00`** <:pixilframe0:1409411734271299584><:pixilframe01:1409412001163247718><:pixilframe02:1409412639246778368><:pixilframe03:1409413056030707803> **`4:04`**>",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)
    await asyncio.sleep(0.15)
    await ctx.send("Placeholder\n\n**`0:00`** <:pixilframe0:1409411734271299584><:pixilframe01:1409412001163247718><:pixilframe02:1409412639246778368><:pixilframe03:1409413056030707803> **`4:04`**")

bot.run(token)