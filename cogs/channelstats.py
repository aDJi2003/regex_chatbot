import re
import aiohttp
import discord
from discord.ext import commands
from asyncio.log import logger
import asyncio

# Asumsikan file-file ini ada di dalam folder utils Anda
from utils.youtube_api import (
    CHANNEL_ID_REGEX, CHANNEL_USER_REGEX, CHANNEL_CUSTOM_REGEX, 
    fetch_channel_by_id, fetch_channel_by_username, search_channel
)
from utils.helpers import fmt_number

class ChannelStatsCog(commands.Cog, name="Channel Stats"):
    """Cog untuk mencari dan menampilkan statistik channel YouTube secara interaktif."""

    def __init__(self, bot):
        self.bot = bot

    async def _get_channel_data(self, session, query):
        """Helper function untuk mencari channel berdasarkan berbagai jenis input."""
        channel = None
        # 1. Cek apakah input adalah URL dengan Channel ID
        m = CHANNEL_ID_REGEX.search(query)
        if m:
            channel_id = m.group(1)
            return await fetch_channel_by_id(session, channel_id)

        # 2. Cek apakah input adalah URL dengan username
        m2 = CHANNEL_USER_REGEX.search(query)
        if m2:
            username = m2.group(1)
            return await fetch_channel_by_username(session, username)

        # 3. Cek apakah input adalah URL custom atau handle (@)
        search_term = query
        m3 = CHANNEL_CUSTOM_REGEX.search(query)
        if m3:
            search_term = m3.group(1)
        elif query.startswith("@"):
            search_term = query[1:]
        
        # 4. Jika tidak cocok semua, lakukan pencarian umum
        search_res = await search_channel(session, search_term)
        if not search_res:
            return None
        
        channel_id = search_res.get("id", {}).get("channelId")
        if not channel_id:
            return None
            
        return await fetch_channel_by_id(session, channel_id)

    @commands.Cog.listener()
    async def on_channelstats_request(self, message: discord.Message, content: str):
        """Listener untuk event 'channelstats_request' dari bot utama."""
        logger.info(f"📈 Channel stats request from {message.author}: {content}")
        query = content.strip()

        async with aiohttp.ClientSession() as session:
            channel = await self._get_channel_data(session, query)

            if not channel:
                await message.channel.send(f"😥 Maaf, aku tidak bisa menemukan channel dengan nama atau URL `{query}`. Coba periksa lagi ya.")
                return

            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})

            title = snippet.get("title", "Nama Tidak Diketahui")
            subs = stats.get("subscriberCount")
            vid_count = stats.get("videoCount")
            view_count = stats.get("viewCount")
            channel_id_val = channel.get("id", "")
            channel_url = f"https://www.youtube.com/channel/{channel_id_val}"
            thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url")

            embed = discord.Embed(
                title=f"🔎 Menemukan Channel: {title}",
                url=channel_url,
                color=discord.Color.red()
            )
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            
            embed.add_field(name="Subscribers", value=f"**{fmt_number(subs)}**", inline=False)
            embed.set_footer(text="Data dari YouTube Data API")

            await message.channel.send(
                "Ini dia channel yang aku temukan:",
                embed=embed
            )
            await asyncio.sleep(1) # Jeda sesaat agar lebih natural
            prompt_msg = await message.channel.send("Apakah kamu mau lihat detail lebih lanjut seperti total video dan total penayangan?")
            
            def check(m):
                return m.author == message.author and m.channel == message.channel

            try:
                response_msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                
                # Gunakan regex untuk deteksi respons positif
                if re.search(r"(?i)\b(ya|iya|yes|y|tentu|boleh|mau|lanjut|ok)\b", response_msg.content):
                    details_embed = discord.Embed(
                        title=f"📊 Statistik Lengkap - {title}",
                        color=discord.Color.green()
                    )
                    details_embed.add_field(name="Total Video", value=fmt_number(vid_count), inline=True)
                    details_embed.add_field(name="Total Penayangan", value=fmt_number(view_count), inline=True)
                    await message.channel.send("Tentu, ini dia detail lengkapnya:", embed=details_embed)
                else:
                    await message.channel.send("Baiklah, jika ada lagi yang perlu dicari, kasih tau aku ya! 👍")

            except asyncio.TimeoutError:
                await prompt_msg.edit(content="Waktu habis. Jika butuh info lagi, tanyakan saja kapan pun.", view=None)

async def setup(bot):
    await bot.add_cog(ChannelStatsCog(bot))
