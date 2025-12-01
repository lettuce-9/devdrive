import asyncio
import discord
import os
import yt_dlp
import time
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, button, Button
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_TOKEN")

version='Test Build 20'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="mb?", intents=intents, help_command=None)
tree = bot.tree

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel debug',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'auto',
}

volume = 0.5 # orig value was 1 but i want it to be 0.5 for temporary
queue = []
now_playing_message = None
now_playing_messages = {}
processing_message = None
current_source = None
current_track = {}
is_looping = False
user_volume_cooldowns = {}
VOLUME_COOLDOWN = timedelta(seconds=1.5)

CUSTOM_BARS = [
    "<:empty_bar:1396166217231896576>",
    "<:quarter_bar:1396166199821467710>",
    "<:half_bar:1396166182196740116>",
    "<:three_quarters_bar:1396166160378232932>",
    "<:full_bar:1396166135258550292>"
]

def get_bar_emoji(ratio):
    if ratio <= 0.10: return CUSTOM_BARS[0]
    if ratio <= 0.35: return CUSTOM_BARS[1]
    if ratio <= 0.60: return CUSTOM_BARS[2]
    if ratio <= 0.85: return CUSTOM_BARS[3]
    return CUSTOM_BARS[4]

def build_emoji_progress_bar(current, total, bar_length=10):
    ratio = current / total if total > 0 else 0
    filled_length = ratio * bar_length

    bar = ""
    for i in range(bar_length):
        segment_ratio = min(max(filled_length - i, 0), 1)
        bar += get_bar_emoji(segment_ratio)
    return f"`{format_time(current)}` - `{format_time(total)}`"

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02}"

def get_ffmpeg_options(volume):
    return {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "volume={volume}"'
    }

def create_audio_source(audio_url: str):
    ffmpeg_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
    return discord.PCMVolumeTransformer(ffmpeg_source, volume=volume)

def build_now_playing_embed(title, elapsed, duration, status=None, color=discord.Color.green()):
    bar = build_emoji_progress_bar(elapsed, duration)
    elapsed_fmt = format_time(elapsed)
    duration_fmt = format_time(duration)
    status_line = f"\n{status}" if status else ""

    embed = discord.Embed(
        description=f"Now playing: **`{title}`**{status_line}\n{elapsed_fmt} - {duration_fmt}",
        color=color
    )
    return embed

async def update_progress_bar(vc, ctx):
    await bot.wait_until_ready()

    guild_id = ctx.guild.id
    message = now_playing_messages.get(guild_id)
    if not message:
        return

    try:
        view = message.components[0] if message.components else None
        if not isinstance(view, BoomboxControls):
            return
    except discord.HTTPException as e:
        print(f"[update_progress_bar, discord.HTTPException] An error occured while trying to defer view : {e}")
    except Exception as e:
        print(f"[update_progress_bar, Exception] An error occured while trying to defer view : {e}")
    
    while vc.is_playing():
        await asyncio.sleep(1)

        if not current_track:
            continue

        try:
            elapsed = time.time() - current_track.get("start_time", time.time())
            duration = current_track.get("duration", 0)
        
            if view.volume_flash_active:
                status = f"**Volume**: `{view.volume_flash_value}%`"
                color = discord.Color.orange()
            else:
                status = None
                color = discord.Color.green()

            embed = build_now_playing_embed(
                current_track["title"],
                elapsed,
                duration,
                status=status,
                color=color
            )
        except discord.HTTPException as e:
            print(f"[update_progress_bar, discord.HTTPException] An error occured while trying to build embed : {e}")
        except Exception as e:
            print(f"[update_progress_bar, Exception] An error occured while trying to build: {e}")

        try:
            try:
                await message.edit(embed=embed, view=view)
            except discord.HTTPException as e:
                print(f"[update_progress_bar, discord.HTTPException] An error occured while trying to update seekbar : {e}")
            except Exception as e:
                print(f"[update_progress_bar, Exception]An error occured while trying to update seekbar : {e}")
        except discord.NotFound:
            print("[update_progress_bar] Message was deleted — stopping updates.")
            break


