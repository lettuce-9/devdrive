import asyncio
import discord
import os
import wavelink
import time
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, button, Button
from dotenv import load_dotenv
load_dotenv()

# starting logic
# ----------------------------------------------------------------------------
token = os.getenv("DISCORD_TOKEN")

version='Test Build 50'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="mb?", intents=intents, help_command=None)
tree = bot.tree
progress_bar_tasks = {}

# global variables for mb?play
# ----------------------------------------------------------------------------

VOLUME_COOLDOWN = timedelta(seconds=1.5)
volume = 0.1 # orig value was 1 but i want it to be 0.1 for temporary
queue = []
now_playing_messages = {}
n_p_tasks = {}
flyout_status = {}
current_track = {}
user_volume_cooldowns = {}
now_playing_message = None
processing_message = None
current_source = None
is_looping = False

# global variables for mb?listenalong
# ----------------------------------------------------------------------------

current_status_message = {}
listenalong_target_user_id = None
currently_listening_along = False
last_spotify_track_id = None
last_user_spotify = None
target_user_obj = None
debounce_task = None
last_stopped_timestamp = None


# variable for build_emoji_progress_bar
# ----------------------------------------------------------------------------

CUSTOM_BARS = [
    "<:empty_bar:1396166217231896576>",
    "<:quarter_bar:1396166199821467710>",
    "<:half_bar:1396166182196740116>",
    "<:three_quarters_bar:1396166160378232932>",
    "<:full_bar:1396166135258550292>"
]

# defs below
# ----------------------------------------------------------------------------

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
    return bar

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

    lines = [f"Now Playing : **`{title}`**"]
    if status:
        lines.append(status)
    lines.append(f"`{elapsed_fmt}` {bar} `{duration_fmt}`")

    embed = discord.Embed(description="\n".join(lines), color=color)
    return embed

def timestamp_to_seconds(timestamp: str):
    parts = list(map(int, timestamp.split(":")))
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = parts
        return m * 60 + s
    elif len(parts) == 1:
        return parts[0]
    return 0

# asyncs below
# ----------------------------------------------------------------------------

