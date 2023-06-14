from copy import copy
from typing import List, Iterable
import random


class NoCardsException(Exception):
    pass


class NoSkullException(Exception):
    pass


class NoFlowerException(Exception):
    pass


class Card:
    FLOWER = "FLOWER"
    SKULL = "SKULL"
    hidden = "HIDDEN"


class Player:
    def __init__(self, name: str):
        self.name: str = name
        self.cards_hand: List[str] = [
            Card.FLOWER,
            Card.FLOWER,
            Card.FLOWER,
            Card.SKULL,
        ]
        self.cards_stack: List[str] = []
        self.points: int = 0
        self.alive: bool = True
        self.is_playing: bool = True
        self.cards_revealed: List[str] = []

    def can_play_skull(self) -> bool:
        return Card.SKULL in self.cards_hand

    def can_play_flower(self) -> bool:
        return Card.FLOWER in self.cards_hand

    def remove_card(self):
        self.collect_cards()
        if len(self.cards_hand) > 0:
            self.cards_hand.pop(random.randrange(len(self.cards_hand)))
        else:
            self.alive = False
            raise NoCardsException()

    def play_flower(self):
        if self.can_play_flower():
            self.cards_hand.remove(Card.FLOWER)
            self.cards_stack.append(Card.FLOWER)
        else:
            raise NoFlowerException()

    def play_skull(self):
        if self.can_play_skull():
            self.cards_hand.remove(Card.SKULL)
            self.cards_stack.append(Card.SKULL)
        else:
            raise NoSkullException()

    def reveal_stack(self) -> Iterable[str]:
        stack = copy(self.cards_stack)
        for card in reversed(stack):
            self.cards_revealed.append(card)
            self.cards_stack = self.cards_stack[:-1]
            yield card

    def collect_cards(self):
        self.cards_hand += self.cards_stack + self.cards_revealed
        self.cards_stack = []
        self.cards_revealed = []
        if len(self.cards_hand) == 0:
            self.alive = False
