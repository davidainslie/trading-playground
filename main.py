from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from decouple import config

client = Client(config("binance-api-key"), config("binance-secret-key"), testnet = True)

# Get market depth
depth = client.get_order_book(symbol = "BNBBTC")

print(depth)
