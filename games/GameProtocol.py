from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from games.GameManager import GameManager


class GameProtocol(Protocol):
    name: str
    minPlayers: int | None = None
    maxPlayers: int | None = None
    needsVoice: bool = False
    manager: GameManager

    def __init__(self, manager: GameManager) -> None:
        self.manager = manager
        self.setup()

    def setup(self) -> None: ...

    async def run(self) -> None: ...
