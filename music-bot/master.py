import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

def run_bot():
    # Load environment variables
    load_dotenv()
    # Retrieve Discord token from environment variables
    TOKEN = os.getenv('discord_token')
    # Define Discord intents
    intents = discord.Intents.default()
    intents.message_content = True
    # Initialize the bot with defined command prefix and intents, we use '.' but you can change it to anything you want
    client = commands.Bot(command_prefix=".", intents=intents)

    # Dictionary to store queues for each guild
    queues = {}

    # Dictionary to store voice clients for each guild
    voice_clients = {}

    # URLs for YouTube API requests
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='

    # Options for yt_dlp (YouTube downloader) and FFmpeg
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    # Event handler for when the bot is ready
    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    # Coroutine to play the next track in the queue
    async def play_next(ctx):
        if queues[ctx.guild.id] != [] and not getattr(play_next, 'running', False):
            play_next.running = True
            print(f"Queue length before skipping track: {len(queues[ctx.guild.id])}")
            link = queues[ctx.guild.id].pop(0)
            print(f"Queue length after skipping track: {len(queues[ctx.guild.id])}")
            await play(ctx, link=link)
            play_next.running = False

    # Command to play a track
    @client.command(name="play")
    async def play(ctx, *, link):

        try:
            # Connect to the voice channel of the user who invoked the command
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            # If the provided link is not a YouTube link, search YouTube for it
            if "www.youtube.com" not in link:
                query_string = urllib.parse.urlencode({
                    'search_query': link
                })

                content = urllib.request.urlopen(
                    youtube_results_url + query_string
                )

                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())

                link = youtube_watch_url + search_results[0]

            # Extract audio information using yt_dlp
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
            song = data['url']

            # Create FFmpeg audio player
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            # Start playing the track, lambda funtion also used to call play_next fuction and play next track in queue
            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
        except Exception as e:
            print(e)

    # Command to clear the queue
    @client.command(name="clear")
    async def clear(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
            print(len(queues[ctx.guild.id]))
        else:
            await ctx.send("There is no queue to clear")

    # Command to pause playback
    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    # Command to resume playback
    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    # Command to stop playback and disconnect from the voice channel, this will also clear queue
    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            await clear(ctx)
        except Exception as e:
            print(e)

    # Command to add a track to the queue
    @client.command(name="add")
    async def add(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")
        print(f"Queue length after adding: {len(queues[ctx.guild.id])}")
        print(f"Queue contents after adding: {queues[ctx.guild.id]}")

    # Command to skip to the next track in the queue
    @client.command(name="next")
    async def next(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await play_next(ctx)
            await ctx.send("Track has been skipped!")
        except Exception as e:
            print(e)

    # Run the bot with the specified token, this will be saved in your .env file is hosted locally or may be moved is hosted online
    client.run(TOKEN)

# Call the run_bot function to start the bot
run_bot()
