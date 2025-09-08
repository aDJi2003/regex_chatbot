import discord
from discord.ext import commands

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="poll")
    async def poll(self, ctx, *, question: str):
        embed = discord.Embed(title="New Poll", description=question)
        try:
            poll_message = await ctx.send(embed=embed)
            await poll_message.add_reaction('👍')
            await poll_message.add_reaction('👎')
        except Exception as e:
            import logging
            logging.exception("Failed to create poll: %s", e)
            await ctx.send("Gagal membuat poll.")

async def setup(bot):
    await bot.add_cog(Poll(bot))
