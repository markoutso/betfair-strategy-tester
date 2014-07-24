from __future__ import division
from __future__ import unicode_literals
from collections import defaultdict
import copy
import operator as op
import datetime
from fuzzywuzzy import process
import locale

# [[a]] -> [a]
def concat(ll):
    return [i for l in ll for i in l]

def f2s(f):
    return locale.format("%.2f", f)

# (a -> b) -> a -> b
def call_unpacked(fn, args):
    if isinstance(args, dict):
        return fn(**args)
    else:
        return fn(*args)

# Timedelta -> Float
def to_minutes(delta):
    return delta.total_seconds() / 60

class Event(object):

    # Class -> Entry-> Event
    @classmethod
    def from_entry(cls, entry):
        time_off = entry['actual_off']
        home, away = entry['home'], entry['away']
        desc = " v ".join((home, away))
        obj = cls(entry['event_id'], entry['market'], desc, time_off, [home, away, "The Draw"])
        obj.entry = entry
        return obj

    # Int -> Str -> [Str] -> Maybe Dict -> Event
    def __init__(self, event_id, market, description, time_off, runners, prices=None):
        """
        prices (dict): {key: runner, value: price}
        """
        self.description = description
        self.home, self.away = description.split(" v ")
        self.time_off = time_off
        self.event_id = event_id
        self.market = market
        self.runners = runners
        if prices:
            self.initial_prices = prices
        else:
            self.update_price_selections(runners)

    # Event -> [Str] -> *
    def fix_selections(self, selections):
        runners = selections.values()
        self.home, _ = process.extractOne(self.home, runners)
        self.away, _ = process.extractOne(self.away, runners)
        self.update_price_selections(runners)

    def update_price_selections(self, runners):
        self.runners = runners
        self.initial_prices = {r: {"BACK": 0, "LAY": 0} for r in runners}

    # Event -> Dict -> *
    def update_prices(self, prices):
        for runner in prices:
            for t in ("BACK", "LAY"):
                self.initial_prices[runner][t] = prices[runner][t]

    # Event -> Str
    @property
    def favorite(self):
        return min(self.runners, key= lambda r: self.initial_prices[r]["BACK"])

    # Event -> Str
    @property
    def outsider(self):
        return max(self.runners, key= lambda r: self.initial_prices[r]["BACK"])

    # Event -> Str
    def __str__(self):
        return "%s (%s)" % (" v ".join(self.runners), self.market)



class Point(object):

    # Strategy -> Point
    def __init__(self, strategy):
        self.prices = copy.deepcopy(strategy.prices)
        self.bet_info = self.copy_bet_info(strategy)
        self.current_time = strategy.current_time
        self.volume = strategy.volume
        self.event = strategy.event

    def copy_bet_info(self, strategy):
        return {
            s: {bt: [b for b in strategy.bet_info[s][bt]]
                for bt in ("BACK", "LAY")}
            for s in strategy.bet_info
        }


class Bet(object):
    counter = 0

    @classmethod
    def sort(cls, bets, key="counter"):
        return sorted(bets, key=op.attrgetter(key))

    # Int -> Str -> Str -> Float -> Float -> Bet
    def __init__(self, bet_type, event, selection, stake, price, time=None):
        self.bet_type = bet_type
        self.event = event
        self.selection = selection
        self.stake = round(stake, 2)
        self.price = price
        self.time = time or datetime.datetime.now()
        self.__class__.counter += 1
        self.counter = Bet.counter

    # Bet -> Float
    def green_stake(self, price):
        """stake that needs to be placed to an opposite bet in order to green selection"""
        return (self.stake * self.price) / price

    @property
    def minutes(self):
        return to_minutes(self.time - self.event.time_off)

    # Bet -> Str
    def __str__(self):
        return "(%s, %s, %s, %s, %s')" % (self.bet_type, self.selection, f2s(self.stake), f2s(self.price), int(self.minutes))

class BackBet(Bet):

    # Int ->  Str -> Float -> Float -> BackBet
    def __init__(self, event, selection, stake, price, time=None):
        super(BackBet, self).__init__("BACK", event, selection, stake, price, time)

    # BackBet -> Float
    @property
    def liability(self):
        return self.stake

    # BackBet -> Float
    @property
    def profit(self):
        return self.stake * (self.price - 1)

    # BackBet -> LayBet
    def green(self, price):
        return LayBet(self.event, self.selection, self.green_stake(price), price)

    # BackBet -> Str -> Float
    def total_with_winner(self, selection):
        """selection (str): winning selection"""
        if selection == self.selection:
            return self.profit
        else:
            return -self.liability


