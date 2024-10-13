import asyncio
import logging
import discord
from discord.ext import commands, tasks

from MieszanyMieszany.MeetingTracker import MeetingTracker
from MieszanyMieszany.StatsHolder import StatsHolder
from MieszanyMieszany.YouTubeManager import extract_audio_url
from config import ADMIN_ID, ALLOWED_CHANNELS, BOT_CHANNELS, DISCONNECT_AFTER, DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}
        self.last_used_channel = {}
        self.check_inactivity.start()
        self.stats = StatsHolder()

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        if self.song_queue[guild_id]:
            next_song = self.song_queue[guild_id].pop(0)
            audio_url, source_url = extract_audio_url(next_song)
            ctx.voice_client.play(
                discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop),
            )
            self.stats.increment_song_counter(guild_id)
            await ctx.send(f"Now playing: {source_url}")

    @commands.command(name="play", help="Plays a song from YouTube. If search query - plays the first result")
    async def play(self, ctx, *, query: str):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You're not connected to a voice channel!")
                return

        guild_id = ctx.guild.id
        if guild_id not in self.song_queue:
            self.song_queue[guild_id] = []
        self.last_used_channel[guild_id] = ctx.channel

        self.song_queue[guild_id].append(query)
        if ctx.voice_client.is_playing():
            await ctx.send(f"Added to queue: {query}")
        else:
            await self.play_next(ctx)

    @commands.command(name="leave", help="Makes the bot leave the voice channel")
    async def leave(self, ctx):
        if ctx.voice_client is not None:
            guild_id = ctx.guild.id
            self.song_queue[guild_id].clear()
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected from the voice channel.")

    @commands.command(name="skip", help="Skips current song")
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            await ctx.send("Skipped the current song.")
            ctx.voice_client.stop()  # trigger play_next via after callback

    @commands.command(name="queue", help="Lists current queue")
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.song_queue and self.song_queue[guild_id]:
            queue_list = "\n".join([f"{idx + 1}. {song}" for idx, song in enumerate(self.song_queue[guild_id])])
            await ctx.send(f"Current queue:\n{queue_list}")
        else:
            await ctx.send("The queue is empty.")

    @commands.command(name="clear", help="Clears the queue")
    async def clear(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.song_queue:
            self.song_queue[guild_id].clear()
            await ctx.send("Cleared the queue.")

    @commands.command(name="stop", help="Stops the current song")
    async def stop(self, ctx):
        guild_id = ctx.guild.id
        if ctx.voice_client is not None:
            self.song_queue[guild_id].clear()
            ctx.voice_client.stop()
            await ctx.send("Music stopped and queue cleared")

    @tasks.loop(minutes=1)
    async def check_inactivity(self):
        for guild in self.bot.guilds:
            if (
                guild.voice_client
                and not guild.voice_client.is_playing()
                and (guild.id not in self.song_queue or not self.song_queue[guild.id])
            ):
                await asyncio.sleep(DISCONNECT_AFTER)
                if guild.voice_client and not guild.voice_client.is_playing():
                    await guild.voice_client.disconnect()

                    last_channel = self.last_used_channel.get(guild.id)
                    if last_channel is not None:
                        await last_channel.send("Disconnected from the voice channel due to inactivity.")

    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        await self.bot.wait_until_ready()


bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")
    await bot.add_cog(MusicBot(bot))


@bot.check
async def only_allowed_channels(ctx):
    return ctx.channel.id in ALLOWED_CHANNELS


@bot.command(name="stats", help="Shows server stats")
async def stats(ctx):
    guild_id = ctx.guild.id
    count = StatsHolder().get_count(guild_id)
    await ctx.send(f"Songs played: {count}")


@bot.command(name="uptime", help="Shows how much the current meeting lasts")
async def uptime(ctx):
    user_voice = ctx.author.voice
    if not user_voice:
        await ctx.send("You're not connected to a voice channel!")
        return

    time = meeting_tracker.cuttent_meeting(user_voice.channel)
    if time is not None:
        await ctx.send(f"Meeting in {user_voice.channel.name} lasts {time}.")


def is_admin(ctx):
    return ctx.author.id == ADMIN_ID


@bot.command(name="createdb")
@commands.check(is_admin)
async def createdb(ctx):
    StatsHolder().create_db()
    print("Datbase created.")


meeting_tracker = MeetingTracker()


@bot.event
async def on_voice_state_update(member, before, after):
    duration = meeting_tracker.update_voice_state(member, before, after)
    if duration:
        guild = before.channel.guild
        if guild.id in BOT_CHANNELS:
            bot_channel_id = BOT_CHANNELS[guild.id]
            bot_channel = guild.get_channel(bot_channel_id)
            if bot_channel:
                await bot_channel.send(f"Meeting in {before.channel.name} lasted {duration}.")


bot.run(DISCORD_TOKEN, log_level=logging.WARN)
