from typing import Union
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from bot import MY_GUILD_ID

CURRENCY_EMOTE = "💰"  # emoji for currency TODO change to custom emoji
TAX = 0.05  # tax for sending money to another user (5%)
# TODO add cooldown for commands


class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_account(self, user_id: int):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, 0, 0))
            await self.bot.db.commit()

    def get_balance(self, user_id: int):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT (wallet, bank) FROM users WHERE user_id = ?", (user_id,))
            wallet, bank = await cursor.fetchone()
        return wallet, bank if wallet and bank else (0, 0)

    def add_money(self, user_id: int, amount: int, to_bank: bool = False):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            if to_bank:
                await cursor.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, user_id))
            else:
                await cursor.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ?", (amount, user_id))
            await self.bot.db.commit()

    def remove_money(self, user_id: int, amount: int, to_bank: bool = False):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            if to_bank:
                await cursor.execute("UPDATE users SET bank = bank - ? WHERE user_id = ?", (amount, user_id))
            else:
                await cursor.execute("UPDATE users SET wallet = wallet - ? WHERE user_id = ?", (amount, user_id))
            await self.bot.db.commit()

    def generate_transaction_id(self):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT id FROM transactions WHERE id = max(SELECT id FROM transactions)")
            transaction_id = await cursor.fetchone()
            transaction_id = transaction_id[0] if transaction_id else 0
        return transaction_id + 1

    def log_transaction(self, sender_id, receiver_id, amount, tax):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                                 (self.generate_transaction_id(), discord.utils.utcnow(),
                                  sender_id, receiver_id, amount, tax))
            await self.bot.db.commit()

    @commands.hybrid_command(name="balance", aliases=["bal"])
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(user="user to check balance of, leave blank to check your own balance")
    async def balance(self, ctx: commands.Context, member: Union[discord.Member, discord.User] = None):
        """Shows your or someone's balance"""
        if member is None:
            member = ctx.author
        wallet, bank = self.get_balance(member.id)
        embed = discord.Embed(title=f"{member.name}'s balance", color=discord.Color.green())
        embed.add_field(name="Wallet", value=wallet+CURRENCY_EMOTE)
        embed.add_field(name="Bank", value=bank+CURRENCY_EMOTE)
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="beg")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def beg(self, ctx: commands.Context):
        """Beg for money"""
        wallet, bank = self.get_balance(ctx.author.id)
        if wallet + bank >= 10000:
            msg = "You already have enough money!"
        else:
            money = random.randint(1, 1000)
            self.add_money(ctx.author.id, money)
            if money < 100:
                msg = f"Someone gave you {money} coins!"
            elif money < 500:
                msg = f"Someone gave you {money} coins! That's a lot!"
            else:
                msg = f"Someone gave you {money} coins! That's a lot! You're rich now!"
        await ctx.send(msg)

    @commands.hybrid_command(name="deposit")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(amount="amount of money to deposit")
    async def deposit(self, ctx: commands.Context, amount: int):
        """Deposit money into your bank"""
        wallet, bank = self.get_balance(ctx.author.id)
        if amount > wallet:
            await ctx.send("You don't have that much money!")
        else:
            self.remove_money(ctx.author.id, amount)
            self.add_money(ctx.author.id, amount, to_bank=True)
            await ctx.send(f"You deposited {amount} coins into your bank!")

    @commands.hybrid_command(name="withdraw")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(amount="amount of money to withdraw")
    async def withdraw(self, ctx: commands.Context, amount: int):
        """Withdraw money from your bank"""
        wallet, bank = self.get_balance(ctx.author.id)
        if amount > bank:
            await ctx.send("You don't have that much money in your bank!")
        else:
            self.remove_money(ctx.author.id, amount, to_bank=True)
            self.add_money(ctx.author.id, amount)
            await ctx.send(f"Withdrew {amount} coins from your bank!")

    @commands.hybrid_command(name="send")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    @app_commands.describe(member="user to send money to", amount="amount of money to send")
    async def send(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Send money to another user"""
        wallet, bank = self.get_balance(ctx.author.id)
        if amount > wallet:
            await ctx.send("You don't have that much money!")
        else:
            self.remove_money(ctx.author.id, amount)
            taxed_amount = int(amount * (1 - TAX))
            self.add_money(member.id, taxed_amount)
            # write how much money was lost to tax
            await ctx.send(f"You sent {taxed_amount} ({TAX * 100}% tax) coins to {member.mention}!")
        # TODO log transaction in database


async def setup(bot):
    await bot.add_cog(Currency(bot))
