import os
import subprocess
import time
import sys
import discord
from discord.ext import commands
from bot import StarCityBot

# the file you are running your bot on linux, used for restarting the bot
file_location = "/home/vronvron/StarBot/bot.py"


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
        """Restarts the bot with new code from github repo"""
        os.system("git pull origin master")
        subprocess.run(f"nohup python3 -u {file_location} &>> activity.log &", shell=True)
        await ctx.bot.close()
        await self.bot.db.close()
        os.system(f"kill -9 {os.getpid()}")
        sys.exit()


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
