from __future__ import annotations

import asyncio
import datetime
import math
import random
import time
from collections.abc import Callable
from enum import Enum
from types import CoroutineType

import discord
from discord.ui import Button, View, button

from .GameProtocol import GameProtocol


class Role(Enum):
    LIBERAL = "Liberal"
    FASCIST = "Fascist"
    HITLER = "Hitler"

    def is_fascist(self):
        return self in [self.FASCIST, self.HITLER]


class Policy(Enum):
    LIBERAL = ("Liberal Policy", discord.ButtonStyle.blurple, discord.Colour.blue())
    FASCIST = ("Fascist Policy", discord.ButtonStyle.red, discord.Colour.red())


def make_deck() -> list[Policy]:
    deck = [Policy.FASCIST] * 11 + [Policy.LIBERAL] * 6
    random.shuffle(deck)
    return deck


def draw(n: int, deck: list[Policy]) -> list[Policy]:
    drawn: list[Policy] = []
    for _ in range(n):
        drawn.append(deck.pop())
    return drawn


class SecretHitlerGame(GameProtocol):
    name = "Secret Hitler"
    # minPlayers = 5
    maxPlayers = 10
    # needsVoice = True

    def setup(self) -> None:
        self.roles: dict[discord.Member, Role] = {}
        self.order: list[discord.Member] = []
        self.previous_government: tuple[
            discord.Member | None, discord.Member | None
        ] = (None, None)
        self.president_index: int = 0
        self.president: discord.Member | None = None
        self.chancellor: discord.Member | None = None
        self.votes: dict[discord.Member, bool] = {}
        self.policy_deck: list[Policy] = make_deck()
        self.policy_discard: list[Policy] = []
        self.liberal_policies: int = 0
        self.fascist_policies: int = 0
        self.policy_enacted: bool = False

    async def run(self) -> None:
        self.order = list(self.manager.players)
        players = len(self.order)
        fascists = math.ceil(players / 2)
        liberals = players - fascists
        pool = (
            [Role.HITLER] + [Role.FASCIST] * (fascists - 1) + [Role.LIBERAL] * liberals
        )
        random.shuffle(pool)
        for player in self.order:
            self.roles[player] = pool.pop()
            e = discord.Embed(title="Role", description=self.roles[player].value)
            message = await self.manager.send_to_player(player, embed=e)
            if message:
                await message.pin()

        while True:
            await self.get_new_government()
            while self.chancellor is None:
                await asyncio.sleep(1)
            assert self.president
            assert self.chancellor
            self.policy_enacted = False
            await self.select_policies_president()
            while not self.policy_enacted:
                await asyncio.sleep(1)

    async def select_policies_president(self) -> None:
        policies = draw(3, self.policy_deck)
        self.policy_discard += policies
        e = discord.Embed(title="Discard a policy")
        e.add_field(
            name="Drawn Policies",
            value=", ".join(policy.value[0] for policy in policies),
        )
        assert self.president
        assert self.chancellor
        await self.manager.send_to_player(
            self.president,
            embed=e,
            view=DiscardPolicyView(
                self, self.president, policies, callback=self.select_policies_chancellor
            ),
        )

    async def select_policies_chancellor(self, available: list[Policy]):
        e = discord.Embed(title="Discard a policy")
        e.add_field(
            name="Passed Policies",
            value=", ".join(policy.value[0] for policy in available),
        )
        assert self.chancellor
        await self.manager.send_to_player(
            self.chancellor,
            embed=e,
            view=DiscardPolicyView(
                self, self.chancellor, available, callback=self.enact_policy
            ),
        )

    async def enact_policy(self, policy: list[Policy]):
        assert len(policy) == 1
        enacted = policy[0]
        if enacted == Policy.LIBERAL:
            self.liberal_policies += 1
        else:
            self.fascist_policies += 1
        e = discord.Embed(title="Enacted Policy", colour=enacted.value[2])
        e.add_field(name="Policy Type", value=enacted.value[0])
        await self.manager.send(embed=e)
        self.policy_enacted = True

    async def get_new_government(self):
        self.president_index += 1
        self.president_index %= len(self.order)
        self.previous_government = (self.president, self.chancellor)
        self.president = None
        self.chancellor = None
        await self.manager.send_to_player(
            self.order[self.president_index],
            self.order[self.president_index].mention,
            embed=discord.Embed(title="Select the next chancellor!"),
            view=PickChancellorView(self, self.order[self.president_index]),
        )

    def make_vote_embed(
        self,
        government: tuple[discord.Member, discord.Member],
        end_time: datetime.datetime,
    ) -> discord.Embed:
        e = discord.Embed(title="Government Vote")
        e.add_field(name="Vote ends", value=discord.utils.format_dt(end_time, "R"))
        e.add_field(name="President", value=government[0].display_name)
        e.add_field(name="Chancellor", value=government[1].display_name)
        return e

    async def get_votes(
        self, government: tuple[discord.Member, discord.Member]
    ) -> bool:
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=30)
        for p in self.order:
            await self.manager.send_to_player(
                p,
                p.mention,
                embed=self.make_vote_embed(government, end_time),
                view=ElectionView(self, p),
            )
        self.votes = {}
        while (
            len(self.votes) < len(self.order)
            and time.time() - start_time.timestamp() < 30
        ):
            await asyncio.sleep(0.1)
        jas = sum([1 for v in self.votes.values() if v])
        if jas > len(self.order) / 2:
            e = discord.Embed(
                title="Results",
                description="The vote passes!",
                colour=discord.Colour.green(),
            )
            e.add_field(name="President", value=government[0].display_name)
            e.add_field(name="Chancellor", value=government[1].display_name)
            await self.manager.send(embed=e)
            return True
        else:
            e = discord.Embed(
                title="Results",
                description="The vote fails.",
                colour=discord.Colour.red(),
            )
            await self.manager.send(embed=e)
            return False

    def vote(self, player: discord.Member, ja: bool) -> None:
        self.votes[player] = ja

    async def pick_chancellor(
        self, president: discord.Member, selected_chancellor: discord.Member
    ):
        ja = await self.get_votes((president, selected_chancellor))
        if ja:
            self.president = president
            self.chancellor = selected_chancellor
            print("Chancellor picked!")

        else:
            await self.get_new_government()