async def update_progress_bar(player: wavelink.Player, ctx: commands.Context):
    guild_id = ctx.guild.id
    prev_elapsed = -1

    while player.is_connected:
        await asyncio.sleep(1)

        if not current_track or player.is_paused:
            continue
        
        elapsed = int(player.position // 1000)
        duration = current_track.get("duration", 0)

        if duration <= 0:
            continue

        if not player.is_playing and elapsed >= duration:
            break

        if elapsed == prev_elapsed:
            continue

        prev_elapsed = elapsed

        try:
            embed = build_now_playing_embed(
                title=current_track.get("title", "Unknown"),
                elapsed=elapsed,
                duration=duration,
                color=discord.Color.green()
            )

            message = now_playing_messages.get(guild_id)
            if message:
                await message.edit(embed=embed)
        except asyncio.CancelledError:
            print(f"[Seekbar] Cancelled for guild {guild_id}")
            return
        except Exception as e:
            print(f"[Seekbar update error] {e}")

async def start_now_playing_updater(ctx, player, show_controls=True):
    guild_id = ctx.guild.id
    if guild_id in n_p_tasks:
        n_p_tasks[guild_id].cancel()

    global guild_show_controls
    try:
        guild_show_controls
    except NameError:
        guild_show_controls = {}
    guild_show_controls[guild_id] = show_controls

    async def updater():
        while player.is_connected:
            await update_now_playing(ctx, player)
            await asyncio.sleep(1)

    n_p_tasks[guild_id] = asyncio.create_task(updater())

async def update_now_playing(ctx, player):
    guild_id = ctx.guild.id
    if not player or not current_track:
        return

    if flyout_status.get(guild_id):
        return

    elapsed = int(player.position // 1000)
    duration = current_track.get("duration", 0)

    embed = build_now_playing_embed(
        current_track["title"],
        elapsed,
        duration,
        color=discord.Color.green()
    )

    view = None
    if guild_show_controls.get(guild_id):
        view = BoomboxControls(player)

    if guild_id in now_playing_messages:
        try:
            await now_playing_messages[guild_id].edit(embed=embed, view=view)
        except discord.NotFound:
            msg = await ctx.send(embed=embed, view=view)
            now_playing_messages[guild_id] = msg
    else:
        msg = await ctx.send(embed=embed, view=view)
        now_playing_messages[guild_id] = msg

async def flash_flyout(ctx, text, duration=3):
    guild_id = ctx.guild.id
    flyout_status[guild_id] = text
    await update_now_playing(ctx)
    await asyncio.sleep(duration)
    if flyout_status.get(guild_id) == text:
        flyout_status[guild_id] = None
        await update_now_playing(ctx)

async def ensure_player(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return None

    player = ctx.voice_client
    if isinstance(player, wavelink.Player):
        return player

    player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    return player

async def start_track(ctx, info):
    global current_track, current_source, queue

    player: wavelink.Player = ctx.voice_client
    if not isinstance(player, wavelink.Player):
        player = await ensure_player(ctx)
        if player is None:
            await ctx.send("Failed to connect to voice channel.")
            return

    if hasattr(info, "title") and hasattr(info, "length"):
        track = info
        current_track = {
            "title": track.title,
            "duration": int(track.length // 1000),
            "track_obj": track,
            "paused": False
        }
    else:
        track = None
        current_track = info

    if player.is_playing():
        raise discord.errors.ClientException("Already playing audio.")

    try:
        if track:
            await player.play(track)
        else:
            return
    except Exception as e:
        print("Failed to play track via Lavalink:", e)
        return

    current_track["start_time"] = time.time()

    if ctx.guild.id in now_playing_messages:
        try:
            await now_playing_messages[ctx.guild.id].delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    duration = current_track.get("duration", 0)
    embed = build_now_playing_embed(
        title=current_track.get("title", "Unknown"),
        elapsed=0,
        duration=duration,
        color=discord.Color.green()
    )

    msg = await ctx.send(embed=embed)
    now_playing_messages[ctx.guild.id] = msg

    existing_task = progress_bar_tasks.get(ctx.guild.id)
    if existing_task:
        existing_task.cancel()
        try:
            await existing_task
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(update_progress_bar(player, ctx))
    progress_bar_tasks[ctx.guild.id] = task

async def handle_after_playing(ctx, error=None):
    guild_id = ctx.guild.id

    task = progress_bar_tasks.get(guild_id)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        del progress_bar_tasks[guild_id]

    if error:
        print(f"[After Playing Error] {error}")

    if is_looping:
        await start_track(ctx, current_track)
    elif queue:
        next_track = queue.pop(0)
        await start_track(ctx, next_track)
    else:
        msg = now_playing_messages.get(guild_id)
        if msg:
            try:
                await msg.edit(
                    content=None,
                    embed=discord.Embed(description="Playback finished.", color=discord.Color.green()),
                    view=None
                )
            except discord.NotFound:
                pass

@bot.event
async def on_member_update(before, after):
    global debounce_task, last_spotify_track_id, currently_listening_along

    if after.id != listenalong_target_user_id:
        return

    old_spotify = next((a for a in before.activities if isinstance(a, discord.Spotify)), None)
    new_spotify = next((a for a in after.activities if isinstance(a, discord.Spotify)), None)

    if debounce_task:
        debounce_task.cancel()

    debounce_task = asyncio.create_task(debounce_handle_track_change(after, new_spotify))


async def debounce_handle_track_change(member, spotify_activity):
    global last_spotify_track_id, currently_listening_along

    await asyncio.sleep(2)

    voice = member.guild.voice_client
    if not voice:
        return

    if spotify_activity is None:
        if voice.is_playing():
            voice.pause()
            print("[SYNC] Paused bot (Spotify not detected)")
            await update_listenalong_status(member, "stopped")
            global last_stopped_timestamp
            last_stopped_timestamp = time.time()
        return

    if spotify_activity.track_id == last_spotify_track_id:
        return

    last_spotify_track_id = spotify_activity.track_id
    currently_listening_along = True

    await play_spotify_track_for_user(member, spotify_activity)
    query = f"{spotify_activity.artist} - {spotify_activity.title}"
    duration = (spotify_activity.end - spotify_activity.start).total_seconds()
    progress = int((discord.utils.utcnow() - spotify_activity.start).total_seconds())
    progress = max(0, min(progress, int(duration)))

    print(f"Switching to: {query} (elapsed: {progress}s)")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            formats = info.get("formats", [])
            audio_url = next((f["url"] for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"), None)
            if not audio_url:
                raise Exception("No valid audio stream found.")
            info["url"] = audio_url
            info["start_time"] = time.time() - progress
            info["duration"] = int(duration)

        guild = member.guild
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            print("Bot is not connected to VC. Skipping autoplay.")
            return

        class FakeCtx:
            def __init__(self, guild):
                self.guild = guild
                self.voice_client = guild.voice_client

            async def send(self, *args, **kwargs):
                msg = await self.guild.text_channels[0].send(*args, **kwargs)
                now_playing_messages[self.guild.id] = msg
                return msg

    except Exception as e:
        print(f"Failed to sync new track: {e}")

async def update_listenalong_status(member, status):
    global current_status_message
    guild_id = member.guild.id
    if current_status_message.get(guild_id) == status:
        return

    current_status_message[guild_id] = status
    message = now_playing_messages.get(member.guild.id)
    if not message:
        return

    elapsed = time.time() - current_track.get("start_time", time.time())
    duration = timestamp_to_seconds(current_track.get("duration", 0))

    statuses = {
        "paused": f"@{member.display_name} paused Spotify. Waiting...",
        "resumed": f"@{member.display_name} continued listening. Syncing...",
        "timeout": f"@{member.display_name} reconnection timed out. Playback finished.",
        "stopped": f"@{member.display_name} stopped listening to Spotify. Waiting for reconnection..."
    }

    embed = build_now_playing_embed(
        title=current_track.get("title", "Unknown"),
        elapsed=elapsed,
        duration=duration,
        status=statuses.get(status, ""),
        color=discord.Color.orange()
    )

    try:
        await message.edit(embed=embed)
    except discord.NotFound:
        pass

async def play_spotify_track_for_user(member, spotify, ctx_or_channel=None):
    query = f"{spotify.artist} - {spotify.title}"
    duration = (spotify.end - spotify.start).total_seconds()
    elapsed = (discord.utils.utcnow() - spotify.start).total_seconds()
    elapsed = max(0, min(elapsed, duration))

    print(f"[SYNC] Playing {query} from {int(elapsed)}s of {int(duration)}s")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            formats = info.get("formats", [])
            audio_url = next((f["url"] for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"), None)

            if not audio_url:
                raise Exception("No valid audio stream")

            info["url"] = audio_url
            info["start_time"] = time.time() - elapsed
            info["duration"] = int(duration)

    except Exception as e:
        print(f"[ERROR] Failed to load track: {e}")
        return

    if not member.voice or not member.voice.channel:
        print("Target user not in VC")
        return

    if not member.guild.voice_client:
        await member.voice.channel.connect(self_deaf=True)

    class FakeCtx:
        def __init__(self, guild, send_func):
            self.guild = guild
            self.voice_client = guild.voice_client
            self.send = send_func

    if ctx_or_channel:
        if hasattr(ctx_or_channel, "send"):
            send_func = ctx_or_channel.send
        else:
            send_func = ctx_or_channel.text_channels[0].send
    else:
        send_func = member.guild.text_channels[0].send

    ctx = FakeCtx(member.guild, send_func)
    
    if ctx.guild.id in now_playing_messages:
        try:
            await now_playing_messages[ctx.guild.id].delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    await start_track(ctx, info)

async def poll_target_user():
    global last_user_spotify, listenalong_target_user_id

    await bot.wait_until_ready()

    while True:
        await asyncio.sleep(3)

        if not listenalong_target_user_id:
            continue

        guild = discord.utils.get(bot.guilds)
        member = guild.get_member(listenalong_target_user_id)
        if not member:
            continue

        voice = member.guild.voice_client
        spotify = next((a for a in member.activities if isinstance(a, discord.Spotify)), None)

        if not spotify:
            if last_user_spotify:
                print("[SYNC] Spotify activity stopped.")
                if voice and voice.is_playing():
                    voice.stop()
                await update_listenalong_status(member, "stopped")
            last_user_spotify = None
            continue

        if last_user_spotify and spotify.track_id != last_user_spotify.track_id:
            print(f"[TRACK CHANGE] Now playing: {spotify.title}")
            await play_spotify_track_for_user(member, spotify)
            last_user_spotify = spotify

        now = discord.utils.utcnow()
        elapsed = (now - spotify.start).total_seconds()
        duration = (spotify.end - spotify.start).total_seconds()
        is_paused = not (spotify.start <= now <= spotify.end)

        if is_paused:
            if voice.is_playing():
                voice.pause()
                await update_listenalong_status(member, "paused")
        else:
            if voice.is_paused():
                voice.resume()
                await update_listenalong_status(member, "resumed")

# class for mb?play controls
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

    @button(label="⏸", style=ButtonStyle.primary)
    async def pause(self, interaction: Interaction, button: Button):
        guild_id = interaction.guild.id

        if self.vc.is_playing():
            self.vc.pause()
            current_track["paused"] = True

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


    @button(label="▶", style=ButtonStyle.success)
    async def resume(self, interaction: Interaction, button: Button):
        guild_id = interaction.guild.id

        if self.vc.is_paused():
            self.vc.resume()
            current_track["paused"] = False

            flyout_status[guild_id] = True

            # Show resumed flyout
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

        self.volume_flash_task = asyncio.create_task(
            self.flash_volume_embed(interaction, vol_percent)
        )


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

        self.volume_flash_task = asyncio.create_task(
            self.flash_volume_embed(interaction, vol_percent)
        )


async def get_current_embed(interaction: Interaction, status: str):
    global current_track
    duration = timestamp_to_seconds(current_track.get("duration", 0))
    elapsed = time.time() - current_track.get("start_time", time.time())
    build_now_playing_embed(
        current_track["title"], elapsed, duration, status=status, color=discord.Color.blue()
    )


# commands logic
# ----------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"{bot.user} is connected to Discord")
    bot.loop.create_task(poll_target_user())

    node = wavelink.Node(uri="http://lavalinkbackend.onrender.com:10000", password="placeholder12345") # ln 751 - 758, here?
    await wavelink.Pool.connect(client=bot, nodes=[node])

# ----------------------------------------------------------------------------

@bot.command(help="Lists all available music bot commands.")
async def commands(ctx):

    command_list = [
        f'`!{cmd.name}` - {cmd.help or "*No description*"}'
        for cmd in bot.commands if not cmd.hidden
    ]

    embed = discord.Embed(
        title="Available Commands",
        description="\n".join(command_list),
        color=0x00FFAA
    )
    await ctx.send(embed=embed)
    
# ----------------------------------------------------------------------------

@bot.command(help="Connect the bot from a VC")
async def connect(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect(self_deaf=True)
    else:
        await ctx.send("You are currently not in a Voice Channel.")

# ----------------------------------------------------------------------------

@bot.command(help="Disonnect the bot from a VC")
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected bot from Voice Channel.")
    else:
        await ctx.send("You are currently not in a Voice Channel.")

# ----------------------------------------------------------------------------

@bot.command(help="Play a track from Youtube. (Currently only accepts Youtube links)")
async def play(ctx, *, query: str = None):
    global current_track, queue

    if not query:
        embed = discord.Embed(
            title="Error 400",
            description="You provided an invalid query or URL.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player = ctx.voice_client
    if not player:
        if ctx.author.voice:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            await ctx.send(embed=discord.Embed(title="Error 400", description="You must be in a voice channel.", color=discord.Color.red()))
            return

    try:
        track = await wavelink.Playable.search("your query here")
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error 500", description=f"Search failed: `{e}`", color=discord.Color.red()))
        return

    if not track:
        await ctx.send("No results found.")
        return

    if player.is_playing:
        queue.append(track)
        await ctx.send(embed=discord.Embed(description=f"Queued: **`{track.title}`**", color=discord.Color.orange()))
        return

    await start_track(ctx, track)
    await start_now_playing_updater(ctx, player, show_controls=True)

# ----------------------------------------------------------------------------

@bot.command(help="Show current music bot version.")
async def ver(ctx):
    embed = discord.Embed(
        description=f"Music Bot version : **`{version}`**",
        color=discord.Color.dark_teal()
    )
    await ctx.send(embed=embed)

# ----------------------------------------------------------------------------

@bot.command(help="Listen along to a target user thats listening to Spotify and has rich presence on for Spotify.")
async def listenalong(ctx, user: discord.Member = None):
    global listenalong_target_user_id, last_user_spotify, target_user_obj

    if not user:
        await ctx.send("Mention a user to follow.")
        return

    try:
        member = ctx.guild.get_member(user.id) or await ctx.guild.fetch_member(user.id)
    except discord.NotFound:
        await ctx.send("User not found in this guild.")
        return

    def find_spotify_activity(member: discord.Member):
        for activity in member.activities:
            if isinstance(activity, discord.Spotify):
                return activity
        return None

    member = ctx.guild.get_member(user.id) or await ctx.guild.fetch_member(user.id)

    spotify_activity = find_spotify_activity(member)
    
    if not spotify_activity:
        await asyncio.sleep(1)
        member = ctx.guild.get_member(user.id) or await ctx.guild.fetch_member(user.id)
        print(f"Retry fetch activities for {member.display_name}: {[type(a) for a in member.activities]}")
        spotify_activity = find_spotify_activity(member)

    if not spotify_activity:
        await ctx.send(f"{member.display_name} is not listening to Spotify.")
        return

    track_title = spotify_activity.title
    artist = spotify_activity.artist
    duration = (spotify_activity.end - spotify_activity.start).total_seconds()
    progress = int((discord.utils.utcnow() - spotify_activity.start).total_seconds())
    progress = max(0, min(progress, int(duration)))

    query = f"{artist} - {track_title}"
    loading_msg = await ctx.send(f"<a:loadinganim:1393847961397497958> Searching & getting ready to play for **`{query}`**...")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            formats = info.get("formats", [])
            audio_url = next((f["url"] for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"), None)

            if not audio_url:
                raise Exception("No valid audio stream found.")

            info["url"] = audio_url
            info["start_time"] = time.time() - progress
            info["duration"] = int(duration)

    except Exception as e:
        await loading_msg.edit(content=f"Failed to find a matching song.\n`{e}`")
        return

    if not ctx.author.voice:
        await loading_msg.edit(content="You must be in a Voice Channel to use this.")
        return

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect(self_deaf=True)

        listenalong_target_user_id = user.id
    target_user_obj = user
    last_user_spotify = None
    await loading_msg.edit(content=f"Now listening along with `{user.display_name}.`\nNow playing : **`{track_title} - {artist}`**")
    await play_spotify_track_for_user(user, spotify_activity, ctx)
    await start_track(ctx, info)

bot.run(token)