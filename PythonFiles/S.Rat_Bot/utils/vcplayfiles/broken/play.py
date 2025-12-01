import asyncio
import datetime
import discord
import os
import wavelink
import time
import yt_dlp
from colorama import Style, init, Fore
from datetime import timedelta
from discord.ext import commands
from discord import Interaction, ButtonStyle
from discord.ui import View, button, Button
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# setup
# ----------------------------------------------------------------------------
node_ready = asyncio.Event()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

uri_nodes = "wss://lavalinkbackend.onrender.com"

YDL_OPTIONS = {
    'format': 'bestaudio[ext=webm]/bestaudio/best',
    'quiet': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2 -b:a 128k'
}


class MusicBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        try:
            await wavelink.Pool.connect(
                client=self,
                nodes=[wavelink.Node(uri=uri_nodes,
                password="e90ae91c9311b66afffeb65b97a949de")]
            )
            print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "[DEBUG]  " + Style.RESET_ALL + "Lavalink connected")
        except Exception as e:
            print(Fore.LIGHTRED_EX + Style.BRIGHT + "[ERROR]  " + Style.RESET_ALL + f"Lavalink connection failed: {e}")


bot = MusicBot(command_prefix="mb?", intents=intents, help_command=None)

# global variables
# ----------------------------------------------------------------------------
VOLUME_COOLDOWN = timedelta(seconds=1.5)
volume = 0.5
queue = []
now_playing_messages = {}
progress_bar_tasks = {}
current_track = {}
is_looping = False
flyout_status = {}
user_volume_cooldowns = {}
now_playing_message = None
init(autoreset=True)

CUSTOM_BARS = {
    "first": {
        "empty": "<:empty1:1409422370976043008>",
        "quarter": "<:quarter1:1409422427405942784>",
        "half": "<:half1:1409422469734862891>",
        "threequarters": "<:threequarters1:1409422521111023657>",
        "full": "<:full1:1409422552060657754>"
    },
    "middle": {
        "empty": "<:empty2:1409422379506995282>",
        "quarter": "<:quarter2:1409422439640862810>",
        "half": "<:half2:1409422482297061447>",
        "threequarters": "<:threequarters2:1409422531370418268> ",
        "full": "<:full2:1409422560936067072>"
    },
    "last": {
        "empty": "<:empty3:1409422396183679099>",
        "quarter": "<:quarter3:1409422450688655360>",
        "half": "<:half3:1409422496649838733>",
        "threequarters": "<:threequarters3:1409422547447058462>",
        "full": "<:full3:1409422571195334723>"
    }
}


# task helpers
# ----------------------------------------------------------------------------
def get_bar_emoji(ratio):
    if ratio <= 0.10: return CUSTOM_BARS[0]
    if ratio <= 0.35: return CUSTOM_BARS[1]
    if ratio <= 0.60: return CUSTOM_BARS[2]
    if ratio <= 0.85: return CUSTOM_BARS[3]
    return CUSTOM_BARS[4]

def build_emoji_progress_bar(current, total, bar_length=10):
    ratio = current / total if total > 0 else 0
    filled = ratio * bar_length
    bar = ""

    for i in range(bar_length):
        if i == 0:
            set_type = "first"
        elif i == bar_length - 1:
            set_type = "last"
        else:
            set_type = "middle"

        if filled >= i + 1:
            bar += CUSTOM_BARS[set_type]["full"]
        elif filled > i:
            fraction = filled - i
            if fraction >= 0.75:
                bar += CUSTOM_BARS[set_type]["threequarters"]
            elif fraction >= 0.5:
                bar += CUSTOM_BARS[set_type]["half"]
            elif fraction >= 0.25:
                bar += CUSTOM_BARS[set_type]["quarter"]
            else:
                bar += CUSTOM_BARS[set_type]["empty"]
        else:
            bar += CUSTOM_BARS[set_type]["empty"]

    return bar


def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02}"

