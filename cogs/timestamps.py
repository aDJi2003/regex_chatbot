import re
import aiohttp
import discord
from discord.ext import commands

from utils.youtube_api import YOUTUBE_VIDEO_REGEX, fetch_comment_threads, TIMESTAMP_REGEX
from utils.helpers import parse_timestamp_to_seconds, seconds_to_hms

MAX_COMMENT_PAGES = 5
MAX_COMMENTS_TO_SCAN = 500
MAX_TIMESTAMP_ENTRIES = 15

class Timestamps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="timestamps")
    async def timestamps(self, ctx, *, arg: str):
        vid_arg = arg.strip()
        m = YOUTUBE_VIDEO_REGEX.search(vid_arg)
        if m:
            vid = m.group(1)
        else:
            candidate = vid_arg.strip()
            if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
                vid = candidate
            else:
                await ctx.send("Tidak dapat mengekstrak video ID. Berikan URL atau ID video yang valid.")
                return

        await ctx.send(f"Mencari timestamp di komentar video `{vid}` (mencari hingga {MAX_COMMENT_PAGES} halaman komentar)...")

        try:
            async with aiohttp.ClientSession() as session:
                items = await fetch_comment_threads(session, vid, max_pages=MAX_COMMENT_PAGES)
                if not items:
                    await ctx.send("Tidak ada komentar yang berhasil diambil atau video tidak memiliki komentar publik.")
                    return

                ts_map = {}
                total_comments_checked = 0
                for it in items:
                    total_comments_checked += 1
                    top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    if not top:
                        continue
                    text = top.get("textDisplay", "")
                    author = top.get("authorDisplayName", "Unknown")
                    for m_ts in TIMESTAMP_REGEX.finditer(text):
                        ts_str = m_ts.group(0)
                        try:
                            seconds = parse_timestamp_to_seconds(ts_str)
                        except Exception:
                            continue
                        preview = text if len(text) <= 200 else text[:197] + "..."
                        entry = {"author": author, "text": preview, "raw_ts": ts_str}
                        ts_map.setdefault(seconds, []).append(entry)

                if not ts_map:
                    await ctx.send(f"Tidak menemukan timestamp pada komentar (di {total_comments_checked} komentar yang diperiksa).")
                    return

                sorted_seconds = sorted(ts_map.keys())
                embed = discord.Embed(title="Timestamp summary (user comments)", description=f"Detected timestamps from comments (top {MAX_TIMESTAMP_ENTRIES})")
                count = 0
                for sec in sorted_seconds:
                    if count >= MAX_TIMESTAMP_ENTRIES:
                        break
                    readable = seconds_to_hms(sec)
                    mentions = ts_map[sec]
                    previews = []
                    for e in mentions[:2]:
                        previews.append(f"**{e['author']}**: {e['text']}")
                    value = "\n\n".join(previews)
                    if len(mentions) > 2:
                        value += f"\n\n_and {len(mentions)-2} more mention(s)_"
                    if len(value) > 1024:
                        value = value[:1021] + "..."
                    embed.add_field(name=f"{readable}", value=value, inline=False)
                    count += 1

                embed.set_footer(text=f"Scanned up to {min(len(items), MAX_COMMENTS_TO_SCAN)} comments across up to {MAX_COMMENT_PAGES} pages.")
                await ctx.send(embed=embed)

        except Exception as e:
            import logging
            logging.exception("Error in timestamps: %s", e)
            await ctx.send("Terjadi kesalahan saat merangkum timestamp. Cek log untuk detail.")

async def setup(bot):
    await bot.add_cog(Timestamps(bot))
