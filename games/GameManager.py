from __future__ import annotations

from collections.abc import Callable

import discord
from discord.interactions import Interaction
from discord.ui import Button, View, ViewItem, button

from .GameProtocol import GameProtocol


class LobbyView(View):
    def __init__(
        self,
        manager: GameManager,
        *items: ViewItem,
        timeout: float | None = None,
        disable_on_timeout: bool = False,
        store: bool = True,
        **kwargs,
    ):
        super().__init__(
            *items,
            timeout=timeout,
            disable_on_timeout=disable_on_timeout,
            store=store,
            **kwargs,
        )
        self.manager = manager

    @button(label="Join", style=discord.ButtonStyle.green)
    async def join_lobby(self, button: Button, interaction: Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if interaction.user in self.manager.players:
            await interaction.response.send_message(
                "You're already in this lobby!", ephemeral=True
            )
            return
        self.manager.add_player(interaction.user)
        await self.manager.update_embed()
        await interaction.response.send_message("Joined game!", ephemeral=True)

    @button(label="Leave", style=discord.ButtonStyle.red)
    async def leave_lobby(self, button: Button, interaction: Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if interaction.user not in self.manager.players:
            await interaction.response.send_message(
                "You aren't in this lobby!", ephemeral=True
            )
            return
        if interaction.user == self.manager.host:
            await interaction.response.send_message(
                "You're the host of this lobby! If you want to close it, use the Close button.",
                ephemeral=True,
            )
            return
        self.manager.remove_player(interaction.user)
        await self.manager.update_embed()
        await interaction.response.send_message("Left game!", ephemeral=True)

    @button(label="Start", style=discord.ButtonStyle.blurple)
    async def start_game(self, button: Button, interaction: Interaction):
        if interaction.user != self.manager.host:
            await interaction.response.send_message(
                "You're not the host of this lobby!", ephemeral=True
            )
            return
        await interaction.response.defer(invisible=True)
        await self.manager.start_game(interaction)

    @button(label="Close", style=discord.ButtonStyle.gray)
    async def close_lobby(self, button: Button, interaction: Interaction):
        if interaction.user != self.manager.host:
            await interaction.response.send_message(
                "You're not the host of this lobby!", ephemeral=True
            )
            return
        await interaction.response.defer(invisible=True)
        await self.manager.delete_embed()


class GameManager:
    def __init__(self, game: type[GameProtocol], host: discord.Member | None = None):
        self.players: set[discord.Member] = set()
        self.lobby_message: discord.Message | discord.InteractionMessage | None = None
        self.voice_client: discord.VoiceClient | None = None
        self.text_channel: discord.abc.Messageable | None = None
        self.voice_channel: discord.abc.Connectable | None = None
        self.started = False
        self.view: LobbyView | None = None
        self.host = host
        self.on_close: Callable[[], None] | None = None
        if host:
            self.add_player(host)
        self.game = game(self)

    def add_player(self, player: discord.Member):
        self.players.add(player)

    def remove_player(self, player: discord.Member):
        self.players.discard(player)

    def _make_embed(self):
        embed = discord.Embed(
            title=f"{self.game.name} Lobby",
            description=f"Host: {self.host and self.host.mention}",
        )
        embed.add_field(
            name="Players",
            value=f"{len(self.players)}/{self.game.maxPlayers or ":infinity:"} ({", ".join([m.mention for m in self.players])})",
        )
        return embed

    async def send_embed(self, ctx: discord.ApplicationContext) -> None:
        self.text_channel = ctx.channel  # pyright: ignore[reportAttributeAccessIssue]
        self.view = LobbyView(self)
        await ctx.respond(embed=self._make_embed(), view=self.view)
        self.lobby_message = await ctx.interaction.original_response()

    async def update_embed(self):
        if self.lobby_message and not self.started:
            await self.lobby_message.edit(embed=self._make_embed())

    async def delete_embed(self):
        if self.view:
            self.view.stop()
        if self.lobby_message:
            try:
                await self.lobby_message.delete()
            except discord.NotFound:
                pass
        self.lobby_message = None
        if self.on_close:
            self.on_close()
            self.on_close = None

    async def start_game(self, interaction: Interaction):
        if self.started:
            return

        if self.game.minPlayers and len(self.players) < self.game.minPlayers:
            await interaction.followup.send("Not enough players!", ephemeral=True)
            return

        if self.game.maxPlayers and len(self.players) > self.game.maxPlayers:
            await interaction.followup.send("Too many players!", ephemeral=True)
            return

        host_channel = None
        if self.host is not None and self.host.voice is not None:
            host_channel = self.host.voice.channel

        if self.game.needsVoice:
            if self.host is None:
                print("No host!")
                return
            if host_channel is None:
                await interaction.followup.send(
                    "You need to be in a voice channel for this game!", ephemeral=True
                )
                return
            self.voice_client = await host_channel.connect(cls=discord.VoiceClient)

        self.voice_channel = host_channel
        if interaction.channel:
            self.text_channel = (
                interaction.channel
            )  # pyright: ignore[reportAttributeAccessIssue]

        self.started = True
        if self.view:
            self.view.stop()
        if self.lobby_message:
            await self.lobby_message.edit(content="Started!", embed=None, view=None)

        await self.game.run()

    async def send(
        self,
        content: str,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
    ):
        if self.lobby_message:
            try:
                await self.lobby_message.edit(content=content, embed=embed, view=view)
                return
            except discord.NotFound:
                self.lobby_message = None
        if self.text_channel:
            if embed is not None and view is not None:
                self.lobby_message = await self.text_channel.send(
                    content=content, embed=embed, view=view
                )
                return
            if embed is not None:
                self.lobby_message = await self.text_channel.send(
                    content=content, embed=embed
                )
                return
            if view is not None:
                self.lobby_message = await self.text_channel.send(
                    content=content, view=view
                )
                return
            self.lobby_message = await self.text_channel.send(content=content)
