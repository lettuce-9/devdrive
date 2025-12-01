import discord
import os
from dotenv import load_dotenv
from discord.ui import button, Button
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="sample?", intents=intents)
token = os.getenv("DISCORD_TOKEN")

MOD_ROLE_ID = 1367831532240371722
ALLOWED_USER_IDS = [] # leave as blank, for special access

class EvalButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def is_mod(self, user: discord.User) -> bool:
        if any(role.id == MOD_ROLE_ID for role in user.roles):
            return True
        if user.id in ALLOWED_USER_IDS:
            return True
        return False
    
    async def check_permissions(self, interaction: Interaction) -> bool:
        if not self.is_mod(interaction.user):
            await interaction.response.send_message("<:sts_denied:1402277571483275294> You do not have permission to use this button.", ephemeral=False)
            return False
        return True

    @button(label=None, emoji="<:sts_previous:1405150279481163897>", style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, button: Button):
        if not await self.check_permissions(interaction):
            return
        await interaction.response.defer()

    @button(label=None, emoji="<:sts_no:1402277277672276068>", style=ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        await interaction.response.defer()

    @button(label=None, emoji="<:sts_yes:1402277268398542940>", style=ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        if not await self.check_permissions(interaction):
            return        
        await interaction.response.defer()

    @button(label=None, emoji="<:sts_skip:1405150298216992808>", style=ButtonStyle.secondary)
    async def skip(self, interaction: Interaction, button: Button):
        if not await self.check_permissions(interaction):
            return
        await interaction.response.defer()

@bot.event
async def on_ready():
    print(f"{bot.user} is connected to Discord")

@bot.command()
async def evalquotes(ctx):
    embed = discord.Embed(
        title='Suggested commands | Page 1 of 10',
        description=f'*“hi yes hi hi”*\n*– @user*',
        color=0x4D5467
    )
    try:
        view = EvalButtons()
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"<:sts_info:1402277598171627551> Embed failed to send : **`{str(e)}`**")

bot.run(token)