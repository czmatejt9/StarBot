import asyncio
import logging
import os
import subprocess
import sys
import discord
from discord.ext import commands
from bot import StarCityBot, HOME_PATH

# the file you are running your bot on linux, used for restarting the bot via update command
file_location = f"{HOME_PATH}/bot.py"
logger = logging.getLogger(__name__)


class Meta(commands.Cog):
    """Some commands for the owner of the bot"""
    def __init__(self, bot):
        super().__init__()
        self.bot: StarCityBot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def turn_off(self, command_name: str):
        logger.info(f"Shuting down due to **{command_name}** command...")
        await self.bot.log_to_channel(f"INFO: Shuting down due to **{command_name}** command...")
        await self.bot.close()
        await self.bot.db.close()
        sys.exit()

    @commands.command(hidden=True)
    async def shutdown(self, ctx: commands.Context):
        await self.turn_off("shutdown")

    @commands.command(hidden=True)
    async def update(self, ctx: commands.Context):
        """Restarts the bot with new code from github repo"""
        os.system("git pull origin master")
        await asyncio.sleep(5)
        subprocess.run(f"nohup python3 -u {file_location} &>> activity.log &", shell=True)
        await self.turn_off("update")

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, msg: str):
        eval(msg)


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
