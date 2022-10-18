import discord
from discord.ext import commands
from bot import StarCityBot


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @commands.command()
    async def prefix(self, ctx: commands.Context, new_prefix: str):
        """Changes prefix for current guild. Must have admin permissions."""
        self.bot.db[ctx.guild.id] = new_prefix
        await ctx.send(f"Successfully changed prefix for {self.bot.user.mention} to ` {new_prefix} `")

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator


async def setup(bot: commands.Bot):
    await bot.add_cog(Mod(bot))
