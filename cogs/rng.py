from discord.ext import commands
from discord import app_commands
from bot import StarCityBot, MY_GUILD_ID
from utils import my_rng


class RNG(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @commands.hybrid_group(pass_context=True, with_app_command=True, invoke_without_command=False)
    async def random(self, ctx: commands.Context):
        """Some random generators"""
        await ctx.send("Use random + name of the subcommand")

    @random.command(name="number")
    @app_commands.describe(lowest="min value", highest="max value")
    async def number(self, ctx: commands.Context, lowest: int, highest: int):
        """Returns an integer between specified values"""
        await ctx.send(f"The random number from `{lowest} to {highest}` is {my_rng.random_int(lowest, highest)}!")

    @random.command(name="float")
    async def float(self, ctx: commands.Context):
        """Returns random float between 0 and 1"""
        await ctx.send(f"The random number between `0 and 1` is {my_rng.random_float()}!")

    @random.command(name="coinflip")
    async def flip_a_coin(self, ctx: commands.Context):
        """Flips a coin"""
        if my_rng.coinflip():
            await ctx.send("Heads!")
            return
        await ctx.send("Tails!")

    @random.command(name="dice")
    @app_commands.describe(sides="number of sides")
    async def dice(self, ctx: commands.Context, sides: int):
        """Rolls a dice with specified number of sides"""
        await ctx.send(f"You rolled a {my_rng.random_int(1, sides)}!")


async def setup(bot: StarCityBot):
    await bot.add_cog(RNG(bot))