def build_now_playing_embed(title, elapsed, duration, status=None, color=discord.Color.green()):
    bar = build_emoji_progress_bar(elapsed, duration)
    elapsed_fmt = format_time(elapsed)
    duration_fmt = format_time(duration)
    lines = [f"Now Playing : **`{title}`**"]
    if status:
        lines.append(status)
    lines.append(f"`{elapsed_fmt}` {bar} `{duration_fmt}`")
    return discord.Embed(description="\n".join(lines), color=color)

def timestamp_to_seconds(timestamp: str | int):
    if isinstance(timestamp, int):
        return timestamp
    parts = list(map(int, str(timestamp).split(":")))
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = parts
        return m * 60 + s
    elif len(parts) == 1:
        return parts[0]
    return 0

def normalize_query(query: str) -> str:
    if query.startswith(("http://", "https://")):
        return query
    if query.startswith("youtube.com/") or query.startswith("www.youtube.com/"):
        return f"https://{query}"
    return f"ytsearch:{query}"

def get_version():
    mtime = os.path.getmtime(__file__)
    dt = datetime.datetime.fromtimestamp(mtime)
    return dt.strftime("Build %m/%d/%Y - %H:%M:%S")

# player & progress bar
# ----------------------------------------------------------------------------
async def update_progress_bar(player: wavelink.Player, ctx: commands.Context):
    guild_id = ctx.guild.id

    while player.connected:
        await asyncio.sleep(2)

        if not player.playing or current_track.get("paused"):
            continue

        elapsed = int(time.monotonic() - current_track.get("start_time", time.monotonic()))
        duration = current_track.get("duration", 0)
        if duration <= 0:
            continue
        if elapsed > duration:
            elapsed = duration

        try:
            embed = build_now_playing_embed(
                title=current_track.get("title", "Unknown"),
                elapsed=elapsed,
                duration=duration
            )
            message = now_playing_messages.get(guild_id)
            if message and not flyout_status.get(guild_id, False):
                await message.edit(embed=embed)
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(Fore.LIGHTRED_EX + Style.BRIGHT + "[ERROR]  " + Style.RESET_ALL + f"{e}")


