from __future__ import division
import operator as op

def const(c):
    return lambda s: c

def identity(x):
    return x

# a -> a -> a -> Bool
def between(x, a, b):
    return a <= x <= b

def plus(a, b):
    return lambda s: a(s) + b(s)

def minus(a, b):
    return lambda s: a(s) + b(s)

def minutes(s):
    return s.minutes

def time(s):
    return s.current_time

def value_at(name, selector):
    return lambda s: selector(s.points[name])

def seconds(selector):
    return lambda s: selector(s).seconds

def points(s):
    return s.points

def seconds_after_point(name):
    return lambda s: (s.current_time - s.points[name].current_time).seconds

def last_bet_at(bet_type=None):
    lambda selector: lambda s: (s.last_bet(selector(s), bet_type).time - s.event.actual_off).total_seconds() / 60

def last_bet(bet_type=None):
    return lambda selector: lambda s: s.last_bet(selector(s), bet_type)

def home(s):
    return s.event.home

def away(s):
    return s.event.away

def event_id(s):
    return s.event.event_id

def favorite(s):
    return s.event.favorite

def outsider(s):
    return s.event.outsider

def initial_price(bet_type):
    return lambda selector: lambda s: s.event.initial_prices[selector(s)][bet_type]

def initial_difference(s1, s2):
    return lambda s: (s.event.initial_prices[s1(s)]["BACK"] -
                      s.event.initial_prices[s2(s)]["BACK"])

def price(bet_type):
    return lambda selector: lambda s: s.prices[selector(s)][bet_type]

def getattr(selector, attr):
    return lambda s: getattr(selector(s), attr)

def bets(s):
    return s.bets

def liability(bet_type, amount):
    return lambda price: amount if bet_type == "BACK" else amount / (price - 1)

def is_in(s):
    return len(s.bets) > 0

back_price = price("BACK")
lay_price = price("LAY")
initial_back_price = initial_price("BACK")
initial_lay_price = initial_price("LAY")
last_back_at = last_bet_at("BACK")
last_lay_at = last_bet_at("LAY")
the_draw = const("The Draw")

def total(s):
    _, total = s.green_check_all()
    return total

def volume(s):
    return s.volume

def ratio(a, b):
    return lambda s: a(s) / b(s)

def minimum(*args):
    l = len(args)

    if l == 0:
        raise Exception("minimum of zero parameters")

    if l == 1:
        return lambda s: min(args[0](s))
    else:
        return lambda s: min([arg(s) for arg in args])

def maximum(*args):
    l = len(args)

    if l == 0:
        raise Exception("minimum of zero parameters")

    if l == 1:
        return lambda s: max(args[0](s))
    else:
        return lambda s: max([arg(s) for arg in args])
