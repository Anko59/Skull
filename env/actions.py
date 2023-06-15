from .card import Card
from dataclasses import dataclass
from abc import ABC, abstractmethod


class Action(ABC):

    @property
    @abstractmethod
    def notation(self) -> str:
        pass


@dataclass
class PlayCardAction(Action):
    card: str

    @property
    def notation(self) -> str:
        return f"{self.card}"


@dataclass
class LoseCardAction(Action):
    card: str

    @property
    def notation(self) -> str:
        return f"L{self.card}"


@dataclass
class RevealCardAction(Action):
    player_name: str

    @property
    def notation(self) -> str:
        return f"R{self.player_name}"


@dataclass
class BetAction(Action):
    amount: int

    @property
    def notation(self) -> str:
        return f"B{self.amount}"


@dataclass
class PassAction(Action):
    pass
    notation: str = "P"


class NotationDoesNotExistException(Exception):
    pass


def parse_notation(notation: str) -> Action:
    if notation.startswith("P"):
        return PassAction()
    elif notation.startswith("B"):
        return BetAction(int(notation[1:]))
    elif notation.startswith("R"):
        return RevealCardAction(notation[1:])
    elif notation.startswith("L"):
        return LoseCardAction(notation[1:])
    elif notation == 'S':
        return PlayCardAction(Card.SKULL)
    elif notation == 'F':
        return PlayCardAction(Card.FLOWER)
    else:
        raise NotationDoesNotExistException()
