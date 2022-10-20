import os
import time
import sys
import discord
from discord.ext import commands
from bot import StarCityBot


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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        os.system("git pull origin master")
        time.sleep(5)
        os.execv(sys.argv[0], sys.argv)


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
