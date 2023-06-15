from .card import Card
from copy import copy
from typing import List, Iterable
from dataclasses import dataclass
import random


class NoCardsException(Exception):
    pass


class NoSkullException(Exception):
    pass


class NoFlowerException(Exception):
    pass


class CannotLoadHiddenStateException(Exception):
    pass


@dataclass
class PlayerState:
    name: str
    cards_hand: List[str]
    cards_stack: List[str]
    points: int
    alive: bool
    is_playing: bool
    cards_revealed: List[str]

    @property
    def is_hidden(self):
        return Card.hidden in self.cards_hand + self.cards_stack


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

    def get_state(self, hidden: bool = False) -> PlayerState:
        return PlayerState(
            name=self.name,
            points=self.points,
            cards_hand=[Card.hidden for _ in self.cards_hand]
            if hidden
            else self.cards_hand,
            cards_stack=[Card.hidden for _ in self.cards_stack]
            if hidden
            else self.cards_stack,
            cards_revealed=self.cards_revealed,
            alive=self.alive,
            is_playing=self.is_playing,
        )

    @classmethod
    def from_state(self, state: PlayerState):
        if state.is_hidden:
            raise CannotLoadHiddenStateException()
        new_player = Player(name=state.name)
        new_player.cards_hand = state.cards_hand
        new_player.cards_stack = state.cards_stack
        new_player.points = state.points
        new_player.alive = state.alive
        new_player.is_playing = state.is_playing
        new_player.cards_revealed = state.cards_revealed
        return new_player
