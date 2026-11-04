from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from enum import Enum

import discord
from discord.ui import Button, Select, View, button

from .GameProtocol import GameProtocol


class Colour(Enum):
    RED = "🟥"
    YELLOW = "🟨"
    GREEN = "🟩"
    BLUE = "🟦"
    WILD = "⬛"


class Value(Enum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    SKIP = "skip"
    REVERSE = "reverse"
    PLUSTWO = "+2"
    WILD = "wild"
    PLUSFOUR = "+4"


@dataclass
class Card:
    colour: Colour
    value: Value

    def __hash__(self) -> int:
        return hash(self.colour.value + self.value.value)


def label(card: Card) -> str:
    return f"{card.colour.value} {card.value.value}"


def build_deck() -> list[Card]:
    deck: list[Card] = []
    for c in [c for c in Colour if c != Colour.WILD]:
        deck.append(Card(c, Value.ZERO))
        for v in [
            v for v in Value if v not in [Value.ZERO, Value.WILD, Value.PLUSFOUR]
        ]:
            deck += [Card(c, v), Card(c, v)]
    deck += [Card(Colour.WILD, Value.WILD)] * 4 + [
        Card(Colour.WILD, Value.PLUSFOUR)
    ] * 4
    return deck


class UnoGame(GameProtocol):
    name = "Uno"
    minPlayers = 2
    maxPlayers = 10

    def setup(self) -> None:
        self.deck: list[Card] = []
        self.discard: list[Card] = []
        self.hands: dict[discord.Member, list[Card]] = {}
        self.order: list[discord.Member] = []
        self.turn = 0
        self.direction = 1
        self.colour: Colour = Colour.RED
        self.last_action: str = ""
        self.over = False
        self.lock = asyncio.Lock()
        self.table_view = None

    @property
    def current(self) -> discord.Member:
        return self.order[self.turn]

    def draw(self, n: int = 1) -> list[Card]:
        out: list[Card] = []
        for _ in range(n):
            if not self.deck:
                if len(self.discard) <= 1:
                    break
                top = self.discard.pop()
                self.deck, self.discard = self.discard, [top]
                random.shuffle(self.deck)
            out.append(self.deck.pop())
        return out

    def playable(self, card: Card) -> bool:
        return (
            card.colour == Colour.WILD
            or card.colour == self.colour
            or card.value == self.discard[-1].value
        )

    async def run(self):
        self.deck = build_deck()
        random.shuffle(self.deck)
        self.order = list(self.manager.players)
        random.shuffle(self.order)
        self.hands = {p: self.draw(7) for p in self.order}
        while True:
            top = self.deck.pop()
            if top.colour != Colour.WILD:
                break
            self.deck.insert(0, top)
        self.discard = [top]
        self.colour = top.colour
        self.last_action = "Game Started!"
        self.table_view = TableView(self)
        await self.refresh()

    def embed(self) -> discord.Embed:
        top = self.discard[-1]
        e = discord.Embed(
            title=self.name,
            description=(
                f"Top: **{label(top)}**  |  Colour: {top.colour.value} {top.colour.name}\n"
                f"{self.last_action}"
            ),
        )
        e.add_field(name="Turn", value=self.current.mention)
        e.add_field(
            name="Cards",
            value="\n".join(
                f"{p.display_name}: {len(self.hands[p])}" for p in self.order
            ),
            inline=False,
        )
        return e

    async def refresh(self):
        await self.manager.send(
            f"{self.current.mention}'s turn", embed=self.embed(), view=self.table_view
        )

    async def play(
        self, player: discord.Member, card: Card, colour: Colour | None
    ) -> str | None:
        if self.over:
            return "Game is over."
        if player != self.current:
            return "It's not your turn."
        hand = self.hands[player]
        if card not in hand or not self.playable(card):
            return "You can't play that card."

        hand.remove(card)
        self.discard.append(card)
        self.colour = colour or card.colour
        action = f"{player.display_name} played {label(card)}"
        steps = 1
        v = card.value

        if v == Value.REVERSE:
            self.direction *= -1
            if len(self.order) == 2:
                steps = 2
        elif v == Value.SKIP:
            steps = 2
        elif v in (Value.PLUSTWO, Value.PLUSFOUR):
            victim = self.order[(self.turn + self.direction) % len(self.order)]
            self.hands[victim] += self.draw(int(v.value[1:]))
            steps = 2
            action += f", {victim.display_name} draws {v.value[1:]}"
        if card.colour == Colour.WILD:
            action += f"  (colour: {self.colour.value})"

        self.last_action = action
        if not hand:
            await self.finish(player)
            return None
        if len(hand) == 1:
            self.last_action += " **UNO!**"
        self.turn = (self.turn + self.direction * steps) % len(self.order)
        await self.refresh()
        return None

    async def draw_turn(self, player: discord.Member) -> str | None:
        if self.over:
            return "Game is over."
        if player != self.current:
            return "It's not your turn."
        self.hands[player] += self.draw(1)
        self.last_action = f"{player.display_name} drew a card"
        self.turn = (self.turn + self.direction) % len(self.order)
        await self.refresh()
        return None

    async def finish(self, winner: discord.Member):
        self.over = True
        if self.table_view:
            self.table_view.stop()
        await self.manager.send(f"🎉 {winner.mention} wins!", embed=None, view=None)

    def hand_text(self, player: discord.Member) -> str:
        hand = sorted(self.hands[player], key=lambda c: f"{c.colour.name}{c.value}")
        return "**Your hand:** " + ", ".join(label(c) for c in hand)

    def hand_message(self, player: discord.Member) -> tuple[str, discord.ui.BaseView]:
        status = (
            "Your turn!"
            if player == self.current
            else f"Waiting for {self.current.display_name}."
        )
        return f"{status}\n{self.hand_text(player)}", HandView(self, player)


async def do_play(
    interaction: discord.Interaction, game: UnoGame, card: Card, colour: Colour | None
):
    await interaction.response.defer()
    async with game.lock:
        err = await game.play(interaction.user, card, colour)  # type: ignore
    await interaction.edit_original_response(
        content=err or f"You played {label(card)}.", view=None
    )
    await interaction.delete_original_response(delay=5)


class TableView(View):
    def __init__(self, game: UnoGame):
        super().__init__(timeout=None)
        self.game = game

    @button(label="My Hand", style=discord.ButtonStyle.blurple)
    async def show_hand(self, button: Button, interaction: discord.Interaction):
        if interaction.user not in self.game.hands:
            await interaction.response.send_message(
                "You're not in this game.", ephemeral=True
            )
            return
        content, view = self.game.hand_message(interaction.user)  # type: ignore
        await interaction.response.send_message(
            content=content, view=view, ephemeral=True
        )


class HandView(View):
    def __init__(self, game: UnoGame, player: discord.Member):
        super().__init__(timeout=180)
        self.game = game
        self.player = player
        if player != game.current or game.over:
            return
        seen: set[Card] = set()
        opts: list[discord.SelectOption] = []
        for c in sorted(game.hands[player], key=lambda c: f"{c.colour.name}{c.value}"):
            if c in seen or not game.playable(c):
                continue
            seen.add(c)
            opts.append(
                discord.SelectOption(
                    label=label(c), value=f"{c.colour.name}|{c.value.name}"
                )
            )
        if opts:
            sel = Select(placeholder="Play a card", options=opts[:25])
            sel.callback = self.on_select
            self.add_item(sel)
        draw = Button(label="Draw", style=discord.ButtonStyle.gray)
        draw.callback = self.on_draw
        self.add_item(draw)

    async def on_select(self, interaction: discord.Interaction):
        colour, value = interaction.data["values"][0].split("|")  # type: ignore
        colour = Colour[colour]
        value = Value[value]
        card = Card(colour, value)
        if colour == Colour.WILD:
            await interaction.response.edit_message(
                content=f"{self.game.hand_text(self.player)}\nPick a colour:",
                view=ColourView(self.game, card),
            )
            return
        await do_play(interaction, self.game, card, None)

    async def on_draw(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.game.lock:
            err = await self.game.draw_turn(self.player)
        content = err or f"Drew a card.\n{self.game.hand_text(self.player)}"
        await interaction.edit_original_response(content=content, view=None)


class ColourView(View):
    def __init__(self, game: UnoGame, card: Card):
        super().__init__(timeout=60)
        self.game = game
        self.card = card
        for c in [c for c in Colour if c != Colour.WILD]:
            b = Button(label=c.name.title(), emoji=c.value)
            b.callback = self._cb(c)
            self.add_item(b)

    def _cb(self, colour: Colour):
        async def cb(interaction: discord.Interaction):
            await do_play(interaction, self.game, self.card, colour)

        return cb
