#!/usr/bin/env python3
"""
Simulateur de Trading en Temps Réel
Stratégie Hybride avec Filtres Multi-Niveaux
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

# Configuration du logging
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
        self.base_amount = 1.0  # $1 par trade
        self.high_precision_multiplier = 2.0  # $2 pour haute précision
        self.ultra_selective_multiplier = 3.0  # $3 pour ultra-sélectif
        self.death_threshold = -0.95  # -95% = mort
        self.fees_percent = 0.02  # 2% de frais
        
        # Objectifs de sortie par stratégie
        self.exit_targets = {
            'auto_optimized': 1.5,
            'ultra_selective': 2.0,
            'high_precision': 2.0,
            'level4': 2.5
        }
        
        self.load_state()
        self.load_filters()
    
    def load_filters(self):
        """Charge tous les filtres disponibles"""
        try:
            # Filtre ultra-sélectif
            ultra_files = glob.glob('combiné_ultra_clean_*_filter.json')
            if ultra_files:
                latest_ultra = max(ultra_files)
                with open(latest_ultra, 'r') as f:
                    self.filters['ultra_selective'] = json.load(f)
                logger.info(f"✅ Filtre ultra-sélectif chargé: {latest_ultra}")
            
            # Filtre auto-optimisé
            auto_files = glob.glob('best_auto_filter_*.json')
            if auto_files:
                latest_auto = max(auto_files)
                with open(latest_auto, 'r') as f:
                    self.filters['auto_optimized'] = json.load(f)
                logger.info(f"✅ Filtre auto-optimisé chargé: {latest_auto}")
            
            # Filtre haute précision
            precision_files = glob.glob('best_high_precision_filter_*.json')
            if precision_files:
                latest_precision = max(precision_files)
                with open(latest_precision, 'r') as f:
                    self.filters['high_precision'] = json.load(f)
                logger.info(f"✅ Filtre haute précision chargé: {latest_precision}")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des filtres: {e}")
    
    def load_state(self):
        """Charge l'état du simulateur"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.active_trades = state.get('active_trades', {})
                    self.dead_tokens = set(state.get('dead_tokens', []))
                    self.total_pnl = state.get('total_pnl', 0.0)
                    self.trade_history = state.get('trade_history', [])
                logger.info(f"✅ État chargé: {len(self.active_trades)} trades actifs")
            else:
                logger.info("🆕 Nouveau simulateur initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement de l'état: {e}")
    
    def save_state(self):
        """Sauvegarde l'état du simulateur"""
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
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
    
    def extract_numeric_features(self, token_data):
        """Extrait les caractéristiques numériques d'un token"""
        features = {}
        
        try:
            # Prix et capitalisation
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
            
            # Date de création
            if 'pairCreatedAt' in token_data:
                features['pairCreatedAt'] = int(token_data['pairCreatedAt'])
                
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Erreur extraction features: {e}")
        
        return features
    
    def apply_filter(self, token_data, filter_criteria):
        """Applique un filtre à un token"""
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
        """Classifie un token selon les filtres"""
        classification = {
            'auto_optimized': False,
            'ultra_selective': False,
            'high_precision': False,
            'level4': False
        }
        
        # Vérifier chaque filtre
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
        
        # Niveau 4 = tous les filtres
        classification['level4'] = (
            classification['auto_optimized'] and 
            classification['ultra_selective'] and 
            classification['high_precision']
        )
        
        return classification
    
    def determine_strategy(self, classification):
        """Détermine la stratégie et l'allocation"""
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
        """Récupère le prix actuel d'un token via Jupiter API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Utiliser Jupiter API pour obtenir le prix
            url = f"https://quote-api.jup.ag/v6/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112&amount=10000000"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'outAmount' in data:
                        # Prix en SOL pour 10M de tokens
                        price_sol = int(data['outAmount']) / 1e9  # Convertir en SOL
                        return price_sol
                return None
        except Exception as e:
            logger.error(f"❌ Erreur récupération prix {token_address}: {e}")
            return None
    
    async def get_token_data(self, token_address):
        """Récupère les données complètes d'un token via DexScreener"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'pairs' in data and data['pairs']:
                        return data['pairs'][0]  # Premier pair trouvé
                return None
        except Exception as e:
            logger.error(f"❌ Erreur récupération données {token_address}: {e}")
            return None
    
    def execute_trade(self, token_address, token_name, strategy_info, entry_price):
        """Exécute un trade simulé"""
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
        
        logger.info(f"🎯 TRADE EXÉCUTÉ:")
        logger.info(f"   📋 Token: {token_name} ({token_address})")
        logger.info(f"   🎯 Stratégie: {strategy_info['strategy']}")
        logger.info(f"   💰 Montant: ${strategy_info['amount']:.2f}")
        logger.info(f"   📈 Prix d'entrée: {entry_price:.8f} SOL")
        logger.info(f"   🎯 Objectif: {strategy_info['exit_target']}x")
        
        self.save_state()
    
    def update_trade(self, token_address, current_price):
        """Met à jour un trade avec le prix actuel"""
        if token_address not in self.active_trades:
            return
        
        trade = self.active_trades[token_address]
        entry_price = trade['entry_price']
        
        # Calculer le PnL
        price_change = (current_price - entry_price) / entry_price
        pnl_amount = trade['amount'] * price_change
        
        trade['current_price'] = current_price
        trade['pnl_percent'] = price_change * 100
        trade['pnl_amount'] = pnl_amount
        
        # Vérifier les conditions de sortie
        if price_change >= trade['exit_target']:
            # Succès - vendre
            self.close_trade(token_address, 'success', current_price)
        elif price_change <= self.death_threshold:
            # Mort - arrêter de tracker
            self.close_trade(token_address, 'dead', current_price)
            self.dead_tokens.add(token_address)
    
    def close_trade(self, token_address, reason, exit_price):
        """Ferme un trade"""
        if token_address not in self.active_trades:
            return
        
        trade = self.active_trades[token_address]
        trade['status'] = reason
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now().isoformat()
        
        # Calculer le PnL final avec frais
        entry_cost = trade['amount']
        exit_value = trade['amount'] * (1 + trade['pnl_percent'] / 100)
        
        # Appliquer les frais (2% entrée + 2% sortie si succès)
        if reason == 'success':
            fees = entry_cost * self.fees_percent * 2  # Entrée + sortie
        else:
            fees = entry_cost * self.fees_percent  # Seulement entrée
        
        net_pnl = exit_value - entry_cost - fees
        trade['net_pnl'] = net_pnl
        trade['fees_paid'] = fees
        
        self.total_pnl += net_pnl
        
        # Ajouter à l'historique
        self.trade_history.append(trade.copy())
        
        # Retirer des trades actifs
        del self.active_trades[token_address]
        
        logger.info(f"🔚 TRADE FERMÉ ({reason.upper()}):")
        logger.info(f"   📋 Token: {trade['token_name']}")
        logger.info(f"   📈 Prix sortie: {exit_price:.8f} SOL")
        logger.info(f"   📊 PnL: {trade['pnl_percent']:.2f}%")
        logger.info(f"   💰 PnL net: ${net_pnl:.2f}")
        logger.info(f"   💸 Frais: ${fees:.2f}")
        logger.info(f"   📊 PnL total: ${self.total_pnl:.2f}")
        
        self.save_state()
    
    async def process_new_token(self, token_address, token_name):
        """Traite un nouveau token"""
        logger.info(f"🆕 NOUVEAU TOKEN DÉTECTÉ: {token_name} ({token_address})")
        
        # Récupérer les données du token
        token_data = await self.get_token_data(token_address)
        if not token_data:
            logger.warning(f"⚠️ Impossible de récupérer les données pour {token_address}")
            return
        
        # Classifier le token
        classification = self.classify_token(token_data)
        
        # Déterminer la stratégie
        strategy_info = self.determine_strategy(classification)
        if not strategy_info:
            logger.info(f"ℹ️ Token {token_name} ne respecte aucun filtre")
            return
        
        # Récupérer le prix d'entrée
        entry_price = await self.get_token_price(token_address)
        if not entry_price:
            logger.warning(f"⚠️ Impossible de récupérer le prix pour {token_address}")
            return
        
        # Exécuter le trade
        self.execute_trade(token_address, token_name, strategy_info, entry_price)
    
    async def update_all_trades(self):
        """Met à jour tous les trades actifs"""
        if not self.active_trades:
            return
        
        logger.info(f"📊 Mise à jour de {len(self.active_trades)} trades actifs...")
        
        for token_address in list(self.active_trades.keys()):
            current_price = await self.get_token_price(token_address)
            if current_price:
                self.update_trade(token_address, current_price)
            
            # Pause pour éviter de spammer l'API
            await asyncio.sleep(0.5)
    
    async def check_dead_tokens(self):
        """Vérifie manuellement les tokens morts"""
        if not self.dead_tokens:
            logger.info("ℹ️ Aucun token mort à vérifier")
            return
        
        logger.info(f"🔍 Vérification de {len(self.dead_tokens)} tokens morts...")
        
        for token_address in list(self.dead_tokens):
            current_price = await self.get_token_price(token_address)
            if current_price:
                # Vérifier si le prix a récupéré
                # Si oui, le retirer des morts
                logger.info(f"🔄 Token mort {token_address}: prix actuel = {current_price:.8f}")
            
            await asyncio.sleep(0.5)
    
    def print_status(self):
        """Affiche le statut actuel"""
        print("\n" + "="*60)
        print("📊 STATUT DU SIMULATEUR")
        print("="*60)
        print(f"💰 PnL Total: ${self.total_pnl:.2f}")
        print(f"🎯 Trades Actifs: {len(self.active_trades)}")
        print(f"💀 Tokens Morts: {len(self.dead_tokens)}")
        print(f"📈 Historique: {len(self.trade_history)} trades")
        
        if self.active_trades:
            print(f"\n🎯 TRADES ACTIFS:")
            for addr, trade in self.active_trades.items():
                print(f"   📋 {trade['token_name']}: {trade['pnl_percent']:.2f}% ({trade['strategy']})")
        
        print("="*60)
    
    async def run_simulation(self):
        """Lance la simulation"""
        logger.info("🚀 Démarrage du simulateur de trading")
        
        try:
            while True:
                # Mettre à jour les trades actifs
                await self.update_all_trades()
                
                # Afficher le statut
                self.print_status()
                
                # Attendre avant la prochaine mise à jour
                await asyncio.sleep(60)  # 1 minute
                
        except KeyboardInterrupt:
            logger.info("⏹️ Arrêt du simulateur")
        finally:
            if self.session:
                await self.session.close()

async def main():
    """Fonction principale"""
    simulator = TradingSimulator()
    
    # Menu interactif
    while True:
        print("\n🎯 SIMULATEUR DE TRADING")
        print("1. Lancer la simulation")
        print("2. Traiter un token manuellement")
        print("3. Vérifier les tokens morts")
        print("4. Afficher le statut")
        print("5. Quitter")
        
        choice = input("\nChoisissez une option (1-5): ")
        
        if choice == "1":
            await simulator.run_simulation()
        elif choice == "2":
            token_address = input("Adresse du token: ")
            token_name = input("Nom du token: ")
            await simulator.process_new_token(token_address, token_name)
        elif choice == "3":
            await simulator.check_dead_tokens()
        elif choice == "4":
            simulator.print_status()
        elif choice == "5":
            break
        else:
            print("❌ Option invalide")

if __name__ == "__main__":
    asyncio.run(main())