class LayBet(Bet):

    # Int ->  Str -> Float -> Float -> LayBet
    def __init__(self, event, selection, stake, price, time=None):
        super(LayBet, self).__init__("LAY", event, selection, stake, price, time)

    # LayBet -> Float
    @property
    def liability(self):
        return self.stake * (self.price - 1)

    # LayBet -> Float
    @property
    def profit(self):
        return self.stake

    # LayBet -> BackBet
    def green(self, price):
        return BackBet(self.event, self.selection, self.green_stake(price), price)

    # Bet -> Str -> Float
    def total_with_winner(self, selection):
        """selection (str): winning selection"""
        if selection == self.selection:
            return -self.liability
        else:
            return self.profit

class Condition(object):

    def __init__(self, fn, *params, **kw_params):
        self.fn = fn
        self.params = params
        self.kw_params = kw_params


    # Condition ->  Strategy -> ([a], Dict Str b)
    def get_parameters(self, strategy):
        params = [v(strategy) for v in self.params]
        kw_params = {n: v(strategy) for n, v in self.kw_params.items()}
        return params, kw_params

    # Condition ->  Strategy -> Bool
    def __call__(self, strategy):
        params, kw_params = self.get_parameters(strategy)
        return self.fn(*params, **kw_params)

    # Condition -> Condition -> Condition
    def __or__(self, other):
        return Condition(lambda s: self(s) or other(s), S.identity)

    # Condition -> Condition -> Condition
    def __and__(self, other):
        return Condition(lambda s: self(s) and other(s), S.identity)

    # Condition -> Condition
    def __invert__(self):
        return Condition(lambda s: not self(s), S.identity)

class Action(object):

    def __init__(self, fn):
        self.fn = fn

    # Action -> Strategy -> a
    def __call__(self, strategy):
        # do stuff
        return self.fn(strategy)

class Rule(object):
    always = []

    # [Condition] -> [Action] -> Int -> Rule
    def __init__(self, conditions, actions, max_triggers=-1):
        """
        max_triggers (int) : maximum number of allowed triggers (default: -1 = infinity)
        """
        self.conditions = conditions
        self.actions = actions
        self.max_triggers = max_triggers
        self.trigger_count = 0

    # Rule -> Bool
    def can_trigger(self):
        return self.max_triggers < 0 or self.trigger_count < self.max_triggers

    # Rule -> Strategy -> [Action]
    def __call__(self, strategy):
        if self.can_trigger() and all(c(strategy) for c in self.conditions):
            self.trigger_count += 1
            return self.actions
        return []


