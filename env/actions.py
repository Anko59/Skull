from .card import Card
from dataclasses import dataclass
from abc import ABC


class NotationDoesNotExistException(Exception):
    pass


class Action(ABC):
    pass

    @classmethod
    def from_notation(cls, notation: str) -> 'Action':
        if notation.startswith("P"):
            return PassAction()
        elif notation.startswith("B"):
            return BetAction(int(notation[1:]))
        elif notation.startswith("R"):
            return RevealCardAction(notation[1:])
        elif notation.startswith("L"):
            return LoseCardAction(Card(notation[1:]))
        elif notation == 'S':
            return PlayCardAction(Card.SKULL)
        elif notation == 'F':
            return PlayCardAction(Card.FLOWER)
        else:
            raise NotationDoesNotExistException()


@dataclass
class PlayCardAction(Action):
    card: Card

    def __str__(self) -> str:
        return f"{self.card.value}"


@dataclass
class LoseCardAction(Action):
    card: Card

    def __str__(self) -> str:
        return f"L{self.card.value}"


@dataclass
class RevealCardAction(Action):
    player_name: str

    def __str__(self) -> str:
        return f"R{self.player_name}"


@dataclass
class BetAction(Action):
    amount: int

    def __str__(self) -> str:
        return f"B{self.amount}"


@dataclass
class PassAction(Action):
    def __str__(self) -> str:
        return "P"

