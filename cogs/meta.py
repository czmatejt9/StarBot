import asyncio
import os
from datetime import datetime
import pytz
import subprocess
import time
import sys
import discord
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID, LOG_CHANNEL_ID

# the file you are running your bot on linux, used for restarting the bot
file_location = "/home/vronvron/StarBot/bot.py"


class Meta(commands.Cog):
    """Some high level commands only for the owner of the bot"""
    def __init__(self, bot):
        super().__init__()
        self.bot: StarCityBot = bot

    async def turn_off(self, command_name: str):
        channel = self.bot.get_guild(MY_GUILD_ID).get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(description=f"Shuting down due to **{command_name}** command...",
                              timestamp=datetime.now(tz=pytz.timezone("Europe/Berlin")))
        await channel.send(embed=embed)
        await self.bot.close()
        await self.bot.db.close()
        sys.exit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        await self.turn_off("shutdown")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        """Restarts the bot with new code from github repo"""
        os.system("git pull origin master")
        await asyncio.sleep(5)
        subprocess.run(f"nohup python3 -u {file_location} &>> activity.log &", shell=True)
        await self.turn_off("update")


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
