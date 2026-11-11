#!/usr/bin/env python3
"""
Real-Time Trading Simulator
Hybrid Strategy with Multi-Level Filters
"""

import json
import asyncio
import aiohttp
import time
import glob
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSimulator:
    def __init__(self):
        self.state_file = 'trading_state.json'
        self.active_trades = {}
        self.dead_tokens = set()
        self.total_pnl = 0.0
        self.trade_history = []
        self.filters = {}
        self.session = None

        # Configuration
        self.base_amount = 1.0  # $1 per trade
        self.high_precision_multiplier = 2.0  # $2 for high precision
        self.ultra_selective_multiplier = 3.0  # $3 for ultra-selective
        self.death_threshold = -0.95  # -95% = dead
        self.fees_percent = 0.02  # 2% fees

        # Exit targets by strategy
        self.exit_targets = {
            'auto_optimized': 1.5,
            'ultra_selective': 2.0,
            'high_precision': 2.0,
            'level4': 2.5
        }

        self.load_state()
        self.load_filters()

    def load_filters(self):
        """Loads all available filters"""
        try:
            # Ultra-selective filter
            ultra_files = glob.glob('combined_ultra_clean_*_filter.json')
            if ultra_files:
                latest_ultra = max(ultra_files)
                with open(latest_ultra, 'r') as f:
                    self.filters['ultra_selective'] = json.load(f)
                logger.info(f"✅ Ultra-selective filter loaded: {latest_ultra}")

            # Auto-optimized filter
            auto_files = glob.glob('best_auto_filter_*.json')
            if auto_files:
                latest_auto = max(auto_files)
                with open(latest_auto, 'r') as f:
                    self.filters['auto_optimized'] = json.load(f)
                logger.info(f"✅ Auto-optimized filter loaded: {latest_auto}")

            # High-precision filter
            precision_files = glob.glob('best_high_precision_filter_*.json')
            if precision_files:
                latest_precision = max(precision_files)
                with open(latest_precision, 'r') as f:
                    self.filters['high_precision'] = json.load(f)
                logger.info(f"✅ High-precision filter loaded: {latest_precision}")

        except Exception as e:
            logger.error(f"❌ Error while loading the filters: {e}")

    def load_state(self):
        """Loads the simulator state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.active_trades = state.get('active_trades', {})
                    self.dead_tokens = set(state.get('dead_tokens', []))
                    self.total_pnl = state.get('total_pnl', 0.0)
                    self.trade_history = state.get('trade_history', [])
                logger.info(f"✅ State loaded: {len(self.active_trades)} active trades")
            else:
                logger.info("🆕 New simulator initialized")
        except Exception as e:
            logger.error(f"❌ Error while loading the state: {e}")

    def save_state(self):
        """Saves the simulator state"""
        try:
            state = {
                'active_trades': self.active_trades,
                'dead_tokens': list(self.dead_tokens),
                'total_pnl': self.total_pnl,
                'trade_history': self.trade_history,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Error while saving: {e}")

    def extract_numeric_features(self, token_data):
        """Extracts the numeric features of a token"""
        features = {}

        try:
            # Price and market capitalization
            if 'priceUsd' in token_data:
                features['priceUsd'] = float(token_data['priceUsd'])

            if 'marketCap' in token_data:
                features['marketCap'] = float(token_data['marketCap'])

            if 'fdv' in token_data:
                features['fdv'] = float(token_data['fdv'])

            if 'liquidity' in token_data and 'usd' in token_data['liquidity']:
                features['liquidity'] = float(token_data['liquidity']['usd'])

            # Volume
            if 'volume' in token_data and 'h24' in token_data['volume']:
                features['volume_24h'] = float(token_data['volume']['h24'])

            # Transactions
            if 'txns' in token_data:
                if 'h24' in token_data['txns']:
                    features['txns_24h'] = int(token_data['txns']['h24']['buys']) + int(token_data['txns']['h24']['sells'])

                if 'm5' in token_data['txns']:
                    features['txns_5m'] = int(token_data['txns']['m5']['buys']) + int(token_data['txns']['m5']['sells'])

            # Creation date
            if 'pairCreatedAt' in token_data:
                features['pairCreatedAt'] = int(token_data['pairCreatedAt'])

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Feature extraction error: {e}")

        return features

    def apply_filter(self, token_data, filter_criteria):
        """Applies a filter to a token"""
        features = self.extract_numeric_features(token_data)

        for criteria in filter_criteria:
            field = criteria['field']
            filter_type = criteria['type']
            value = criteria['value']

            if field not in features or features[field] is None:
                return False

            if filter_type == 'min_threshold' and features[field] < value:
                return False
            elif filter_type == 'max_threshold' and features[field] > value:
                return False

        return True

    def classify_token(self, token_data):
        """Classifies a token according to the filters"""
        classification = {
            'auto_optimized': False,
            'ultra_selective': False,
            'high_precision': False,
            'level4': False
        }

        # Check each filter
        if 'auto_optimized' in self.filters:
            classification['auto_optimized'] = self.apply_filter(
                token_data,
                self.filters['auto_optimized']['filter_criteria']
            )

        if 'ultra_selective' in self.filters:
            classification['ultra_selective'] = self.apply_filter(
                token_data,
                self.filters['ultra_selective']['filter_criteria']
            )

        if 'high_precision' in self.filters:
            classification['high_precision'] = self.apply_filter(
                token_data,
                self.filters['high_precision']['filter_criteria']
            )

        # Level 4 = all filters
        classification['level4'] = (
            classification['auto_optimized'] and
            classification['ultra_selective'] and
            classification['high_precision']
        )

        return classification

    def determine_strategy(self, classification):
        """Determines the strategy and allocation"""
        if classification['level4']:
            return {
                'strategy': 'level4',
                'amount': self.base_amount * self.ultra_selective_multiplier,
                'exit_target': self.exit_targets['level4'],
                'priority': 4
            }
        elif classification['ultra_selective']:
            return {
                'strategy': 'ultra_selective',
                'amount': self.base_amount * self.ultra_selective_multiplier,
                'exit_target': self.exit_targets['ultra_selective'],
                'priority': 3
            }
        elif classification['high_precision']:
            return {
                'strategy': 'high_precision',
                'amount': self.base_amount * self.high_precision_multiplier,
                'exit_target': self.exit_targets['high_precision'],
                'priority': 2
            }
        elif classification['auto_optimized']:
            return {
                'strategy': 'auto_optimized',
                'amount': self.base_amount,
                'exit_target': self.exit_targets['auto_optimized'],
                'priority': 1
            }
        else:
            return None

    async def get_token_price(self, token_address):
        """Retrieves the current price of a token via the Jupiter API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Use the Jupiter API to get the price
            url = f"https://quote-api.jup.ag/v6/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112&amount=10000000"

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'outAmount' in data:
                        # Price in SOL for 10M tokens
                        price_sol = int(data['outAmount']) / 1e9  # Convert to SOL
                        return price_sol
                return None
        except Exception as e:
            logger.error(f"❌ Error retrieving price {token_address}: {e}")
            return None

    async def get_token_data(self, token_address):
        """Retrieves the full data of a token via DexScreener"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'pairs' in data and data['pairs']:
                        return data['pairs'][0]  # First pair found
                return None
        except Exception as e:
            logger.error(f"❌ Error retrieving data {token_address}: {e}")
            return None

    def execute_trade(self, token_address, token_name, strategy_info, entry_price):
        """Executes a simulated trade"""
        trade = {
            'token_address': token_address,
            'token_name': token_name,
            'strategy': strategy_info['strategy'],
            'amount': strategy_info['amount'],
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'exit_target': strategy_info['exit_target'],
            'status': 'active',
            'current_price': entry_price,
            'pnl_percent': 0.0,
            'pnl_amount': 0.0
        }

        self.active_trades[token_address] = trade

        logger.info(f"🎯 TRADE EXECUTED:")
        logger.info(f"   📋 Token: {token_name} ({token_address})")
        logger.info(f"   🎯 Strategy: {strategy_info['strategy']}")
        logger.info(f"   💰 Amount: ${strategy_info['amount']:.2f}")
        logger.info(f"   📈 Entry price: {entry_price:.8f} SOL")
        logger.info(f"   🎯 Target: {strategy_info['exit_target']}x")

        self.save_state()

    def update_trade(self, token_address, current_price):
        """Updates a trade with the current price"""
        if token_address not in self.active_trades:
            return

        trade = self.active_trades[token_address]
        entry_price = trade['entry_price']

        # Calculate the PnL
        price_change = (current_price - entry_price) / entry_price
        pnl_amount = trade['amount'] * price_change

        trade['current_price'] = current_price
        trade['pnl_percent'] = price_change * 100
        trade['pnl_amount'] = pnl_amount

        # Check the exit conditions
        if price_change >= trade['exit_target']:
            # Success - sell
            self.close_trade(token_address, 'success', current_price)
        elif price_change <= self.death_threshold:
            # Dead - stop tracking
            self.close_trade(token_address, 'dead', current_price)
            self.dead_tokens.add(token_address)

    def close_trade(self, token_address, reason, exit_price):
        """Closes a trade"""
        if token_address not in self.active_trades:
            return

        trade = self.active_trades[token_address]
        trade['status'] = reason
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now().isoformat()

        # Calculate the final PnL with fees
        entry_cost = trade['amount']
        exit_value = trade['amount'] * (1 + trade['pnl_percent'] / 100)

        # Apply the fees (2% entry + 2% exit on success)
        if reason == 'success':
            fees = entry_cost * self.fees_percent * 2  # Entry + exit
        else:
            fees = entry_cost * self.fees_percent  # Entry only

        net_pnl = exit_value - entry_cost - fees
        trade['net_pnl'] = net_pnl
        trade['fees_paid'] = fees

        self.total_pnl += net_pnl

        # Add to the history
        self.trade_history.append(trade.copy())

        # Remove from the active trades
        del self.active_trades[token_address]

        logger.info(f"🔚 TRADE CLOSED ({reason.upper()}):")
        logger.info(f"   📋 Token: {trade['token_name']}")
        logger.info(f"   📈 Exit price: {exit_price:.8f} SOL")
        logger.info(f"   📊 PnL: {trade['pnl_percent']:.2f}%")
        logger.info(f"   💰 Net PnL: ${net_pnl:.2f}")
        logger.info(f"   💸 Fees: ${fees:.2f}")
        logger.info(f"   📊 Total PnL: ${self.total_pnl:.2f}")

        self.save_state()

    async def process_new_token(self, token_address, token_name):
        """Processes a new token"""
        logger.info(f"🆕 NEW TOKEN DETECTED: {token_name} ({token_address})")

        # Retrieve the token data
        token_data = await self.get_token_data(token_address)
        if not token_data:
            logger.warning(f"⚠️ Unable to retrieve data for {token_address}")
            return

        # Classify the token
        classification = self.classify_token(token_data)

        # Determine the strategy
        strategy_info = self.determine_strategy(classification)
        if not strategy_info:
            logger.info(f"ℹ️ Token {token_name} does not match any filter")
            return

        # Retrieve the entry price
        entry_price = await self.get_token_price(token_address)
        if not entry_price:
            logger.warning(f"⚠️ Unable to retrieve the price for {token_address}")
            return

        # Execute the trade
        self.execute_trade(token_address, token_name, strategy_info, entry_price)

    async def update_all_trades(self):
        """Updates all active trades"""
        if not self.active_trades:
            return

        logger.info(f"📊 Updating {len(self.active_trades)} active trades...")

        for token_address in list(self.active_trades.keys()):
            current_price = await self.get_token_price(token_address)
            if current_price:
                self.update_trade(token_address, current_price)

            # Pause to avoid spamming the API
            await asyncio.sleep(0.5)

    async def check_dead_tokens(self):
        """Manually checks the dead tokens"""
        if not self.dead_tokens:
            logger.info("ℹ️ No dead token to check")
            return

        logger.info(f"🔍 Checking {len(self.dead_tokens)} dead tokens...")

        for token_address in list(self.dead_tokens):
            current_price = await self.get_token_price(token_address)
            if current_price:
                # Check whether the price has recovered
                # If so, remove it from the dead list
                logger.info(f"🔄 Dead token {token_address}: current price = {current_price:.8f}")

            await asyncio.sleep(0.5)

    def print_status(self):
        """Displays the current status"""
        print("\n" + "="*60)
        print("📊 SIMULATOR STATUS")
        print("="*60)
        print(f"💰 Total PnL: ${self.total_pnl:.2f}")
        print(f"🎯 Active Trades: {len(self.active_trades)}")
        print(f"💀 Dead Tokens: {len(self.dead_tokens)}")
        print(f"📈 History: {len(self.trade_history)} trades")

        if self.active_trades:
            print(f"\n🎯 ACTIVE TRADES:")
            for addr, trade in self.active_trades.items():
                print(f"   📋 {trade['token_name']}: {trade['pnl_percent']:.2f}% ({trade['strategy']})")

        print("="*60)

    async def run_simulation(self):
        """Starts the simulation"""
        logger.info("🚀 Starting the trading simulator")

        try:
            while True:
                # Update the active trades
                await self.update_all_trades()

                # Display the status
                self.print_status()

                # Wait before the next update
                await asyncio.sleep(60)  # 1 minute

        except KeyboardInterrupt:
            logger.info("⏹️ Simulator stopped")
        finally:
            if self.session:
                await self.session.close()

async def main():
    """Main function"""
    simulator = TradingSimulator()

    # Interactive menu
    while True:
        print("\n🎯 TRADING SIMULATOR")
        print("1. Start the simulation")
        print("2. Process a token manually")
        print("3. Check the dead tokens")
        print("4. Display the status")
        print("5. Quit")

        choice = input("\nChoose an option (1-5): ")

        if choice == "1":
            await simulator.run_simulation()
        elif choice == "2":
            token_address = input("Token address: ")
            token_name = input("Token name: ")
            await simulator.process_new_token(token_address, token_name)
        elif choice == "3":
            await simulator.check_dead_tokens()
        elif choice == "4":
            simulator.print_status()
        elif choice == "5":
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    asyncio.run(main())
