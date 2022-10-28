import sys
from datetime import datetime, timedelta
from typing import Union
import discord
from typing import Optional, Literal
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import random
from bot import MY_GUILD_ID, StarCityBot, logger
from .utils import my_math

logger.name = __name__

CURRENCY_EMOTE = "💰"  # emoji for currency TODO change to custom emoji
TAX = 0.05  # tax for sending money to another user (5%)
DAILY_REWARD = 10000  # daily reward for using daily command
DAILY_STREAK_BONUS = 2000  # bonus for daily reward if user has a streak
MONEY_FOR_WORK = 2000, 4000  # range of money for work command
CENTRAL_BANK_ID = 1
LOTTO_BANK_ID = 2
ITEMS = Literal["apple", "Spjáťa's bulletproof vest", "lotto ticket"]
# TODO top priority: add lotto drawing every midnight utc


class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot
        self.daily_loop_starter.start()
        self.set_items = False

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
            return False

    async def get_item_id(self, item_name: str) -> int:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT item_id FROM items WHERE name = ?", (item_name,))
            item_id = await cursor.fetchone()
        return item_id[0] if item_id is not None else False

    async def get_all_items(self) -> list:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT * FROM items")
            items = await cursor.fetchall()
        return list(items)

    async def buy_item(self, user_id: int, item: str, amount: int, can_go_negative: bool = False) -> str:
        await self.ensure_user_exists(user_id)
        if(item_id := await self.get_item_id(item)) is False:
            return "Item not found"
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT price FROM items WHERE item_id = ?", (item_id,))
            price = await cursor.fetchone()
            price = price[0]
            await cursor.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,))
            wallet = await cursor.fetchone()
            wallet = wallet[0]
            if wallet < price * amount and not can_go_negative:
                return "You don't have enough money"
            await self.transfer_money(user_id, CENTRAL_BANK_ID if item != "lotto ticket" else LOTTO_BANK_ID,
                                      price * amount, 0, f"item purchase ({item})")
            await cursor.execute("INSERT INTO user_items VALUES (?, ?, ?)", (user_id, item_id, amount))
            await self.bot.db.commit()
        return f"You bought {amount} {item} for {price * amount}{CURRENCY_EMOTE}"

    # lotto related functions
    async def create_new_lotto(self, last_lotto_winner: str):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE lottery SET winner_id = ? WHERE lottery_id = (SELECT max(lottery_id) FROM lottery)",
                                 (last_lotto_winner,))
            await cursor.execute("INSERT INTO lottery VALUES ((SELECT max(lottery_id) FROM lottery) + 1, ?, ?)",
                                 (datetime.utcnow().strftime("%Y-%m-%d"), 0))

            await self.bot.db.commit()

    async def bot_buy_lotto_ticket(self):  # bot buys 100 lotto ticket every 24 hours to increase the jackpot
        await self.buy_item(self.bot.id, "lotto ticket", 100, True)

    async def generate_lotto_numbers(self) -> list:
        seeded_random = random.Random(random.randint(-sys.maxsize, sys.maxsize))
        return seeded_random.sample(range(1, 49), 6)

    async def get_lotto_jackpot(self) -> int:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT bank FROM users WHERE user_id = ?", (LOTTO_BANK_ID,))
            lotto_bank = await cursor.fetchone()
            lotto_bank = lotto_bank[0]
        return int(lotto_bank*(0.50 + await self.get_days_without_winner()/100))

    async def get_days_without_winner(self) -> int:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT * FROM lottery")
            _all = await cursor.fetchall()
            days_without_winner = 0
            for _id, time, winner_id in _all:
                if winner_id is None or winner_id == 0:
                    days_without_winner += 1
                else:
                    days_without_winner = 0
        return days_without_winner

    async def get_and_remove_all_lotto_tickets(self) -> list:
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT * FROM user_items WHERE item_id = ?", (await self.get_item_id("lotto ticket"),))
            tickets = await cursor.fetchall()
            await cursor.execute("DELETE FROM user_items WHERE item_id = ?", (await self.get_item_id("lotto ticket"),))
            await self.bot.db.commit()
        return list(tickets)

    async def get_tickets_per_user(self, all_tickets: list) -> dict:
        tickets_per_user = {}
        for user_id, item_id, amount in all_tickets:
            if user_id in tickets_per_user:
                tickets_per_user[user_id] += amount
            else:
                tickets_per_user[user_id] = amount
        return tickets_per_user

    async def evaluate_lotto_ticket(self, ticket: list, winning_numbers: list) -> int:
        return sum(number in winning_numbers for number in ticket)

    async def get_lotto_winners(self, tickets_per_user: dict, winning_numbers: list) -> list:
        winners = []
        for user_id, amount in tickets_per_user.items():
            for _ in range(amount):
                ticket = await self.generate_lotto_numbers()
                if (correct := await self.evaluate_lotto_ticket(ticket, winning_numbers)) >= 3:
                    winners.append((user_id, correct))
        return winners

    async def send_dm_to_winner(self, winner_id: int, amount: int, msg: str):
        try:
            user = await self.bot.fetch_user(winner_id)
            if user.dm_channel is None:
                await user.create_dm()
            await user.send(f"You won {amount}{CURRENCY_EMOTE} {msg}!")
        except Exception as e:
            logger.error(f"Could not send DM to {winner_id} because of {e}")

    async def pay_prizes(self, winners: list, amount: int) -> list:
        jackpot = await self.get_lotto_jackpot()
        percetages = {3: 0.20, 4: 0.30, 5: 0.50}
        winners_with_prize = []
        total_people_with_correct = {}
        for user_id, correct in winners:
            total_people_with_correct[correct] = total_people_with_correct.get(correct, 0) + 1
        for user_id, correct in winners:
            if correct == 6:
                prize = jackpot // total_people_with_correct[correct]
                winners_with_prize.append((user_id, prize, correct))
                await self.move_money_to_bank(LOTTO_BANK_ID, -prize)  # withdraw money from lotto bank to pay jackpot
                await self.transfer_money(LOTTO_BANK_ID, user_id, prize, 0, "lottery jackpot")
                await self.send_dm_to_winner(user_id, prize, "in the lotto. You won the jackpot!")
            else:
                prize = int(amount * percetages[correct] // total_people_with_correct[correct])
                winners_with_prize.append((user_id, prize, correct))
                await self.transfer_money(LOTTO_BANK_ID, user_id, prize, 0, "lottery prize")
                await self.send_dm_to_winner(user_id, prize, f"in the lotto. You had {correct} numbers!")

        winners_with_prize = sorted(winners_with_prize, key=lambda x: x[1], reverse=True)
        return winners_with_prize

# #############################################TASKS#########################################################
    @tasks.loop(time=(datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
                      + timedelta(seconds=1)).time(), count=1)
    async def daily_loop_starter(self):
        await self.bot.wait_until_ready()
        self.daily_loop.start()

    @tasks.loop(hours=24)
    async def daily_loop(self):
        await self.daily_reset()
        await self.lotto_reset()

    # daily reset function
    async def daily_reset(self):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("UPDATE users SET daily_streak = 0 WHERE daily_today = 0")
            await cursor.execute("UPDATE users SET daily_today = 0")
            await self.bot.db.commit()
            await self.bot.log_to_channel("Daily reset.")

    async def lotto_reset(self):
        await self.bot_buy_lotto_ticket()
        lotto_wallet, lotto_bank = await self.get_balance(LOTTO_BANK_ID)
        await self.move_money_to_bank(LOTTO_BANK_ID, int(lotto_wallet * 0.31))  # 31% of the lotto wallet is profit

        amount_to_be_paid = lotto_wallet - int(lotto_wallet * 0.31)
        all_tickets = await self.get_and_remove_all_lotto_tickets()
        tickets_per_user = await self.get_tickets_per_user(all_tickets)
        winning_numbers = await self.generate_lotto_numbers()
        winners = await self.get_lotto_winners(tickets_per_user, winning_numbers)

        prizes: list = await self.pay_prizes(winners, amount_to_be_paid)
        embed = discord.Embed(title="Lotto results", description=f"Winning numbers: {winning_numbers}", color=0x00ff00,
                              timestamp=datetime.utcnow())
        winner = ""
        for user_id, prize, correct_numbers in prizes:
            msg = ""
            if correct_numbers == 6:
                winner += f"{user_id} "
                msg = "Jackpot winner!"
            embed.add_field(name=self.bot.get_user(user_id),
                            value=f"{prize}{CURRENCY_EMOTE} ({correct_numbers} correct numbers) {msg}", inline=False)
        await self.bot.log_to_channel("", embed=embed)
        await self.create_new_lotto(winner)

    @commands.command(hidden=True, name="testlotto")
    @commands.is_owner()
    async def test_lotto(self, ctx):
        await self.lotto_reset()

    @commands.command(hidden=True, name="testdaily")
    @commands.is_owner()
    async def test_daily(self, ctx):
        await self.daily_reset()

    @commands.command(hidden=True, name="transfer_central_to_lotto")
    @commands.is_owner()
    async def transfer_central_to_lotto(self, ctx, amount: int):
        await self.transfer_money(CENTRAL_BANK_ID, LOTTO_BANK_ID, amount, 0, "starting lotto money")
        await self.move_money_to_bank(LOTTO_BANK_ID, amount)
        await self.bot.log_to_channel(f"Transferred {amount}{CURRENCY_EMOTE} from central bank to lotto bank.")

# #############################################TASKS#########################################################

    @commands.hybrid_command(name="balance", aliases=["bal"])
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

    @commands.hybrid_command(name="deposit", aliases=["dep"])
    @app_commands.describe(amount="normal number or 'all'")
    @commands.cooldown(10, 86400, commands.BucketType.user)
    async def deposit(self, ctx: commands.Context, amount: str):
        """Deposit money into your bank (10 uses per day)"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if not (amount := self.parse_amount(amount, wallet)):
            return await ctx.reply("Amount must be a number or 'all'!")
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > wallet:
            return await ctx.reply("You don't have that much money!")
        await self.move_money_to_bank(ctx.author.id, amount)
        await ctx.reply(f"Deposited {amount}{CURRENCY_EMOTE} into your bank!")

    @commands.hybrid_command(name="withdraw", aliases=["with"])
    @app_commands.describe(amount="normal number or 'all'")
    @commands.cooldown(10, 86400, commands.BucketType.user)
    async def withdraw(self, ctx: commands.Context, amount: str):
        """Withdraw money from your bank (10 uses per day)"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if amount == "all":
            amount = bank
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
    @app_commands.describe(member="user to send money to", amount="normal number or 'all'")
    async def send(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Send money to another user (there is a 5% tax)"""
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

        taxed_amount = await self.transfer_money(ctx.author.id, member.id, amount, TAX, "user to user transfer")
        embed = discord.Embed(title="Money transfer", color=discord.Color.gold(),
                              description=f"Sent {taxed_amount}{CURRENCY_EMOTE} to {member.mention} "
                                          f"({amount - taxed_amount}{CURRENCY_EMOTE} lost to tax)")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context):
        """View the leaderboard of top 10 richest users"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT user_id, wallet + bank AS balance FROM users ORDER BY balance DESC LIMIT 13")
            rows = await cursor.fetchall()
            rows = [(user_id, balance) for user_id, balance in rows
                    if user_id not in (CENTRAL_BANK_ID, LOTTO_BANK_ID, self.bot.id)]
        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        for i, row in enumerate(rows):
            user_id, balance = row
            user = self.bot.get_user(user_id)
            if user is None:
                user = await self.bot.fetch_user(user_id)
            embed.add_field(name=f"{i + 1}. {user}", value=f"{balance}{CURRENCY_EMOTE}", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="daily")
    async def daily(self, ctx: commands.Context):
        """Get your daily reward"""
        await self.ensure_user_exists(ctx.author.id)
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT daily_streak, daily_today FROM users WHERE user_id = ?", (ctx.author.id,))
            row = await cursor.fetchone()
            daily_streak, daily_today = row
            if bool(daily_today):
                timestamp = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(seconds=1)
                embed = discord.Embed(title="You already claimed your daily reward today!",
                                      description="Come back at", timestamp=timestamp, color=discord.Color.red())
                embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
                return await ctx.reply(embed=embed)

            await cursor.execute("UPDATE users SET daily_today = 1, daily_streak = daily_streak + 1"
                                 " WHERE user_id = ?", (ctx.author.id,))
            await self.bot.db.commit()

        amount = int((DAILY_REWARD + daily_streak * DAILY_STREAK_BONUS)*(1 + daily_streak/50))
        await self.transfer_money(CENTRAL_BANK_ID, ctx.author.id, amount, 0, "daily reward")
        embed = discord.Embed(title="Daily reward", color=discord.Color.gold(),
                              description=f"You got {amount}!"
                                          f"\nYour daily streak is now {daily_streak + 1}!")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="beg")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def beg(self, ctx: commands.Context):
        """Beg for money"""
        wallet, bank = await self.get_balance(ctx.author.id)
        if wallet + bank >= 100000:
            msg = "You already have enough money!"
        else:
            money = random.randint(10, 100)
            await self.transfer_money(CENTRAL_BANK_ID, ctx.author.id, money, 0, "begging")
            if money < 20:
                msg = f"Someone gave you {money}{CURRENCY_EMOTE}!"
            elif money < 60:
                msg = f"Someone tripped and {money}{CURRENCY_EMOTE} fell out of their pocket into your hand!"
            else:
                msg = f"{money}{CURRENCY_EMOTE} fell out of the sky and landed in your pocket!"
        embed = discord.Embed(title="Begging", color=discord.Color.green(), description=msg)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="crime")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def crime(self, ctx: commands.Context):
        """Commit a crime"""
        if random.randint(1, 100) <= 20:
            money = random.randint(100, 1000)
            await self.transfer_money(ctx.author.id, CENTRAL_BANK_ID, money, 0, "failed crime")
            msg = f"You got caught and had to pay {money}{CURRENCY_EMOTE} to the police!"
        else:
            money = random.randint(50, 500)
            await self.transfer_money(CENTRAL_BANK_ID, ctx.author.id, money, 0, "successful crime")
            # custom messages based on how much money you get
            if money < 150:
                msg = f"You stole {money}{CURRENCY_EMOTE}!"
            elif money < 350:
                msg = f"You stole {money}{CURRENCY_EMOTE} from a rich person!"
            else:
                msg = f"You stole {money}{CURRENCY_EMOTE} from a bank!"
        embed = discord.Embed(title="Crime", color=discord.Color.red() if "caught" in msg else discord.Color.green(),
                              description=msg)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="rob")
    @app_commands.describe(member="user to rob")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, member: discord.Member):
        """Rob a user"""
        if member.bot:
            return await ctx.reply("You can't rob bots!")
        if member.id == ctx.author.id:
            return await ctx.reply("You can't rob yourself!")
        victim_wallet, victim_bank = await self.get_balance(member.id)
        if victim_wallet < 100:
            return await ctx.reply("This user doesn't have enough money to rob!")

        if random.randint(1, 100) <= 70:
            money = random.randint(10, 100)
            await self.transfer_money(ctx.author.id, member.id, money, 0, "failed robbery")
            msg = f"You got caught and had to pay {money}{CURRENCY_EMOTE} to {member.mention}!"
        else:
            my_list = []
            for i in range(10):
                my_list.extend((i+1)*10 for _ in range(10 - i))
            money = random.choice(my_list)
            money = int(victim_wallet * money / 100)
            await self.transfer_money(member.id, ctx.author.id, money, 0, "successful robbery")
            msg = f"You stole {money}{CURRENCY_EMOTE} from {member.mention}!"

        embed = discord.Embed(title="Robbery", color=discord.Color.red() if "caught" in msg else discord.Color.green(),
                              description=msg)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    # todo heist command with multiple people and a chance of failure (discord view)

    @commands.hybrid_command(name="gamble")
    @app_commands.describe(guess="higher or lower", amount="normal number or 'all'")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gamble(self, ctx: commands.Context, guess: Literal[1, 2], amount: str):
        """Gamble your money! Guess if you will roll more or less than computer on a 6-sided dice"""
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
        if guess not in ("higher", "lower"):
            return await ctx.reply("Guess must be 'higher' or 'lower'!")

        dice = random.randint(1, 6)
        starbot_guess = random.randint(1, 6)
        if (dice < starbot_guess and guess == "lower") or (dice > starbot_guess and guess == "higher"):
            await self.transfer_money(self.bot.id, ctx.author.id, amount, 0, "gambling")
            embed = discord.Embed(title=f"You won {amount}{CURRENCY_EMOTE}!", color=discord.Color.green(),
                                  description=f"You rolled {dice}. StarBot rolled {starbot_guess}.\n"
                                              f"And you guessed correctly `{guess}`")
        elif dice != starbot_guess:
            await self.transfer_money(ctx.author.id, self.bot.id, amount, 0, "gambling")
            embed = discord.Embed(title=f"You lost {amount}{CURRENCY_EMOTE}!", color=discord.Color.red(),
                                  description=f"You rolled {dice}. StarBot rolled {starbot_guess}.\n"
                                              f"And you guessed incorrectly `{guess}`")
        else:
            embed = discord.Embed(title="It's a tie!", color=discord.Color.gold(),
                                  description=f"You rolled {guess}. StarBot rolled {starbot_guess}.\n"
                                              f"You both rolled the same number so you don't lose or gain anything.")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    # TODO inventory commands

    @commands.hybrid_command(name="shop")
    async def shop(self, ctx: commands.Context):
        """View the shop"""  # TODO: scrollable embed
        items = await self.get_all_items()
        embed = discord.Embed(title="Shop", color=discord.Color.blue())
        for _id, name, price, sell, description in items:
            embed.add_field(name=f"**{name}** ({price}{CURRENCY_EMOTE})", value=description, inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="buy")
    @app_commands.describe(item="item to buy", amount="number of items to buy, default is 1")
    async def buy(self, ctx: commands.Context, amount: Optional[int], *,
                  item: ITEMS):
        """Buy an item from the shop"""
        if amount is None:
            amount = 1
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        msg = await self.buy_item(ctx.author.id, item, amount)
        embed = discord.Embed(title="Shop", color=discord.Color.green() if "bought" in msg else discord.Color.red(),
                              description=msg)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    # TODO: sell command

    @commands.hybrid_command(name="work")
    @commands.cooldown(1, 60 * 30, commands.BucketType.user)  # 30 minutes
    async def work(self, ctx: commands.Context):
        """Work to earn money"""
        equation, answer = my_math.generate_equation()
        embed = discord.Embed(title="Working as Math Teacher", color=discord.Color.yellow(),
                              description=f"Quick! You got 10 seconds answer this equation to get paid:\n{equation}")
        lowest_money, highest_money = MONEY_FOR_WORK
        view = my_math.MathView(embed, equation, answer, self.bot, lowest_money, highest_money, ctx.author.id)
        msg = await ctx.reply(embed=embed, view=view)
        view.message = msg

    @commands.hybrid_group(name="lotto", invoke_without_command=False, with_app_command=True)
    async def lotto(self, ctx: commands.Context):
        """Lotto commands"""
        pass

    @lotto.command(name="buy")
    @app_commands.describe(amount="number of tickets to buy, default is 1")
    async def lotto_buy(self, ctx: commands.Context, amount: Optional[int]):
        """Buy lotto tickets (same as /buy lotto ticket)"""
        if amount is None:
            amount = 1
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        msg = await self.buy_item(ctx.author.id, "lotto ticket", amount)
        embed = discord.Embed(title="Shop", color=discord.Color.green() if "bought" in msg else discord.Color.red(),
                              description=msg)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    @lotto.command(name="jackpot")
    async def lotto_jackpot(self, ctx: commands.Context):
        """View the lotto jackpot"""
        jackpot = await self.get_lotto_jackpot()
        embed = discord.Embed(title="Current Lotto Jackpot", color=discord.Color.blue(),
                              description=f"{jackpot:,}{CURRENCY_EMOTE}".replace(",", " "))
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)

    # TODO: lotto winners command


async def setup(bot):
    await bot.add_cog(Currency(bot))
