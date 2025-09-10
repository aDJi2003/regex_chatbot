import re
import aiohttp
import discord
from discord.ext import commands
import asyncio
from asyncio.log import logger

from utils.youtube_api import YOUTUBE_VIDEO_REGEX, fetch_comment_threads, TIMESTAMP_REGEX
from utils.helpers import parse_timestamp_to_seconds, seconds_to_hms

MAX_COMMENT_PAGES = 5
MAX_COMMENTS_TO_SCAN = 500
MAX_TIMESTAMP_ENTRIES = 15

class TimestampsCog(commands.Cog, name="Timestamps"):
    """Cog untuk mencari dan merangkum timestamp dari komentar video YouTube."""

    def __init__(self, bot):
        self.bot = bot
        # State management: {user_id: {"state": "waiting_for_video"}}
        self.user_states = {}

    @commands.Cog.listener()
    async def on_timestamps_request(self, message: discord.Message, content: str):
        """Listener untuk memulai alur pencarian timestamp."""
        logger.info(f"⏱️ Timestamps request from {message.author}: {content}")
        user_id = message.author.id

        # Coba ekstrak link video dari content awal
        yt_match = YOUTUBE_VIDEO_REGEX.search(content)
        if yt_match:
            video_id = yt_match.group(1)
            await self._perform_search(message, video_id)
        else:
            await message.channel.send("Tentu! Kasih aku link video YouTube yang mau dicari timestamp-nya.")
            self.user_states[user_id] = {"state": "waiting_for_video"}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listener untuk menangani respons user yang sedang dalam state menunggu."""
        if message.author.bot:
            return

        user_id = message.author.id
        if user_id in self.user_states:
            state_info = self.user_states[user_id]
            if state_info.get("state") == "waiting_for_video":
                yt_match = YOUTUBE_VIDEO_REGEX.search(message.content)
                if yt_match:
                    video_id = yt_match.group(1)
                    # Hapus state sebelum memulai pencarian
                    del self.user_states[user_id]
                    await self._perform_search(message, video_id)
                else:
                    await message.channel.send("Hmm, sepertinya itu bukan link YouTube yang valid. Coba kirim lagi ya.")

    async def _perform_search(self, message: discord.Message, video_id: str):
        """Fungsi inti untuk melakukan pencarian timestamp dan menampilkan hasil."""
        await message.channel.send(f"⏱️ Oke, aku cari timestamp di komentar video `{video_id}`. Ini mungkin butuh beberapa saat...")

        try:
            async with aiohttp.ClientSession() as session:
                items = await fetch_comment_threads(session, video_id, max_pages=MAX_COMMENT_PAGES)
                if not items:
                    await message.channel.send("Tidak ada komentar yang bisa diambil. Mungkin video ini dinonaktifkan komentarnya.")
                    return

                ts_map = {}
                for it in items:
                    top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    if not top: continue

                    text = top.get("textDisplay", "")
                    # Cari semua timestamp dalam satu komentar
                    for m_ts in TIMESTAMP_REGEX.finditer(text):
                        ts_str = m_ts.group(0)
                        try:
                            seconds = parse_timestamp_to_seconds(ts_str)
                            # Simpan info timestamp
                            ts_map.setdefault(seconds, []).append(text.strip())
                        except Exception:
                            continue
            
            if not ts_map:
                await message.channel.send(f"Maaf, tidak kutemukan format timestamp (seperti 01:23) di {len(items)} komentar terakhir.")
                return

            # Urutkan berdasarkan detik
            sorted_seconds = sorted(ts_map.keys())
            
            embed = discord.Embed(
                title=" Rangkuman Timestamp dari Komentar",
                description=f"Menampilkan hingga {MAX_TIMESTAMP_ENTRIES} momen yang paling sering disebut:",
                color=discord.Color.purple()
            )
            
            count = 0
            for sec in sorted_seconds:
                if count >= MAX_TIMESTAMP_ENTRIES: break
                
                readable_time = seconds_to_hms(sec)
                mentions = ts_map[sec]
                # Ambil satu contoh komentar untuk preview
                preview_text = mentions[0]
                if len(preview_text) > 150:
                    preview_text = preview_text[:147] + "..."
                
                field_value = f"Disebut dalam **{len(mentions)}** komentar.\n*Contoh: \"{preview_text}\"*"
                
                # Buat link YouTube dengan timestamp
                yt_url = f"https://www.youtube.com/watch?v={video_id}&t={sec}s"
                embed.add_field(
                    name=f"[{readable_time}]({yt_url})",
                    value=field_value,
                    inline=False
                )
                count += 1

            embed.set_footer(text=f"Memindai {len(items)} komentar teratas.")
            await message.channel.send(embed=embed)

        except Exception as e:
            logger.exception("Error in timestamps cog: %s", e)
            await message.channel.send("Terjadi kesalahan saat mencari timestamp. Coba periksa kembali link videonya.")

async def setup(bot):
    await bot.add_cog(TimestampsCog(bot))
