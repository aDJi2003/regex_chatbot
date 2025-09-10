from asyncio.log import logger
import asyncio
import re
import discord
from discord.ext import commands

from utils.youtube_api import YOUTUBE_VIDEO_REGEX


class Chatbot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_ytinfo = {}  # {user_id: True}
        # Regex patterns (expand later for ytinfo, ytsearch, etc.)
        self.patterns = {
            # Pola lama: r"\b(hi|hello|hey|halo)\b"
            "hello": r"(?i)\b(h[ai]+|he(y|llo)|halo|pagi|siang|sore|malam|yo|sup)\b",

            # Pola lama: r"(info|detail).*(youtu|video)"
            "ytinfo": r"(?i)(?=.*(info|det[ai]l|keterangan|jelaskan|apa itu))(?=.*(youtu|video|klip|rekaman))",

            # Pola lama: r"(search|find|cari).*video"
            "ytsearch": r"(?i)(?=.*(search|find|car[i|ikan]|temukan|putar|play|mainkan))(?=.*(video|youtube|lagu|musik|film|klip))",

            # Pola lama: r"(statistik|channel|subscriber)"
            "channelstats": r"(?i)(?=.*(info|statistik|stats|data|jumlah|berapa))(?=.*(channel|kanal|subscriber))",

            # Pola lama: r"(timestamp|penanda waktu)"
            "timestamps": r"(?i)\b(timestamps?|penanda waktu|lompat ke|menit ke|detik ke|bagian|chapter)\b|\d{1,2}:\d{2}",

            # Pola lama: r"(cari|temukan).*komentar"
            "findcomment": r"(?i)(?=.*(car[i|ikan]|temukan|search|find|lihat|tampilkan))(?=.*(komentar|comment|komen))",

            # Pola lama: r"(poll|vote|voting)"
            "poll": r"(?i)\b(poll|vote|voting|polling|jajak pendapat|bikin vote|buat polling)\b",
        }
        self.positive_mood_pattern = re.compile(
            r"(?i)\b(baik|senang|bahagia|luar biasa|semangat|hebat|bagus|mantap|oke|aman|sip)\b|baik-baik"
        )
        self.negative_mood_pattern = re.compile(
            r"(?i)\b(buruk|sedih|lelah|capek|sakit|pusing|kecewa|stres|down|ga (enak|semangat|mood))\b|(kurang|tidak|gak|ga) (baik|sehat|oke|semangat|fit|enak)"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content.lower()
        original_content = message.content

        

        # Greeting
        if re.search(self.patterns["hello"], content):
            self.bot.dispatch("hello_request", message)
        
        # Video info
        if message.author.id in self.pending_ytinfo:
            if re.search(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/", original_content):
                m = YOUTUBE_VIDEO_REGEX.search(original_content)
                if m:
                    vid = m.group(1)
                    await message.channel.send("🎬 Oke, tunggu sebentar ya... lagi ambil detail videonya!")
                    self.bot.dispatch("ytinfo_request", message, vid)
                    del self.pending_ytinfo[message.author.id]  # reset state
                    return
                else:
                    await message.channel.send(
                        "⚠️ Itu bukan link YouTube yang valid.\n"
                        "Contoh: https://youtu.be/dQw4w9WgXcQ"
                    )
                    return
            else:
                await message.channel.send(
                    "⚠️ Aku butuh link YouTube yang valid.\n"
                    "Contoh: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
                return
        elif re.search(self.patterns["ytinfo"], content):
            logger.info("🔍 YtInfo request detected: %s", content)
            # check apakah ada link youtube di pesan
            # cek apakah langsung ada link
            if not re.search(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/", original_content):
                await message.channel.send("Mau info video apa? Kasih aku link YouTube-nya ya!")
                # simpan state user
                self.pending_ytinfo[message.author.id] = True
                return
            else:
                m = YOUTUBE_VIDEO_REGEX.search(original_content)
                if m:
                    vid = m.group(1)
                    await message.channel.send("🎬 Oke, tunggu sebentar ya... lagi ambil detail videonya!")
                    self.bot.dispatch("ytinfo_request", message, vid)
                    # apakah ada hal lain yang bisa dibantu
                    # tunggu 100 ms
                    await asyncio.sleep(0.1)
                    await message.channel.send("apakah ada hal lain yang bisa saya bantu?")
                    del self.pending_ytinfo[message.author.id]  # reset state
                    return
                else:
                    await message.channel.send(
                        "⚠️ Itu bukan link YouTube yang valid.\n"
                        "Contoh: https://youtu.be/dQw4w9WgXcQ"
                    )
                    return
                
        # Video search
        elif re.search(self.patterns["ytsearch"], content):
            query = re.sub(self.patterns["ytsearch"], "", content).strip()
            logger.info("🔍 YtSearch query: %s", query)
            if query:
                await message.channel.send(f"🔎 Lagi cari video tentang **{query}** ... (dummy result)")
                # tanyakan berapa jumlah hasil yang diinginkan
                await message.channel.send("Mau berapa hasil yang ditampilkan? (1-10)")
                def check(m):
                    return m.author == message.author and m.channel == message.channel and m.content.isdigit() and 1 <= int(m.content) <= 10

                try:
                    response = await self.bot.wait_for("message", check=check, timeout=30)
                    count = int(response.content)
                    self.bot.dispatch("ytsearch_request", message, query, count)
                except TimeoutError:
                    await message.channel.send("⏰ Timeout! Silakan coba lagi.")
            else:
                await message.channel.send("Mau cari video tentang apa?")
        
        # Channel stats
        elif re.search(self.patterns["channelstats"], content):
            await message.channel.send("📊 Channel apa yang mau dicek? (kasih nama/link)")
        
        # Timestamp
        elif re.search(self.patterns["timestamps"], content):
            await message.channel.send("⏱️ Kasih link video, aku bantu kumpulin timestamp dari komentar.")
        
        # Comment finder
        elif re.search(self.patterns["findcomment"], content):
            await message.channel.send("💬 Kasih link video + kata kunci komentar yang dicari.")
        
        # Poll creation
        elif re.search(self.patterns["poll"], content):
            self.bot.dispatch("poll_request", message, content)
        # If bot is mentioned
        elif self.bot.user.mentioned_in(message):
            await message.channel.send("👀 Kamu manggil aku? Aku bisa bantu cek info video, cari video, cari komentar, atau statistik channel!")
        
        # jika bot tidak memahami keyword dalam self patterns. tetapi bukan keyword dalam positive_mood_pattern atau negative_mood_pattern
        elif not any(re.search(pattern, content) for pattern in self.patterns.values()) and not self.positive_mood_pattern.search(content) and not self.negative_mood_pattern.search(content):
            await message.channel.send("🤖 Maaf, aku belum paham. Coba tanya soal info video, cari video, cari komentar, atau statistik channel.")

async def setup(bot):
    await bot.add_cog(Chatbot(bot))
