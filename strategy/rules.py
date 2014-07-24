from __future__ import division
from . import Rule, S, actions, conditions as conds, Condition
import operator as op

class Guard(Rule):
    def __init__(self, conditions, rule):
        self.rule = rule
        super(Guard, self).__init__(conditions=conditions,
                                    actions=[actions.Trigger(self.rule)],
                                    max_triggers=-1)



class LayTheOutsider(Rule):
    def __init__(self, liability, initial_price_from=4.5, price_from=3, price_to=6, time_from=-10, time_to=30, ratio=1.4):
        self.liability = liability
        self.initial_price_from = initial_price_from
        self.price_from = price_from
        self.price_to = price_to
        self.time_from = time_from
        self.time_to = time_to
        self.ratio = ratio
        super(LayTheOutsider, self).__init__(
            conditions=[
                conds.away_is_outsider,
                Condition(op.gt,
                          S.initial_lay_price(S.away),
                          S.const(self.initial_price_from)),
                conds.rise(S.lay_price(S.away),
                           S.initial_lay_price(S.away),
                           S.const(self.ratio)),
                Condition(S.between,
                          S.lay_price(S.away),
                          S.const(self.price_from),
                          S.const(self.price_to)),
                Condition(op.gt, S.volume, S.const(5000)),
                Condition(S.between,
                          S.minutes,
                          S.const(self.time_from),
                          S.const(self.time_to)),
                conds.valid_prices
            ],
            actions=[
                actions.LayAway(S.liability("LAY", self.liability))
            ],
            max_triggers=1)


class OneX(Rule):
    def __init__(self, liability, margin=.07, away_initial_price_from=3.5, time_from=-10, time_to=70, ratio=.8):
        self.liability = liability
        self.margin = margin
        self.away_initial_price_from = away_initial_price_from
        self.time_from = time_from
        self.time_to = time_to
        self.ratio = ratio

        super(OneX, self).__init__(
            conditions=[
                conds.away_is_outsider,
                conds.valid_prices,
                Condition(op.gt,
                          S.initial_lay_price(S.away),
                          S.const(self.away_initial_price_from)),

                conds.fall(S.back_price(S.home),
                           S.initial_back_price(S.home),
                           S.const(self.ratio)),

                conds.rise(S.back_price(S.const("The Draw")),
                           S.initial_back_price(S.const("The Draw")),
                           S.const(1.2)),

                Condition(op.gt, S.volume, S.const(10000)),

                Condition(S.between,
                          S.minutes,
                          S.const(self.time_from),
                          S.const(self.time_to))
            ],
            actions=[self.back_one_x],
            max_triggers=1
        )

    def back_one_x(self, strategy):
        home_price = strategy.prices[strategy.event.home]["BACK"]
        draw_price = strategy.prices["The Draw"]["BACK"]
        away_price = strategy.prices[strategy.event.away]["BACK"]
        home_prob = 1 / home_price
        draw_prob = 1 / draw_price
        s = home_prob + draw_prob
        home_stake = self.liability * (home_prob / s)
        draw_stake = self.liability * (draw_prob / s)
        total = home_stake * (home_price - 1) - draw_stake
        lay_stake = self.liability / (away_price - 1)

        if (total >= lay_stake) and (total >= self.liability * self.margin):
            actions.BackHome(S.const(home_stake))(strategy),
            actions.BackTheDraw(S.const(draw_stake))(strategy)
        elif lay_stake >= self.liability * self.margin:
            actions.LayAway(S.const(lay_stake))(strategy)

    def __call__(self, strategy):
        #print([c(strategy) for c in self.conditions])
        if self.can_trigger() and all([c(strategy) for c in self.conditions]):
            self.trigger_count += 1
            return self.actions
        return []


class BFD(Rule):

    def __init__(self, liability, margin=.07, ratio=.9):
        self.liability = liability
        self.margin = margin
        self.ratio = ratio

        super(BFD, self).__init__(
            conditions=[
                conds.away_is_outsider,
                conds.valid_prices,
                conds.fall(S.back_price(S.home),
                           S.initial_back_price(S.home),
                           S.const(self.ratio)),
                Condition(op.gt, S.volume, S.const(10000)),
            ],
            actions=[self.back_one_x],
            max_triggers=1
        )


    def back_one_x(self, strategy):
        home_price = strategy.prices[strategy.event.home]["BACK"]
        draw_price = strategy.prices["The Draw"]["BACK"]
        away_price = strategy.prices[strategy.event.away]["BACK"]
        home_prob = 1 / home_price
        draw_prob = 1 / draw_price
        s = home_prob + draw_prob
        home_stake = self.liability * (home_prob / s)
        draw_stake = self.liability * (draw_prob / s)
        total = home_stake * (home_price - 1) - draw_stake
        lay_stake = self.liability / (away_price - 1)

        if (total >= lay_stake) and (total >= self.liability * self.margin):
            actions.BackHome(S.const(home_stake))(strategy),
            actions.BackTheDraw(S.const(draw_stake))(strategy)
        elif lay_stake >= self.liability * self.margin:
            actions.LayAway(S.const(lay_stake))(strategy)

    def __call__(self, strategy):
        #print([c(strategy) for c in self.conditions])
        if self.can_trigger() and all([c(strategy) for c in self.conditions]):
            self.trigger_count += 1
            return self.actions
        return []


