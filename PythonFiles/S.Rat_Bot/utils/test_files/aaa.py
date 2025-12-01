import discord
from discord.ext import commands
import qrcode
from PIL import Image
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=intents)
token = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.command(name="createQR")
async def generate_qr(ctx, *, data: str):
    try:
        qr = qrcode.QRCode(version=3, box_size=8, border=8)
        qr.add_data(data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill="black", back_color="white")

        filename = f"qr_{ctx.message.id}.png"
        qr_image.save(filename)

        try:
            with open(filename, "rb") as file:
                await ctx.send(file=discord.File(file, filename=filename))
        except discord.Forbidden:
            encoded_data = quote_plus(data)
            qr_link = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded_data}&size=200x200"
            await ctx.send(f"-# {qr_link}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    except Exception as e:
        await ctx.send(f"Failed to generate QR code: {e}")

bot.run(token)
