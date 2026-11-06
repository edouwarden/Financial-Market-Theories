TRADING_SETTINGS = {
    # Order settings
    'default_order_amount': 0.01,  # Default BTC amount per order
    'max_slippage': 0.0005,  # Maximum allowed slippage (0.05%)
    'exchange_fee': 0.0004,  # Exchange fee (0.04%)
    
    # Display settings
    'orderbook_depth': 50,  # Number of levels to display
    'min_volume': 0.05,  # Minimum volume to display
    'tick_size': 10,  # Price tick size
    
    # Trading parameters
    'min_volume_btc': 5,  # Volume threshold for significant levels
    'tick_threshold': 20,  # Number of ticks to consider "approaching"
    'update_interval': 30,  # Orderbook update interval
    
    # Symbol settings
    'symbol': "BTCUSDT",
    'price_precision': 2,
    'quantity_precision': 5
} 