class BackTheDraw(Rule):
    def __init__(self, stake, time_from, time_to):
        self.stake = stake
        self.time_from = time_from
        self.time_to = time_to
        super(BackTheDraw, self).__init__(
            conditions=[
                Condition(op.eq, S.favorite, S.const("The Draw")),
                Condition(S.between, S.minutes, S.const(self.time_from), S.const(self.time_to))
            ],
            actions=[actions.BackTheDraw(S.const(self.stake))],
            max_triggers=1
        )


class LayTheDraw(Rule):
    def __init__(self, stake, time_from, time_to):
        self.stake = stake
        self.time_from = time_from
        self.time_to = time_to
        super(LayTheDraw, self).__init__(
            conditions=[
                Condition(op.eq, S.favorite, S.const("The Draw")),
                Condition(S.between, S.minutes, S.const(self.time_from), S.const(self.time_to)),
                Condition(S.between, S.lay_price(S.const("The Draw")), S.const(1.01), S.const(2))
            ],
            actions=[actions.LayTheDraw(S.const(self.stake))],
            max_triggers=1
        )



class Green(Rule):
    def __init__(self, conditions):
        super(Green, self).__init__(
            conditions=[conds.is_in] + conditions,
            actions=[
                actions.green_all,
                actions.AddPoint("Greened")
            ],
            max_triggers=1)

class GreenSelection(Rule):
    def __init__(self, selector, conditions):
        self.selector = selector
        super(GreenSelection, self).__init__(
            conditions=[conds.is_in] + conditions,
            actions=[actions.GreenSelection(self.selector)] + conditions,
            max_triggers=1)

class GreenAfterLastBet(Green):
    def __init__(self, time):
        self.time = time
        super(GreenAfterLastBet, self).__init__(
            conditions=[
                Condition(op.gt, S.minutes, lambda s: s.last_bet().minutes + self.time)
            ])


class GreenTotal(Green):
    def __init__(self, amount):
        self.amount = amount
        self.operator = op.gt if amount > 0 else op.lt
        super(GreenTotal, self).__init__(
            conditions=[
                Condition(self.operator, S.total, S.const(amount))
            ])

class GreenPrice(Green):
    def __init__(self, operator, selector, price):
        self.operator = operator
        self.selector = selector
        self.price = price
        super(GreenPrice, self).__init__(
            conditions=[
                Condition(self.operator, self.selector, S.const(self.price))
            ])


class GreenAfter(Green):
    def __init__(self, time):
        self.time = time
        super(GreenAfter, self).__init__(
            conditions=[
                Condition(op.gt, S.minutes, S.const(time))
            ])

class StopLoss(GreenTotal):
    def __init__(self, loss):
        super(StopLoss, self).__init__(-loss)


class Collect(GreenTotal):
    def __init__(self, profit):
        super(Collect, self).__init__(profit)

class BackTheFavorite(Rule):
    def __init__(self, stake, ratio=1, initial_price_to=2, price_from=0, price_to=100):
        self.stake = stake
        self.ratio = ratio
        self.price_from = price_from
        self.price_to = price_to
        self.initial_price_to = initial_price_to
        super(BackTheFavorite, self).__init__(
            conditions=[
                conds.home_is_favorite,
                conds.fall(S.back_price(S.home), S.initial_back_price(S.home), S.const(self.ratio)),
                Condition(S.between, S.back_price(S.favorite), S.const(self.price_from), S.const(self.price_to)),
                Condition(op.lt, S.initial_back_price(S.home), S.const(self.initial_price_to)),
                Condition(op.gt, S.volume, S.const(10000))],
            actions=[actions.BackHome(S.const(self.stake))],
            max_triggers=1)


class LayTheFavorite(Rule):
    def __init__(self, stake, until=50, price_from=4, price_to=6):
        self.stake = stake
        self.price_from = price_from
        self.price_to = price_to
        self.until = until
        super(LayTheFavorite, self).__init__(
            conditions=[
                Condition(op.lt, S.minutes, S.const(until)),
                conds.home_is_favorite,
                conds.Condition(S.between,
                                S.back_price(S.favorite),
                                S.const(self.price_from),
                                S.const(self.price_to)),
                Condition(op.gt, S.volume, S.const(10000))],
            actions=[actions.LayHome(S.const(self.stake))],
            max_triggers=10)


class BackWhenFalling(Rule):
    def __init__(self, stake, until=90, price_from=1.4, price_to=1.3):
        self.stake = stake
        self.until = until
        self.price_from = price_from
        self.price_to = price_to
        super(BackWhenFalling, self).__init__(
            conditions=[
                conds.home_is_favorite,
                Condition(S.between, S.back_price(S.favorite), S.const(self.price_from), S.const(self.price_to)),
                Condition(op.lt, S.minutes, S.const(self.until))
            ],
            actions=[actions.BackHome(S.const(self.stake))],
            max_triggers=1
        )



class LayLow(Rule):
    def __init__(self, stake, until=50, price_from=1.05, price_to=1.48):
        self.stake = stake
        self.until = until
        self.price_from = price_from
        self.price_to = price_to
        super(LayLow, self).__init__(
            conditions=[
                conds.home_is_favorite,
                Condition(S.between, S.lay_price(S.away), S.const(self.price_from), S.const(self.price_to)),
                Condition(op.lt, S.minutes, S.const(self.until)),
                Condition(op.gt, S.volume, S.const(10000))
            ],
            actions=[
                actions.LayAway(S.const(self.stake))],
            max_triggers=1)
