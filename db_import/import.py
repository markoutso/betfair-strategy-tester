import csv
import datetime
import psycopg2
import os
from progressbar import ProgressBar
import time
import psycopg2.extensions

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

def parse_date(bf_date):
    if bf_date:
        if len(bf_date) == 16:
            return datetime.datetime.strptime(bf_date, "%d-%m-%Y %H:%M")
        else:
            return datetime.datetime.strptime(bf_date, "%d-%m-%Y %H:%M:%S")
    return None

def identity(x):
    return x

def noneIfFalsy(fn):
    def wrapper(data):
        result = fn(data)
        return None if not result else result
    return wrapper

def noneIfError(fn):
    def wrapper(data):
        try:
            return fn(data)
        except:
            return None
    return wrapper


def size_format(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

def time_format(t):
    return str(datetime.timedelta(seconds=int(t)))

csv_fields = {n: (i, f) for i, (n, f) in enumerate([
    ("sports_id", int),
    ("event_id", int),
    ("settled_date", parse_date),
    ("description", identity),
    ("scheduled_off", parse_date),
    ("market", identity),
    ("actual_off", parse_date),
    ("selection_id", int),
    ("selection", identity),
    ("odds", float),
    ("number_bets", int),
    ("volume", float),
    ("latest_taken", parse_date),
    ("first_taken", parse_date),
    ("win_flag", noneIfFalsy(identity)),
    ("in_play", identity)])}

event_fields = ["sports_id", "event_id", "market", "settled_date", "description", "scheduled_off",  "actual_off"]
event_table_fields = ["market", "away", "home", "sub_cat", "cat", "actual_off", "scheduled_off", "sports_id", "event_id"]

entry_fields = ["event_id", "selection_id", "selection", "odds", "number_bets", "volume", "latest_taken", "first_taken", "win_flag", "in_play", "settled_date"]
entry_table_fields = ["in_play", "win_flag", "first_taken", "latest_taken", "volume", "number_bets", "odds", "selection", "selection_id", "event_id", "settled_date"]

def get_values(row, fields):
    return {f: csv_fields[f][1](row[csv_fields[f][0]]) for f in fields}

def event_values(row):
    return get_values(row, event_fields)

def entry_values(row):
    return get_values(row, entry_fields)

@noneIfError
def create_event(row):

    values = event_values(row)
    desc_fields = [v.strip() for v in values['description'].split("/")]

    # might raise errors
    fixt_pos = None
    for i, f in enumerate(desc_fields):
        if f.startswith("Fixt"):
            fixt_pos = i

    game = desc_fields[fixt_pos + 1]
    values['home'], values['away'] = game.split(" v ")

    values['cat'] = desc_fields[0]
    values['sub_cat'] = "$".join(desc_fields[1:fixt_pos]) or None
    return values

def create_entry(row):
    return entry_values(row)

def create_insert_sql(table, fields):
    return "INSERT INTO " + table + "(" + ",".join(fields) + ") VALUES (" + ",".join(["%(" + f + ")s" for f in fields])  +  ")"

insert_event_sql = create_insert_sql("event", event_table_fields)
insert_entry_sql = create_insert_sql("entry", entry_table_fields)

def add_event(cur, event):
    cur.execute(insert_event_sql, event)

def add_entry(cur, entry):
    cur.execute(insert_entry_sql, entry)


if __name__ == "__main__":
    conn = psycopg2.connect("dbname=db_name user=user password=password host=localhost")
    cur = conn.cursor()
    entries = sorted(filter(lambda p: os.path.splitext(p)[1] == ".csv", os.listdir(unicode("."))))
    number_of_entries = len(entries)
    print "Found %s csv files" % len(entries)


    dir_start = time.time()
    dir_rows = 0

    i = 0
    for entry in entries:
        i += 1
        path = os.path.join(".", entry)
        size = os.path.getsize(path)
        print "Processing file %s of %s - '%s' (%s)" % (i, number_of_entries, entry, size_format(size))
        file_start = time.time()
        file_rows = 0
        with open(path, "rb") as f:
            reader = csv.reader(f)
            header = next(reader)
            events = {}
            errors = []
            pbar = ProgressBar(maxval=size).start()
            for row in reader:
                pbar.update(f.tell())
                if row[csv_fields["sports_id"][0]] == '1' and row[csv_fields["market"][0]] == 'Match Odds':
                    event = create_event(row)
                    if not event:
                        continue
                    if event['event_id'] not in events:
                        events[event['event_id']] = event
                        try:
                            add_event(cur, event)
                        except psycopg2.IntegrityError as e:
                            # first bets of a day might exist in last lines of previous file
                            print "Error!"
                            print str(e)
                            print "Retrieving.."
                            conn.rollback()
                            # event from now on will collide with the existing in the dict
                            f.seek(0)
                            continue
                        add_entry(cur, create_entry(row))
                        file_rows += 1
                        pbar.finish()
                        dir_rows += file_rows
                        print "Commiting changes to database. Total entries parsed successfully: %s" % file_rows
                        conn.commit()
                        file_end = time.time()
                        print "Success! Time elapsed %s" % time_format(file_end - file_start)

    dir_end = time.time()
    cur.close()
    conn.close()
    print "Inserted all files successfully! Total time elapsed %s" % time_format(dir_end - dir_start)
    print "Total entries parsed successfully: %s" % dir_rows
