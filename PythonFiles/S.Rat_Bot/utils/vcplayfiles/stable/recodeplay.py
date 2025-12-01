import discord, os, asyncio, time
from discord.ext import commands
from discord.ui import View, button, Button
from discord import Interaction, ButtonStyle, FFmpegPCMAudio
from colorama import init, Fore, Style
import yt_dlp
import re
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True
TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="mb?", intents=intents)

init(autoreset=True)

current_track = {}
now_playing_messages = {}
flyout_status = {}
progress_update_tasks = {}
volume = 0.7
is_looping = False
queue = []

EMOJI_BAR = {
    "empty": ["<:empty1:1409422370976043008>", "<:empty2:1409422379506995282>", "<:empty3:1409422396183679099>"],
    "quarter": ["<:quarter1:1409422427405942784>", "<:quarter2:1409422439640862810>", "<:quarter3:1409422450688655360>"],
    "half": ["<:half1:1409422469734862891>", "<:half2:1409422482297061447>", "<:half3:1409422496649838733>"],
    "threequarters": ["<:threequarters1:1409422521111023657>", "<:threequarters2:1409422531370418268>", "<:threequarters3:1409422547447058462>"],
    "full": ["<:full1:1409422552060657754>", "<:full2:1409422560936067072>", "<:full3:1409422571195334723>"]
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -loglevel quiet'
}

YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'default_search': 'ytsearch',
    'force-ipv4': True
}


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02}"

def build_detailed_progress_bar(progress_ratio, total_slots=10):
    exact_progress = progress_ratio * total_slots
    bar = []
    for i in range(total_slots):
        slot_ratio = exact_progress - i
        if slot_ratio >= 1:
            key = "full"
        elif slot_ratio >= 0.75:
            key = "threequarters"
        elif slot_ratio >= 0.5:
            key = "half"
        elif slot_ratio >= 0.25:
            key = "quarter"
        else:
            key = "empty"
        emoji = EMOJI_BAR[key][0 if i == 0 else 2 if i == total_slots - 1 else 1]
        bar.append(emoji)
    return "".join(bar)

def build_now_playing_embed(title, elapsed, duration, status="", color=discord.Color.green()):
    progress_ratio = max(0, min(elapsed / duration if duration else 0, 1.0))
    progress_bar = build_detailed_progress_bar(progress_ratio)
    embed = discord.Embed(title="Now Playing", color=color)
    embed.add_field(name="Track", value=f"`{title}`", inline=False)
    embed.add_field(name="Progress", value=f"`{format_time(elapsed)}` {progress_bar} `{format_time(duration)}`", inline=False)
    if status:
        embed.set_footer(text=status)
    return embed

def normalize_url(query: str) -> str:
    if "youtube.com" in query or "youtu.be" in query:
        query = re.sub(r"^(https?://)?(www\.)?", "", query)
        # Rebuild the full URL
        print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "[DEBUG]     " + Fore.RESET + Style.RESET_ALL + f"Detected '{query}' as a YouTube URL{Style.RESET_ALL}")  # Debug log in green
        return f"https://www.{query}"
    else:
        print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "[DEBUG]     " + Fore.RESET + Style.RESET_ALL + f"Detected '{query}' as a search query{Style.RESET_ALL}")  # Debug log in yellow
        return f"https://www.youtube.com/results?search_query={query}"

async def update_progress_bar(vc, ctx, view: "BoomboxControls"):
    await bot.wait_until_ready()
    guild_id = ctx.guild.id
    message = now_playing_messages.get(guild_id)

    if not message:
        return

    while True:
        await asyncio.sleep(0.5)  # smaller sleep to update more frequently

        if not vc.is_connected():
            break

        if not (vc.is_playing() or current_track.get("paused")):
            try:
                await message.edit(
                    embed=discord.Embed(description="Finished playback.", color=discord.Color.green()),
                    view=None
                )
            except discord.NotFound:
                pass
            break

        try:
            title = current_track.get("title", "Unknown")
            start_time = current_track.get("start_time", time.time())
            duration = current_track.get("duration", 0)

            if current_track.get("paused"):
                elapsed = current_track.get("pause_time", time.monotonic()) - current_track["start_time"]
                embed = build_now_playing_embed(title, elapsed, duration, "Paused", discord.Color.orange())
            else:
                elapsed = time.monotonic() - current_track["start_time"]
                embed = build_now_playing_embed(title, elapsed, duration)

            await message.edit(embed=embed, view=view)

        except Exception as e:
            print(f"[update_progress_bar] Error updating embed: {e}")
            continue

