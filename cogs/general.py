import random
from datetime import datetime
import aiosqlite
import pytz
import discord
from discord.ext import commands
from discord import app_commands
from bot import StarCityBot, MY_GUILD_ID, mybot, DEFAULT_PREFIX


def coinflip():
    return random.randint(0, 1)


class General(commands.Cog):
    """Some basic fun commands that don't fit into other categories"""
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Greets user in dms when he joins a server"""
        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(f"Welcome to {member.guild.name}")

    @mybot.hybrid_group(fallbakck="get", pass_context=True, with_app_command=True)
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def random(self, ctx: commands.Context):
        """Some random generators"""
        await ctx.send("Use random + name of the subcommand")

    @random.command(name="number")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(lowest="min value", highest="max value")
    async def number(self, ctx: commands.Context, lowest: int, highest: int):
        """Returns an integer between specified values"""
        await ctx.send(f"The random number from `{lowest} to {highest}` is {random.randint(lowest, highest)}!")

    @random.command(name="float")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def float(self, ctx: commands.Context):
        """Returns random float between 0 and 1"""
        await ctx.send(f"The random number between `0 and 1` is {random.uniform(0, 1)}!")

    @commands.hybrid_command(name="hi", aliases=["hello"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def hi(self, ctx: commands.Context):
        """Greets you and show prefix for current server"""
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (ctx.guild.id, ))
            prefix = await cursor.fetchone()
            prefix = prefix[0] if prefix is not None else DEFAULT_PREFIX
        await ctx.send(f"Hi {ctx.author.name}! Prefix for this server is `{prefix}`")

    @commands.hybrid_command(name="ping")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def ping(self, ctx: commands.Context):
        """Shows current ping"""
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="secret")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def secret(self, ctx: commands.Context):
        """Sends ephemeral message"""
        await ctx.send("Shh! Only you can see this", ephemeral=True)

    @commands.hybrid_command(name="smurf")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def tip(self, ctx: commands.Context):
        """Sends daily tip"""
        await ctx.send("Coming soon!", ephemeral=True)  # TODO

    @commands.hybrid_command(name="coinflip")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def flip_a_coin(self, ctx: commands.Context):
        """Flips a coin"""
        if coinflip():
            await ctx.send("Heads!")
            return
        await ctx.send("Tails!")

    @commands.hybrid_command(name="time")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def time(self, ctx: commands.Context):
        """Shows current times around the world."""
        europe_time = datetime.now(pytz.timezone("Europe/Berlin"))
        india_time = europe_time.now(pytz.timezone("Asia/Kolkata"))
        usa_time = europe_time.now(pytz.timezone("US/Eastern"))
        pacific_time = europe_time.now(pytz.timezone("US/Pacific"))
        await ctx.send(f"```{'USA Eastern': <20}{usa_time.strftime('%a %H:%M')}\n"
                       f"{'USA Pacific': <20}{pacific_time.strftime('%a %H:%M')}\n"
                       f"{'Central Europe': <20}{europe_time.strftime('%a %H:%M')}\n"
                       f"{'India': <20}{india_time.strftime('%a %H:%M')}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