class Strategy(object):

    # [Rule] -> Event ->  Strategy
    def __init__(self, rules, event):
        self.rules = rules
        self.event = event
        self.current_time = 0
        self.volume = 0

        self.prices = {s: {"BACK": 0, "LAY": 0} for s in event.runners}
        # TODO: CHECK VALIDITY!
        # self.prices = dict(event.initial_prices)
        # e.g.
        # {
        #     'Liverpool': {'BACK': 1.5': 'LAY': 1.52 },
        #     'Other': {'BACK': 4.1, 'LAY': 4.2},
        # }

        # Dict Str (Dict Str [Bet])
        self.bet_info = defaultdict(lambda: defaultdict(list))
        # e.g.
        # {
        #     'Liverpool': {'BACK': [b1, b2], 'LAY': [b1, b2]},
        #     'Other': {'BACK': [b1, b2], 'LAY': [b1, b2]},
        # }

        self.times = {s: 0 for s in event.runners}

        # Dict Str Point
        self.points = {}

        self.entry = {}

        self.entries_iter = None

    # Strategy -> [Entry] ->  [Bet] *
    def run(self, entries):
        self.entries_iter = iter(entries)
        try:
            while True:
                self.apply(next(self.entries_iter))
        except StopIteration:
            pass
        return self.bets
        # return concat([self.apply(e) for e in entries])

    # Strategy -> Entry ->  *
    def apply(self, entry):
        self.update(entry)
        results = []
        for r in self.rules:
            actions = r(self)
            for a in actions:
                results.append(a(self))
        return filter(bool, results)


    # Stategy -> Str -> *
    def add_point(self, name):
        self.points[name] = Point(self)

    # Strategy -> Entry -> *
    def update(self, entry):
        """Updates strategy with live information from entries"""
        selection, odds, time = entry['selection'], entry['odds'], entry['latest_taken']
        for t in ("BACK", "LAY"):
            self.prices[selection][t] = odds
        self.current_time = time
        self.times[selection] = time
        self.volume += entry['volume']
        self.entry = entry

    # Strategy -> *
    def fix_timing(self, selection=None):
        time = max(self.times.values())
        if selection is None:
            while any([t < time for t in self.times.values()]):
                self.update(next(self.entries_iter))
        else:
            while self.times[selection] < time:
                self.update(next(self.entries_iter))


    # Strategy -> Str -> Float
    def back_price(self, selection):
        return self.prices[selection]["BACK"]

    # Strategy -> Str -> Float
    def lay_price(self, selection):
        return self.prices[selection]["LAY"]

    # Strategy -> Bet -> *
    def place(self, bet):
        bet.time = self.entry['latest_taken']
        self.bet_info[bet.selection][bet.bet_type].append(bet)

    # Strategy -> Float
    @property
    def minutes(self):
        return to_minutes(self.current_time - self.event.time_off)

    # Strategy -> [Bet]
    @property
    def bets(self):
        return concat([self.bet_info[sel][t] for sel in self.bet_info for t in self.bet_info[sel]])

    # Strategy -> [Str]
    @property
    def selections(self):
        return self.bet_info.keys()

    # Strategy -> Str
    @property
    def winner(self):
        return min([(s, self.prices[s]["BACK"]) for s in self.prices], key=op.itemgetter(1))[0]

    # Strategy -> Str -> Maybe Bet
    def average_bet(self, selection, bet_type):
        cls = BackBet if bet_type == "BACK" else LayBet
        bets = self.bet_info[selection][bet_type]
        if len(bets) > 0:
            total_product = sum([b.price * b.stake for b in bets])
            total_stake = sum([b.stake for b in bets])
            average_price = total_product / total_stake
            return cls(self.event, selection, total_stake, average_price)
        else:
            return None

    # Strategy -> Maybe String -> Maybe String -> [Bet]
    def get_bets(self, selection=None, bet_type=None):
        if selection:
            if bet_type:
                return self.bet_info[selection][bet_type]
            else:
                return self.selection_bets(selection)
        else:
            return self.bets

    # Strategy -> Maybe Bet
    def last_bet(self, selection=None, bet_type=None):
        bets = self.get_bets(selection, bet_type)
        if len(bets) > 0:
            return max(bets, key=op.attrgetter("counter"))
        else:
            return None

    # Strategy -> Str -> [Bet]
    def selection_bets(self, selection):
        return concat([self.bet_info[selection][t] for t in self.bet_info[selection]])

    # Strategy -> String -> [BackBet]
    def selection_back_bets(self, selection):
        return self.bet_info[selection]["BACK"]

    # Strategy -> String -> [LayBet]
    def selection_lay_bets(self, selection):
        return self.bet_info[selection]["LAY"]

    # Strategy -> Str -> Float
    def total_if_wins(self, selection):
        """Total for the bets of a (only one) given selection if it wins"""
        winnings = sum([b.profit for b in self.selection_back_bets(selection)])
        losses = sum([b.liability for b in self.selection_lay_bets(selection)])
        return winnings - losses

    # Strategy -> Str -> Float
    def total_if_looses(self, selection):
        """Total for the bets of a (only one) given selection if it looses"""
        winnings = sum([b.profit for b in self.selection_lay_bets(selection)])
        losses = sum([b.liability for b in self.selection_back_bets(selection)])
        return winnings - losses

    # Strategy -> Str -> Float
    def liability(self, selection):
        return abs(min(0, self.total_if_wins(selection), self.total_if_looses(selection)))

    # Strategy -> Str -> Float
    def total_with_winner(self, selection):
        """selection (str): winning selection"""
        return sum([b.total_with_winner(selection) for b in self.bets])

    # Strategy -> Bool
    @property
    def is_greened(self):
        return all(abs(self.total_if_wins(s) - self.total_if_looses(s)) < .5 for s in self.selections)

    # Strategy -> Float
    @property
    def total(self):
        return self.total_with_winner(self.winner)

    # Strategy -> ([Maybe Bet], Float)
    def green_check_all(self):
        bets = []
        total = 0
        for s in self.selections:
            b, t = self.green_check(s)
            if b is not None:
                total += t
                bets.append(b)
        return (bets, total)

    # Strategy -> Str -> Float -> (Maybe Bet, Float)
    def green_check(self, selection):
        total_if_wins = self.total_if_wins(selection)
        total_if_looses = self.total_if_looses(selection)
        outcome = total_if_looses - total_if_wins
        if outcome < 0:
            price = self.lay_price(selection)
            cls = LayBet
        else:
            price = self.back_price(selection)
            cls = BackBet

        if price != 0:
            stake = abs(outcome) / price
            total = total_if_looses + stake if outcome < 0 else total_if_wins + stake * (price - 1)
            bet = cls(self.event, selection, stake, price)
            return (bet, total)
        else:
            return (None, 0)

    # Strategy -> [Bet]
    def green_all(self):
        if not self.is_greened:
            [self.green_selection(s) for s in self.selections]
        return self.bets

    # Strategy -> Str -> Float -> Float *
    def green_selection(self, selection):
        """selection (str): the selection to be greened"""
        bet, total = self.green_check(selection)
        if bet is not None:
            self.place(bet)
        return total
