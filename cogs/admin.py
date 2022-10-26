import asyncio
import copy
import os
import sys
from typing import Optional, Union
import discord
from discord.ext import commands
import ast
from bot import StarCityBot, HOME_PATH, logger

logger.name = __name__
# the file you are running your bot on linux, used for restarting the bot via update command
file_location = f"{HOME_PATH}/bot.py"


class Admin(commands.Cog):
    """Some commands for the owner of the bot"""
    def __init__(self, bot):
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
        await self.bot.db.commit()
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
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invokation context
        - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invokation will cause the bot to send the text '9'
        to the channel of invokation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        fn_name = "_eval_expr"
        msg = msg.strip("` ")
        msg = "\n".join(f"    {i}" for i in msg.splitlines())
        body = f"async def {fn_name}():\n{msg}"
        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{fn_name}()", env))
        await ctx.send(result)

    @commands.command(hidden=True, name="log")
    async def send_log(self, ctx: commands.Context, number: Optional[int]):
        """sends log file directly to discord"""
        if number is None:
            number = ""
        file = discord.File(f"{HOME_PATH}/StarBot.log{number}")
        await ctx.send(file=file)

    @commands.command(hidden=True, name="file")
    async def get_file(self, ctx: commands.Context, file_name: str):
        """sends a file directly to discord"""
        file = discord.File(f"{HOME_PATH}/{file_name}")
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

    @commands.command(hidden=True, name="broadcast")
    async def broadcast(self, ctx: commands.Context, *, msg: str):
        """Sends a message to all guilds the bot is in"""
        for guild in self.bot.guilds:
            await guild.system_channel.send(msg)

    @commands.command(hidden=True, name="msg")
    async def send_msg(self, ctx: commands.Context, channel: discord.TextChannel, *, msg: str):
        """Sends a message to a specific channel"""
        await channel.send(msg)

    @commands.command(hidden=True, name="sync")
    async def sync(self, ctx: commands.Context, guild_id: Optional[int], global_: bool = False):
        """Syncs slash commands"""
        if not global_:  # sync guild commands
            guild = ctx.guild if guild_id is None else discord.Object(id=guild_id)
            self.bot.tree.copy_global_to(guild=guild)
            cmds = await self.bot.tree.sync(guild=guild)
        else:
            cmds = await self.bot.tree.sync()

        await ctx.send(f"Synced {len(cmds)} commands {'globally' if global_ else f'locally to guild {guild.name}'}")


def insert_returns(body):
    # insert return stmt if the last expression is an expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the or else
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


async def setup(bot: StarCityBot):
    await bot.add_cog(Admin(bot))
