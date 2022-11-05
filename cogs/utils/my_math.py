import random
from datetime import datetime

from bot import StarCityBot
import discord.ui

CURRENCY_EMOTE = "<:SMURFPENIZE:1038485999795318844>"


def generate_equation(lowest: int = 1, highest: int = 100):
    operator = random.choice(["+", "-", "*", "/"])
    if operator == "+":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a+b > highest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} + {b} = ?", a+b
    elif operator == "-":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a-b < lowest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} - {b} = ?", a-b
    elif operator == "*":
        a, b = random.randint(lowest, highest // 10), random.randint(lowest, highest // 10)
        while a*b > highest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} * {b} = ?", a*b
    elif operator == "/":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a//b != a/b:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} / {b} = ?", a//b


class MathButton(discord.ui.Button["MathView"]):
    def __init__(self, *, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        await self.view.process_answer(interaction, self)


class MathView(discord.ui.View):
    def __init__(self, embed: discord.Embed, equation: str, answer: int, bot: StarCityBot,
                 lowest_money: int, highest_money: int, user_id: int):
        super().__init__(timeout=11.0)
        self.user_id = user_id
        self.embed = embed
        self.equation, self.answer = equation, answer
        self.bot = bot
        self.lowest_money, self.highest_money = lowest_money, highest_money
        self.start_time = datetime.utcnow()
        self.message: discord.Message = None

        self.wrong_answers = [random.randint(1, 100) for _ in range(4)]
        while self.answer in self.wrong_answers:
            self.wrong_answers = [random.randint(1, 100) for _ in range(4)]
        self.wrong_answers.append(self.answer)
        random.shuffle(self.wrong_answers)
        for each in self.wrong_answers:
            self.add_item(MathButton(label=str(each), style=discord.ButtonStyle.blurple))

    async def get_money_for_work(self):
        end_time = datetime.utcnow()
        return int(self.highest_money
                   - (self.highest_money - self.lowest_money) * (end_time - self.start_time).total_seconds() / 10)

    async def process_answer(self, interaction: discord.Interaction, button: MathButton):
        correct = button.label == str(self.answer)
        if correct:
            money = await self.get_money_for_work()
            self.embed.title = f"Great work! You got {money}{CURRENCY_EMOTE}."
            self.embed.description = "You answered correctly!"
        else:
            money = self.lowest_money // 2
            self.embed.title = f"Terrible work! At least you got {money}{CURRENCY_EMOTE}."
            self.embed.description = f"The answer was {self.answer}"

        for item in self.children:
            item.disabled = True
            item.style = discord.ButtonStyle.grey
        button.style = discord.ButtonStyle.green if correct else discord.ButtonStyle.red

        await interaction.response.edit_message(embed=self.embed, view=self)
        await self.bot.get_cog("Currency").transfer_money(1, self.user_id, money, 0, "WORK")
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the author of this message!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        money = self.lowest_money // 2

        for item in self.children:
            item.disabled = True
            item.style = discord.ButtonStyle.grey
        self.embed.title = f"Terrible work! At least you got {money}{CURRENCY_EMOTE}."
        self.embed.description = f"You took too long to answer! The answer was {self.answer}"

        await self.message.edit(embed=self.embed, view=self)
        await self.bot.get_cog("Currency").transfer_money(1, self.user_id, money, 0, "WORK")
        self.stop()
