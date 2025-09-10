# cogs/greetings.py

import datetime
import discord
import re
import random
from discord.ext import commands
from asyncio.log import logger
import aiohttp
from utils.youtube_api import fetch_search_videos

# Anda perlu membuat fungsi ini atau mengimpornya dari file utilitas Anda.
# Fungsi ini akan berinteraksi dengan YouTube API untuk mencari video.
# Untuk saat ini, kita akan buat versi tiruannya (mock-up).
async def search_youtube_video(query: str) -> str:
    """
    Fungsi placeholder untuk mencari video di YouTube.
    Gantilah ini dengan implementasi YouTube API Anda.
    """
    logger.info(f"Mencari video di YouTube dengan query: '{query}'")
    async with aiohttp.ClientSession() as session:
            items = await fetch_search_videos(session, query, max_results=1)
            if items is None or len(items) == 0:
                return "Tidak ada hasil."

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
    return embed


class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex kompleks untuk mendeteksi mood pengguna
        self.positive_mood_pattern = re.compile(
            r"(?i)\b(baik|senang|bahagia|luar biasa|semangat|hebat|bagus|mantap|oke|aman|sip)\b|baik-baik"
        )
        self.negative_mood_pattern = re.compile(
            r"(?i)\b(buruk|sedih|lelah|capek|sakit|pusing|kecewa|stres|down|ga (enak|semangat|mood))\b|(kurang|tidak|gak|ga) (baik|sehat|oke|semangat|fit|enak)"
        )

    @commands.Cog.listener()
    async def on_hello_request(self, message: discord.Message):
        logger.info("👋 Greetings received request from: %s", message.author)

        current_hour = datetime.datetime.now().hour

        if 4 <= current_hour < 11:
            greeting = "Selamat Pagi"
        elif 11 <= current_hour < 15:
            greeting = "Selamat Siang"
        elif 15 <= current_hour < 19:
            greeting = "Selamat Sore"
        else:
            greeting = "Selamat Malam"

        # Kirim sapaan awal dan langsung tanyakan kabar
        await message.channel.send(
            f"{greeting}, {message.author.mention}! Oh iya, bagaimana kabarmu hari ini?"
        )

        # Cek bahwa respons berikutnya datang dari user yang sama dan di channel yang sama
        def check(m):
            return m.author == message.author and m.channel == message.channel

        try:
            # Tunggu respons dari user selama 30 detik
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            user_mood_text = response.content

            # Cek mood user menggunakan regex
            if self.positive_mood_pattern.search(user_mood_text):
                logger.info(f"User {message.author} merasa baik.")
                await message.channel.send("Syukurlah kalau begitu! Aku ikut senang mendengarnya. 😄")
                
                # Rekomendasikan video penyemangat/menarik
                queries = ["video motivasi", "lagu semangat playlist", "stand up comedy indonesia", "daily dose of internet"]
                chosen_query = random.choice(queries)
                video_url = await search_youtube_video(chosen_query)

                if video_url:
                    await message.channel.send(f"Biar harimu makin seru, coba tonton video ini deh:\n", embed=video_url)

            elif self.negative_mood_pattern.search(user_mood_text):
                logger.info(f"User {message.author} merasa kurang baik.")
                await message.channel.send("Yahh, semoga lekas membaik ya. Tetap semangat! 🤗")
                
                # Rekomendasikan video penghibur/menenangkan
                queries = ["video kucing lucu", "musik santai instrumental", "relaxing nature sounds", "kompilasi video lucu"]
                chosen_query = random.choice(queries)
                video_url = await search_youtube_video(chosen_query)

                if video_url:
                    await message.channel.send(f"Mungkin video ini bisa sedikit menghiburmu:\n", embed=video_url)
            
            else:
                logger.info(f"Maaf ya, Aku belum dapat mendeteksi mood yang kamu inputkan {message.author}.")
                
            await message.channel.send("Baiklah, kalau butuh bantuan cari video di YouTube, kasih tau aku ya!")

        except TimeoutError:
            # Jika user tidak merespons dalam 30 detik
            logger.info(f"User {message.author} tidak merespons pertanyaan kabar.")
            await message.channel.send("Baiklah, kalau butuh sesuatu nanti panggil aku lagi ya! 👍")


async def setup(bot):
    await bot.add_cog(Greetings(bot))