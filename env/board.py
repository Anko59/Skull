from .player import Player, Card
from typing import List, Optional
from dataclasses import dataclass


class MoveIsNotLegal(Exception):
    pass


class GameIsOver(Exception):
    pass


@dataclass
class Action:
    pass


@dataclass
class PlayCardAction(Action):
    card: str


@dataclass
class LoseCardAction(Action):
    card: str


@dataclass
class RevealCardAction(Action):
    player_name: str


@dataclass
class BetAction(Action):
    amount: int


@dataclass
class PassAction(Action):
    pass


class Board:
    def __init__(self, player_names: List[str]):
        self.players: List[Player] = [Player(name=x) for x in player_names]
        self.bet_holder: Optional[Player] = None
        self.highest_bet: int = 0
        self._cards_shown: int = 0
        self.winner: Optional[Player] = None
        self.next_player: Player = self.players[0]
        self.legal_moves: List[Action] = self._get_legal_moves(self.next_player)

    def _has_anyone_won(self) -> bool:
        return any([player.points > 1 for player in self.players])

    def _are_more_than_two_players_alive(self) -> bool:
        return sum([int(player.alive) for player in self.players]) > 1

    def _is_round_over(self) -> bool:
        return not any([player.is_playing for player in self.players])

    def _nbr_cards_on_board(self) -> int:
        return sum([len(player.cards_stack) for player in self.players])

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
        self._cards_shown = 0

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
            cards_shown = max(self._cards_shown, len(player.cards_revealed))
            for p in self.players:
                if p.name == action.player_name:
                    card = next(p.reveal_stack())  # type: ignore
                    if card == Card.SKULL:
                        player.is_playing = False
                        player.remove_card()
                    else:
                        cards_shown += 1
                        self._cards_shown = cards_shown
                        if cards_shown == self.highest_bet:
                            player.is_playing = False
                            player.points += 1

        elif isinstance(action,  LoseCardAction):
            player.collect_cards()
            player.cards_hand.remove(action.card)
            if len(player.cards_hand) == 0:
                player.alive = False
            player.is_playing = False

        elif isinstance(action, PassAction):
            player.is_playing = False

    def push(self, action: Action):
        if self.winner is not None:
            raise GameIsOver()
        if action not in self.legal_moves:
            raise MoveIsNotLegal()
        self._process_action(self.next_player, action)
        if self._is_round_over():
            self._start_round()
        else:
            self.next_player = self.players[
                (self.players.index(self.next_player) + 1) % len(self.players)
            ]
        self.legal_moves = self._get_legal_moves(self.next_player)
        if not self._are_more_than_two_players_alive():
            self.winner = [x for x in self.players if x.alive][0]  # type: ignore
        elif self._has_anyone_won():
            self.winner = [x for x in self.players if x.points > 1][0]  # type: ignore

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

    def get_state(self) -> dict:
        return {
            "NEXT_PLAYER": self.next_player.name,
            "PLAYER_ORDER": [p.name for p in self.players],
            "BET_HOLDER": self.bet_holder.name if self.bet_holder is not None else None,
            "HIGHEST_BET": self.highest_bet,
            "BOARD": {
                p.name: {
                    "HAND": p.cards_hand
                    if p == self.next_player
                    else [Card.hidden for x in p.cards_hand],
                    "STACK": p.cards_stack
                    if p == self.next_player
                    else [Card.hidden for x in p.cards_stack],
                    "POINTS": p.points,
                    "REVEALED": p.cards_revealed,
                }
                for p in self.players
            },
        }
