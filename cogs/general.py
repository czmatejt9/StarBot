from datetime import datetime
import aiosqlite
import pytz
import discord
from discord.ext import commands
from bot import StarCityBot, DEFAULT_PREFIX


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

    @commands.hybrid_command(name="hi", aliases=["hello"])
    async def hi(self, ctx: commands.Context):
        """Greets you and show prefix for current server"""
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (ctx.guild.id, ))
            prefix = await cursor.fetchone()
            prefix = prefix[0] if prefix is not None else DEFAULT_PREFIX
        await ctx.send(f"Hi {ctx.author.name}! Prefix for this server is `{prefix}`")

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Shows current ping"""
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="secret")
    async def secret(self, ctx: commands.Context):
        """Sends ephemeral message"""
        await ctx.send("Shh! Only you can see this", ephemeral=True)

    @commands.hybrid_command(name="smurf")
    async def tip(self, ctx: commands.Context):
        """Sends daily tip"""
        await ctx.send("Coming soon!", ephemeral=True)  # TODO

    @commands.hybrid_command(name="time")
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
