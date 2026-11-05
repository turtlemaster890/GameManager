from __future__ import annotations

import asyncio
import math
import random
import time
from enum import Enum

import discord
from discord.ui import Button, View, button

from .GameProtocol import GameProtocol


class Role(Enum):
    LIBERAL = 1
    FASCIST = 2
    HITLER = 3

    def is_fascist(self):
        return self in [self.FASCIST, self.HITLER]


class SecretHitlerGame(GameProtocol):
    name = "Secret Hitler"
    minPlayers = 5
    maxPlayers = 10

    def setup(self) -> None:
        self.roles: dict[discord.Member, Role] = {}
        self.order: list[discord.Member] = []
        self.previous_government: tuple[discord.Member, discord.Member] | None = None
        self.president_index: int = 0
        self.chancellor: discord.Member | None = None
        self.votes: dict[discord.Member, bool] = {}

    async def run(self) -> None:
        self.order = list(self.manager.players)
        players = len(self.order)
        fascists = math.ceil(players / 2) - 1
        liberals = players - fascists
        pool = (
            [Role.HITLER] + [Role.FASCIST] * (fascists - 1) + [Role.LIBERAL] * liberals
        )
        random.shuffle(pool)
        for player in self.order:
            self.roles[player] = pool.pop()

    async def get_new_government(self):
        self.president_index += 1
        await self.manager.send()

    def make_vote_embed(
        self, government: tuple[discord.Member, discord.Member]
    ) -> discord.Embed:
        e = discord.Embed(title="Government Vote")
        e.add_field(name="President", value=government[0].display_name)
        e.add_field(name="Chancellor", value=government[1].display_name)
        return e

    async def get_votes(
        self, government: tuple[discord.Member, discord.Member]
    ) -> bool:
        await self.manager.send(
            embed=self.make_vote_embed(government), view=StartVoteView(self, government)
        )
        self.votes = {}
        start_time = time.time()
        while len(self.votes) < len(self.order) and time.time() - start_time < 30:
            await asyncio.sleep(0.1)
        jas = sum([1 for v in self.votes.values() if v])
        if jas > len(self.order) / 2:
            e = discord.Embed(title="Results", description="The vote passes!")
            e.add_field(name="President", value=government[0].display_name)
            e.add_field(name="Chancellor", value=government[1].display_name)
            await self.manager.send(embed=e)
            return True
        else:
            e = discord.Embed(title="Results", description="The vote fails.")
            await self.manager.send(embed=e)
            return False

    async def send_vote_menu(
        self,
        interaction: discord.Interaction,
        government: tuple[discord.Member, discord.Member],
    ):
        await interaction.followup.send(embed=self.make_vote_embed(government), view=ElectionView(self, interaction.user))  # type: ignore

    def vote(self, player: discord.Member, ja: bool) -> None:
        self.votes[player] = ja


class PickChancellorView(View):
    def __init__(self, game: SecretHitlerGame, player: discord.Member): ...


class StartVoteView(View):
    def __init__(
        self, game: SecretHitlerGame, government: tuple[discord.Member, discord.Member]
    ):
        super().__init__(timeout=None)
        self.game = game
        self.government = government

    @button(label="Vote", style=discord.ButtonStyle.blurple)
    async def vote(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.game.send_vote_menu(interaction, self.government)


class ElectionView(View):
    def __init__(self, game: SecretHitlerGame, player: discord.Member):
        super().__init__(timeout=180)
        self.game = game
        self.player = player

    @button(label="Ja", style=discord.ButtonStyle.green)
    async def voteJa(self, button: Button, interaction: discord.Interaction):
        self.game.vote(self.player, True)
        self.disable_all_items()
        await interaction.response.defer(invisible=True)

    @button(label="Nein", style=discord.ButtonStyle.red)
    async def voteNein(self, button: Button, interaction: discord.Interaction):
        self.game.vote(self.player, False)
        self.disable_all_items()
        await interaction.response.defer(invisible=True)
