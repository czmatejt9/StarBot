import asyncio
import copy
import logging
import os
import subprocess
import sys
from typing import Optional, Union
import discord
from discord.ext import commands
from bot import StarCityBot, HOME_PATH, logger

logger.name = __name__
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
        """logs info when shutting down/restarting"""
        logger.info(f"Shuting down due to **{command_name}** command...")
        await self.bot.log_to_channel(f"Shuting down due to **{command_name}** command...")
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE sessions SET ended_at = ? WHERE session_id = ?", (discord.utils.utcnow(),
                                                                                           self.bot.session_id))
        await self.bot.db.close()
        await self.bot.close()
        sys.exit()

    @commands.command(hidden=True)
    async def shutdown(self, ctx: commands.Context):
        """shuts down the bot"""
        await self.turn_off("shutdown")

    @commands.command(hidden=True)
    async def update(self, ctx: commands.Context):
        """Restarts the bot with updated code from github repo"""
        os.system("git pull origin master")
        await asyncio.sleep(5)
        os.system(f"nohup python3 -u {file_location} &>> activity.log &")
        await self.turn_off("update")

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, msg: str):
        await ctx.send("#TODO")  # TODO

    @commands.command(hidden=True, name="log")
    async def send_log(self, ctx: commands.Context, number: Optional[int]):
        """sends log file directly to discord"""
        if number is None:
            number = ""
        file = discord.File(f"{HOME_PATH}/StarBot.log{number}")
        await ctx.send(file=file)

    @commands.command(hidden=True, name="info")
    async def write_log(self, ctx: commands.Context, *, msg: str):
        """writes info to log file"""
        logger.info(msg)

    @commands.command(hidden=True)
    async def sudo(self, ctx: commands.Context, channel: Optional[discord.TextChannel],
                   member: Union[discord.Member, discord.User], *, command: str):
        """Runs a command as another user"""
        msg = copy.copy(ctx.message)
        new_channel = channel or ctx.channel
        msg.channel = new_channel
        msg.author = member
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    @commands.command(hidden=True, name="sql")
    async def run_sql(self, ctx: commands.Context, *, sql: str):
        """Runs a sql command"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(sql)
            result = await cursor.fetchall()
        await ctx.send(result)


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
