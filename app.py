import asyncio
from collections import deque
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")
DISCONNECT_AFTER = int(os.getenv("DISCONNECT_AFTER", 3))

# Bot configuration and intents
intents = discord.Intents.default()
intents.message_content = True

# DefaultHelpCommand enables the built-in !help command
help_command = commands.DefaultHelpCommand(no_category="Commands")
bot = commands.Bot(
    command_prefix="!", intents=intents, help_command=help_command
)

# yt-dlp and FFmpeg options
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": True,
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ),
    "options": "-vn",
}

# Dictionaries to store queues and inactivity timers per guild
queues = {}
inactivity_tasks = {}


def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = deque()
    return queues[guild_id]


async def inactivity_disconnect(ctx):
    """Waits for DISCONNECT_AFTER minutes and disconnects if still inactive."""
    await asyncio.sleep(DISCONNECT_AFTER * 60)
    vc = ctx.voice_client
    if vc and not vc.is_playing() and not vc.is_paused():
        get_queue(ctx.guild.id).clear()
        await vc.disconnect()
        await ctx.send(
            f"Left the voice channel due to {DISCONNECT_AFTER} minutes of inactivity."
        )


def cancel_inactivity_timer(guild_id):
    """Cancels the active inactivity timer for a guild if one exists."""
    task = inactivity_tasks.pop(guild_id, None)
    if task and not task.done():
        task.cancel()


def start_inactivity_timer(ctx):
    """Starts a new inactivity timer for a guild."""
    cancel_inactivity_timer(ctx.guild.id)
    inactivity_tasks[ctx.guild.id] = bot.loop.create_task(
        inactivity_disconnect(ctx)
    )


async def play_next(ctx):
    """Plays the next song in the queue or starts the inactivity timer."""
    queue = get_queue(ctx.guild.id)
    if queue and ctx.voice_client:
        cancel_inactivity_timer(ctx.guild.id)
        url, title = queue.popleft()
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop
            ),
        )
        await ctx.send(f"Now playing: **{title}**")
    elif ctx.voice_client:
        # Queue is empty and playback finished -> start inactivity countdown
        start_inactivity_timer(ctx)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.command(
    name="play",
    help="Plays a song from YouTube. If search query - plays the first result",
)
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    await ctx.send(f"Searching for: `{query}`...")

    loop = asyncio.get_running_loop()
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )
            if "entries" in info:
                if not info["entries"]:
                    await ctx.send("No results found.")
                    if not ctx.voice_client.is_playing():
                        start_inactivity_timer(ctx)
                    return
                info = info["entries"][0]
            url = info["url"]
            title = info.get("title", "Unknown Title")
    except Exception as e:
        await ctx.send("An error occurred while fetching the song.")
        print(f"Error extracting info: {e}")
        if ctx.voice_client and not ctx.voice_client.is_playing():
            start_inactivity_timer(ctx)
        return

    queue = get_queue(ctx.guild.id)

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append((url, title))
        await ctx.send(f"Added to queue: **{title}**")
    else:
        cancel_inactivity_timer(ctx.guild.id)
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop
            ),
        )
        await ctx.send(f"Now playing: **{title}**")


@bot.command(name="queue", help="Lists current queue")
async def show_queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue:
        await ctx.send("The queue is currently empty.")
        return

    queue_list = "\n".join(
        [f"{idx + 1}. {title}" for idx, (_, title) in enumerate(queue)]
    )
    await ctx.send(f"**Current Queue:**\n{queue_list}")


@bot.command(name="skip", help="Skips current song")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # Triggers play_next via the 'after' callback
        await ctx.send("Skipped the current song.")
    else:
        await ctx.send("No song is currently playing.")


@bot.command(name="stop", help="Stops the current song")
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        queue = get_queue(ctx.guild.id)
        queue.clear()
        ctx.voice_client.stop()  # Triggers play_next, which starts the inactivity timer
        await ctx.send("Stopped playback and cleared the queue.")
    else:
        await ctx.send("No song is currently playing.")


@bot.command(name="clear", help="Clears the queue")
async def clear(ctx):
    queue = get_queue(ctx.guild.id)
    queue.clear()
    await ctx.send("Cleared the queue.")


@bot.command(name="leave", help="Makes the bot leave the voice channel")
async def leave(ctx):
    if ctx.voice_client:
        cancel_inactivity_timer(ctx.guild.id)
        queue = get_queue(ctx.guild.id)
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I am not in a voice channel.")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("No TOKEN found in environment variables.")
    bot.run(TOKEN)
