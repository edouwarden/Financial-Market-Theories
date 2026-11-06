import json
import time
import threading
import requests
from orderbook_display import OrderbookDisplay, run_display

# --- Paramètres stratégiques ---
symbol = "BTCUSDT"
min_volume_btc = 5  # Volume minimum en BTC pour considérer un niveau important
tick_threshold = 20  # Nombre de ticks pour considérer "à l'approche"
update_interval = 30  # Intervalle de mise à jour en secondes

# --- Trading settings ---
ORDER_AMOUNT = 0.001  # Amount in BTC per trade
EXCHANGE_FEE = 0.0004  # 0.04% fee per trade
SLIPPAGE = 0.0001  # Expected slippage 0.01%
TAKE_PROFIT_ROWS = 5  # Number of rows to place take profit from entry
MIN_PROFIT_TICKS = 2  # Minimum number of ticks for take profit

# --- Suivi d'état ---
display = OrderbookDisplay()
last_price = None
orderbook_data = {'bids': [], 'asks': []}
new_orderbook_data = False
level_trades = []

def merge_orderbook_data(existing_data, new_data):
    """Return the latest full depth snapshot.

    The Binance depth endpoint returns a complete top-N book on every request.
    Keeping old price levels would make the book grow monotonically and would
    treat stale liquidity as live liquidity. Each full update therefore replaces
    the previous snapshot instead of merging into it.
    """
    bids = sorted(
        [(str(price), str(volume)) for price, volume in new_data.get('bids', [])],
        key=lambda x: float(x[0]),
        reverse=True,
    )
    asks = sorted(
        [(str(price), str(volume)) for price, volume in new_data.get('asks', [])],
        key=lambda x: float(x[0]),
    )
    return {'bids': bids, 'asks': asks}




def process_orderbook(is_full_update=False):
    global last_price, orderbook_data, new_orderbook_data
    if last_price is None or not orderbook_data.get('bids') or not orderbook_data.get('asks'):
        return
    
    # Préparation des niveaux d'orderbook pour l'affichage
    orderbook_levels = []
    
    # Analyse des bids
    for price_str, volume_str in orderbook_data['bids']:
        price = float(price_str)
        volume = float(volume_str)
        if last_price <= price:
            orderbook_levels.append((price, volume, True))
        else:
            volume = 0.05
            orderbook_levels.append((price, volume, False))
        
        for order in [o for o in display.orders if o['status'] == 'ACTIVE'and o['side'] == 'BUY'] :
                    if last_price >= order['take_profit']:
                        profit = (last_price - order['price']) * order['size']
                        profit_after_fees = profit - (2 * EXCHANGE_FEE * order['size'] * last_price)  # Fee for entry and exit
                        display.close_order(order['id'], last_price, profit_after_fees)
                        display.add_logs(f"Taking profit on BUY order #{order['id']} at {last_price} (profit: {profit_after_fees:.4f} USDT)")
        if volume >= min_volume_btc and price not in level_trades and last_price <= price+display.tick_size:
            # Check if we should place a new order
            take_profit = abs(last_price + (display.tick_size * (volume/20)))
            display.add_logs(f"Placing BUY order at {last_price} (big bid level at {price}, volume: {volume}, TP: {take_profit})")
            display.add_order(last_price, ORDER_AMOUNT, 'BUY', take_profit, price)
            level_trades.append(price)
    
    # Analyse des asks
    for price_str, volume_str in orderbook_data['asks']:
        price = float(price_str)
        volume = float(volume_str)
        if last_price >= price:
            orderbook_levels.append((price, volume, False))
        else:
            volume = 0.05
            orderbook_levels.append((price, volume, True))

        for order in [o for o in display.orders if o['status'] == 'ACTIVE']:
                if order['side'] == 'SELL' and order['take_profit'] is not None:
                    if last_price <= order['take_profit']:
                        profit = (order['price'] - last_price) * order['size']
                        profit_after_fees = profit - (2 * EXCHANGE_FEE * order['size'] * last_price)  # Fee for entry and exit
                        display.close_order(order['id'], last_price, profit_after_fees)
                        display.add_logs(f"Taking profit on SELL order #{order['id']} at {last_price} (profit: {profit_after_fees:.4f} USDT)")
            

        if volume >= min_volume_btc and price not in level_trades and last_price >= price-display.tick_size:
            take_profit = abs(last_price - (display.tick_size * (volume/20)))
            display.add_logs(f"Placing SELL order at {last_price} (big ask level at {price}, volume: {volume}, TP: {take_profit})")
            display.add_order(last_price, ORDER_AMOUNT, 'SELL', take_profit, price)
            level_trades.append(price)
    
    # Mise à jour de l'affichage
    display.add_logs(f"Last price: {last_price}")
    #display.add_logs(f"Orderbook levels: {orderbook_levels}")
    display.update_orderbook(orderbook_levels, last_price, new_orderbook_data)
    if is_full_update:
        new_orderbook_data = False

def fetch_orderbook():
    global last_price, orderbook_data, new_orderbook_data, level_trades
    i = 0
    orderbook_url = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=1000"
    ticker_url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
    
    while True:
        # Mise à jour du prix chaque seconde
        try:
            response = requests.get(ticker_url)
            if response.status_code == 200:
                data = response.json()
                last_price = float(data['price'])
                process_orderbook(is_full_update=False)
        except Exception as e:
            print(f"Erreur ticker: {str(e)}, {ticker_url}")

        # Mise à jour complète de l'orderbook toutes les 30 secondes
        if i == 0:
            try:
                response = requests.get(orderbook_url)
                if response.status_code == 200:
                    data = response.json()
                    # Merge new data with existing data
                    orderbook_data = merge_orderbook_data(orderbook_data, data)
                    new_orderbook_data = True
                    level_trades = []
                    process_orderbook(is_full_update=True)
                else:
                    print(f"Erreur API orderbook: {response.status_code}")
            except Exception as e:
                print(f"Erreur orderbook: {str(e)}")
        
        time.sleep(0.5)
        i = 0 if i == 60 else i + 1

if __name__ == "__main__":
    # Démarrage du polling dans un thread
    threading.Thread(target=fetch_orderbook, daemon=True).start()
    
    # Démarrage de l'interface TUI
    run_display(display)
