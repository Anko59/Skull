from .player import Player, PlayerState
from .card import Card
from .actions import (
    Action,
    PlayCardAction,
    BetAction,
    RevealCardAction,
    LoseCardAction,
    PassAction,
    parse_notation,
)
from typing import List, Optional, Union
from copy import copy
from dataclasses import dataclass


class MoveIsNotLegal(Exception):
    pass


class GameIsOver(Exception):
    pass


class GameHasNotStarted(Exception):
    pass

class CannotLoadStateException(Exception):
    pass


@dataclass
class BoardState:
    players: List[PlayerState]
    bet_holder: Optional[str]
    highest_bet: int
    next_player: str


class Board:
    def __init__(self, player_names: List[str]):
        self.players: List[Player] = [Player(name=x) for x in player_names]
        self.bet_holder: Optional[Player] = None
        self.highest_bet: int = 0
        self.next_player: Player = self.players[0]
        self.legal_moves: List[Action] = self._get_legal_moves(self.next_player)
        self.action_record: List[str] = []
        self.state_record: List[BoardState] = []

    def _has_anyone_won(self) -> bool:
        return any([player.points > 1 for player in self.players])

    def _are_more_than_two_players_alive(self) -> bool:
        return sum([int(player.alive) for player in self.players]) > 1

    def _is_round_over(self) -> bool:
        return not any([player.is_playing for player in self.players])

    def _nbr_cards_on_board(self) -> int:
        return sum([len(player.cards_stack) for player in self.players])

    def _cards_shown(self) -> int:
        return sum([len(player.cards_revealed) for player in self.players])

    def _start_round(self):
        # Collect cards
        for player in self.players:
            player.collect_cards()
            if player.alive:
                player.is_playing = True
            if player == self.bet_holder:
                index = self.players.index(player)
                # Last bet_holder is next first player
                self.players = self.players[index:] + self.players[:index]
        self.next_player = self.players[0]
        self.bet_holder = None
        self.highest_bet = 0

    def _process_action(self, player: Player, action: Action):
        if isinstance(action, PlayCardAction):
            if action.card == Card.FLOWER:
                player.play_flower()
            else:
                player.play_skull()

        elif isinstance(action, BetAction):
            self.bet_holder = player
            self.highest_bet = action.amount

        elif isinstance(action, RevealCardAction):
            for p in self.players:
                if p.name == action.player_name:
                    card = next(p.reveal_stack())  # type: ignore
                    if card == Card.SKULL:
                        player.is_playing = False
                        player.remove_card()
                    else:
                        if self._cards_shown() == self.highest_bet:
                            player.is_playing = False
                            player.points += 1

        elif isinstance(action, LoseCardAction):
            player.collect_cards()
            player.cards_hand.remove(action.card)
            if len(player.cards_hand) == 0:
                player.alive = False
            player.is_playing = False

        elif isinstance(action, PassAction):
            player.is_playing = False

    def winner(self):
        if not self._are_more_than_two_players_alive():
            return [x for x in self.players if x.alive][0]  # type: ignore
        elif self._has_anyone_won():
            return [x for x in self.players if x.points > 1][0]  # type: ignore
        else:
            return None

    def push(self, action: Union[Action, str]):
        if self.winner() is not None:
            raise GameIsOver()
        if isinstance(action, str):
            action = parse_notation(action)
        if action not in self.legal_moves:
            raise MoveIsNotLegal()
        self.state_record.append(copy(self.get_state()))
        self.action_record.append(action.notation)
        self._process_action(self.next_player, action)
        if self._is_round_over():
            self._start_round()
        else:
            self.next_player = self.players[
                (self.players.index(self.next_player) + 1) % len(self.players)
            ]
        self.legal_moves = self._get_legal_moves(self.next_player)

    def pop(self):
        if len(self.state_record) == 0:
            raise GameHasNotStarted()
        last_state = self.state_record[-1]
        self.load_state(last_state)
        self.state_record = self.state_record[:-1]
        self.action_record = self.action_record[:-1]
        self.legal_moves = self._get_legal_moves()

    def load_state(self, state: BoardState):
        if len(state.players) != len(self.players):
            raise CannotLoadStateException()
        for player, player_state in zip(self.players, state.players):
            player.load_state(player_state)

        self.highest_bet = state.highest_bet
        if state.bet_holder is None:
            self.bet_holder = None
        else:
            self.bet_holder = self.players[
                [x.name for x in self.players].index(state.bet_holder)
            ]
        self.next_player = self.players[
            [x.name for x in self.players].index(state.next_player)
        ]

    def _get_legal_moves(self, player: Player) -> List[Action]:  # type: ignore
        if not player.alive or not player.is_playing:
            return [PassAction()]
        if self.bet_holder != player:
            # Player did not place the highest bet
            legal_actions: list[Action] = []
            # If there is no bet, he can place cards
            if self.bet_holder is None:
                if player.can_play_flower():
                    legal_actions.append(PlayCardAction(Card.FLOWER))
                if player.can_play_skull():
                    legal_actions.append(PlayCardAction(Card.SKULL))
            # If there is a bet, he can abandon
            else:
                legal_actions.append(PassAction())

            # If everyone has played at least once, he can bet
            # up to the total number of cards
            if not any(
                [(len(p.cards_stack) == 0) and p.is_playing for p in self.players]
            ):
                for i in range(self.highest_bet + 1, self._nbr_cards_on_board() + 1):
                    legal_actions.append(BetAction(i))
            return legal_actions
        else:
            # One round has passed and player still has the highest bets
            # He can show cards
            # Starting with his own car
            for card in player.reveal_stack():
                if card == Card.SKULL:
                    # Auto Skulled
                    player.collect_cards()
                    if player.can_play_flower():
                        return [LoseCardAction(Card.FLOWER), LoseCardAction(Card.SKULL)]
                    else:
                        return [LoseCardAction(Card.SKULL)]

                if len(player.cards_revealed) == self.highest_bet:
                    # Victory by returning only own cards
                    player.points += 1
                    return [PassAction()]

            # Player can return cards from every player
            # except himself if they have played more cards then they have shown
            return [
                RevealCardAction(opponent.name)
                for opponent in self.players
                if opponent != player and len(opponent.cards_stack) > 0
            ]

    def get_state(
        self, show_hand: Union[List[str], str] = "next_player"
    ) -> BoardState:
        if show_hand == "next_player":
            show_hand = [self.next_player.name]
        return BoardState(
            next_player=self.next_player.name,
            players=[
                p.get_state(hidden=(p.name in show_hand))  # type: ignore
                for p in self.players],
            highest_bet=self.highest_bet,
            bet_holder=self.bet_holder.name if self.bet_holder is not None else None,
        )
