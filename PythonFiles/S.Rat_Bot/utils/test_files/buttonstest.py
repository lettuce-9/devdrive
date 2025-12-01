import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

token=os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="tg?", intents=intents)

class ColorsTest(discord.ui.View):
    @discord.ui.button(label=None, emoji='<:vol_up_tr:1395681284197711932>', style=discord.ButtonStyle.secondary)
    async def button1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label=None, emoji='<:vol_down_tr:1395681259782537286>', style=discord.ButtonStyle.secondary)
    async def button2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

#    @discord.ui.button(label="danger ButtonStyle", style=discord.ButtonStyle.danger)
#    async def button3(self, interaction: discord.Interaction, button: discord.ui.Button):
#        await interaction.response.defer()
#
#    @discord.ui.button(label="success ButtonStyle", style=discord.ButtonStyle.success)
#    async def button4(self, interaction: discord.Interaction, button: discord.ui.Button):
#        await interaction.response.defer()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(1271852678086918279)

    if channel is None:
        print("Channel not found!")
        return

    embed = discord.Embed(
        #title="⚠️ Alert",
        description="coolio placeholder",
        color=discord.Color.blurple()
    )

    view1 = ColorsTest()
    await channel.send(embed=embed, view=view1)

@bot.command()
async def cemojis(ctx):
    await ctx.send("vol_up_tr <:vol_up_tr:1395681284197711932>\nvol_down_tr <:vol_down_tr:1395681259782537286>\nloop_tr <:loop_tr:1395677376440041482>\npopout <:popout:1395673338130464839>")

bot.run(token)
