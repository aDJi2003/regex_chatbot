import re
import aiohttp
import discord
from discord.ext import commands

from utils.youtube_api import YOUTUBE_VIDEO_REGEX, fetch_comment_threads
from utils.helpers import parse_video_arg_and_keyword

MAX_COMMENT_PAGES = 5
MAX_COMMENTS_TO_SCAN = 500
MAX_MATCHES_RETURN = 10

class FindComment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="findcomment")
    async def findcomment(self, ctx, *, arg: str):
        vid_arg, keyword = parse_video_arg_and_keyword(arg)
        if not vid_arg or not keyword:
            await ctx.send("Gunakan: `!findcomment <video_url_or_id> \"keyword\"`")
            return

        m = YOUTUBE_VIDEO_REGEX.search(vid_arg)
        if m:
            vid = m.group(1)
        else:
            candidate = vid_arg.strip()
            if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
                vid = candidate
            else:
                await ctx.send("Tidak dapat mengekstrak video ID dari argumen pertama.")
                return

        await ctx.send(f"Mencari komentar yang mengandung '{keyword}' di video `{vid}` (mencari hingga {MAX_COMMENT_PAGES} halaman komentar)...")

        matches = []
        try:
            async with aiohttp.ClientSession() as session:
                items = await fetch_comment_threads(session, vid, max_pages=MAX_COMMENT_PAGES)
                if not items:
                    await ctx.send("Tidak ada komentar yang berhasil diambil atau video tidak memiliki komentar publik.")
                    return

                lower_kw = keyword.lower()
                for it in items:
                    top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    if not top:
                        continue
                    text = top.get("textDisplay", "")
                    if lower_kw in text.lower():
                        author = top.get("authorDisplayName", "Unknown")
                        likes = top.get("likeCount", 0)
                        published = top.get("publishedAt", "")
                        preview = text if len(text) <= 300 else text[:297] + "..."
                        matches.append({
                            "author": author,
                            "likes": likes,
                            "published": published,
                            "text": preview
                        })
                        if len(matches) >= MAX_MATCHES_RETURN:
                            break

            if not matches:
                await ctx.send(f"Tidak menemukan komentar yang mengandung '{keyword}' (di maksimum {len(items)} komentar yang diperiksa).")
                return

            embed = discord.Embed(title=f"Komentar mengandung: {keyword}", description=f"Hasil teratas (max {len(matches)}):")
            for i, mitem in enumerate(matches, start=1):
                name = f"{i}. {mitem['author']} ({mitem['likes']} likes)"
                value = f"{mitem['text']}\nPublished: {mitem['published']}"
                if len(value) > 1024:
                    value = value[:1021] + "..."
                embed.add_field(name=name, value=value, inline=False)

            embed.set_footer(text=f"Scanned up to {min(len(items), MAX_COMMENTS_TO_SCAN)} comments across up to {MAX_COMMENT_PAGES} pages.")
            await ctx.send(embed=embed)

        except Exception as e:
            import logging
            logging.exception("Error in findcomment: %s", e)
            await ctx.send("Terjadi kesalahan saat mencari komentar. Cek log untuk detail.")

async def setup(bot):
    await bot.add_cog(FindComment(bot))
