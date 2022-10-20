from typing import Union
import discord
from .utilities import coinflip


class Gobblet:
    emojis = {
        "blue": {1: "<:blue_gobblet1:1029838287432589312>", 2: "<:blue_gobblet2:1029838265102123028>",
                 3: "<:blue_gobblet3:1029838267111194644>", 0: None},
        "red": {1: "<:red_gobblet1:1029836615121633310>", 2: "<:red_gobblet2:1029834838133452827>",
                3: "<:red_gobblet3:1029834301510013038>", 0: None},
        "": {0: None}
    }

    def __init__(self, strength: int, color: str):
        self.strength = strength
        self.color = color
        self.emoji = self.emojis[color][strength]


class Player:
    def __init__(self, member: discord.Member, color: str, first: bool):
        self.p = member
        self.color = color
        self.pieces: list[Gobblet] = []
        for i in range(3):
            self.pieces.append(Gobblet(i + 1, color))
            self.pieces.append(Gobblet(i + 1, color))
        self.is_turn = first
        self.action = None
        self.selected_piece: Gobblet = None
        self.interaction: discord.Interaction = None
        self.embed: discord.Embed = None
        self.opponent: "Player" = None
        self.view: discord.ui.View = None
        self.board: Board = None

    def is_ready(self):
        return bool(self.interaction)

    def count_remaining(self):
        a = {1: 0, 2: 0, 3: 0}
        for each in self.pieces:
            a[each.strength] += 1
        return a.values()

    def has_pieces_left(self):
        return bool(len(self.pieces))

    def create_embed(self):
        self.embed = discord.Embed(color=(0xFF0000 if self.color == "red" else 0x0000FF), title="Gobblet Gobblers UI",
                                   description=f"{self.p.mention} vs {self.opponent.p.mention}\n")
        self.embed.set_author(name=self.p.display_name, icon_url=self.p.display_avatar)
        self.update_embed()

    def update_embed(self, end=False, winner=False):
        a, b, c = self.count_remaining()
        d, e, f = self.opponent.count_remaining()
        self.embed.clear_fields()
        self.embed.title = f"Gobblet Gobblers UI\t " \
                           f"selected piece: {self.selected_piece.emoji if self.selected_piece else 'None'}"
        self.embed.add_field(name="Your pieces left", value=f"{a}x{Gobblet.emojis[self.color][1]}, "
                                                            f"{b}x{Gobblet.emojis[self.color][2]}, "
                                                            f"{c}x{Gobblet.emojis[self.color][3]}",
                             inline=True)
        self.embed.add_field(name="Current turn", value="Yours!" if self.is_turn else "Opponent's"
                             if self.opponent.is_ready() else "Waiting...")
        self.embed.add_field(name="Opponent's pieces left", value=f"{d}x{Gobblet.emojis[self.opponent.color][1]}, "
                                                                  f"{e}x{Gobblet.emojis[self.opponent.color][2]}, "
                                                                  f"{f}x{Gobblet.emojis[self.opponent.color][3]}",
                             inline=True)

        text = (("Please select action to play" if self.action is None else "Please click on board to play selected "
                                                                            "piece" if self.selected_piece else
                                                                            "Please select new piece to place on board"
                 if "Place" in self.action else "Please select a piece from the board to move it ("
                                                "warning: once you select piece you **must** move it to another place. "
                                                "If you select piece that cannot be moved, you lose)")
                if self.is_turn else "Please wait for your opponent to finish their turn") \
            if self.opponent.is_ready() else "Please wait for your opponent to ready up"
        if end:
            text = "Game ended. You win!" if winner else "Game ended. You lose :("
        self.embed.set_footer(
            text=f"Selected action: {self.action}\t Selected piece's strength: "
                 f"{self.selected_piece.strength if self.selected_piece else 'None'}\n{text}")


class Tile(discord.ui.Button["Board"]):
    def __init__(self, x, y):
        super().__init__(label=" ", style=discord.ButtonStyle.grey, row=y, custom_id=f"Tile {x} {y}")
        self.x = x
        self.y = y
        self.stack = [Gobblet(0, "")]

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view.process_board_click(interaction, self)

    def add_piece(self, gobblet: Gobblet):
        self.stack.append(gobblet)
        self.emoji = self.stack[-1].emoji

    def remove_piece(self) -> Gobblet:
        a = self.stack.pop()
        self.emoji = self.stack[-1].emoji
        return a


