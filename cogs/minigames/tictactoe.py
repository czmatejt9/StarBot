import random
import discord
from .utilities import coinflip


class Tile(discord.ui.Button['Board']):
    def __init__(self, first_player: discord.Member, second_player: discord.Member, x: int, y: int):
        super().__init__(label=" ", style=discord.ButtonStyle.grey, row=y)
        self.p1 = first_player
        self.p2 = second_player
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.defer()
        await self.view.process_move(interaction, self)


class Board(discord.ui.View):
    def __init__(self, first_player: discord.Member, second_player: discord.Member):
        super().__init__(timeout=900.0)
        self.p1 = first_player
        self.p2 = second_player
        self.p1_symbol = "X"
        self.p2_symbol = "O"
        self.message: discord.Message = None
        if coinflip():
            self.p1, self.p2 = self.p2, self.p1
        self.p1_turn = True

        self.board_state = ([""]*3,
                            [""]*3,
                            [""]*3)
        for i in range(3):
            for j in range(3):
                self.add_item(Tile(self.p1, self.p2, j, i))

    def check_win(self):
        for i in range(3):
            # rows
            if self.board_state[i][0] == self.board_state[i][1] == self.board_state[i][2] and self.board_state[i][0]:
                return self.board_state[i][0]
            # columns
            if self.board_state[0][i] == self.board_state[1][i] == self.board_state[2][i] and self.board_state[0][i]:
                return self.board_state[0][i]
        # diagonals
        if self.board_state[0][0] == self.board_state[1][1] == self.board_state[2][2] and self.board_state[0][0]:
            return self.board_state[0][0]
        if self.board_state[2][0] == self.board_state[1][1] == self.board_state[0][2] and self.board_state[0][2]:
            return self.board_state[0][2]
        # no win
        return False

    def check_draw(self):
        return all(all(each) for each in self.board_state)

    async def process_move(self, interaction: discord.Interaction, tile: Tile):
        if interaction.user.id != (self.p1.id if self.p1_turn else self.p2.id):
            await interaction.followup.send("It isn't your turn", ephemeral=True)
            return
        if self.board_state[tile.y][tile.x]:
            await interaction.followup.send("This tile is already taken", ephemeral=True)
            return

        symbol = self.p1_symbol if self.p1_turn else self.p2_symbol
        self.board_state[tile.y][tile.x] = symbol
        tile.style = discord.ButtonStyle.red if self.p1_turn else discord.ButtonStyle.blurple
        tile.label = symbol
        self.p1_turn = not self.p1_turn
        if not self.check_win() and not self.check_draw():
            await interaction.followup.edit_message(
                content=f"**TicTacToe**\n{self.p1.mention} {self.p1_symbol} vs {self.p2.mention} {self.p2_symbol}\n\n"
                        f"{self.p1.name if self.p1_turn else self.p2.name}'s turn!", view=self, message_id=self.message.id)
            return
        # someone wins or a draw
        a = self.check_win()
        if self.check_win():
            winner = self.p1 if self.p1_symbol == a else self.p2
            msg = f"{winner.mention} wins!"
        else:  # draw
            msg = "It's a tie!"

        for child in self.children:
            child.disabled = True
        await interaction.followup.edit_message(
            content=f"**TicTacToe**\n{self.p1.mention} {self.p1_symbol} vs {self.p2.mention} {self.p2_symbol}\n\n"
                    f"Game ended. {msg}", view=self, message_id=self.message.id)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.p2.id, self.p1.id]:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(content=f"**TicTacToe**\n{self.p1.mention} {self.p1_symbol} vs {self.p2.mention}"
                                        f" {self.p2_symbol}\n\n**Game timed out...**", view=self,
                                allowed_mentions=discord.AllowedMentions.none())
        self.stop()


class Prompt(discord.ui.View):
    def __init__(self, author, member):
        super().__init__(timeout=300.0)
        self.author: discord.Member = author
        self.member: discord.Member = member
        self.message: discord.Message = None

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.style = discord.ButtonStyle.green
        for x in self.children:
            x.disabled = True
        board = Board(self.author, self.member)
        await interaction.response.edit_message(content=f"{self.member.name} has accepted the challenge!"
                                                        f" Creating board...", view=self)
        self.stop()
        msg = await interaction.followup.send(f"**TicTacToe**\n{board.p1.mention} {board.p1_symbol} vs {board.p2.mention}"
                                              f" {board.p2_symbol}\n\n{board.p1.name}'s turn!", view=board)
        board.message = msg

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="❎")
    async def decline(self, interaction: discord.Interaction, button: discord.Button):
        button.style = discord.ButtonStyle.red
        for x in self.children:
            x.disabled = True
        await interaction.response.edit_message(content=f"{self.member.name} has declined the challenge!", view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(content="Challenge timed out...", view=self)
        self.stop()
