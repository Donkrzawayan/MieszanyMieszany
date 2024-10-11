import asyncio
import logging
import discord
from discord.ext import commands

from MieszanyMieszany.YouTubeManager import extract_audio_url
from config import ALLOWED_CHANNELS, DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

song_queue = {}

async def play_next(ctx):
    guild_id = ctx.guild.id
    if song_queue[guild_id]:
        # Get the next song in queue
        next_song = song_queue[guild_id].pop(0)
        audio_url, source_url = extract_audio_url(next_song)
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'Now playing: {source_url}')

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.check
async def only_allowed_channels(ctx):
    return ctx.channel.id in ALLOWED_CHANNELS

@bot.command(name='play', help='Plays a song from YouTube. If search query - plays the first result.')
async def play(ctx, *, query: str):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You're not connected to a voice channel!")
            return

    guild_id = ctx.guild.id

    if guild_id not in song_queue:
        song_queue[guild_id] = []
    
    song_queue[guild_id].append(query)
    if ctx.voice_client.is_playing():
        await ctx.send(f"Added to queue: {query}")
    else:
        await play_next(ctx)

@bot.command(name='leave', help='Makes the bot leave the voice channel.')
async def leave(ctx):
    if ctx.voice_client is not None:
        guild_id = ctx.guild.id
        song_queue[guild_id].clear()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")

@bot.command(name='skip', help='Skips current song')
async def skip(ctx):
    if ctx.voice_client.is_playing():
        await ctx.send("Skipped the current song.")
        ctx.voice_client.stop() # trigger play_next via after callback

@bot.command(name='queue', help='Lists current queue.')
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queue and song_queue[guild_id]:
        queue_list = "\n".join([f"{idx + 1}. {song}" for idx, song in enumerate(song_queue[guild_id])])
        await ctx.send(f"Current queue:\n{queue_list}")
    else:
        await ctx.send("The queue is empty.")

@bot.command(name='clear', help='Clear the queue.')
async def clear(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queue:
        song_queue[guild_id].clear()
        await ctx.send("Cleared the queue.")

@bot.command(name='stop', help='Stops the current song.')
async def stop(ctx):
    guild_id = ctx.guild.id
    if ctx.voice_client is not None:
        song_queue[guild_id].clear()
        ctx.voice_client.stop()
        await ctx.send("Music stopped and queue cleared.")

bot.run(DISCORD_TOKEN, log_level=logging.WARN)