class Board(discord.ui.View):
    def __init__(self, author: discord.Member, member: discord.Member):
        super().__init__(timeout=900.0)
        if coinflip():
            author, member = member, author
        self.p1 = Player(author, "red", False)
        self.p2 = Player(member, "blue", False)
        self.p1.board = self
        self.p2.board = self
        self.players: tuple[Player, Player] = (self.p1, self.p2)
        self.turn_index = True
        self.started = False
        self.message: discord.Message = None
        self.board_state = ([["", 0]] * 3,
                            [["", 0]] * 3,
                            [["", 0]] * 3)
        for i in range(3):
            for j in range(3):
                self.add_item(Tile(j, i))
        self.fetch_board_state()

    def fetch_board_state(self):
        values = []
        for child in self.children:
            if "Tile" in child.custom_id:
                a, b = child.stack[-1].color, child.stack[-1].strength
                values.append([a, b])
        board_state = ([values[0], values[1], values[2]],
                       [values[3], values[4], values[5]],
                       [values[6], values[7], values[8]])
        self.board_state = board_state

    async def update_board(self):
        await self.message.edit(content=f"**Gobblet gobblers**\n{self.p1.p.mention}({self.p1.color}) vs "
                                        f"{self.p2.p.mention}({self.p2.color})\n"
                                        f"{self.p1.p.mention}: ✅\n{self.p2.p.mention}: ✅\n"
                                        f"{self.players[self.turn_index].p.display_name}'s turn!", view=self,
                                allowed_mentions=discord.AllowedMentions.none())

    def get_available_tiles(self, p: Player):
        tiles = []
        strength = p.selected_piece.strength
        for y, row in enumerate(self.board_state):
            tiles.extend((x, y) for x, tile in enumerate(row) if tile[1] < strength)
        return tiles

    def can_move_piece(self, color):
        return any(any(1 if color in each[0] else 0 for each in self.board_state[i]) for i in range(3))

    async def end_game(self, winner: Player, text: str):
        for child in self.children:
            child.disabled = True
        await self.message.edit(content=f"**Gobblet gobblers**\n{self.p1.p.mention}({self.p1.color}) vs "
                                        f"{self.p2.p.mention}({self.p2.color})\n"
                                        f"{self.p1.p.mention}: ✅\n{self.p2.p.mention}: ✅\n"
                                        f"Game ended. {winner.p.mention} wins! {text}", view=self,
                                allowed_mentions=discord.AllowedMentions.none())
        winner.selected_piece = None
        winner.action = None
        winner.opponent.selected_piece = None
        winner.opponent.selected_piece = None
        winner.update_embed(True, True)
        winner.opponent.update_embed(True, False)
        for child1, child2 in zip(winner.view.children, winner.opponent.view.children):
            child1.disabled = True
            child2.disabled = True
        await winner.interaction.edit_original_response(embed=winner.embed, view=winner.view)
        await winner.opponent.interaction.edit_original_response(embed=winner.opponent.embed, view=winner.opponent.view)
        self.stop()

    async def check_win(self):
        winners = ""
        for i in range(3):
            # rows
            if self.board_state[i][0][0] == self.board_state[i][1][0] == self.board_state[i][2][0] and self.board_state[i][0][0]:
                winners += self.board_state[i][0][0]
            # columns
            if self.board_state[0][i][0] == self.board_state[1][i][0] == self.board_state[2][i][0] and self.board_state[0][i][0]:
                winners += self.board_state[0][i][0]
        # diagonals
        if self.board_state[0][0][0] == self.board_state[1][1][0] == self.board_state[2][2][0] and self.board_state[0][0][0]:
            winners += self.board_state[0][0][0]
        if self.board_state[2][0][0] == self.board_state[1][1][0] == self.board_state[0][2][0] and self.board_state[0][2][0]:
            winners += self.board_state[0][2][0]

        if "red" in winners and "blue" in winners:
            await self.end_game(self.players[not self.turn_index], f"(Both players have 3 in a row but "
                                                                   f"{self.players[self.turn_index].p.mention} "
                                                                   f"made the last move thus loses)")
        elif "red" in winners:
            await self.end_game(self.p1, "")
        elif "blue" in winners:
            await self.end_game(self.p2, "")
        else:
            return True
        return False

    def get_player(self, player_id: int):
        if self.p1.p.id == player_id:
            return self.p1
        elif self.p2.p.id == player_id:
            return self.p2
        else:
            raise ValueError

    async def switch_turn(self):
        cp: Player = self.players[self.turn_index]
        cp.is_turn = False
        cp.selected_piece = None
        cp.action = None
        cp.update_embed()
        for child in cp.view.children:
            child.style = discord.ButtonStyle.grey
            child.disabled = True
        await cp.interaction.edit_original_response(embed=cp.embed, view=cp.view)

        self.turn_index = not self.turn_index
        cp: Player = self.players[self.turn_index]
        cp.is_turn = True
        cp.update_embed()
        for child in cp.view.children:
            if "piece" not in child.custom_id:
                child.disabled = False
        await cp.interaction.edit_original_response(embed=cp.embed, view=cp.view)

        await self.update_board()

    async def update_new_ui(self, player_id):  # TODO edit this, to reflect current state
        p = self.get_player(player_id)
        p.update_embed()
        if p.is_turn and "Move" not in p.action:
            for child in p.view.children:
                if "piece" not in child.custom_id:
                    child.disabled = False
        await p.interaction.edit_original_response(embed=p.embed, view=p.view)

    @discord.ui.button(label="Click to ready up!", row=4)
    async def ready(self, interaction: discord.Interaction, button: discord.Button):
        # creating user ui for the user who clicked it
        if interaction.user.id == self.p1.p.id:
            self.p1.opponent = self.p2
            self.p1.create_embed()
            view = PlayerUI(self.p1)
            await interaction.response.send_message(embed=self.p1.embed, view=view, ephemeral=True)
            self.p1.interaction = interaction
        else:
            self.p2.opponent = self.p1
            self.p2.create_embed()
            view = PlayerUI(self.p2)
            await interaction.response.send_message(embed=self.p2.embed, view=view, ephemeral=True)
            self.p2.interaction = interaction

        m1, m2 = self.p1.p.mention, self.p2.p.mention,
        r1, r2 = self.p1.is_ready(), self.p2.is_ready()
        if r1 and r2:
            button.label = "Click to resend the UI for playing"

        if self.started:  # make sure not to 'start' the game again if we're only resending the ui
            await self.update_new_ui(interaction.user.id)
        else:
            await interaction.followup.edit_message(
                content=f"**Gobblet gobblers**\n{m1} vs {m2}\n"
                        f"{m1}: {'✅' if r1 else 'not ready'}\n{m2}: {'✅' if r2 else 'not ready'}\n"
                        f"{'Starting...' if r1 and r2 else 'Waiting for players to ready up...'}",
                view=self, allowed_mentions=discord.AllowedMentions.none(), message_id=self.message.id)
        if r1 and r2 and not self.started:
            self.started = True
            self.p2.is_turn = True
            self.p1.is_turn = True
            await self.switch_turn()

    async def process_board_click(self, interaction: discord.Interaction, tile: Tile):
        p = self.get_player(interaction.user.id)
        if not p.is_turn:  # not players turn
            await interaction.followup.send("It isnt' your turn!", ephemeral=True)
        elif p.action is None:  # no selected action
            await interaction.followup.send("You must select an action first!", ephemeral=True)
        elif p.selected_piece is None and "Place" in p.action:  # no selected piece
            await interaction.followup.send("You must select a piece before you play it", ephemeral=True)
        elif "Move" in p.action and p.selected_piece is None:  # choosing piece to move
            if self.board_state[tile.y][tile.x][0] != p.color:  # cannot move opponent's piece
                await interaction.followup.send("You must select your piece to move!", ephemeral=True)
                return
            p.selected_piece = tile.remove_piece()
            p.update_embed()
            for child in p.view.children:
                child.disabled = True
            await p.interaction.edit_original_response(embed=p.embed, view=p.view)
            await self.update_board()
            if not self.get_available_tiles(p):
                await self.end_game(self.players[not self.turn_index], f"({p.p.mention} touched a piece he cannot move)")
        elif (tile.x, tile.y) not in self.get_available_tiles(p):  # too weak piece for selected tile
            await interaction.followup.send("Your piece cannot be put on that tile", ephemeral=True)
        else:  # successfully placed tile
            assert p.selected_piece is not None
            for child in self.children:
                child.style = discord.ButtonStyle.grey
            tile.style = discord.ButtonStyle.green
            tile.add_piece(p.selected_piece)
            if "Place" in p.action:
                p.pieces.remove(p.selected_piece)

            self.fetch_board_state()
            if await self.check_win():
                await self.switch_turn()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.p2.p.id, self.p1.p.id]:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(content=f"**Gobblet gobblers**\n{self.p1.p.mention}({self.p1.color}) vs "
                                        f"{self.p2.p.mention}({self.p2.color})\n"
                                        f"{self.p1.p.mention}: ✅\n{self.p2.p.mention}: ✅\n\n"
                                        f"**Game timed out...***", view=self,
                                allowed_mentions=discord.AllowedMentions.none())


