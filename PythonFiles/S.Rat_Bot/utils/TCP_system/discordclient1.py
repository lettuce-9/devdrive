import discord
from discord.ext import commands
import socket
import time
import os
from threading import Thread
import asyncio
from colorama import init, Fore, Style
from dotenv import load_dotenv

class DiscordBridge:
    bot = None
    channel = None

    @classmethod
    def set_channel(cls, ch):
        cls.channel = ch

    @classmethod
    def set_bot(cls, b):
        cls.bot = b

    @classmethod
    def send_message(cls, content):
        if cls.channel and cls.bot:
            asyncio.run_coroutine_threadsafe(cls.channel.send(content), cls.bot.loop)

active_channel = None
tcp_server_process = None
load_dotenv()

token=os.getenv("DISCORD_TOKEN")
serv_ip = os.getenv("SERVER_IP")
port_ip = os.getenv("PORT_IP")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and connected to Discord!")

@bot.command(help="Lists all available TCP commands.")
async def TCPcommands(ctx):
    command_list = [
        f'`.{cmd.name}` - {cmd.help or "*No description*"}'
        for cmd in bot.commands if not cmd.hidden
    ]

    embed = discord.Embed(
        title="Available TCP Commands",
        description="\n".join(command_list),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.command(help="Ping To A Live Server")
async def TCPping1(ctx):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    DiscordBridge.set_channel(ctx.channel)
    DiscordBridge.set_bot(bot)
    try:
        client_socket.connect((f'{serv_ip}', int(port_ip)))
    except Exception as e:
        await ctx.send(f"An error occured while trying to connect to the server : **`{e}`**\n-# Binded Port : **`{port_ip}`**")

    message = ["Send Client1DiscordMessage"]
    for msg in message:
        client_socket.sendall(msg.encode())
        time.sleep(2)

    client_socket.close()
    await ctx.send("<:localindc:1386697415847051304>Sent Signal1 To Server.")

@bot.command(help="Ping To A Live Server")
async def TCPping2(ctx):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((f'{serv_ip}', int(port_ip)))
    except Exception as e:
        await ctx.send(f"An error occured while trying to connect to the server : **`{e}`**\n-# Binded Port : **`{port_ip}`**")

    message = ["Send Client2DiscordMessage"]
    for msg in message:
        client_socket.sendall(msg.encode())
        time.sleep(2)

    client_socket.close()
    await ctx.send("<:localindc:1386697415847051304>Sent Signal2 To Server.")

@bot.command(help="Ping To A Live Server")
async def TCPping3(ctx):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((f'{serv_ip}', int(port_ip)))
    except Exception as e:
         await ctx.send(f"An error occured while trying to connect to the server : **`{e}**\n-# Binded Port : **`{port_ip}`**")

    message = ["Send Client3DiscordMessage"]
    for msg in message:
        client_socket.sendall(msg.encode())
        time.sleep(2)

    client_socket.close()
    await ctx.send("<:localindc:1386697415847051304>Sent Signal3 To Server.")

@bot.command(help="Shutdown Server")
async def TCPterminate(ctx):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((f'{serv_ip}', int(port_ip)))
    except Exception as e:
        await ctx.send(f"An error occured while trying to connect to the server : **`{e}`**\n-# Binded Port : **`{port_ip}`**")

    message = ["C205"]
    for msg in message:
        client_socket.sendall(msg.encode())
        time.sleep(2)

    client_socket.close()
    await ctx.send(f"Sent Disconnect Signal To Server.\n-# Code : **`205`** Port : **`{port_ip}`**")

bot.run(token)