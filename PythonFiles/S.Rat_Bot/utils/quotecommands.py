import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import os
load_dotenv()

QUOTE_FILE = "quotes.json"
MOD_ROLE_ID = 1367831532240371722
ACCESS_USER_IDS = [945608534010241024]

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="tst?", intents=intents)
token = os.getenv("DISCORD_TOKEN")

def load_quotes():
    if not os.path.exists(QUOTE_FILE):
        return []
    with open(QUOTE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_quotes(quotes):
    with open(QUOTE_FILE, "w") as f:
        json.dump(quotes, f, indent=4)

@bot.command(name="suggestquote")
async def suggestquote(ctx):
    if not ctx.message.reference:
        return await ctx.send("Please reply to a message to suggest it as a quote.")
    
    try:
        replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("Could not fetch the replied message.")

    quotes = load_quotes()
    quote_data = {
        "quote": replied_msg.content,
        "author_id": replied_msg.author.id,
        "author_name": str(replied_msg.author)
    }
    quotes.append(quote_data)
    save_quotes(quotes)

    embed = discord.Embed(
        title=f"Suggested quote out of {len(quotes)}",
        description=f"*{replied_msg.content}*\n*– <@{replied_msg.author.id}>*"
    )
    await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))

class EvaluateView(discord.ui.View):
    def __init__(self, quotes, user_id):
        super().__init__()
        self.quotes = quotes
        self.index = 0
        self.user_id = user_id
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.index == 0
        self.children[3].disabled = self.index == len(self.quotes) - 1

    def get_embed(self):
        quote = self.quotes[self.index]
        return discord.Embed(
            title=f"Suggested quote {self.index + 1} out of {len(self.quotes)}",
            description=f"*{quote['quote']}*\n*– <@{quote['author_id']}>*"
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_roles = [role.id for role in interaction.user.roles]
        user_id = interaction.user.id

        if MOD_ROLE_ID not in user_roles and user_id not in ACCESS_USER_IDS:
            await interaction.response.send_message(
                "<:sts_denied:1402277571483275294> You are not authorized to evaluate quotes.\n-# **This command is currently access limited.**",
                ephemeral=True
            )
            return False

        return True


    @discord.ui.button(label=None, emoji="<:sts_previous:1405150279481163897>", style=discord.ButtonStyle.secondary, row=1)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=None, emoji="<:sts_no:1402277277672276068>", style=discord.ButtonStyle.danger, row=1)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.quotes:
            await interaction.response.send_message("No quotes to evaluate.", ephemeral=True)
            return

        self.quotes.pop(self.index)
        save_quotes(self.quotes)

        if not self.quotes:
            await interaction.followup.send("<:sts_info:1402277598171627551> All quotes evaluated.", ephemeral=True)
            await interaction.message.delete()
            return

        if self.index >= len(self.quotes):
            self.index = len(self.quotes) - 1

        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Placeholder (Stop Evaluating)", emoji=None, style=discord.ButtonStyle.primary, row=2)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "<:sts_info:1402277598171627551> Evaluation session stopped.",
            ephemeral=True
        )
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label=None, emoji="<:sts_yes:1402277268398542940>", style=discord.ButtonStyle.success, row=1)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        approved_quote = self.quotes.pop(self.index)
        save_quotes(self.quotes)
        if self.index >= len(self.quotes):
            self.index = max(len(self.quotes) - 1, 0)
        self.update_buttons()
        if self.quotes:
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.followup.send("<:sts_info:1402277598171627551> All quotes evaluated.", ephemeral=True)
            await interaction.message.delete()

    @discord.ui.button(label=None, emoji="<:sts_skip:1405150298216992808>", style=discord.ButtonStyle.secondary, row=1)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

@bot.command(name="evalquotes")
async def evalquotes(ctx):
    if MOD_ROLE_ID not in [role.id for role in ctx.author.roles] and ctx.author.id not in ACCESS_USER_IDS:
        return await ctx.send("<:sts_denied:1402277571483275294> You are not authorized to use this command.\n-# **This command is currently access limited.**")

    
    quotes = load_quotes()
    if not quotes:
        return await ctx.send("<:sts_info:1402277598171627551> No quotes to evaluate.")

    view = EvaluateView(quotes, ctx.author.id)
    await ctx.send(embed=view.get_embed(), view=view, allowed_mentions=discord.AllowedMentions(users=False))

bot.run(token)
