import os
import subprocess
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
        subprocess.run("nohup python3 -u home/StarBot/bot.py &>> activity.log &", shell=True)
        await ctx.bot.close()
        await self.bot.db.close()
        sys.exit()


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
