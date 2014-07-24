# betfair-strategy-tester
A simple python framework for creating and simulating betting
strategies against betfair soccer data in Match Odds markets. Written in python.

## Data
Betfair provides [historical market data] formatted in csv files but without detailed timestamps.

## Disclaimer
Betfair historical csv data cannot be used in order to build precise time to price graphs an so the simulations are only learning expreriments. On the other hand Fracsoft provides fully timestamped data which could be used for precise strategy simulations (with the appropriate tweaks).

## Technology
betfair-strategy-tester uses [postgresql] for data storage and query and depends on [psycopg2], [fuzzywuzzy] for name string matching. Data importer also uses [python-progressbar].

## License
  - betfair-strategy-tester is distributed under the GPLv3.

[historical market data]: http://data.betfair.com
[postgresql]: http://www.postgresql.org/
[psycopg2]: http://initd.org/psycopg/
[fuzzywuzzy]: https://github.com/seatgeek/fuzzywuzzy
[python-progressbar]: https://code.google.com/p/python-progressbar/
