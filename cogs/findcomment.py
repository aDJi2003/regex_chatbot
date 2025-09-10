import re
import aiohttp
import discord
from discord.ext import commands
import asyncio
from asyncio.log import logger

from utils.youtube_api import YOUTUBE_VIDEO_REGEX, fetch_comment_threads

MAX_COMMENT_PAGES = 5
MAX_MATCHES_RETURN = 10

class FindCommentCog(commands.Cog, name="Find Comment"):
    """Cog untuk mencari komentar di video YouTube secara interaktif."""

    def __init__(self, bot):
        self.bot = bot
        # State management: {user_id: {"state": "waiting_for_video" | "waiting_for_keyword", "video_id": str}}
        self.user_states = {}

    @commands.Cog.listener()
    async def on_findcomment_request(self, message: discord.Message, content: str):
        """Listener untuk memulai alur pencarian komentar."""
        logger.info(f"💬 FindComment request from {message.author}: {content}")
        user_id = message.author.id

        # Coba ekstrak link video dan keyword dari pesan awal
        video_id = None
        keyword = None

        # Cek apakah ada link di content
        yt_match = YOUTUBE_VIDEO_REGEX.search(content)
        if yt_match:
            video_id = yt_match.group(1)
            # Sisa content dianggap keyword
            keyword = content.replace(yt_match.group(0), "").strip().strip('"')

        if video_id and keyword:
            # Jika video dan keyword sudah ada, langsung cari
            await self._perform_search(message, video_id, keyword)
        elif video_id:
            # Jika hanya video yang ada, tanyakan keyword
            await message.channel.send(f"✅ Oke, aku sudah simpan link videonya. Sekarang, kata kunci apa yang mau kamu cari di kolom komentar?")
            self.user_states[user_id] = {"state": "waiting_for_keyword", "video_id": video_id}
        else:
            # Jika tidak ada info sama sekali, mulai dari awal
            await message.channel.send("Tentu! Kasih aku link video YouTube yang mau dicari komentarnya.")
            self.user_states[user_id] = {"state": "waiting_for_video"}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listener untuk menangani respons user dalam alur pencarian."""
        if message.author.bot:
            return

        user_id = message.author.id
        state_info = self.user_states.get(user_id)

        if not state_info:
            return

        state = state_info.get("state")
        
        if state == "waiting_for_video":
            yt_match = YOUTUBE_VIDEO_REGEX.search(message.content)
            if yt_match:
                video_id = yt_match.group(1)
                await message.channel.send("✅ Oke, link video diterima. Sekarang, kata kunci apa yang mau kamu cari?")
                self.user_states[user_id] = {"state": "waiting_for_keyword", "video_id": video_id}
            else:
                await message.channel.send("Hmm, sepertinya itu bukan link YouTube yang valid. Coba kirim lagi ya.")
        
        elif state == "waiting_for_keyword":
            video_id = state_info.get("video_id")
            keyword = message.content.strip().strip('"')
            if video_id and keyword:
                await self._perform_search(message, video_id, keyword)
                del self.user_states[user_id] # Hapus state setelah selesai

    async def _perform_search(self, message: discord.Message, video_id: str, keyword: str):
        """Fungsi inti untuk melakukan pencarian dan menampilkan hasil."""
        await message.channel.send(f"🔎 Oke, aku cari komentar dengan kata kunci **'{keyword}'** di video `{video_id}`. Tunggu sebentar ya...")

        matches = []
        scanned_count = 0
        try:
            async with aiohttp.ClientSession() as session:
                items = await fetch_comment_threads(session, video_id, max_pages=MAX_COMMENT_PAGES)
                if not items:
                    await message.channel.send("Tidak ada komentar yang bisa diambil. Mungkin video ini dinonaktifkan komentarnya.")
                    return

                scanned_count = len(items)
                lower_kw = keyword.lower()
                for it in items:
                    top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    if not top: continue
                    
                    text = top.get("textDisplay", "")
                    if lower_kw in text.lower():
                        matches.append({
                            "author": top.get("authorDisplayName", "Unknown"),
                            "likes": top.get("likeCount", 0),
                            "text": text if len(text) <= 300 else text[:297] + "..."
                        })
                        if len(matches) >= MAX_MATCHES_RETURN:
                            break
            
            if not matches:
                await message.channel.send(f"Maaf, tidak kutemukan komentar yang mengandung **'{keyword}'** (dari {scanned_count} komentar terakhir).")
                return

            embed = discord.Embed(
                title=f"💬 Komentar Mengandung: '{keyword}'",
                description=f"Menampilkan hingga {len(matches)} hasil teratas:",
                color=discord.Color.gold()
            )
            for i, match in enumerate(matches, 1):
                embed.add_field(
                    name=f"#{i} oleh {match['author']} ({match['likes']} suka)",
                    value=match['text'],
                    inline=False
                )
            embed.set_footer(text=f"Memindai {scanned_count} komentar teratas.")
            await message.channel.send(embed=embed)

        except Exception as e:
            logger.exception("Error in findcomment: %s", e)
            await message.channel.send("Terjadi kesalahan saat mencari komentar. Coba periksa kembali link videonya.")

async def setup(bot):
    await bot.add_cog(FindCommentCog(bot))
