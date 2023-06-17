from .player import Player, PlayerState
from .card import Card
from .actions import (
    Action,
    PlayCardAction,
    BetAction,
    RevealCardAction,
    LoseCardAction,
    PassAction,
)
from typing import List, Optional, Union
from copy import deepcopy
from dataclasses import dataclass
from logging import getLogger


logger = getLogger()


class MoveIsNotLegal(Exception):
    pass


class GameIsOver(Exception):
    pass


class GameHasNotStarted(Exception):
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
        self.legal_moves: List[Action] = self._get_legal_moves()
        self.action_record: List[str] = []
        self.state_record: List[BoardState] = []

    def _has_anyone_won(self) -> bool:
        return any([player.points > 1 for player in self.players])

    def _is_more_than_one_player_alive(self) -> bool:
        return sum([int(player.alive) for player in self.players]) > 1

    def _is_round_over(self) -> bool:
        return not any([player.is_playing for player in self.players])

    def _nbr_cards_on_board(self) -> int:
        return sum([len(player.cards_stack) for player in self.players])

    def _cards_shown(self) -> int:
        return sum([len(player.cards_revealed) for player in self.players])

    def _start_round(self):
        logger.debug('Starting round')
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
        logger.debug(f'First player of round is {self.next_player.name}')
        self.bet_holder = None
        self.highest_bet = 0

    def _process_action(self, player: Player, action: Action):
        if isinstance(action, PlayCardAction):
            logger.debug(f'Player {player.name} played card {action.card.value}')
            if action.card == Card.FLOWER:
                player.play_flower()
            elif action.card == Card.SKULL:
                player.play_skull()
            else:
                raise MoveIsNotLegal()

        elif isinstance(action, BetAction):
            logger.debug(f'Player {player.name} bet {action.amount}')
            self.bet_holder = player
            self.highest_bet = action.amount

        elif isinstance(action, RevealCardAction):
            for p in self.players:
                if p.name == action.player_name:
                    card = next(p.reveal_stack())  # type: ignore
                    logger.debug(
                        f'Player {player.name} revealed the card of {p.name}'
                        f' and it is a {card.value}')
                    if card == Card.SKULL:
                        player.is_playing = False
                        player.remove_card()
                        logger.debug(f'Player {player.name} lost a random card')
                    else:
                        if self._cards_shown() == self.highest_bet:
                            player.is_playing = False
                            logger.debug(f'Player {player.name} earned a point')
                            player.points += 1

        elif isinstance(action, LoseCardAction):
            logger.debug(f'Player {player.name} chose to lose {action.card.value}')
            player.collect_cards()
            player.cards_hand.remove(action.card)
            if len(player.cards_hand) == 0:
                logger.debug(f'Player {player.name} got eliminated')
                player.alive = False
            player.is_playing = False

        elif isinstance(action, PassAction):
            player.is_playing = False

    def winner(self) -> Optional[Player]:
        if not self._is_more_than_one_player_alive():
            winner = [x for x in self.players if x.alive][0]
            logger.debug(f'We have a winner: {winner}')
            return winner
        elif self._has_anyone_won():
            winner = [x for x in self.players if x.points > 1][0]
            logger.debug(f'We have a winner: {winner}')
            return winner
        else:
            return None

    def push(self, action: Union[Action, str]):
        if self.winner() is not None:
            raise GameIsOver()
        if isinstance(action, str):
            action = Action.from_notation(action)
        if action not in self.legal_moves:
            raise MoveIsNotLegal()
        self.state_record.append(deepcopy(self.get_state(show_hand=[p.name for p in self.players])))
        self.action_record.append(str(action))
        self._process_action(self.next_player, action)
        if self._is_round_over():
            self._start_round()
        else:
            self.next_player = self.players[
                (self.players.index(self.next_player) + 1) % len(self.players)
            ]
        self.legal_moves = self._get_legal_moves()

    def pop(self):
        if len(self.state_record) == 0:
            raise GameHasNotStarted()
        last_state = self.state_record[-1]
        self.load_state(last_state)
        self.state_record = self.state_record[:-1]
        self.action_record = self.action_record[:-1]

    def forward(self, action: Union[Action, str]):
        self.push(action)
        if len(self.legal_moves) == 1:
            self.forward(self.legal_moves[0])

    def load_state(self, state: BoardState):
        self.players = [
            Player.from_state(state=player_state)
            for player_state in state.players
        ]

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
        self.legal_moves = self._get_legal_moves()
        logger.debug(f'State loaded, next player is {self.next_player.name}')

    def _get_legal_moves_cards_and_bet_stage(self) -> List[Action]:
        player = self.next_player
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
        logger.debug(f'Legal moves {legal_actions}')
        return legal_actions
    
    def _get_legal_moves_reveal_cards_stage(self) -> List[Action]:
        player = self.next_player
        # Starting with his own cards
        for card in player.reveal_stack():
            logger.debug(f'Player {player.name} reveald card {card.value} from his stack')
            if card == Card.SKULL:
                # Auto Skulled
                player.collect_cards()
                if player.can_play_flower():
                    return [LoseCardAction(Card.FLOWER), LoseCardAction(Card.SKULL)]
                else:
                    return [LoseCardAction(Card.SKULL)]

            if len(player.cards_revealed) == self.highest_bet:
                # Victory by returning only own cards
                logger.debug(f'Player {player.name} earned a point')
                player.points += 1
                return [PassAction()]

        # Player can return cards from every player
        # except himself if they have played more cards then they have shown
        return [
            RevealCardAction(opponent.name)
            for opponent in self.players
            if opponent != player and len(opponent.cards_stack) > 0
            ]


    def _get_legal_moves(self) -> List[Action]:  # type: ignore
        player = self.next_player
        if not player.alive or not player.is_playing:
            return [PassAction()]
        if self.bet_holder != player:
            # Player did not place the highest bet
            return self._get_legal_moves_cards_and_bet_stage()
        else:
            # One round has passed and player still has the highest bets
            # He can show cards
            return self._get_legal_moves_reveal_cards_stage()

    def get_state(
        self, show_hand: Union[List[str], str] = "next_player"
    ) -> BoardState:
        if show_hand == "next_player":
            show_hand = [self.next_player.name]
        return BoardState(
            next_player=self.next_player.name,
            players=[
                p.get_state(hidden=(p.name not in show_hand))  # type: ignore
                for p in self.players],
            highest_bet=self.highest_bet,
            bet_holder=self.bet_holder.name if self.bet_holder is not None else None,
        )

    @classmethod
    def from_state(self, state: BoardState):
        new_board = Board(player_names=[])
        new_board.load_state(state)
        new_board.legal_moves = new_board._get_legal_moves()
        return new_board
