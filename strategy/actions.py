from . import Action, S, BackBet, LayBet

@Action
def green_all(strategy):
    strategy.green_all()

@Action
def fix_timing(strategy):
    strategy.fix_timing()

class AddPoint(Action):
    def __init__(self, name):
        self.name = name

    def fn(self, strategy):
        strategy.fix_timing()
        strategy.add_point(self.name)


class GreenSelection(Action):
    def __init__(self, selector):
        self.selector = selector

    def fn(self, strategy):
        strategy.green_selection(self.selector(strategy))

class Trigger(Action):
    def __init__(self, rule):
        self.rule = rule

    def fn(self, strategy):
        return filter(bool, [a(strategy) for a in self.rule(strategy)])


class BetOnSelection(Action):
    def __init__(self, bet_type, selector, stake_fn):
        self.bet_type = bet_type
        self.selector = selector
        self.stake_fn = stake_fn

    def fn(self, strategy):
        selection = self.selector(strategy)
        stake = self.stake_fn(strategy.prices[selection][self.bet_type])
        if self.bet_type == "BACK":
            strategy.place(
                BackBet(strategy.event,
                        selection, stake,
                        strategy.prices[selection]["BACK"]))
        else:
            strategy.place(
                LayBet(strategy.event,
                        selection, stake,
                        strategy.prices[selection]["LAY"]))

class BackHome(BetOnSelection):
    def __init__(self, stake_fn):
        super(BackHome, self).__init__("BACK", S.home, stake_fn)

class BackAway(BetOnSelection):
    def __init__(self, stake_fn):
        super(BackAway, self).__init__("BACK", S.away, stake_fn)

class LayHome(BetOnSelection):
    def __init__(self, stake_fn):
        super(LayHome, self).__init__("LAY", S.home, stake_fn)

class LayAway(BetOnSelection):
    def __init__(self, stake_fn):
        super(LayAway, self).__init__("LAY", S.away, stake_fn)

class BackTheDraw(BetOnSelection):
    def __init__(self, stake_fn):
        super(BackTheDraw, self).__init__("BACK", S.const("The Draw"), stake_fn)

class LayTheDraw(BetOnSelection):
    def __init__(self, stake_fn):
        super(LayTheDraw, self).__init__("LAY", S.const("The Draw"), stake_fn)
