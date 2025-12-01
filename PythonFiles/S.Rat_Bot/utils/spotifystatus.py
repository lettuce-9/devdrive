import discord
import os
import datetime
import asyncio
import math
from discord.ext import commands
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())
token = os.getenv("DISCORD_TOKEN")

EMOJI_BAR = {
    "empty":      ["<:empty1:1409422370976043008>", "<:empty2:1409422379506995282>", "<:empty3:1409422396183679099>"],
    "quarter":    ["<:quarter1:1409422427405942784>", "<:quarter2:1409422439640862810>", "<:quarter3:1409422450688655360>"],
    "half":       ["<:half1:1409422469734862891>", "<:half2:1409422482297061447>", "<:half3:1409422496649838733>"],
    "threequarters": ["<:threequarters1:1409422521111023657>", "<:threequarters2:1409422531370418268>", "<:threequarters3:1409422547447058462>"],
    "full":       ["<:full1:1409422552060657754>", "<:full2:1409422560936067072>", "<:full3:1409422571195334723>"]
}

def log_debug(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}[DEBUG]  {Style.RESET_ALL}{message}")

def log_error(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp}  {Fore.LIGHTRED_EX}{Style.BRIGHT}[ERROR]  {Style.RESET_ALL}{message}")

def format_time(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02}"

def build_detailed_progress_bar(progress_ratio: float) -> str:
    total_slots = 10
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

        if i == 0:
            emoji = EMOJI_BAR[key][0]
        elif i == total_slots - 1:
            emoji = EMOJI_BAR[key][2]
        else:
            emoji = EMOJI_BAR[key][1]

        bar.append(emoji)

    return "".join(bar)

@bot.event
async def on_ready():
    log_debug(f"{bot.user} is ready and connected to Discord.")

@bot.command()
async def fetchSpotifyActivity(ctx, target: discord.Member = None):
    member = target or ctx.author

    def get_spotify(member):
        for activity in member.activities:
            if isinstance(activity, discord.Spotify):
                return activity
        return None
    
    def build_embed(spotify, is_paused=False, elapsed_override=None):
        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed = (now - spotify.start).total_seconds() if elapsed_override is None else elapsed_override
        total = (spotify.end - spotify.start).total_seconds()
        progress_ratio = max(0, min(elapsed / total, 1.0))
        progress_bar = build_detailed_progress_bar(progress_ratio)
    
        color = discord.Color.yellow() if is_paused else discord.Color.green()

        embed = discord.Embed(title=f"{member.display_name}'s Spotify Now Playing", color=color)
        embed.set_thumbnail(url=spotify.album_cover_url)
        embed.description = (
            f"**[{spotify.title} - {spotify.artist}](https://open.spotify.com/track/{spotify.track_id})**\n"
            f"**`{format_time(elapsed)}`** {progress_bar} **`{format_time(total)}`**"
        )
        if is_paused:
            embed.set_footer(text="Paused")

        return embed, elapsed

    spotify = get_spotify(member)
    if not spotify:
        await ctx.send(f"{member.display_name} is not listening to Spotify right now.")
        log_debug(f"User {member.display_name} is not listening to Spotify at command start.")
        return

    embed, last_elapsed = build_embed(spotify)
    message = await ctx.send(embed=embed)
    log_debug(f"Sent initial embed for {member.display_name}: '{embed.description}'")

    interval = 0.6
    pause_timeout_duration = 35
    pause_timeout_start = None

    last_paused_state = False
    last_track_id = spotify.track_id
    last_embed_description = embed.description

    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        current_spotify = get_spotify(member)

        if not current_spotify:
            if pause_timeout_start is None:
                pause_timeout_start = now
                log_debug(f"Spotify RPC disappeared for {member.display_name}, starting pause timeout...")
        
                paused_embed, _ = build_embed(spotify, is_paused=True, elapsed_override=last_elapsed)
                try:
                    await message.edit(embed=paused_embed)
                    log_debug(f"Embed updated to paused state for {member.display_name}.")
                except Exception as e:
                    log_error(f"Failed to update paused embed for {member.display_name}: {e}")
        
            else:
                elapsed_pause = (now - pause_timeout_start).total_seconds()
                log_debug(f"Pause timeout running for {member.display_name}: {elapsed_pause:.1f}/{pause_timeout_duration} seconds")
                if elapsed_pause >= pause_timeout_duration:
                    await message.edit(content="Spotify paused or stopped. Preview ended after timeout.", embed=None)
                    log_debug(f"Pause timeout reached for {member.display_name}, ending preview.")
                    break
            await asyncio.sleep(1)
            continue


        if pause_timeout_start is not None:
            log_debug(f"Spotify RPC returned for {member.display_name}, cancelling pause timeout.")
            pause_timeout_start = None

        if current_spotify.track_id != last_track_id:
            await message.edit(content=f"{member.display_name} changed tracks or stopped listening.", embed=None)
            log_debug(f"Detected track change for {member.display_name} from {last_track_id} to {current_spotify.track_id}. Ending preview.")
            break

        is_paused = getattr(current_spotify, "is_paused", False)

        elapsed = (now - current_spotify.start).total_seconds()
        total = (current_spotify.end - current_spotify.start).total_seconds()
    
        next_second = math.ceil(elapsed)
        sleep_duration = max(0, next_second - elapsed - 0.05)

        embed, _ = build_embed(current_spotify, is_paused=is_paused, elapsed_override=next_second)

        embed_needs_update = embed.description != last_embed_description

        if next_second != last_elapsed or is_paused != last_paused_state or embed_needs_update:
            try:
                log_debug(f"Attempting to update embed for {member.display_name} at elapsed {format_time(next_second)} (paused={is_paused})")
                await message.edit(embed=embed)
                log_debug(f"Embed updated successfully for {member.display_name}.")
                last_elapsed = next_second
                last_paused_state = is_paused
                last_embed_description = embed.description
            except Exception as e:
                log_error(f"Failed to update embed for {member.display_name}: {e}")
                log_error("Failed to do previous update/s, attempting to skip...")

        if is_paused:
            if pause_timeout_start is None:
                pause_timeout_start = now
                log_debug(f"Spotify paused for {member.display_name}, starting pause timeout...")
            else:
                elapsed_pause = (now - pause_timeout_start).total_seconds()
                log_debug(f"Pause timeout running during pause for {member.display_name}: {elapsed_pause:.1f}/{pause_timeout_duration} seconds")
                if elapsed_pause >= pause_timeout_duration:
                    await message.edit(content="Spotify paused. Preview ended after timeout.", embed=None)
                    log_debug(f"Pause timeout reached during pause for {member.display_name}, ending preview.")
                    break
        else:
            pause_timeout_start = None

        await asyncio.sleep(max(sleep_duration, 0.05))

bot.run(token)
