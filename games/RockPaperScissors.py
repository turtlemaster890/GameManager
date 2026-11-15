from __future__ import annotations

import asyncio
from enum import Enum, auto

import discord

from .GameProtocol import GameConfig, GameProtocol


class Choice(Enum):
    ROCK = auto()
    PAPER = auto()
    SCISSORS = auto()

    def beats(self, other: Choice) -> bool:
        wins = {
            Choice.ROCK: Choice.SCISSORS,
            Choice.PAPER: Choice.ROCK,
            Choice.SCISSORS: Choice.PAPER,
        }
        return wins[self] == other


class RockPaperScissorsGame(GameProtocol):
    name = "Rock Paper Scissors"
    minPlayers = 2
    maxPlayers = 2

    playerChannels = False

    def setup(self) -> None:
        self.rounds = 1
        self.wins: dict[discord.Member, int] = {}
        self.players: list[discord.Member] = []
        self.config = GameConfig().add_option(
            name="Rounds",
            options=[],
            callback=self.set_rounds,
            default=1,
            input_type="Freeform",
        )

    def set_rounds(self, rounds: int):
        self.rounds = rounds

    async def run(self) -> None:
        self.players = list(self.manager.players)
        self.wins = {plr: 0 for plr in self.players}
        loop = asyncio.get_running_loop()
        for _ in range(self.rounds):
            futures = {plr: loop.create_future() for plr in self.players}
            view = RockPaperScissorsChoiceView(self.players, futures)
            await self.manager.send(view=view)
            results: list[Choice] = await asyncio.gather(
                *(futures[plr] for plr in self.players)
            )

            round_results = {
                self.players[i]: results[i] for i in range(len(self.players))
            }

            wins = {
                plr: all(
                    choice.beats(o) for plr2, o in round_results.items() if plr != plr2
                )
                for plr, choice in round_results.items()
            }

            if not any(wins):
                await self.manager.send("Tie! No winners.")
            else:
                await self.manager.send(
                    f"{next(plr for plr, win in wins.items() if win).display_name} wins!"
                )
                self.wins[next(plr for plr, win in wins.items() if win)] += 1

        await self.manager.send_win(
            [max(self.wins.items(), key=lambda x: x[1])[0]],
            f"They won {max(self.wins.items(), key=lambda x: x[1])[1]}/{self.rounds} rounds.",
        )


class RockPaperScissorsChoiceView(discord.ui.View):
    def __init__(
        self,
        members: list[discord.Member],
        futures: dict[discord.Member, asyncio.Future[Choice]],
    ):
        super().__init__(timeout=None)
        self.members = members
        self.futures = futures

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user in self.members:
            return True
        await interaction.response.defer(invisible=True)
        return False

    @discord.ui.button(emoji="🪨")
    async def rock(self, button: discord.ui.Button, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        if self.futures[interaction.user].done:
            await interaction.respond(
                "You've already made a choice this round!", ephemeral=True
            )
        self.futures[interaction.user].set_result(Choice.ROCK)
        await interaction.response.defer()

    @discord.ui.button(emoji="📃")
    async def paper(self, button: discord.ui.Button, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        if self.futures[interaction.user].done:
            await interaction.respond(
                "You've already made a choice this round!", ephemeral=True
            )
        self.futures[interaction.user].set_result(Choice.PAPER)
        await interaction.response.defer()

    @discord.ui.button(emoji="✂️")
    async def scissors(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        assert isinstance(interaction.user, discord.Member)
        if self.futures[interaction.user].done:
            await interaction.respond(
                "You've already made a choice this round!", ephemeral=True
            )
        self.futures[interaction.user].set_result(Choice.SCISSORS)
        await interaction.response.defer()