async def start_track(ctx, info):
    global current_track, current_source, queue

    current_track = info
    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS),
        volume=volume
    )
    current_track["start_time"] = time.time()
    current_source = source
    vc = ctx.voice_client

    def after_playing(error=None):
        if error:
            print("Error in after_playing:", error)
        if is_looping:
            coro = start_track(ctx, current_track)
        elif queue:
            next_track = queue.pop(0)
            coro = start_track(ctx, next_track)
        else:
            msg = now_playing_messages.get(ctx.guild.id)
            if msg:
                coro = msg.edit(
                    content=None,
                    embed=discord.Embed(description="Playback finished.", color=discord.Color.green()),
                    view=None
                )
                asyncio.run_coroutine_threadsafe(coro, bot.loop)


    vc.play(source, after=after_playing)

    if ctx.guild.id in now_playing_messages:
        try:
            await now_playing_messages[ctx.guild.id].delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    duration = info.get("duration", 0)
    bar = build_emoji_progress_bar(0, duration)
    embed = discord.Embed(
        description=f"Now playing: **`{info['title']}`**\n{bar}",
        color=discord.Color.green()
    )
    view = BoomboxControls(vc)
    msg = await ctx.send(embed=embed, view=view)
    now_playing_messages[ctx.guild.id] = msg

    asyncio.create_task(update_progress_bar(vc, ctx))

