import re
import aiohttp
import discord
from discord.ext import commands

from utils.youtube_api import YOUTUBE_VIDEO_REGEX, fetch_youtube_video_info
from utils.helpers import iso8601_duration_to_readable, fmt_number

class YtInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ytinfo")
    async def ytinfo(self, ctx, *, arg: str):
        vid = None
        m = YOUTUBE_VIDEO_REGEX.search(arg)
        if m:
            vid = m.group(1)
        else:
            candidate = arg.strip()
            if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
                vid = candidate

        if not vid:
            await ctx.send("Tidak dapat mengekstrak video ID. Berikan URL atau ID video yang valid.")
            return

        async with aiohttp.ClientSession() as session:
            info = await fetch_youtube_video_info(session, vid)
            if not info:
                await ctx.send("Gagal mengambil data video.")
                return

            snippet = info.get("snippet", {})
            stats = info.get("statistics", {})
            details = info.get("contentDetails", {})

            title = snippet.get("title", "Unknown")
            channel_title = snippet.get("channelTitle", "Unknown")
            duration = iso8601_duration_to_readable(details.get("duration", ""))
            views = fmt_number(stats.get("viewCount"))
            likes = stats.get("likeCount")
            embed = discord.Embed(title=title, url=f"https://youtu.be/{vid}", description=f"Channel: {channel_title}")
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Views", value=views, inline=True)
            if likes is not None:
                embed.add_field(name="Likes", value=fmt_number(likes), inline=True)

            thumbs = snippet.get("thumbnails", {})
            thumb = None
            if isinstance(thumbs, dict):
                if "high" in thumbs and isinstance(thumbs["high"], dict):
                    thumb = thumbs["high"].get("url")
                elif "default" in thumbs and isinstance(thumbs["default"], dict):
                    thumb = thumbs["default"].get("url")
            if thumb:
                embed.set_thumbnail(url=thumb)

            embed.set_footer(text="Info provided by YouTube Data API")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(YtInfo(bot))
