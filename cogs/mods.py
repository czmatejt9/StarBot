import aiosqlite
import discord
from discord.ext import commands
from bot import StarCityBot


class Mods(commands.Cog):
    """Some commands for mods on servers"""
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @commands.command()
    async def prefix(self, ctx: commands.Context, new_prefix: str):
        """Changes prefix for current guild. Must have admin permissions."""
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Connection
            await cursor.execute("UPDATE guilds SET prefix = ? WHERE guild_id = ?", (new_prefix, ctx.guild.id))
            await self.bot.db.commit()
        await ctx.send(f"Successfully changed prefix for this server to `{new_prefix}`")

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator


async def setup(bot: commands.Bot):
    await bot.add_cog(Mods(bot))
