import asyncio
import datetime
import random
from asyncio import Future
from collections.abc import Callable
from enum import Enum, auto
from typing import Generic, TypeVar

import discord
from discord.ui import View

from games.GameProtocol import GameConfig, GameProtocol

T = TypeVar("T")


class Role(Enum):
    VILLAGER = "Villager"
    WEREWOLF = "Werewolf"
    SEER = "Seer"
    MEDIC = "Medic"


class GamePhase(Enum):
    NIGHT = auto()
    DAY_DISCUSSION = auto()
    DAY_VOTING = auto()


class WerewolfGame(GameProtocol):
    name = "Werewolf"
    minPlayers = 5

    def assign_roles(self):
        plrs = list(self.manager.players)
        random.shuffle(plrs)

        num_players = len(plrs)
        num_wolves = max(1, num_players // 4)

        special_roles: list[Role] = []
        if self.include_seer:
            special_roles.append(Role.SEER)
        if self.include_medic:
            special_roles.append(Role.MEDIC)

        for i, plr in enumerate(plrs):
            if i < num_wolves:
                self.roles[plr] = Role.WEREWOLF
            elif i - num_wolves < len(special_roles):
                self.roles[plr] = special_roles[i - num_wolves]
            else:
                self.roles[plr] = Role.VILLAGER

    async def notify_roles(self):
        for plr, role in self.roles.items():
            if role == Role.WEREWOLF:
                team = [p.name for p, r in self.roles.items() if r == Role.WEREWOLF]
                await self.manager.send_to_player(
                    plr,
                    f"🐺 You are a **Werewolf**. Your fellow werewolves are {', '.join(team)}",
                )
            else:
                await self.manager.send_to_player(plr, f"You are a **{role.value}**")

    def setup(self) -> None:
        self.phase: GamePhase
        self.roles: dict[discord.Member, Role] = {}
        self.alive: dict[discord.Member, bool] = {}

        self.phase_event = asyncio.Event()
        self.submitted_players: set[discord.Member] = set()

        self.night_targets: dict[Role, discord.Member | None] = {}
        self.day_votes: dict[discord.Member, discord.Member] = {}

        self.discussion_time = 45
        self.include_seer = True
        self.include_medic = True

        self.config = GameConfig().add_option(
            name="Discussion Time",
            options=[30, 45, 60, 90],
            callback=self.set_discussion_time,
            default=45,
            input_type="Button",
        ).add_option(
            name="Include Seer",
            options=[True, False],
            callback=lambda v: setattr(self, "include_seer", v),
            default=True,
            input_type='Button'
        ).add_option(
            name="Include Medic",
            options=[True, False],
            callback=lambda v: setattr(self, "include_medic", v),
            default=True,
            input_type='Button'
        )

    def set_discussion_time(self, seconds: int):
        self.discussion_time = seconds

    async def get_target(
        self,
        player: discord.Member,
        targets: list[discord.Member],
        prompt: str = "Pick a target.",
    ) -> discord.Member:
        view = SelectView(player, targets, lambda p: p.display_name)

        await self.manager.send_to_player(player, prompt, view=view)

        return await view._f

    # async def get_werewolf_target(self, player: discord.Member) -> discord.Member:
    #     targets = [
    #         plr for plr, alive in self.alive.items() if alive and self.roles[plr] != Role.WEREWOLF
    #     ]

    #     view = SelectView(player, targets, lambda p: p.display_name)

    #     await self.manager.send_to_player(player, "**Choose tonight's victim:**", view=view)
    #     return await view._f

    # async def get_exile_vote(self, player: discord.Member) -> discord.Member:
    #     targets = [plr for plr, alive in self.alive.items() if alive and plr != player]

    #     view = SelectView(player, targets, lambda p: p.display_name)

    #     await self.manager.send_to_player(player, "**Cast your vote for the lynching:**", view=view)
    #     return await view._f

    async def run_night_phase(self):
        self.phase = GamePhase.NIGHT
        self.night_targets = {}
        await self.manager.send("**Night falls. The town sleeps...**")

        wolf_tasks = [
            self.get_target(
                player,
                [
                    plr
                    for plr, alive in self.alive.items()
                    if alive and self.roles[plr] != Role.WEREWOLF
                ],
                "**Choose tonight's victim:**",
            )
            for player, role in self.roles.items()
            if self.alive[player] and role == Role.WEREWOLF
        ]

        seer_tasks = [
            (
                player,
                self.get_target(
                    player,
                    [
                        plr
                        for plr, alive in self.alive.items()
                        if alive and plr != player
                    ],
                    "**Choose a player to inspect:**",
                ),
            )
            for player, role in self.roles.items()
            if self.alive[player] and role == Role.SEER
        ]

        medic_tasks = [
            self.get_target(
                player,
                [plr for plr, alive in self.alive.items() if alive],
                "**Choose a player to protect:**",
            )
            for player, role in self.roles.items()
            if self.alive[player] and role == Role.MEDIC
        ]

        wolf_results = await asyncio.gather(*wolf_tasks)
        victim = wolf_results[0]

        seer_results = [(player, await result) for player, result in seer_tasks]

        medic_results = await asyncio.gather(*medic_tasks)

        protected = medic_results[0] if medic_results else None

        for player, target in seer_results:
            await self.manager.send_to_player(
                player, f"**{target.display_name}** is a {self.roles[target].value}"
            )

        death = None
        if victim and self.alive[victim]:
            if protected and protected == victim:
                await self.manager.send(
                    f"☀️ **Morning is here!**\nThe wolves attacked {victim.mention}, but they were saved by the doctor."
                )
            else:
                self.alive[victim] = False
                await self.manager.send(
                    f"☀️ **Morning is here!**\nThe town wakes up to find {victim.mention} dead."
                )
        else:
            await self.manager.send(
                "☀️  **Morning is here!**\nMiraculously, no one died."
            )

    async def run_day_phase(self):
        self.phase = GamePhase.DAY_DISCUSSION
        await self.manager.send(
            f"🗣️ **Discussion:**\nYou have {self.discussion_time} seconds to debate who the werewolves are.",
            embed=discord.Embed(
                description=discord.utils.format_dt(
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=self.discussion_time),
                    style="R",
                )
            ),
        )
        await asyncio.sleep(self.discussion_time)

        self.phase = GamePhase.DAY_VOTING
        await self.manager.send("⚖️ **Voting:**\nCast your vote to lynch someone.")

        vote_tasks = [
            self.get_target(
                player,
                [plr for plr, alive in self.alive.items() if alive and plr != player],
                "**Choose a player to lynch:**",
            )
            for player in self.alive
        ]
        vote_results = await asyncio.gather(*vote_tasks)

        vote_counts: dict[discord.Member, int] = {}
        for target in vote_results:
            if target:
                vote_counts[target] = vote_counts.get(target, 0) + 1

        if vote_counts:
            lynched = max(vote_counts, key=lambda p: vote_counts.get(p, 0))
            self.alive[lynched] = False
            await self.manager.send(f"{lynched.mention} was lynched.")

    async def run(self):
        self.assign_roles()
        self.alive = {plr: True for plr in self.manager.players}
        await self.notify_roles()

        while not self.check_win_condition():
            await self.run_night_phase()
            if self.check_win_condition():
                break
            await self.run_day_phase()
        winner = self.check_win_condition()
        await self.manager.send(f"Game Over! The {winner} win!")

    def check_win_condition(self) -> str | None:
        alive_wolves = sum(
            1
            for plr, alive in self.alive.items()
            if alive and self.roles[plr] == Role.WEREWOLF
        )
        alive_town = sum(
            1
            for plr, alive in self.alive.items()
            if alive and self.roles[plr] != Role.WEREWOLF
        )

        if alive_wolves == 0:
            return "Villagers"
        if alive_wolves >= alive_town:
            return "Werewolves"
        return None


class SelectView(View, Generic[T]):
    def __init__(
        self,
        player: discord.Member,
        options: list[T],
        nameKey: Callable[[T], str],
        # future: Future[T],
    ):
        super().__init__(timeout=None)
        self.player = player
        self.options = options
        self._f: Future[T] = asyncio.get_running_loop().create_future()
        opts = [
            discord.SelectOption(label=nameKey(opt), value=str(i))
            for i, opt in enumerate(options)
        ]
        sel = discord.ui.Select(options=opts)
        sel.callback = self._cb
        self.add_item(sel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.defer(invisible=True)
            return False
        return True

    async def _cb(self, interaction: discord.Interaction):
        if self._f.done:
            await interaction.response.defer(invisible=True)
            return
        i = int(interaction.data["values"][0])  # type: ignore
        self._f.set_result(self.options[i])
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
