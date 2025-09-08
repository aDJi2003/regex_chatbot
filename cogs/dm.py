import discord
from discord.ext import commands

class Dm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dm")
    async def dm(self, ctx, *, msg: str):
        try:
            await ctx.author.send(f'You said: {msg}')
            await ctx.send(f"{ctx.author.mention} saya telah mengirim DM ke Anda.")
        except Exception as e:
            import logging
            logging.exception("Failed to send DM: %s", e)
            await ctx.send(f"{ctx.author.mention} gagal mengirim DM. Pastikan DM dari server diizinkan.")

async def setup(bot):
    await bot.add_cog(Dm(bot))
