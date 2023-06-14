from .player import Player, Card
from typing import List
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
class ShowCardAction(Action):
    player_name: str


@dataclass
class BetAction(Action):
    amount: int


@dataclass
class PassAction(Action):
    pass


class Env:
    def __init__(self, player_names: List[str]):
        self.players = [Player(name=x) for x in player_names]
        self.bet_holder: str = self.players[0].name
        self.highest_bet: int = 0
        self.cards_shown: int = 0
        self.winner = None
        self.next_player = self.players[0]
        self.legal_moves = self.get_legal_moves(self.next_player)

    def has_anyone_won(self) -> bool:
        return any([player.points > 1 for player in self.players])

    def are_more_than_two_players_alive(self) -> bool:
        return sum([int(player.alive) for player in self.players]) > 1

    def is_round_over(self) -> bool:
        return not any([player.is_playing for player in self.players])

    def nbr_cards_on_board(self) -> int:
        return sum([len(player.cards_stack) for player in self.players])

    def start_round(self):
        # Collect cards
        for player in self.players:
            player.collect_cards()
            if player.alive:
                player.is_playing = True
            if player.name == self.bet_holder:
                index = self.players.index(player)

        # Last bet_holder is next first player
        self.players = self.players[index:] + self.players[:index]
        self.next_player = self.players[0]
        self.bet_holder = None
        self.highest_bet = 0
        self.cards_shown = 0

    def process_action(self, player: Player, action: Action):
        if type(action) == PlayCardAction:
            if action.card == Card.FLOWER:
                player.play_flower()
            else:
                player.play_skull()

        elif type(action) == BetAction:
            self.bet_holder = player.name
            self.highest_bet = action.amount

        elif type(action) == ShowCardAction:
            cards_shown = max(self.cards_shown, len(player.cards_revealed))
            for p in self.players:
                if p.name == action.player_name:
                    card = next(p.reveal_stack())  # type: ignore
                    if card == Card.SKULL:
                        player.is_playing = False
                        player.remove_card()
                    else:
                        cards_shown += 1
                        self.cards_shown = cards_shown
                        if cards_shown == self.highest_bet:
                            player.is_playing = False
                            player.points += 1

        elif type(action) == LoseCardAction:
            player.collect_cards()
            player.cards_hand.remove(action.card)
            if len(player.cards_hand) == 0:
                player.alive = False
            player.is_playing = False

        elif type(action) == PassAction:
            player.is_playing = False

    def push(self, action: Action):
        if self.winner is None:
            if action not in self.legal_moves:
                raise MoveIsNotLegal()
            self.process_action(self.next_player, action)
            if self.is_round_over():
                self.start_round()
            else:
                self.next_player = self.players[
                    (self.players.index(self.next_player) + 1) % len(self.players)
                ]
            self.legal_moves = self.get_legal_moves(self.next_player)
            if not self.are_more_than_two_players_alive():
                self.winner = [x for x in self.players if x.alive][0]  # type: ignore
            elif self.has_anyone_won():
                self.winner = [x for x in self.players if x.points > 1][0]  # type: ignore
        else:
            raise GameIsOver()

    def get_legal_moves(self, player: Player) -> List[Action]:  # type: ignore
        if not player.alive or not player.is_playing:
            return [PassAction()]
        if self.bet_holder != player.name:
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
                for i in range(self.highest_bet + 1, self.nbr_cards_on_board() + 1):
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
                ShowCardAction(opponent.name)
                for opponent in self.players
                if opponent != player and len(opponent.cards_stack) > 0
            ]

    def get_state(self) -> dict:
        return {
            "NEXT_PLAYER": self.next_player,
            "PLAYERS_ORDER": [p.name for p in self.players],
            "BET_HOLDER": self.bet_holder,
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
