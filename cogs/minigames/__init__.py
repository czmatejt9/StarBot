import discord
from discord.ext import commands
from discord import app_commands
from . import tictactoe, gobblet
from bot import StarCityBot, MY_GUILD_ID, mybot


class Minigames(commands.Cog):
    """Minigames to play with other users"""
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    @mybot.hybrid_group(fallbakck="get", pass_context=True, with_app_command=True)
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def game(self, ctx: commands.Context):
        """Some minigames to play with other users"""
        await ctx.send("Use game + name of the game + opponent")

    @game.command(name="xo", aliases=["tic", "tictactoe"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @commands.guild_only()
    @app_commands.describe(member="The user you wanna play against")
    async def tic_tac_toe(self, ctx: commands.Context, *, member: discord.Member):
        """Challenges specified user to a game of tic-tac-toe"""
        if member.bot:
            await ctx.reply("You cannot play against a bot", ephemeral=True)
            return
        elif ctx.author.id == member.id:
            await ctx.reply("You cannot play against yourself! Go find some friends!", ephemeral=True)
            return

        prompt = tictactoe.Prompt(ctx.author, member)
        msg = await ctx.send(f"{member.mention} has been challenged to a game of tic-tac-toe by {ctx.author.mention}\n"
                             f"Do you accept?", view=prompt)
        prompt.message = msg

    @game.command(name="gobblet", aliases=["gobbletgobblers"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @commands.guild_only()
    @app_commands.describe(member="The user you wanna play against")
    async def gobblet_gobblers(self, ctx: commands.Context, *, member: discord.Member):
        """Challenges specified user to a game of Gobblet gobblers. This game is similar to tic-tac-toe.
        For full rules use /gobblet_rules or prefix+gobblet_rules"""
        if member.bot:
            await ctx.reply("You cannot play against a bot", ephemeral=True)
            return
        elif ctx.author.id == member.id:
            await ctx.reply("You cannot play against yourself! Go find some friends!", ephemeral=True)
            return

        prompt = gobblet.Prompt(ctx.author, member)
        msg = await ctx.send(f"{member.mention} has been challenged to a game of Gobblet gobblers by "
                             f"{ctx.author.mention}\nDo you accept? (for rules use /gobblet_rules)", view=prompt)
        prompt.message = msg

    @commands.hybrid_command(name="gobblet_rules")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @commands.guild_only()
    async def gobblet_rules(self, ctx: commands.Context):
        """Sends a link with rules of Gobblet gobblers"""
        await ctx.send("Rules here: https://themindcafe.com.sg/wp-content/uploads/2018/07/Gobblet-Gobblers.pdf\n"
                       "Some clarification on rules: **Three in a row counts only after a whole move is finished** e.g."
                       " If a player chooses to move piece which uncovers opponent's piece that creates 3 in a row"
                       " for opponent, but with that piece covers one of the other 2 pieces which are in the opponent's"
                       " 3 in a row (thus the 3 in a row isn't visible anymore), he DOESN'T lose.\n"
                       "**If after any move there are 3 in a row for both players, the player making the last move loses.**")


async def setup(bot: StarCityBot):
    await bot.add_cog(Minigames(bot))