async def play_next(ctx):
    global queue
    vc = ctx.voice_client

    if vc.is_playing() or vc.is_paused():
        return

    next_track = None

    if is_looping and current_track:
        next_track = current_track.copy()
    elif queue:
        next_track = queue.pop(0)

    if next_track:
        audio = FFmpegPCMAudio(next_track["url"], **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(audio, volume=volume)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

        current_track.update({
            "title": next_track["title"],
            "duration": next_track["duration"],
            "start_time": time.monotonic(),
            "paused": False,
            "vc": vc,
            "source": source
        })

        embed = build_now_playing_embed(next_track["title"], 0, next_track["duration"])
        view = BoomboxControls(vc)

        message = now_playing_messages.get(ctx.guild.id)
        if message:
            await message.edit(embed=embed, view=view)
        else:
            message = await ctx.send(embed=embed, view=view)

        now_playing_messages[ctx.guild.id] = message
        old_task = progress_update_tasks.get(ctx.guild.id)
        if old_task and not old_task.done():
            old_task.cancel()
        asyncio.create_task(update_progress_bar(vc, ctx, view))
        progress_update_tasks[ctx.guild.id] = task

    else:
        message = now_playing_messages.get(ctx.guild.id)
        if message:
            try:
                await message.edit(
                    embed=discord.Embed(description="Finished playback.", color=discord.Color.green()),
                    view=None
                )
            except discord.NotFound:
                pass

        now_playing_messages.pop(ctx.guild.id, None)
        current_track.clear()


class BoomboxControls(View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc
        self.volume_flash_task = None

    async def flash_volume_embed(self, interaction, vol_percent):
        try:
            await asyncio.sleep(0.05)
            title = current_track.get("title", "Unknown")
            duration = current_track.get("duration", 0)
            start_time = current_track.get("start_time", time.monotonic())
            paused = current_track.get("paused", False)

            if paused:
                elapsed = time.monotonic() - current_track["start_time"]
                color = discord.Color.orange()
                footer = "Paused"
            else:
                elapsed = time.monotonic() - current_track["start_time"]
                color = discord.Color.green()
                footer = f"**Volume**: `{vol_percent}%`"

            embed = build_now_playing_embed(title, elapsed, duration, footer, color)
            msg = now_playing_messages.get(interaction.guild.id)
            if msg:
                await msg.edit(embed=embed, view=self)

            await asyncio.sleep(2.5)

            if paused:
                elapsed = time.monotonic() - current_track["start_time"]
                embed = build_now_playing_embed(title, elapsed, duration, "Paused", discord.Color.orange())
            else:
                elapsed = time.monotonic() - current_track["start_time"]
                embed = build_now_playing_embed(title, elapsed, duration)

            await msg.edit(embed=embed, view=self)

        except Exception as e:
            print(f"[flash_volume_embed] Error: {e}")
        finally:
            self.volume_flash_task = None

    @button(label="⏸", style=ButtonStyle.primary, row=1)
    async def pause(self, interaction: Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            print("Paused:", self.vc.is_paused())
            current_track["paused"] = True
            current_track["pause_time"] = time.monotonic()
            elapsed = time.monotonic() - current_track["start_time"]
            embed = build_now_playing_embed(current_track["title"], elapsed, current_track["duration"], "Paused", discord.Color.orange())
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing is playing. Did you mean **`resume`**?", ephemeral=True)

    @button(label="▶", style=ButtonStyle.success, row=1)
    async def resume(self, interaction: Interaction, button: Button):
        try:
            if self.vc.is_paused():
                self.vc.resume()
                paused_duration = time.monotonic() - current_track["pause_time"]
                current_track["start_time"] += paused_duration
                current_track["paused"] = False
                elapsed = time.monotonic() - current_track["start_time"]
                embed = build_now_playing_embed(current_track["title"], elapsed, current_track["duration"], "Resumed", discord.Color.green())
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("Nothing to resume. Did you mean **`pause`**?", ephemeral=True)
        except Exception as e:
            print(f"[resume button] Error: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @button(label="⏹", style=ButtonStyle.danger, row=1)
    async def stop(self, interaction: Interaction, button: Button):
        if self.vc.is_playing() or self.vc.is_paused():
            self.vc.stop()
            await interaction.response.send_message("Stopped playback.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @button(label=None, emoji="<:loop_track:1396006300747431936>", style=ButtonStyle.secondary, row=2)
    async def loop(self, interaction: Interaction, button: Button):
        global is_looping
        is_looping = not is_looping

        await interaction.response.send_message(f"Looping {'enabled' if is_looping else 'disabled'}.", ephemeral=True)

    @button(label=None, emoji="<:vol_down_track:1395742084492820620>", style=ButtonStyle.secondary, row=2)
    async def vol_down(self, interaction: Interaction, button: Button):
        global volume
        volume = round(max(volume - 0.1, 0.1), 2)

        await interaction.response.defer()

        if current_track.get("source"):
            current_track["source"].volume = volume
        if self.volume_flash_task and not self.volume_flash_task.done():
            self.volume_flash_task.cancel()

        self.volume_flash_task = asyncio.create_task(self.flash_volume_embed(interaction, int(volume * 100)))

    @button(label=None, emoji="<:vol_up_track:1395742106437554236>", style=ButtonStyle.secondary, row=2)
    async def vol_up(self, interaction: Interaction, button: Button):
        global volume
        volume = round(min(volume + 0.1, 2.0), 2)

        await interaction.response.defer()

        if current_track.get("source"):
            current_track["source"].volume = volume
        if self.volume_flash_task and not self.volume_flash_task.done():
            self.volume_flash_task.cancel()

        self.volume_flash_task = asyncio.create_task(self.flash_volume_embed(interaction, int(volume * 100)))


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:
        guild_id = before.channel.guild.id
        current_track.clear()
        now_playing_messages.pop(guild_id, None)
        queue.clear()

@bot.command(name="play", aliases=["p", "mb?play"])
async def play(ctx, *, query: str):
    global queue

    # Check if user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Join a voice channel first.")

    voice_channel = ctx.author.voice.channel

    # Connect to voice channel if not already connected
    if ctx.voice_client:
        vc = ctx.voice_client
    else:
        try:
            vc = await voice_channel.connect()
        except discord.ClientException:
            return await ctx.send("Already connected to a voice channel.")
        if not vc:
            return await ctx.send("Could not connect to the voice channel.")

    # Send processing message with loading animation
    loading_message = await ctx.send("<a:loadinganim:1393847961397497958> Processing media...")

    # Normalize the URL (if it's a link) or treat as a search query
    normalized_query = normalize_url(query)

    # Extract information using yt-dlp
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(normalized_query, download=False)

    # Delete the loading message after extraction
    await loading_message.delete()

    # Ensure `info` has entries (for single video or playlist)
    entries = info["entries"] if "entries" in info else [info]

    for i, entry in enumerate(entries):
        formats = entry.get("formats", [])
        audio_url = None

        # Force to use audio-only formats
        for f in formats:
            # Look for an audio-only format that is not a video
            if f.get("acodec") != "none" and f.get("vcodec") == "none" and not f.get("manifest_url"):
                audio_url = f["url"]
                break

        # If no suitable audio format is found, notify the user
        if not audio_url:
            await ctx.send(f"Could not find playable audio for `{entry.get('title', 'Unknown')}`")
            continue

        title = entry.get("title", "Unknown Title")
        duration = entry.get("duration", 0)

        # Prepare track info
        track_info = {
            "url": audio_url,
            "title": title,
            "duration": duration
        }

        if i == 0 and not vc.is_playing():  # Play the first track if not already playing
            audio = FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(audio, volume=volume)
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

            current_track.update({
                "title": title,
                "duration": duration,
                "start_time": time.monotonic(),
                "paused": False,
                "vc": vc,
                "source": source
            })

            # Send the 'Now Playing' embed
            embed = build_now_playing_embed(title, 0, duration)
            view = BoomboxControls(vc)
            message = await ctx.send(embed=embed, view=view)
            now_playing_messages[ctx.guild.id] = message
            old_task = progress_update_tasks.get(ctx.guild.id)
            if old_task and not old_task.done():
                old_task.cancel()
            asyncio.create_task(update_progress_bar(vc, ctx, view))
            progress_update_tasks[ctx.guild.id] = task

        else:
            queue.append(track_info)

    # Notify if there are more than one track in the queue
    if len(entries) > 1:
        await ctx.send(f"Added `{len(entries) - 1}` tracks to the queue.")
        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