class BoomboxControls(discord.ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc
        self.volume_flash_active = False
        self.volume_flash_value = None
        self.volume_flash_task = None


    async def flash_volume_embed(self, interaction: discord.Interaction, vol_percent: int):
        self.volume_flash_active = True
        self.volume_flash_value = vol_percent

        title = current_track["title"]
        elapsed = time.time() - current_track.get("start_time", time.time())
        duration = current_track.get("duration", 0)

        embed = build_now_playing_embed(
            title=title,
            elapsed=elapsed,
            duration=duration,
            status=f"**Volume**: `{vol_percent}%`",
            color=discord.Color.orange()
        )

        try:
            await now_playing_messages[interaction.guild.id].edit(embed=embed, view=self)
        except discord.NotFound:
            return

        await asyncio.sleep(3)

        self.volume_flash_active = False
        self.volume_flash_value = None

        if now_playing_messages.get(interaction.guild.id):
            reverted = build_now_playing_embed(
                title=title,
                elapsed=time.time() - current_track.get("start_time", time.time()),
                duration=duration,
                color=discord.Color.green()
            )
            try:
                await now_playing_messages[interaction.guild.id].edit(embed=reverted, view=self)
            except discord.NotFound:
                return

    @button(label="⏸", style=ButtonStyle.primary)
    async def pause(self, interaction: Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            embed = await get_current_embed(interaction, "Paused")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @button(label="▶", style=ButtonStyle.success)
    async def resume(self, interaction: Interaction, button: Button):
        if self.vc.is_paused():
            self.vc.resume()
            embed = await get_current_embed(interaction, "Resumed")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing to resume.", ephemeral=True)

    @button(label="⏹", style=ButtonStyle.danger)
    async def stop(self, interaction: Interaction, button: Button):
        if self.vc.is_playing() or self.vc.is_paused():
            self.vc.stop()
            await interaction.response.send_message("Stopped current track", ephemeral=False)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @button(label=None, emoji="<:loop_track:1396006300747431936>", style=ButtonStyle.secondary)
    async def loop(self, interaction: Interaction, button: Button):
        global is_looping
        is_looping = not is_looping
        loop_status = "enabled" if is_looping else "disabled"
        await interaction.response.send_message(f"Looping {loop_status}!", ephemeral=True)

        embed = await get_current_embed(interaction, f"Loop {loop_status}")
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label=None, emoji="<:vol_down_track:1395742084492820620>", style=ButtonStyle.secondary, row=1)
    async def volume_down(self, interaction: Interaction, button: Button):
        global volume, user_volume_cooldowns, current_track, now_playing_message, current_source

        if volume <= 0.1:
            await interaction.response.send_message("Volume is already at minimum.", ephemeral=True)
            return

        volume = round(max(volume - 0.1, 0.0), 2)
        vol_percent = int(volume * 100)

        if current_source:
            current_source.volume = volume

        await interaction.response.defer(ephemeral=True)

        if self.volume_flash_task:
            self.volume_flash_task.cancel()
        try:
            await self.volume_flash_task
        except:
            pass

        self.volume_flash_task = asyncio.create_task(self.flash_volume_embed(vol_percent))

    @button(label=None, emoji="<:vol_up_track:1395742106437554236>", style=ButtonStyle.secondary, row=1)
    async def volume_up(self, interaction: Interaction, button: Button):
        global volume, user_volume_cooldowns, current_track, now_playing_message, current_source

        if volume >= 2.0:
            await interaction.response.send_message("Volume is already at max.", ephemeral=True)
            return

        volume = round(min(volume + 0.1, 2.0), 2)
        vol_percent = int(volume * 100)

        if current_source:
            current_source.volume = volume

        await interaction.response.defer(ephemeral=True)

        if self.volume_flash_task:
            self.volume_flash_task.cancel()
        try:
            await self.volume_flash_task
        except:
            pass

        self.volume_flash_task = asyncio.create_task(self.flash_volume_embed(vol_percent))

async def get_current_embed(interaction: Interaction, status: str):
    global current_track
    duration = current_track.get("duration", 0)
    elapsed = time.time() - current_track.get("start_time", time.time())
    return build_now_playing_embed(
        current_track["title"], elapsed, duration, status=status, color=discord.Color.blue()
    )

    return embed


@bot.event
async def on_ready():
    print(f"{bot.user} is connected to Discord")

@bot.command()
async def connect(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        ctx.voice_client.self_mute = True
    else:
        await ctx.send("what")

@bot.command()
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("im gone")
    else:
        await ctx.send("huh")

@bot.command()
async def play(ctx, *, url: str = None):
    global current_track, queue, volume, current_source

    if not url:
        embed = discord.Embed(
            title="Error 400",
            description="You provided an invalid YouTube URL.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    processing_message = await ctx.send("<a:loadinganim:1393847961397497958> Processing media...")

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            embed = discord.Embed(
                title="Error 400",
                description="You are currently not in a voice channel.",
                color=discord.Color.red()
            )
            await processing_message.edit(content=None, embed=embed)
            return

    vc = ctx.voice_client

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        audio_url = None
        for f in formats:
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                audio_url = f["url"]
                break
        if not audio_url:
            embed = discord.Embed(
                title="Error 500",
                description="Couldn't extract audio stream.",
                color=discord.Color.red()
            )
            await processing_message.edit(content=None, embed=embed)
            return

    info["url"] = audio_url

    if vc.is_playing() or vc.is_paused():
        queue.append(info)
        embed = discord.Embed(
            description=f"Queued: **`{info['title']}`**", color=discord.Color.orange()
        )
        await processing_message.edit(content=None, embed=embed)
        await asyncio.sleep(3)
        try:
            await processing_message.delete()
        except discord.NotFound:
            pass
        return

    current_track = info
    current_source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(info["url"], **FFMPEG_OPTIONS),
        volume=volume
    )

    guild_id = ctx.guild.id
    now = discord.utils.utcnow()

    if guild_id in now_playing_messages:
        existing = now_playing_messages[guild_id]
        if (now - existing.created_at).total_seconds() > 30:
            try:
                await existing.delete()
            except discord.NotFound:
                pass

    duration = info.get("duration", 0)
    bar = build_emoji_progress_bar(0, duration)

    embed = discord.Embed(
        description=f"Now playing: **`{info['title']}`**\n{bar}",
        color=discord.Color.green()
    )


    view = BoomboxControls(vc)
    message = await ctx.send(embed=embed, view=view)
    now_playing_messages[ctx.guild.id] = message

    await processing_message.delete()

    await start_track(ctx, info)

    asyncio.create_task(update_progress_bar(vc, ctx))

@bot.command()
async def ver(ctx):
    embed = discord.Embed(
        description=f"Music Bot [MB] version : **`{version}`**",
        color=discord.Color.dark_teal()
    )
    await ctx.send(embed=embed)

bot.run(token)