class GobbletButton(discord.ui.Button["PlayerUI"]):
    def __init__(self, x, y, color: str):
        self.strength = x + 1
        self.y = y
        self.color = color
        super().__init__(label="", emoji=Gobblet.emojis[color][x + 1], row=y, disabled=True, custom_id=f"piece{x}{y}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view.piece_selection(interaction, self)


class PlayerUI(discord.ui.View):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player
        self.player.view = self
        for i in range(3):
            self.add_item(GobbletButton(i, 1, player.color))

    @discord.ui.button(label="Place a new piece", style=discord.ButtonStyle.grey, row=0, disabled=True,
                       custom_id="place")
    async def new_piece(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()
        if self.player.has_pieces_left():
            self.player.action = "Place new piece"
            for child in self.children:
                if "piece" in child.custom_id:
                    child.disabled = False
                child.style = discord.ButtonStyle.grey
            button.style = discord.ButtonStyle.green
            self.player.selected_piece = None
            self.player.update_embed()
        else:
            await interaction.followup.send("You don't have any pieces left, you must move one", ephemeral=True)
            button.disabled = True
        await self.player.interaction.edit_original_response(embed=self.player.embed, view=self)

    @discord.ui.button(label="Move one of your pieces", style=discord.ButtonStyle.grey, row=0, disabled=True,
                       custom_id="move")
    async def move_piece(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()
        if self.player.board.can_move_piece(self.player.color):
            self.player.action = "Move existing piece"
            for child in self.children:
                if "piece" in child.custom_id:
                    child.disabled = True
                child.style = discord.ButtonStyle.grey
            button.style = discord.ButtonStyle.green
            self.player.selected_piece = None
            self.player.update_embed()
        else:
            await interaction.followup.send("You don't have any piece on board which you can move", ephemeral=True)
            button.disabled = True
        await self.player.interaction.edit_original_response(embed=self.player.embed, view=self)

    async def piece_selection(self, interaction: discord.Interaction, button: GobbletButton):
        if button.strength in [piece.strength for piece in self.player.pieces]:
            self.player.selected_piece = [piece for piece in self.player.pieces if button.strength == piece.strength][0]
            self.player.update_embed()
            for child in self.children:
                if "piece" in child.custom_id:
                    child.style = discord.ButtonStyle.grey
            button.style = discord.ButtonStyle.green
        else:
            await interaction.followup.send("You don't have that piece left", ephemeral=True)
            button.disabled = True
        await self.player.interaction.edit_original_response(embed=self.player.embed, view=self)


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
        a, b = board.p1.p.mention, board.p2.p.mention
        msg = await interaction.followup.send(f"**Gobblet gobblers**\n"
                                              f"{a} vs {b}\n{a}: not ready\n{b}: not ready\n"
                                              f"Waiting for players to ready up...", view=board,
                                              allowed_mentions=discord.AllowedMentions.none())
        board.message = msg
        self.stop()

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
