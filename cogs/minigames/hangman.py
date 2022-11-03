import random
import discord
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID, HOME_PATH

with open(f"{HOME_PATH}/assets/words.txt", "r") as f:
    words = f.read().split("\n")
words = [word.lower() for word in words if "z" not in word and len(word) > 3]
letters = "abcdefghijklmnopqrstuvwxy"


class LetterButton(discord.ui.Button['Hangman']):
    def __init__(self, letter: str):
        super().__init__(label=letter.upper(), style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await self.view.update(self.label, interaction)


class Hangman(discord.ui.View):
    def __init__(self, author: discord.Member):
        self.word = random.choice(words)
        self.display_word = ["_" for _ in self.word]
        self.guessed_letters = []
        self.lives = 7
        super().__init__(timeout=300.0)
        for letter in letters:
            self.add_item(LetterButton(letter))
        self.message = None
        self.embed = None

    async def update(self, letter: str, interaction: discord.Interaction) -> None:
        self.guessed_letters.append(letter)
        if letter in self.word:
            for i, char in enumerate(self.word):
                if char == letter.lower():
                    self.display_word[i] = letter
            self.embed.set_footer(text=f"You correctly guessed letter {letter}")
        else:
            self.lives -= 1
            self.embed.set_footer(text=f"Letter {letter} is not in the word")

        stop = False
        if self.display_word == list(self.word):
            self.embed.set_footer(text="You WON!")
            for child in self.children:
                child.disabled = True
            stop = True
        if self.lives == 0:
            self.embed.set_footer(text=f"You LOST! The word was {self.word}")
            for child in self.children:
                child.disabled = True
            stop = True

        self.embed.description = "Word: " + " ".join(self.display_word) + f"\nLives left: {self.lives}"
        await interaction.response.edit_message(embed=self.embed, view=self)
        if stop:
            self.stop()

    async def on_timeout(self) -> None:
        self.embed.description = " ".join(self.display_word)
        self.embed.set_footer(text="You ran out of time!")
        for child in self.children:
            child.disabled = True
        await self.message.edit(embed=self.embed, view=self)
        self.stop()
