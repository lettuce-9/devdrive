import discord
from discord.ext import commands
from discord.ui import Button, View, ButtonStyle
import os
import yt_dlp
import asyncio
import time
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='mb?', intents=intents)
token = os.getenv('DISCORD_TOKEN')

EMOJI_BAR = {
    "empty":      ["<:empty1:1409422370976043008>", "<:empty2:1409422379506995282>", "<:empty3:1409422396183679099>"],
    "quarter":    ["<:quarter1:1409422427405942784>", "<:quarter2:1409422439640862810>", "<:quarter3:1409422450688655360>"],
    "half":       ["<:half1:1409422469734862891>", "<:half2:1409422482297061447>", "<:half3:1409422496649838733>"],
    "threequarters": ["<:threequarters1:1409422521111023657>", "<:threequarters2:1409422531370418268>", "<:threequarters3:1409422547447058462>"],
    "full":       ["<:full1:1409422552060657754>", "<:full2:1409422560936067072>", "<:full3:1409422571195334723>"]
}

def add_to_queue(track):
    queue.append(track)

# Play the next track from the queue
def play_next(vc):
    global current_track
    if queue:
        current_track = queue.pop(0)
        vc.play(discord.FFmpegPCMAudio(current_track["url"]))

# Play the previous track (if applicable)
def play_previous(vc):
    global current_track
    if queue:
        current_track = queue.pop(-1)  # Taking the last track
        vc.play(discord.FFmpegPCMAudio(current_track["url"]))

# Progress bar emoji constants (same as before)
EMOJI_BAR = {
    "empty":      ["<:empty1:1409422370976043008>", "<:empty2:1409422379506995282>", "<:empty3:1409422396183679099>"],
    "quarter":    ["<:quarter1:1409422427405942784>", "<:quarter2:1409422439640862810>", "<:quarter3:1409422450688655360>"],
    "half":       ["<:half1:1409422469734862891>", "<:half2:1409422482297061447>", "<:half3:1409422496649838733>"],
    "threequarters": ["<:threequarters1:1409422521111023657>", "<:threequarters2:1409422531370418268>", "<:threequarters3:1409422547447058462>"],
    "full":       ["<:full1:1409422552060657754>", "<:full2:1409422560936067072>", "<:full3:1409422571195334723>"]
}

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

# BoomboxControls with play, pause, resume, next, previous buttons
class BoomboxControls(discord.ui.View):
    def __init__(self, vc, track):
        super().__init__(timeout=None)
        self.vc = vc
        self.track = track
        self.paused = False

    async def update_progress_bar(self):
        """Continuously updates the progress bar"""
        while self.vc.is_playing():
            current_time = time.time() - self.track['start_time']
            total_duration = self.track['duration']
            progress_ratio = current_time / total_duration if total_duration else 0
            progress_bar = build_detailed_progress_bar(progress_ratio)
            
            # Update the "Now Playing" message
            embed = discord.Embed(title="Now Playing", description=f"{self.track['title']}", color=discord.Color.green())
            embed.add_field(name="Progress", value=progress_bar)
            await now_playing_messages[self.vc.guild.id].edit(embed=embed)
            
            await asyncio.sleep(1)

    # Pause button
    @Button(label="⏸", style=ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            self.paused = True
            self.track["paused"] = True
            # Edit the Now Playing embed
            embed = discord.Embed(title="Now Playing", description=f"Paused: {self.track['title']}", color=discord.Color.orange())
            await interaction.response.edit_message(embed=embed)

    # Resume button
    @button(label="▶", style=ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_paused():
            self.vc.resume()
            self.paused = False
            self.track["paused"] = False
            # Edit the Now Playing embed
            embed = discord.Embed(title="Now Playing", description=f"Resumed: {self.track['title']}", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed)

    # Stop button (stop current track)
    @button(label="⏹", style=ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        self.vc.stop()
        # Stop and remove from queue
        global queue, current_track
        queue.clear()
        current_track = None
        await interaction.response.send_message("Playback stopped.", ephemeral=True)

    # Next track button
    @button(label="⏭", style=ButtonStyle.primary)
    async def next_track(self, interaction: discord.Interaction, button: Button):
        if len(queue) > 0:
            # Play next track
            play_next(self.vc)
            embed = discord.Embed(title="Now Playing", description=f"Next: {self.track['title']}", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed)
        else:
            await interaction.response.send_message("No next track in the queue.", ephemeral=True)

    # Previous track button
    @button(label="⏮", style=ButtonStyle.primary)
    async def previous_track(self, interaction: discord.Interaction, button: Button):
        if len(queue) > 1:
            # Play previous track
            play_previous(self.vc)
            embed = discord.Embed(title="Now Playing", description=f"Previous: {self.track['title']}", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed)
        else:
            await interaction.response.send_message("No previous track in the queue.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def play(ctx, *, search: str):
    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best',
        'quiet': True,
        'extractaudio': True,
        'audioquality': 1,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        url2 = info['formats'][0]['url'] if 'url' in info else None
        track_title = info.get('title', 'Unknown Title')
        track_artist = info.get('artist', 'Unknown Artist')

    voice_channel = ctx.author.voice.channel
    vc = await voice_channel.connect()

    # Play audio
    vc.play(discord.FFmpegPCMAudio(url2))

    embed = discord.Embed(title="Now Playing", description=f"{track_title} by {track_artist}", color=discord.Color.green())
    await ctx.send(embed=embed)

    controls = BoomboxControls(vc)
    await ctx.send("Use the buttons below to control playback.", view=controls)

bot.run(token)
