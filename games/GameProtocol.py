from typing import Protocol

class GameProtocol(Protocol):
    name: str
    minPlayers: int | None = None
    maxPlayers: int | None = None
    needsVoice: bool = False

    async def run(self) -> None:
        ...