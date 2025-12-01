import discord
from discord.ext import commands
import threading
import asyncio
import os
from RealtimeSTT import AudioToTextRecorder
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "."

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

latest_text = []
message_to_edit = None
lock = threading.Lock()

transcription_active = False
transcription_stop_event = threading.Event()


def process_text(text):
    global latest_text
    with lock:
        latest_text.append(text.strip())


def start_transcription():
    recorder = AudioToTextRecorder()
    while not transcription_stop_event.is_set():
        recorder.text(process_text)
    print("Transcription thread exiting.")


async def update_discord_message(user_id):
    global message_to_edit, transcription_active
    while not transcription_stop_event.is_set():
        await asyncio.sleep(2)
        with lock:
            if latest_text:
                content = f"Voice logs from <@{user_id}>\n\n```\n" + "\n".join(latest_text[-20:]) + "\n```"
            else:
                content = f"Voice logs from <@{user_id}>\n\n```\nListening...\n```"
        try:
            await message_to_edit.edit(content=content)
        except Exception as e:
            print(f"Error editing message: {e}")
            break

@bot.event
async def on_ready():
    print(f"Bot is ready.")
    print("All lines below this are logs.")
    print("------------------------------")


@bot.command(name="startVoiceTranscribe")
@commands.is_owner()
async def start_voice_transcribe(ctx):
    global message_to_edit, latest_text, transcription_active

    if transcription_active:
        await ctx.send("<:sts_info:1402277598171627551> Transcription is already running.")
        return

    transcription_stop_event.clear()
    latest_text = []
    transcription_active = True

    starting_msg = await ctx.send("<a:loadinganim:1393847961397497958> Starting voice transcription...")

    message_to_edit = await ctx.send(
        f"Voice logs from <@{ctx.author.id}>\n\n```\nListening...\n```"
    )

    await starting_msg.delete()

    threading.Thread(target=start_transcription, daemon=True).start()
    asyncio.create_task(update_discord_message(ctx.author.id))


@bot.command(name="stopVoiceTranscribe")
@commands.is_owner()
async def stop_voice_transcribe(ctx):
    global transcription_stop_event, transcription_active

    if not transcription_active:
        await ctx.send("<:sts_info:1402277598171627551> Transcription is not currently running.")
        return

    transcription_stop_event.set()
    transcription_active = False
    await ctx.send("Stopping voice transcription...")

if __name__ == "__main__":
    bot.run(token)
