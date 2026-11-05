from enum import Enum

from .SecretHitler import SecretHitlerGame
from .Uno import UnoGame


class Games(Enum):
    Uno = UnoGame
    SecretHitler = SecretHitlerGame
