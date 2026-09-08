import ccxt

exchange = ccxt.binanceusdm()

print(exchange.fetch_ticker('ETH/USDT'))