class DiscardPolicyView(View):
    def __init__(
        self,
        game: SecretHitlerGame,
        player: discord.Member,
        available_policies: list[Policy],
        callback: Callable[[list[Policy]], CoroutineType],
    ):
        super().__init__(timeout=None)
        self.game = game
        self.player = player
        self.policies = list(available_policies)
        self.callback = callback

        for policy in self.policies:
            b = Button(label=policy.value[0], emoji="🗑️", style=policy.value[1])
            b.callback = self._cb(policy)
            self.add_item(b)

    def _cb(self, policy: Policy):
        async def interior(interaction: discord.Interaction):
            self.disable_all_items()
            await interaction.response.edit_message(view=self)
            policies = self.policies
            policies.remove(policy)
            await self.callback(policies)

        return interior


class PickChancellorView(View):
    def __init__(self, game: SecretHitlerGame, player: discord.Member):
        super().__init__(timeout=None)
        self.game = game
        self.player = player
        opts: list[discord.SelectOption] = []
        for pl in game.order:
            if (
                game.previous_government
                and pl in game.previous_government
                and len(game.manager.players) > 5
            ):
                continue
            if player == pl:
                continue
            opts.append(discord.SelectOption(label=pl.display_name, value=str(pl.id)))
        sel = discord.ui.Select(options=opts, placeholder="Next Chancellor")
        sel.callback = self.sel_callback
        self.add_item(sel)

    async def sel_callback(self, interaction: discord.Interaction):
        selection_id: str = interaction.data["values"][0]  # type: ignore
        assert interaction.guild
        selected_player = interaction.guild.get_member(int(selection_id))
        assert selected_player
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await self.game.pick_chancellor(self.player, selected_player)


# class StartVoteView(View):
#     def __init__(
#         self, game: SecretHitlerGame, government: tuple[discord.Member, discord.Member]
#     ):
#         super().__init__(timeout=None)
#         self.game = game
#         self.government = government

#     @button(label="Vote", style=discord.ButtonStyle.blurple)
#     async def vote(self, button: Button, interaction: discord.Interaction):
#         await interaction.response.defer(ephemeral=True)
#         await self.game.send_vote_menu(interaction, self.government)


class ElectionView(View):
    def __init__(self, game: SecretHitlerGame, player: discord.Member):
        super().__init__(timeout=180)
        self.game = game
        self.player = player

    @button(label="Ja", style=discord.ButtonStyle.green)
    async def voteJa(self, button: Button, interaction: discord.Interaction):
        if interaction.user != self.player:
            await interaction.response.defer(invisible=True)
            return
        self.game.vote(self.player, True)
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        # await interaction.response.defer()

    @button(label="Nein", style=discord.ButtonStyle.red)
    async def voteNein(self, button: Button, interaction: discord.Interaction):
        if interaction.user != self.player:
            await interaction.response.defer(invisible=True)
            return
        self.game.vote(self.player, False)
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        # await interaction.response.defer()
