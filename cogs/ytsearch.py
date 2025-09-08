import aiohttp
import discord
from discord.ext import commands

from utils.youtube_api import fetch_search_videos
from utils.helpers import fmt_number

SEARCH_LIMIT_PER_DAY = 5
_search_usage = {}

def increment_search_usage(user_id: int) -> int:
    from datetime import date
    today = date.today()
    entry = _search_usage.get(user_id)
    if entry is None or entry['date'] != today:
        _search_usage[user_id] = {'date': today, 'count': 1}
        return 1
    else:
        entry['count'] += 1
        return entry['count']

def get_search_usage(user_id: int) -> int:
    from datetime import date
    entry = _search_usage.get(user_id)
    if not entry or entry['date'] != date.today():
        return 0
    return entry['count']

class YtSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ytsearch")
    async def ytsearch(self, ctx, *, query: str):
        user_id = ctx.author.id
        used = get_search_usage(user_id)
        if used >= SEARCH_LIMIT_PER_DAY:
            await ctx.send(f"{ctx.author.mention} Anda telah mencapai batas pencarian harian ({SEARCH_LIMIT_PER_DAY}).")
            return

        current_count = increment_search_usage(user_id)
        remaining = SEARCH_LIMIT_PER_DAY - current_count

        await ctx.send(f"Mencari: `{query}` (sisa jatah hari ini: {remaining})...")

        async with aiohttp.ClientSession() as session:
            items = await fetch_search_videos(session, query, max_results=5)
            if items is None or len(items) == 0:
                await ctx.send("Tidak ada hasil.")
                return

            embed = discord.Embed(title=f"Search results for: {query}", description=f"Top {len(items)} results")
            for it in items:
                vid_id = it.get("id", {}).get("videoId")
                snip = it.get("snippet", {})
                title = snip.get("title")
                channel = snip.get("channelTitle")
                url = f"https://youtu.be/{vid_id}" if vid_id else None
                tv = f"[{title}]({url})\nChannel: {channel}" if url else f"{title}\nChannel: {channel}"
                embed.add_field(name="\u200b", value=tv, inline=False)
            embed.set_footer(text="Note: YouTube Data API search endpoint is quota-expensive.")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(YtSearch(bot))
