import re
import aiohttp
import discord
from discord.ext import commands

from utils.youtube_api import CHANNEL_ID_REGEX, CHANNEL_USER_REGEX, CHANNEL_CUSTOM_REGEX, fetch_channel_by_id, fetch_channel_by_username, search_channel
from utils.helpers import fmt_number

class ChannelStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="channelstats")
    async def channelstats(self, ctx, *, arg: str):
        query = arg.strip()
        async with aiohttp.ClientSession() as session:
            channel = None
            m = CHANNEL_ID_REGEX.search(query)
            if m:
                channel_id = m.group(1)
                channel = await fetch_channel_by_id(session, channel_id)
            else:
                m2 = CHANNEL_USER_REGEX.search(query)
                if m2:
                    username = m2.group(1)
                    channel = await fetch_channel_by_username(session, username)
                else:
                    m3 = CHANNEL_CUSTOM_REGEX.search(query)
                    if m3:
                        search_term = m3.group(1)
                    elif query.startswith("@"):
                        search_term = query[1:]
                    else:
                        search_term = query
                    search_res = await search_channel(session, search_term)
                    if not search_res:
                        await ctx.send("Tidak dapat menemukan channel tersebut.")
                        return
                    channel_id = search_res.get("id", {}).get("channelId")
                    if not channel_id:
                        await ctx.send("Tidak dapat menemukan channel tersebut (no channelId).")
                        return
                    channel = await fetch_channel_by_id(session, channel_id)

            if not channel:
                await ctx.send("Gagal mengambil data channel. Pastikan input benar.")
                return

            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})

            title = snippet.get("title", "Unknown")
            subs = stats.get("subscriberCount")
            vid_count = stats.get("videoCount")
            view_count = stats.get("viewCount")
            channel_id_val = channel.get("id") or ""
            channel_url = f"https://www.youtube.com/channel/{channel_id_val}" if channel_id_val else None

            embed = discord.Embed(title=f"Channel stats — {title}", url=channel_url)
            embed.add_field(name="Subscribers", value=fmt_number(subs), inline=True)
            embed.add_field(name="Total videos", value=fmt_number(vid_count), inline=True)
            embed.add_field(name="Total views", value=fmt_number(view_count), inline=True)
            embed.set_footer(text="Data dari YouTube Data API")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ChannelStats(bot))