async def ensure_player(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return None

    if isinstance(ctx.voice_client, wavelink.Player):
        return ctx.voice_client

    return await ctx.author.voice.channel.connect(cls=wavelink.Player)

async def start_track(ctx, track):
    global current_track, queue, progress_bar_tasks

    player: wavelink.Player = ctx.voice_client
    if not isinstance(player, wavelink.Player):
        player = await ensure_player(ctx)
        if not player:
            await ctx.send("Failed to connect to VC.")
            return

    current_track = {
        "title": track.title,
        "duration": int(track.length // 1000),
        "track_obj": track,
        "start_time": time.monotonic(),
        "paused": False,
        "ctx": ctx
    }

    await player.play(track)

    embed = build_now_playing_embed(track.title, 0, current_track["duration"])
    msg = await ctx.send(embed=embed, view=BoomboxControls(player))
    now_playing_messages[ctx.guild.id] = msg

    # cancel old task if running
    if ctx.guild.id in progress_bar_tasks:
        progress_bar_tasks[ctx.guild.id].cancel()

    task = asyncio.create_task(update_progress_bar(player, ctx))
    progress_bar_tasks[ctx.guild.id] = task

async def update_seekbar(self, message):
    while self.is_playing:
        if self.is_paused:
            await asyncio.sleep(1)
            continue

        elapsed = time.monotonic() - self.seekbar_start_time
        progress = elapsed / self.current_song_duration
        if progress > 1:
            break

        index = int(progress * (len(CUSTOM_BARS) - 1))
        current_frame = CUSTOM_BARS[index]

        embed = self.build_now_playing_embed(current_frame)
        try:
            await message.edit(embed=embed)
        except discord.HTTPException:
            pass

        await asyncio.sleep(3)


# buttons
# ----------------------------------------------------------------------------
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
        duration = timestamp_to_seconds(current_track.get("duration", 0))

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

    @button(label="⏸", style=ButtonStyle.primary, row=1)
    async def pause(self, interaction: Interaction, button: Button):
        guild_id = interaction.guild.id

        if self.vc.playing:
            self.vc.pause()
            current_track["paused"] = True
            current_track["pause_time"] = time.monotonic()  

            flyout_status[guild_id] = True

            flyout_embed = discord.Embed(
                description=f"⏸ **Paused**: `{current_track['title']}`",
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=flyout_embed, view=self)

            await asyncio.sleep(3)
            flyout_status[guild_id] = False

            embed = await get_current_embed(interaction, "Paused")
            try:
                await interaction.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)


    @button(label="▶", style=ButtonStyle.success, row=1)
    async def resume(self, interaction: Interaction, button: Button):
        guild_id = interaction.guild.id

        if self.vc.paused:
            self.vc.resume()
            current_track["paused"] = False
            paused_duration = time.monotonic() - current_track["pause_time"]
            current_track["start_time"] += paused_duration

            flyout_status[guild_id] = True

            flyout_embed = discord.Embed(
                description=f"▶ **Resumed**: `{current_track['title']}`",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=flyout_embed, view=self)

            await asyncio.sleep(3)
            flyout_status[guild_id] = False

            embed = await get_current_embed(interaction, "Resumed")
            try:
                await interaction.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass
        else:
            await interaction.response.send_message("Nothing to resume.", ephemeral=True)


    @button(label="⏹", style=ButtonStyle.danger, row=1)
    async def stop(self, interaction: Interaction, button: Button):
        if self.vc.playing or self.vc.paused:
            self.vc.stop()
            await interaction.response.send_message("Stopped current track", ephemeral=False)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @button(label=None, emoji="<:loop_track:1396006300747431936>", style=ButtonStyle.secondary, row=2)
    async def loop(self, interaction: Interaction, button: Button):
        global is_looping
        is_looping = not is_looping
        loop_status = "enabled" if is_looping else "disabled"
        await interaction.response.send_message(f"Looping {loop_status}!", ephemeral=True)

        embed = await get_current_embed(interaction, f"Loop {loop_status}")
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label=None, emoji="<:vol_down_track:1395742084492820620>", style=ButtonStyle.secondary, row=2)
    async def volume_down(self, interaction: Interaction, button: Button):
        global volume, user_volume_cooldowns, current_track, now_playing_message, current_source

        if volume <= 0.1:
            await interaction.response.send_message("Volume is already at minimum.", ephemeral=True)
            return

        volume = round(max(volume - 0.1, 0.0), 2)
        vol_percent = int(volume * 100)

        await self.vc.set_volume(vol_percent)

        await interaction.response.defer(ephemeral=True)

        if self.volume_flash_task:
            self.volume_flash_task.cancel()
        try:
            await self.volume_flash_task
        except:
            pass

        self.volume_flash_task = asyncio.create_task(
            self.flash_volume_embed(interaction, vol_percent)
        )


    @button(label=None, emoji="<:vol_up_track:1395742106437554236>", style=ButtonStyle.secondary, row=2)
    async def volume_up(self, interaction: Interaction, button: Button):
        global volume, user_volume_cooldowns, current_track, now_playing_message, current_source

        if volume >= 2.0:
            await interaction.response.send_message("Volume is already at max.", ephemeral=True)
            return

        volume = round(min(volume + 0.1, 2.0), 2)
        vol_percent = int(volume * 100)

        await self.vc.set_volume(vol_percent)

        await interaction.response.defer(ephemeral=True)

        if self.volume_flash_task:
            self.volume_flash_task.cancel()
        try:
            await self.volume_flash_task
        except:
            pass

        self.volume_flash_task = asyncio.create_task(
            self.flash_volume_embed(interaction, vol_percent)
        )


async def get_current_embed(interaction: Interaction, status: str):
    global current_track
    duration = timestamp_to_seconds(current_track.get("duration", 0))
    elapsed = time.time() - current_track.get("start_time", time.time())
    return build_now_playing_embed(
        current_track["title"], elapsed, duration, status=status, color=discord.Color.blue()
    )

