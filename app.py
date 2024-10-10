import discord
from discord.ext import commands

from YouTubeManager import extract_audio_url
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.command(name='play', help='Plays a song from YouTube. If a search query is given, it plays the first result.')
async def play(ctx, *, url):
    voice_channel = ctx.author.voice.channel

    if not voice_channel:
        await ctx.send("You're not connected to a voice channel!")
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice_client = await voice_channel.connect()

    if voice_client.is_playing():
        voice_client.stop()

    audio_url, source_url = extract_audio_url(url)
    voice_client.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS))
    await ctx.send(f'Now playing: {source_url}')

@bot.command(name='leave', help='Makes the bot leave the voice channel.')
async def leave(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")

@bot.command(name='pause', help='Pauses the current song.')
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Music paused.")
    else:
        await ctx.send("No music is playing right now.")

@bot.command(name='resume', help='Resumes the paused song.')
async def resume(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Music resumed.")
    else:
        await ctx.send("No music is paused right now.")

@bot.command(name='stop', help='Stops the current song.')
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Music stopped.")
    else:
        await ctx.send("No music is playing right now.")


bot.run(DISCORD_TOKEN)
