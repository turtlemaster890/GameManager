from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    Protocol,
    Self,
    TypeVar,
    overload,
)

import discord
from discord.ui import Modal, View

if TYPE_CHECKING:
    from games.GameManager import GameManager


class GameProtocol(Protocol):
    name: str
    minPlayers: int | None = None
    maxPlayers: int | None = None
    needsVoice: bool = False
    playerChannels: bool = True
    manager: GameManager

    config: GameConfig

    def __init__(self, manager: GameManager) -> None:
        self.manager = manager
        self.config = GameConfig()
        self.setup()

    def setup(self) -> None: ...

    async def run(self) -> None: ...

T = TypeVar("T")

InputType = Literal['Freeform', 'Select', 'Button']

class ConfigSelectView(View):
    def __init__(self, host: discord.Member, options: list[T], callback: Callable[[T], None], default: str = ""):
        super().__init__(timeout=None)
        self.host = host
        self.callback = callback
        self.options = options
        opts = [discord.SelectOption(label=str(opt), value=str(i)) for i, opt in enumerate(options)]
        sel = discord.ui.Select(options=opts, placeholder=default)
        sel.callback = self._cb
        self.add_item(sel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.host:
            await interaction.response.defer(invisible=True)
            return False
        return True

    async def _cb(self, interaction: discord.Interaction):
        i = int(interaction.data['values'][0]) # type: ignore
        self.callback(self.options[i])

class ConfigButtonView(View):
    def __init__(self, host: discord.Member, options: list[T], callback: Callable[[T], None]):
        super().__init__(timeout=None)
        self.host = host
        self.callback = callback
        self.options = options
        for i, opt in enumerate(options):
            b = discord.ui.Button(label=str(opt), custom_id=str(i))
            b.callback = self._cb
            self.add_item(b)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.host:
            await interaction.response.defer(invisible=True)
            return False
        return True

    async def _cb(self, interaction: discord.Interaction):
        i = int(interaction.data['custom_id']) # type: ignore
        self.callback(self.options[i])

class ConfigFreeformView(Modal):
    def __init__(self, host: discord.Member, callback: Callable[[Any], None], caster: Callable[[str], Any] | None = None):
        super().__init__(title="Config")
        self.host = host
        self.cb = callback
        self.caster = caster

        self.add_item(discord.ui.InputText(label="Option"))

    async def callback(self, interaction: discord.Interaction):
        raw_value = self.children[0].value # type: ignore
        assert raw_value
        try:
            value = self.caster(raw_value) if self.caster else raw_value
            self.cb(value)
        except ValueError:
            await interaction.response.send_message("Invalid input type. Please try again.", ephemeral=True)


@dataclass
class ConfigEntry(Generic[T]):
    name: str
    options: list[T]
    callback: Callable[[T], None]
    default: T | None = None
    input_type: InputType = 'Select'

    def __post_init__(self):
        if self.default:
            self.callback(self.default)

    def create_view(self, host: discord.Member) -> View | Modal:
        match self.input_type:
            case 'Select':
                view = ConfigSelectView(host, self.options, self.callback, str(self.default) if self.default else "")
            case 'Button':
                view = ConfigButtonView(host, self.options, self.callback)
            case 'Freeform':
                caster = type(self.default) if self.default is not None else str
                view = ConfigFreeformView(host, self.callback, caster=caster)

        return view


class GameConfig:
    def __init__(self):
        self.configs: list[ConfigEntry] = []

    @overload
    def add_option(self, *, option: ConfigEntry) -> Self: ...

    @overload
    def add_option(self, *, name: str, options: list[T], callback: Callable[[T], Any], default: T | None = None, input_type: InputType = 'Select') -> Self: ...

    def add_option(self, *, option: ConfigEntry | None = None, name: str | None = None, options: list[T] | None = None, callback: Callable[[T], Any] | None = None, default: T | None = None, input_type: InputType = 'Select') -> Self:
        if option:
            self.configs.append(option)
            return self
        assert name
        assert options
        assert callback
        self.configs.append(
            ConfigEntry(
                name, options, callback, default, input_type
            )
        )
        return self

class ConfigMenuSelect(discord.ui.Select):
    def __init__(self, config: GameConfig, host: discord.Member):
        self.config_manager = config
        self.host = host

        options = [
            discord.SelectOption(label=entry.name, value=str(i))
            for i, entry in enumerate(config.configs)
        ]

        super().__init__(placeholder="Select a configuration option to edit...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0]) # type: ignore
        entry = self.config_manager.configs[index]

        view_or_modal = entry.create_view(self.host)

        if isinstance(view_or_modal, Modal):
            await interaction.response.send_modal(view_or_modal)
        else:
            await interaction.response.edit_message(
                content=f"**Configuring `{entry.name}`:**",
                view=view_or_modal
            )

class ConfigHomeView(View):
    def __init__(self, config: GameConfig, host: discord.Member):
        super().__init__(timeout=None)
        self.host = host
        self.add_item(ConfigMenuSelect(config, host))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.host:
            await interaction.response.defer(invisible=True)
            return False
        return True