from datetime import datetime
import aiosqlite
import pytz
import discord
from discord.ext import commands
from discord import app_commands
from bot import StarCityBot, MY_GUILD_ID


class General(commands.Cog):
    """Some basic commands that don't fit into other categories"""
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(f"Welcome to {member.guild.name}")

    @commands.hybrid_command(name="hi", aliases=["hello"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def hi(self, ctx: commands.Context):
        """Greets you and show prefix for current server"""
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (ctx.guild.id, ))
            prefix = await cursor.fetchone()
            prefix = prefix[0]
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
