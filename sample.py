from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import datetime
import operator as op
import psycopg2.extras
import psycopg2
import psycopg2.extensions
import time
import itertools
import locale
from strategy import Strategy, Event, Rule, rules, S, Condition, actions, conditions as conds
import sys
import codecs

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)
#locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())
locale.setlocale(locale.LC_ALL, ('en_US', 'UTF-8'))

def with_debug(fn):
    try:
        return fn()
    except Exception as e:
        print(e)
        import pdb;pdb.set_trace()


def f2s(f):
    return locale.format("%.2f", f)


# Int -> Int -> [[Entries]]
def create_events(offset, limit):
    conn = psycopg2.connect("dbname=bf user=user password=password host=localhost")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    events_sub_query = """select event_id from (
		select entry.event_id
		from entry inner join event on (entry.event_id=event.event_id)
                where event.market='Match Odds'
                and actual_off is not null
                --and sub_cat !~* 'cup' and cat !~* 'cup'
                --and home !~* '(19)|(20)(21)'
		group by entry.event_id
                having count(*) > 20
                offset %s
		limit %s) as bar""" % (offset, limit)
    sql = """Select entry.*, event.*
                    from entry
                    inner join (%s) as foo on (foo.event_id=entry.event_id)
                    inner join event on event.event_id = entry.event_id
                    -- where in_play='IP' and number_bets > 3
                    where number_bets > 3
                    order by entry.event_id, in_play desc, latest_taken asc""" % events_sub_query
    cursor.execute(sql)

    it = itertools.groupby(cursor, op.itemgetter("event_id"))
    while True:
        _, group = next(it)
        entries = list(group)
        while len(set([e['selection'] for e in entries if e['in_play'] == 'IP'])) != 3:
            _, group = next(it)
            entries = list(group)
        yield entries

# Int -> Event
def create_event(event_id):
    conn = psycopg2.connect("dbname=bf_2011a user=postgres password=qwe123 host=localhost")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    sql = """Select entry.*, event.*
                    from entry
                    inner join event on event.event_id = entry.event_id
                    where in_play='IP' and number_bets > 3 and event.event_id=%s
                    order by latest_taken asc""" % event_id
    cursor.execute(sql)
    yield [r for r in cursor]


def first_price(entries, selection):
    return next(e['odds'] for e in entries if e['selection'] == selection and e['in_play'] == 'IP')

def avg(*args):
    iterable = args[0] if len(args) == 1 else args
    if len(iterable) == 0:
        return 0
        # raise Exception("average of empty iterable")
    return sum(iterable) / float(len(iterable))

# type Result = (Str, Str, Int, Float, Str, Str)
# [Entries] -> (Event -> Strategy) -> Result
def test_event(entries, strat):
    first = entries[0]
    event = Event.from_entry(first)
    selections = {e['selection_id']: e['selection'] for e in entries}
    event.fix_selections(selections)

    strategy = strat(event)
    # prices = defaultdict(list)

    for k, g in itertools.groupby(entries, op.itemgetter("in_play")):
        if k == "PE":
            entries = list(g)
            for e in entries:
                # FIXME: prices[e['selection']].append(e['odds'])
                strategy.volume += e['volume']
        else:
            entries = list(g)
            try:
                home_price = first_price(entries, event.home)
                away_price = first_price(entries, event.away)
                draw_price = first_price(entries, "The Draw")
            except Exception as e:
                raise Exception("Not enough valid prices for event %s" % event.event_id)

            event.update_prices({event.home: {"BACK": home_price, "LAY": home_price},
                                 event.away: {"BACK": away_price, "LAY": away_price},
                                "The Draw": {"BACK": draw_price, "LAY": draw_price}})
            strategy.run(entries)

    prices = (strategy.event.initial_prices[strategy.event.home]["BACK"],
              strategy.event.initial_prices[strategy.event.away]["BACK"],
              strategy.event.initial_prices["The Draw"]["BACK"])
    return (
        strategy.event.home,
        strategy.event.away,
        strategy.event.event_id,
        strategy.total,
        ["%s" % b for b in strategy.bets],
        strategy.winner,
        ";".join(map(str, prices)),
        strategy.volume
    )

# Timedelta -> Str
def time_format(t):
    return str(datetime.timedelta(seconds=int(t)))


# Event -> Strategy
lo = lambda event: Strategy([
    rules.LayTheOutsider(
        liability=100,
        initial_price_from=3.75,
        price_from=4,
        price_to=13,
        time_from=-10,
        time_to=70),
    rules.Green([
        Condition(op.eq,
                  S.back_price(S.home),
                  S.maximum(S.back_price(S.away),
                            S.back_price(S.home),
                            S.back_price(S.the_draw))),
        Condition(op.eq,
                  S.back_price(S.away),
                  S.minimum(S.back_price(S.away),
                            S.back_price(S.home),
                            S.back_price(S.the_draw)))

    ])
], event)

one_x = lambda event: Strategy([
    rules.OneX(
        liability=100,
        margin=.07,
        away_initial_price_from=3.5,
        time_from=-10,
        time_to=70,
        ratio=.8),
    rules.Green([
        Condition(op.eq,
                  S.back_price(S.home),
                  S.maximum(S.back_price(S.away),
                            S.back_price(S.home),
                            S.back_price(S.const("The Draw")))),
        Condition(op.eq,
                  S.back_price(S.away),
                  S.minimum(S.back_price(S.away),
                            S.back_price(S.home),
                            S.back_price(S.const("The Draw"))))

    ])
], event)

lay_home_gt = lambda event: Strategy([
    Rule(
        conditions=[
            Condition(op.le, S.lay_price(S.home), S.const(7)),
            conds.valid_prices,
            Condition(op.gt, S.back_price(S.home), S.back_price(S.away)),
            Condition(op.gt, S.back_price(S.home), S.const(2))
        ],
        actions=[
            actions.LayHome(S.liability("LAY", 100)),
        ],
        max_triggers=1),
    rules.GreenPrice(op.lt, S.back_price(S.home), 2),
], event)



# Result -> Float -> Str
def make_row(result, s):
    home, away, event_id, total, bets, winner, initial_prices, volume = result
    return ";".join([home, away, str(event_id), f2s(total), f2s(s), "->".join(bets), winner, initial_prices, str(volume)])

# (Event -> Strategy) -> Int -> *
def test_strategy(strat, count=1000):
    start = time.time()
    print("HOME;AWAY;EVENT_ID;TOTAL;SUM;BETS;WINNER;INIT_HOME;INIT_AWAY;INIT_DRAW;VOLUME")
    s, c, positive, negative, sump = 0, 0, 0, 0, 0
    for entries in create_events(0, count):
        result = test_event(entries, strat)
        total = result[3]
        if total != 0:
            s += total
            c += 1
            if total > 0:
                positive += 1
                sump += total
            else:
                negative += 1

            print(make_row(result, s))

    print("-------------")
    print("%s at %s games." % (s, c))
    if c != 0:
        after = s - sump * 0.05
        print("Bets won: %s percent Bets lost: %s" % (f2s(positive / c * 100), f2s(negative / c * 100)))
        print("Total after commission 5%%: %s" % f2s(after))
        print("Average profit: %s" % f2s(after / c))
    end = time.time()
    print(time_format(end - start))


if __name__ == "__main__":
    test_strategy(lay_home_gt, 100000)
