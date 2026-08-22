# Input Contract

`executions.csv` must contain `timestamp,symbol,side,quantity,price`; `side` is `buy` or `sell`, quantities and prices are positive. Optional `quotes.csv` contains `timestamp,symbol,bid,ask`. Optional `bars.csv` contains `timestamp,symbol,close,volume`.

Timestamps are parsed as UTC. For each fill, the script uses the latest quote or bar at or before the fill timestamp for its reference price. Quote mid is preferred; a prior bar close is a fallback. Participation is `quantity / volume` when bar volume is available. Commission input is a constant bps assumption and is reported separately from signed slippage.
