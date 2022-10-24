from datetime import datetime, timedelta
from typing import Union
import discord
import pytz
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import random
from bot import MY_GUILD_ID, StarCityBot

CURRENCY_EMOTE = "💰"  # emoji for currency TODO change to custom emoji
TAX = 0.05  # tax for sending money to another user (5%)
DAILY_REWARD = 1000  # daily reward for using daily command
DAILY_STREAK_BONUS = 200  # bonus for daily reward if user has a streak
CENTRAL_BANK_ID = 1
# TODO add cooldown for commands


class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        await self.add_xp(ctx.author.id, random.randint(3, 5))
        return True

    async def create_account(self, user_id: int):
        user = self.bot.get_user(user_id)
        display_name = str(user)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                 (user_id, display_name, 0, 0, 0, 0, 0, 0))
            await self.bot.db.commit()

    async def ensure_user_exists(self, user_id: int):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if user is None:
                await self.create_account(user_id)

    async def add_xp(self, user_id: int, amount: int):
        await self.ensure_user_exists(user_id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
            await self.bot.db.commit()

    async def get_balance(self, user_id: int) -> tuple:
        await self.ensure_user_exists(user_id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT wallet, bank FROM users WHERE user_id = ?", (user_id,))
            wallet, bank = await cursor.fetchone()
        return wallet, bank

    async def move_money_to_bank(self, user_id: int, amount: int):
        await self.ensure_user_exists(user_id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE users SET wallet = wallet - ?, bank = bank + ? WHERE user_id = ?", (amount, amount, user_id))
            await self.bot.db.commit()

    # used for every money interaction
    async def transfer_money(self, sender_id: int, receiver_id: int, amount: int, tax: float, description: str) -> int:
        await self.ensure_user_exists(sender_id)
        await self.ensure_user_exists(receiver_id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE users SET wallet = wallet - ? WHERE user_id = ?", (amount, sender_id))
            await cursor.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ?",
                                 (int(amount - (amount * tax)), receiver_id))
            await self.bot.db.commit()
            if tax > 0:
                await cursor.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ?", (int(amount * tax), CENTRAL_BANK_ID))
                await self.log_transaction(sender_id, CENTRAL_BANK_ID, int(amount * tax), 0, "Tax")
        await self.log_transaction(sender_id, receiver_id, amount, tax, description)
        return int(amount - (amount * tax))

    async def get_transaction_id(self) -> int:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT max(transaction_id) FROM transactions")
            transaction_id = await cursor.fetchone()
            transaction_id = transaction_id[0]
        return transaction_id + 1

    async def log_transaction(self, sender_id: int, receiver_id: int, amount: int, tax: float, description: str):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (await self.get_transaction_id(), discord.utils.utcnow(), description,
                                  sender_id, receiver_id, amount, f"{tax * 100}%"))
            await self.bot.db.commit()

    async def get_transaction_log(self, user_id: int) -> list:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT * FROM transactions WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
            transactions = await cursor.fetchall()
        return list(transactions)

    def parse_amount(self, amount: str, wallet: int) -> int:
        if amount == "all":
            return wallet
        try:
            return int(amount)
        except ValueError as e:
            raise commands.BadArgument("Invalid amount.") from e

    # daily reset task
    @tasks.loop(hours=24)
    async def daily_reset(self):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE users SET daily_streak = 0 WHERE daily_today = 0")
            await cursor.execute("UPDATE users SET daily_today = 0")
            await self.bot.db.commit()

    @commands.hybrid_command(name="balance", aliases=["bal"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(member="user to check balance of, leave blank to check your own balance")
    async def balance(self, ctx: commands.Context, member: Union[discord.Member, discord.User] = None):
        """Shows your or someone's balance"""
        if member is None:
            member = ctx.author
        wallet, bank = await self.get_balance(member.id)
        embed = discord.Embed(title=f"{member.name}'s balance", color=discord.Color.green())
        embed.add_field(name="Wallet", value=f"{wallet} {CURRENCY_EMOTE}")
        embed.add_field(name="Bank", value=f"{bank} {CURRENCY_EMOTE}")
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="beg")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def beg(self, ctx: commands.Context):
        """Beg for money"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if wallet + bank >= 1000:
            msg = "You already have enough money!"
        else:
            money = random.randint(1, 100)
            await self.transfer_money(CENTRAL_BANK_ID, ctx.author.id, money, 0, "begging")
            if money < 10:
                msg = f"Someone gave you {money}{CURRENCY_EMOTE}!"
            elif money < 50:
                msg = f"Someone gave you {money}{CURRENCY_EMOTE}! That's a lot!"
            else:
                msg = f"Someone gave you {money}{CURRENCY_EMOTE}! That's a lot! You're rich now!"
        await ctx.reply(msg)

    @commands.hybrid_command(name="deposit", aliases=["dep"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(amount="normal number or 'all'")
    async def deposit(self, ctx: commands.Context, amount):
        """Deposit money into your bank"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if amount == "all":
            amount = wallet
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.reply("Amount must be a number or 'all'!")
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > wallet:
            return await ctx.reply("You don't have that much money!")
        await self.move_money_to_bank(ctx.author.id, amount)
        await ctx.reply(f"Deposited {amount}{CURRENCY_EMOTE} into your bank!")

    @commands.hybrid_command(name="withdraw", aliases=["with"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(amount="normal number or 'all'")
    async def withdraw(self, ctx: commands.Context, amount):
        """Withdraw money from your bank"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if amount == "all":
            amount = wallet
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.reply("Amount must be a number or 'all'!")
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > bank:
            return await ctx.reply("You don't have that much money in your bank!")
        await self.move_money_to_bank(ctx.author.id, -amount)
        await ctx.reply(f"Withdrew {amount}{CURRENCY_EMOTE} from your bank!")

    @commands.hybrid_command(name="send")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(member="user to send money to", amount="normal number or 'all'")
    async def send(self, ctx: commands.Context, member: discord.Member, amount):
        """Send money to another user"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if amount == "all":
            amount = wallet
        elif amount is str:
            return await ctx.reply("Amount must be a number or 'all'!")
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > wallet:
            return await ctx.reply("You don't have that much money!")

        taxed_amount = await self.transfer_money(ctx.author.id, member.id, amount, TAX, "user to user transfer")
        await ctx.reply(
            f"You sent {taxed_amount}{CURRENCY_EMOTE} to {member.mention}! ({amount - taxed_amount}{CURRENCY_EMOTE} lost to tax)")

    @commands.hybrid_command(name="gamble")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(guess="number from 1 to 6", amount="normal number or 'all'")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gamble(self, ctx: commands.Context, guess: int, amount):
        """Gamble your money against StarBot! Guess which number will be rolled on a 6-sided dice,
         StarBot also takes a guess, if yours is closer you win"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if amount == "all":
            amount = wallet
        elif amount is str:
            return await ctx.reply("Amount must be a number or 'all'!")
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if guess < 1 or guess > 6:
            return await ctx.reply("Guess must be between 1 and 6!")
        if amount > wallet:
            return await ctx.reply("You don't have that much money!")

        dice = random.randint(1, 6)
        starbot_guess = random.randint(1, 6)
        if abs(guess - dice) < abs(starbot_guess - dice):
            await self.transfer_money(self.bot.id, ctx.author.id, amount, 0, "gambling")
            embed = discord.Embed(title="You won!", color=discord.Color.green(),
                                  description=f"You guessed {guess}. StarBot guessed {starbot_guess}.\n"
                                              f"The dice rolled {dice}")
        elif abs(guess - dice) > abs(starbot_guess - dice):
            await self.transfer_money(ctx.author.id, self.bot.id, amount, 0, "gambling")
            embed = discord.Embed(title="You lost!", color=discord.Color.red(),
                                  description=f"You guessed {guess}. StarBot guessed {starbot_guess}.\n"
                                              f"The dice rolled {dice}")
        else:
            embed = discord.Embed(title="It's a tie!", color=discord.Color.gold(),
                                  description=f"You guessed {guess}. StarBot guessed {starbot_guess}.\n"
                                              f"The dice rolled {dice}")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="leaderboard", aliases=["lb"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def leaderboard(self, ctx: commands.Context):
        """View the leaderboard of the richest users"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT user_id, wallet + bank AS balance FROM users ORDER BY balance DESC LIMIT 10")
            rows = await cursor.fetchall()
        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        for i, row in enumerate(rows):
            user_id, balance = row
            if user_id in [self.bot.id, 1]:
                continue

            user = self.bot.get_user(user_id)
            if user is None:
                user = await self.bot.fetch_user(user_id)
            embed.add_field(name=f"{i + 1}. {user}", value=f"{balance}{CURRENCY_EMOTE}", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="daily")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def daily(self, ctx: commands.Context):
        """Get your daily reward"""
        await self.ensure_user_exists(ctx.author.id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT daily_streak, daily_today FROM users WHERE user_id = ?", (ctx.author.id,))
            row = await cursor.fetchone()
            daily_streak, daily_today = row
            if bool(daily_today):
                timestamp = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.utcnow()
                timestamp = datetime.fromtimestamp(timestamp.total_seconds())
                embed = discord.Embed(title="You already claimed your daily reward today!",
                                      description="Come back at", timestamp=timestamp, color=discord.Color.red())
                embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
                return await ctx.reply(embed=embed)

            await cursor.execute("UPDATE users SET daily_today = 1, daily_streak = daily_streak + 1"
                                 " WHERE user_id = ?", (ctx.author.id,))
            await self.bot.db.commit()
            await self.transfer_money(CENTRAL_BANK_ID, ctx.author.id, DAILY_REWARD + daily_streak * DAILY_STREAK_BONUS,
                                      0, "daily reward")
            embed = discord.Embed(title="Daily reward", color=discord.Color.gold(),
                                  description=f"You got {DAILY_REWARD + daily_streak * DAILY_STREAK_BONUS}{CURRENCY_EMOTE}!"
                                              f"\nYour daily streak is now {daily_streak + 1}!")
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Currency(bot))