# events
# ----------------------------------------------------------------------------
@bot.event
async def on_ready():
    print(Fore.LIGHTBLUE_EX + Style.BRIGHT + "[INFO]   " + Style.RESET_ALL + f"{bot.user} is online.")
    print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "[DEBUG]  " + Style.RESET_ALL + f"current set URI : {uri_nodes}")

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    node = payload.node
    print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "[DEBUG]  " + Style.RESET_ALL + f"Node ready: {node.identifier}")
    node_ready.set()

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player = payload.player
    guild_id = player.guild.id
    ctx = current_track.get("ctx")

    if is_looping:
        await player.play(current_track["track_obj"])
        return

    if queue:
        next_track = queue.pop(0)
        await start_track(ctx, next_track)
        return

    if guild_id in now_playing_messages:
        finished = discord.Embed(
            description="Playback finished.",
            color=discord.Color.red()
        )
        try:
            await now_playing_messages[guild_id].edit(embed=finished, view=None)
        except discord.NotFound:
            pass

# commands
# ----------------------------------------------------------------------------
@bot.command()
@commands.is_owner()
async def play(ctx, *, query: str = None):
    if not query:
        return await ctx.send("Please provide a search query or URL.")

    player = await ensure_player(ctx)
    if not player:
        return await ctx.send("You need to join a voice channel first.")

    query = normalize_query(query)
    try:
        tracks = await wavelink.Playable.search(query)
        if not tracks:
            return await ctx.send("No tracks found. Please check the query or URL.")

        track = tracks[0]

        if player.playing:
            queue.append(track)
            return await ctx.send(f"Queued: **{track.title}**")

        await start_track(ctx, track)

    except wavelink.exceptions.LavalinkException as e:
        await ctx.send(f"Lavalink error: {e}")
        print(f"Lavalink error: {e}")
    except Exception as e:
        await ctx.send(f"An error occurred while playing the track: {e}")
        print(f"Error: {e}")

async def auto_disconnect(ctx, voice_client, timeout_minutes):
    channel = voice_client.channel
    empty_seconds = 0
    check_interval = 1

    while voice_client.is_connected():
        member_count = len([m for m in channel.members if not m.bot])

        if member_count == 0:
            empty_seconds += check_interval
            if empty_seconds >= timeout_minutes * 60:
                await ctx.send("yeah im leaving\nthats just mean why would you do that")
                await voice_client.disconnect()
                break
        else:
            empty_seconds = 0

        await asyncio.sleep(check_interval)

@bot.command()
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("im gone")
    else:
        await ctx.send("huh")

@bot.command()
@commands.is_owner()
async def playver(ctx):
    lalala = get_version()
    verembed = discord.Embed(
        description=f"mb?play version : **`{lalala}`**",
        color=0x0099FF
    )
    await ctx.send(embed=verembed)

@bot.command(name="legacyplay")
async def legacyplay(ctx, url: str):
    if not ctx.author.voice:
        return await ctx.send("You must be in a voice channel to play music.")

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    await ctx.send(f"Loading track...")

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
    audio_url = data['url']
    title = data.get('title', 'Unknown Track')
    duration = int(data.get('duration', 0))

    source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
    ctx.voice_client.stop()
    ctx.voice_client.play(source)

    global current_track
    current_track = {
        "title": title,
        "duration": duration,
        "start_time": time.monotonic(),
        "paused": False,
        "ctx": ctx
    }

    embed = build_now_playing_embed(title, 0, duration)
    msg = await ctx.send(embed=embed, view=BoomboxControls(ctx.voice_client))
    now_playing_messages[ctx.guild.id] = msg

    if ctx.guild.id in progress_bar_tasks:
        progress_bar_tasks[ctx.guild.id].cancel()

    task = asyncio.create_task(update_progress_bar(ctx.voice_client, ctx))
    progress_bar_tasks[ctx.guild.id] = task

bot.run(token)