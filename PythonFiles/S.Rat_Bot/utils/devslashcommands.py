import discord
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
appID = int(os.getenv("APP_ID"))
guild_id = int(os.getenv("MAIN_GUILD_ID"))
guild = discord.Object(id=guild_id)

# Context Menu Commands
@app_commands.context_menu(name="Get User ID")
async def get_user_id(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(
        f"User ID: \n```{user.id}```\n-# You can click the copy icon in the top right corner.",
        ephemeral=True
    )

@app_commands.context_menu(name="Fetch Message ID")
async def get_message_id(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(
        f"Message ID: ```{message.id}```\n-# You can click the copy icon in the top right corner.",
        ephemeral=True
    )

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="t!",
            intents=discord.Intents.all(),
            application_id=appID
        )

    async def setup_hook(self):
        @app_commands.context_menu(name="Get User ID")
        async def get_user_id(interaction: discord.Interaction, user: discord.User):
            await interaction.response.send_message(
                f"User ID of {user.name}: `{user.id}`", ephemeral=True
            )

        @app_commands.context_menu(name="Fetch Message ID")
        async def get_message_id(interaction: discord.Interaction, message: discord.Message):
            await interaction.response.send_message(
                f"Message ID: ```{message.id}```", ephemeral=True
            )

        self.tree.clear_commands(guild=guild)
        self.tree.add_command(get_user_id)
        self.tree.add_command(get_message_id)
        await self.tree.sync(guild=guild)
        print("[setup_hook] Synced commands successfully.")

    async def on_ready(self):
        print(f"[on_ready] {self.user} is connected to Discord")

bot = MyBot()



@bot.command()
@commands.is_owner()
async def tree_remove_commands(ctx):
    try:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        await ctx.send("Cleared all commands from the command tree.")
        print("[tree_remove_commands] Cleared all guild commands.")
    except Exception as e:
        await ctx.send(f"An error occurred while trying to clear the bot tree : **`{e}`**")
        print(f"[tree_remove_commands] Error: {e}")

@bot.command()
@commands.is_owner()
async def tree_add_commands(ctx):
    loading_message = await ctx.send("<a:loadinganim:1393847961397497958> Fetching bot.tree commands...")
    try:
        bot.tree.clear_commands(guild=guild)

        bot.tree.add_command(get_user_id)
        bot.tree.add_command(get_message_id)

        await bot.tree.sync(guild=guild)
        await loading_message.edit(content="Added commands to bot.tree successfully.")
        print("[tree_add_commands] Added and synced commands.")
    except Exception as e:
        await loading_message.edit(content=f"Failed to add commands to bot.tree. {e}")
        print(f"[tree_add_commands] Error: {e}")

@bot.command(name="show_synced_commands")
@commands.is_owner()
async def show_synced_commands(ctx):
    try:
        commands_list = await bot.tree.fetch_commands(guild=guild)

        if not commands_list:
            await ctx.send("No commands found in the bot's command tree for this guild.")
            print("[tree_show_synced_commands] No commands synced.")
            return

        formatted = "\n".join(f"- `{cmd.name}` ({type(cmd).__name__})" for cmd in commands_list)
        await ctx.send(f"Synced commands in the tree for this guild:\n{formatted}")
        print(f"[tree_show_synced_commands] {len(commands_list)} commands found.")

    except Exception as e:
        await ctx.send(f"Failed to fetch synced commands: `{e}`")
        print(f"[tree_show_synced_commands] Error: {e}")

bot.run(token)
