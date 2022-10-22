import asyncio
import logging
import os
import subprocess
import sys
from typing import Optional
import discord
from discord.ext import commands
from bot import StarCityBot, HOME_PATH, logger

# the file you are running your bot on linux, used for restarting the bot via update command
file_location = f"{HOME_PATH}/bot.py"


class Meta(commands.Cog):
    """Some commands for the owner of the bot"""
    def __init__(self, bot):
        super().__init__()
        self.bot: StarCityBot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def turn_off(self, command_name: str):
        logger.info(f"Shuting down due to **{command_name}** command...")
        await self.bot.log_to_channel(f"Shuting down due to **{command_name}** command...")
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

    @commands.command(hidden=True, name="log")
    async def send_log(self, ctx: commands.Context, number: Optional[int]):
        if number is None:
            number = ""
        file = discord.File(f"{HOME_PATH}/StarBot.log{number}")
        await ctx.send(file=file)


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
