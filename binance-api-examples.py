# https://github.com/sammchardy/python-binance

from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from binance.exceptions import BinanceAPIException
from decouple import config
import pprint

client = Client(config("binance-api-key"), config("binance-secret-key"), testnet = True)

# Get market depth
depth = client.get_order_book(symbol = "BNBUSDT")
print(depth)

# Place a test market buy order, to place an actual order use the create_order function
order = client.create_test_order(
  symbol = "BNBUSDT",
  side = Client.SIDE_SELL,
  type = Client.ORDER_TYPE_LIMIT,
  timeInForce = Client.TIME_IN_FORCE_GTC,
  quantity = 0.1,
  price = 1000
)

print(order)
pprint.pprint(client.get_all_orders(symbol = "BNBUSDT"))

# Get all symbol prices
prices = client.get_all_tickers()
print(prices)

# Withdraw 100 ETH
# try:
#   result = client.withdraw(
#     asset = "ETH",
#     address = config("ether-address"),
#     amount = 1
#   )
# except BinanceAPIException as e:
#   print(e)
# else:
#   print("Success")

# Fetch list of withdrawals
# withdraws = client.get_withdraw_history()

# Fetch list of ETH withdrawals
# eth_withdraws = client.get_withdraw_history(coin = "ETH")

# Get a deposit address for BTC
# address = client.get_deposit_address(coin = "BTC")

# Fetch 1 minute klines for the last day up until now
klines = client.get_historical_klines("BNBBTC", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
pprint.pprint(klines)

# Fetch 30 minute klines for the last month of 2017
klines = client.get_historical_klines("ETHBTC", Client.KLINE_INTERVAL_30MINUTE, "1 Dec, 2017", "1 Jan, 2018")
pprint.pprint(klines)

# Fetch weekly klines since it listed
klines = client.get_historical_klines("ETHBTC", Client.KLINE_INTERVAL_1WEEK, "1 Jan, 2017")
pprint.pprint(klines)