import discord
from discord.ext import commands
from bot import StarCityBot, DEFAULT_PREFIX


class Meta(commands.Cog):
    """Some high level commands only for the owner of the bot"""
    def __init__(self, bot):
        super().__init__()
        self.bot: StarCityBot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        await ctx.send("Shutting down...")
        await self.bot.db.close()
        await ctx.bot.close()


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
