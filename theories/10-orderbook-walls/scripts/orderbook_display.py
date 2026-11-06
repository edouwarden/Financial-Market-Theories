import curses
import time
from datetime import datetime
from typing import Dict, List, Tuple

class OrderbookDisplay:
	def __init__(self):
		self.orders: List[Dict] = []  # Liste des ordres actifs et passés
		self.pnl_total = 0.0
		self.current_price = 0.0
		self.orderbook_levels: List[Tuple[float, float, bool]] = []  # (prix, volume, is_bid)
		self.last_full_update = 0  # Timestamp du dernier rafraîchissement complet
		self.last_partial_update = 0  # Timestamp du dernier rafraîchissement partiel
		self.base_price = 0.0  # Prix de référence pour l'affichage fixe
		self.tick_size = 10  # Taille d'un tick en points
		self.orderbook_size = 50
		self.min_volume = 0.05
		self.logs: List[str] = []
	def add_logs(self, log: str):
		self.logs.append("- " + log)
		if len(self.logs) > 40:
			self.logs.pop(0)

	def add_order(self, price: float, size: float, side: str, take_profit: float = None, level_price: float = None, order_type: str = "LIMIT"):
		order = {
			'id': len(self.orders) + 1,
			'price': price,
			'size': size,
			'side': side,
			'type': order_type,
			'status': 'ACTIVE',
			'entry_time': datetime.now(),
			'exit_time': None,
			'take_profit': take_profit,
			'level_price': level_price,
			'pnl': 0.0
		}
		self.orders.append(order)
		
	def close_order(self, order_id: int, exit_price: float, pnl: float):
		for order in self.orders:
			if order['id'] == order_id and order['status'] == 'ACTIVE':
				order['status'] = 'CLOSED'
				order['exit_time'] = datetime.now()
				order['pnl'] = pnl
				self.pnl_total += pnl
				break

	def update_orderbook(self, levels: List[Tuple[float, float, bool]], current_price: float, new_orderbook_data: bool):
		self.orderbook_levels = levels
		self.current_price = current_price
		
		# Mise à jour du prix de base uniquement lors d'une mise à jour complète de l'orderbook
		current_time = time.time()
		if new_orderbook_data:
			self.base_price = round(current_price / self.tick_size) * self.tick_size
			self.last_full_update = current_time
		self.last_partial_update = current_time

	def get_volume_at_price(self, target_price: float) -> Tuple[float, bool]:
		for price, volume, is_bid in self.orderbook_levels:
			if abs(price - target_price) < 0.1:  # Tolérance pour la comparaison de float
				return volume, is_bid
		return 0.0, False

	def display(self, stdscr):
		stdscr.clear()
		height, width = stdscr.getmaxyx()
		
		# Configuration des couleurs
		curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Prix sous le current
		curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Prix au-dessus du current
		curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Prix actuel
		curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Gros volumes
		curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)   # En-têtes
		curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Profit positif
		curses.init_pair(7, curses.COLOR_RED, curses.COLOR_BLACK)    # Profit négatif
		curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Active orders
		curses.init_pair(9, curses.COLOR_MAGENTA, curses.COLOR_BLACK)   # Recent trades
		curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Logs
		
		# En-tête
		title = f"ORDERBOOK MONITOR {self.current_price:.2f}"
		stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(5))
		
		# Layout configuration
		start_row = 2
		orderbook_width = 25
		active_orders_width = 30
		recent_trades_width = 30
		col1 = 2  # Orderbook
		col2 = col1 + orderbook_width + 1  # Active orders
		col3 = col2 + active_orders_width + 1  # Recent trades
		col4 = col3 + recent_trades_width + 1  # Logs
		
		# En-têtes des colonnes
		stdscr.addstr(start_row, col1, "PRICE     |VOLUME (BTC)", curses.color_pair(5))
		stdscr.addstr(start_row, col2, "ACTIVE ORDERS", curses.color_pair(5))
		stdscr.addstr(start_row, col3, "RECENT TRADES", curses.color_pair(5))
		stdscr.addstr(start_row, col4, "LOGS", curses.color_pair(5))
		start_row += 1
		
		# Calcul des niveaux de prix à afficher (fixe basé sur base_price)
		display_prices = []
		self.add_logs(f"{self.orderbook_size}")
		for i in range(-self.orderbook_size, self.orderbook_size + 1):
			price = self.base_price + (i * self.tick_size)
			volume, is_bid = self.get_volume_at_price(price)
			self.add_logs(f"Price: {price}, Volume: {volume}, Is bid: {is_bid}")
			if volume > self.min_volume or abs(price - self.current_price) < (self.tick_size / 2):
				display_prices.append(price)
		
		# Tri des prix dans l'ordre décroissant
		display_prices.sort(reverse=True)
		
		# Get active and recent orders
		active_orders = [o for o in self.orders if o['status'] == 'ACTIVE']
		recent_trades = [o for o in self.orders if o['status'] == 'CLOSED'][-20:]  # Last 20 trades
		
		# Affichage des prix et orderbook
		row = start_row
		for price in display_prices:
			if row >= height - 3:
				break
				
			volume, is_bid = self.get_volume_at_price(price)
			
			# Détermination de la couleur
			if abs(price - self.current_price) < (self.tick_size / 2):
				color = curses.color_pair(3)  # Jaune pour le prix actuel
			elif volume >= 5:
				color = curses.color_pair(4)  # Cyan pour les gros volumes
			elif price > self.current_price:
				color = curses.color_pair(2)  # Rouge pour les prix au-dessus
			else:
				color = curses.color_pair(1)  # Vert pour les prix en-dessous
			
			# Affichage de la ligne d'orderbook
			price_str = f" {price:9.2f}|{volume:10.2f}"
			for order in active_orders:
				if order['price'] > price and order['price'] + self.tick_size < price:
					price_str = price_str.replace(" ", "⇒")
				elif order['price'] > price and order['take_profit'] <= price and order['side'] == 'BUY':
					if order['take_profit'] + self.tick_size > price and order['take_profit'] < price:
						price_str = price_str.replace(" ", "↱")
					else:
						price_str = price_str.replace(" ", "|")
				elif order['price'] < price and order['take_profit'] >= price and order['side'] == 'SELL':
					if order['take_profit'] + self.tick_size < price and order['take_profit'] > price:
						price_str = price_str.replace(" ", "↳")
					else:
						price_str = price_str.replace(" ", "|")
			stdscr.addstr(row, col1, price_str, color)
			
			# Affichage des ordres actifs à ce niveau
			orders_at_price = [o for o in self.orders if o['status'] == 'ACTIVE' and abs(o['price'] - price) < 0.1]
			if orders_at_price:
				orders_str = " ".join([f"#{o['id']}" for o in orders_at_price])
				stdscr.addstr(row, col1 + len(price_str) + 1, orders_str, color)
			
			row += 1
		
		# Affichage des ordres actifs
		row = start_row
		for order in active_orders:
			if row >= height - 3:
				break
			order_str = f"#{order['id']} {order['side']} {order['size']:.3f} @ {order['price']:.2f}"
			if order['take_profit']:
				order_str += f" TP:{order['take_profit']:.2f}"
			stdscr.addstr(row, col2, order_str, curses.color_pair(3))
			row += 1
		
		# Affichage des trades récents
		row = start_row
		for trade in reversed(recent_trades):
			if row >= height - 3:
				break
			trade_str = (f"#{trade['id']} {trade['side']} {trade['size']:.3f} "
						f"@ {trade['price']:.2f} P/L: {trade['pnl']:.4f}")
			color = curses.color_pair(6) if trade['pnl'] >= 0 else curses.color_pair(7)
			stdscr.addstr(row, col3, trade_str, color)
			row += 1
		
		# Affichage des logs
		row = start_row
		for log in self.logs:
			stdscr.addstr(row, col4, log, curses.color_pair(10))
			row += 1
		
		# Performance et timestamp
		perf_str = f"Performance totale: {self.pnl_total:.4f} USDT"
		perf_color = curses.color_pair(6) if self.pnl_total >= 0 else curses.color_pair(7)
		stdscr.addstr(height - 2, 2, perf_str, perf_color)
		
		time_str = f"Dernière mise à jour: {datetime.fromtimestamp(self.last_partial_update).strftime('%H:%M:%S')}"
		stdscr.addstr(height - 2, width - len(time_str) - 2, time_str)
		
		stdscr.refresh()

def run_display(display: OrderbookDisplay):
	def main(stdscr):
		curses.start_color()
		curses.use_default_colors()
		stdscr.timeout(1000)  # 1 seconde de timeout pour getch()
		
		while True:
			try:
				display.display(stdscr)
				key = stdscr.getch()
				if key == ord('q'):
					break
				time.sleep(0.1)
			except Exception as e:
				# Log the error instead of breaking immediately
				display.add_logs(f"Display error: {str(e)}")
				time.sleep(1)  # Add delay to prevent rapid error loops
				try:
					stdscr.refresh()  # Try to refresh the screen
				except:
					pass  # Ignore refresh errors
				
	curses.wrapper(main) 