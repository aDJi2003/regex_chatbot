import discord
from discord.ext import commands, tasks
import re
import datetime
import asyncio
from asyncio.log import logger

# Helper function untuk mengubah string durasi (e.g., "5m", "1h") menjadi detik
def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    
    match = re.match(r"(\d+)([smhd])", duration_str.lower())
    if not match:
        return 0
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    return 0

class PollCog(commands.Cog, name="Polling"):
    """Cog untuk membuat dan mengelola polling interaktif."""
    
    def __init__(self, bot):
        self.bot = bot
        # Emoji yang akan digunakan untuk pilihan polling
        self.poll_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        # List untuk menyimpan polling yang sedang aktif
        self.active_polls = []
        # Memulai background task untuk memeriksa polling yang sudah selesai
        self.check_expired_polls.start()

    def cog_unload(self):
        """Menghentikan background task saat cog di-unload."""
        self.check_expired_polls.cancel()

    @commands.Cog.listener()
    async def on_poll_request(self, message: discord.Message, content: str):
        """
        Listener untuk event 'poll_request' dari bot utama.
        Memproses string untuk membuat polling kustom.
        Format content: 
        1. "Judul" "Pilihan 1" "Pilihan 2" ... [Durasi]
        2. Judul\nPilihan 1\nPilihan 2\n...[Durasi]
        """
        logger.info(f"📊 Poll request received from {message.author}: {content}")
        
        args = []
        duration_str = None

        # Cek apakah pengguna menggunakan format tanda kutip
        if '"' in content:
            args = re.findall(r'"(.*?)"', content)
            duration_str_match = re.search(r'\s+(\d+[smhd])$', content.strip())
            duration_str = duration_str_match.group(1) if duration_str_match else None
        # Jika tidak, cek apakah pengguna menggunakan format baris baru
        elif '\n' in content:
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            
            # Cek apakah baris terakhir adalah durasi
            last_line = lines[-1]
            duration_match = re.fullmatch(r"(\d+[smhd])", last_line.lower())
            if duration_match:
                duration_str = duration_match.group(1)
                args = lines[:-1] # Semua baris kecuali terakhir adalah argumen
            else:
                args = lines # Semua baris adalah argumen
        else:
            # Jika format tidak dikenali, kirim pesan bantuan
            await message.channel.send(
                "❌ **Format polling tidak dikenali!**\n\n"
                "Gunakan salah satu format berikut:\n"
                "1. **Dengan tanda kutip:**\n`buat poll \"Judul\" \"Pilihan A\" \"Pilihan B\" 5m`\n\n"
                "2. **Dengan baris baru (enter):**\n"
                "```\nbuat poll Judul Pollingnya\nPilihan A\nPilihan B\n5m\n```"
            )
            return
            
        if len(args) < 3:
            await message.channel.send("❌ **Argumen kurang!** Kamu butuh setidaknya 1 judul dan 2 pilihan.")
            return
            
        if len(args) > 11:
            await message.channel.send(f"❌ **Terlalu banyak pilihan!** Maksimal adalah {len(self.poll_emojis)} pilihan.")
            return

        title = args[0]
        options = args[1:]
        duration_seconds = parse_duration(duration_str) if duration_str else 0

        # Membuat deskripsi untuk embed
        description = []
        for i, option in enumerate(options):
            description.append(f"{self.poll_emojis[i]} **{option}**")
        
        embed = discord.Embed(
            title=f"📊 {title}",
            description="\n\n".join(description),
            color=discord.Color.blue()
        )
        
        end_time = None
        if duration_seconds > 0:
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
            embed.set_footer(text=f"Polling ini akan berakhir pada {end_time.strftime('%H:%M:%S, %d %B %Y')}")
        else:
            embed.set_footer(text="Polling ini tidak memiliki batas waktu.")

        try:
            poll_message = await message.channel.send(embed=embed)
            # Menambahkan reaksi emoji ke pesan polling
            for i in range(len(options)):
                await poll_message.add_reaction(self.poll_emojis[i])
            
            # Jika ada durasi, simpan info polling untuk dicek nanti
            if duration_seconds > 0 and end_time is not None:
                self.active_polls.append({
                    "message_id": poll_message.id,
                    "channel_id": message.channel.id,
                    "end_time": end_time,
                    "title": title,
                    "options": options
                })
        except Exception as e:
            logger.error(f"Gagal membuat poll: {e}")
            await message.channel.send("⚠️ Gagal membuat polling. Pastikan aku punya izin untuk menambah reaksi.")

    @tasks.loop(seconds=5)
    async def check_expired_polls(self):
        """Background task yang berjalan setiap 5 detik untuk memeriksa polling yang kedaluwarsa."""
        # Iterasi melalui copy dari list untuk menghindari masalah saat menghapus item
        for poll in self.active_polls[:]:
            if datetime.datetime.now() > poll["end_time"]:
                try:
                    channel = self.bot.get_channel(poll["channel_id"])
                    if not channel:
                        self.active_polls.remove(poll)
                        continue

                    message = await channel.fetch_message(poll["message_id"])
                    
                    # Menghitung hasil
                    results = {}
                    highest_votes = 0
                    for reaction in message.reactions:
                        if str(reaction.emoji) in self.poll_emojis:
                            # Mengurangi 1 untuk menghilangkan suara dari bot itu sendiri
                            vote_count = reaction.count - 1
                            option_index = self.poll_emojis.index(str(reaction.emoji))
                            results[poll["options"][option_index]] = vote_count
                            if vote_count > highest_votes:
                                highest_votes = vote_count

                    winners = [option for option, votes in results.items() if votes == highest_votes and highest_votes > 0]
                    
                    # Membuat embed hasil
                    result_description = "\n".join([f"**{option}**: {votes} suara" for option, votes in sorted(results.items(), key=lambda item: item[1], reverse=True)])
                    
                    result_embed = discord.Embed(
                        title=f"🏁 Hasil Polling: {poll['title']}",
                        description=result_description,
                        color=discord.Color.green()
                    )

                    if winners:
                        result_embed.add_field(name="🏆 Pemenang", value=", ".join(winners))
                    else:
                        result_embed.add_field(name="Hasil", value="Tidak ada suara yang masuk.")

                    await channel.send(embed=result_embed)
                    
                except discord.NotFound:
                    logger.warning(f"Pesan polling {poll['message_id']} tidak ditemukan. Mungkin sudah dihapus.")
                except Exception as e:
                    logger.error(f"Error saat memproses polling kedaluwarsa: {e}")
                finally:
                    # Hapus polling dari list aktif
                    self.active_polls.remove(poll)

    @check_expired_polls.before_loop
    async def before_check_expired_polls(self):
        """Menunggu bot siap sebelum memulai loop."""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PollCog(bot))

