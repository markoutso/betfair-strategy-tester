from __future__ import division
import operator as op
from . import S
from . import Condition

def condition(*args, **kwargs):
    return lambda fn: Condition(fn, *args, **kwargs)

rise = lambda s1, s2, limit: Condition(op.gt, S.ratio(s1, s2), limit)
fall = lambda s1, s2, limit: Condition(op.lt, S.ratio(s1, s2), limit)
home_is_favorite = Condition(op.eq, S.home, S.favorite)
away_is_favorite = Condition(op.eq, S.away, S.favorite)
away_is_outsider = Condition(op.eq, S.away, S.outsider)
first_half = Condition(op.lt, S.minutes, 50)
is_in = Condition(lambda bets: len(bets) > 0, S.bets)
has_point = lambda name: Condition(op.contains, S.points, S.const(name))

@condition(S.identity)
def valid_prices(s):
    return all(d[sel][bet_type] != 0
               for d in (s.event.initial_prices, s.prices)
               for sel in s.event.runners
               for bet_type in ("BACK", "LAY"))


