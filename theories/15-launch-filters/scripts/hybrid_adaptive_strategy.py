#!/usr/bin/env python3
"""
Stratégie Hybride Adaptative
Combine Auto-Optimisé (base) + Ultra-Sélectif et Haute Précision (adaptatif)
"""

import json
import pandas as pd
import numpy as np
import glob
from datetime import datetime

def load_all_filters():
    """Charge tous les filtres disponibles"""
    filters = {}
    
    # Charger le filtre ultra-sélectif
    ultra_files = glob.glob('combiné_ultra_clean_*_filter.json')
    if ultra_files:
        latest_ultra = max(ultra_files)
        with open(latest_ultra, 'r') as f:
            filters['ultra_selective'] = json.load(f)
        print(f"✅ Filtre ultra-sélectif chargé: {latest_ultra}")
    
    # Charger le filtre auto-optimisé
    auto_files = glob.glob('best_auto_filter_*.json')
    if auto_files:
        latest_auto = max(auto_files)
        with open(latest_auto, 'r') as f:
            filters['auto_optimized'] = json.load(f)
        print(f"✅ Filtre auto-optimisé chargé: {latest_auto}")
    
    # Charger le filtre haute précision
    precision_files = glob.glob('best_high_precision_filter_*.json')
    if precision_files:
        latest_precision = max(precision_files)
        with open(latest_precision, 'r') as f:
            filters['high_precision'] = json.load(f)
        print(f"✅ Filtre haute précision chargé: {latest_precision}")
    
    return filters

def load_clean_data():
    """Charge les données nettoyées"""
    print("📊 Chargement des données...")
    
    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)
    
    # Utiliser le dataset nettoyé le plus récent
    clean_files = glob.glob('data/raw/merged_new_data_clean_*.json')
    if clean_files:
        latest_clean_file = max(clean_files)
        with open(latest_clean_file, 'r') as f:
            new_data = json.load(f)
        print(f"✅ Dataset nettoyé: {latest_clean_file}")
    else:
        print("❌ Aucun dataset nettoyé trouvé")
        return None, None
    
    return success_data, new_data

def get_token_address_from_new_data(token):
    """Extrait l'adresse du token depuis new_data"""
    if 'baseToken' in token and 'address' in token['baseToken']:
        return token['baseToken']['address']
    elif 'token_address' in token:
        return token['token_address']
    elif 'address' in token:
        return token['address']
    return None

def extract_numeric_features(token):
    """Extrait les caractéristiques numériques d'un token"""
    features = {}
    
    # Prix et capitalisation
    if 'priceUsd' in token:
        try:
            features['priceUsd'] = float(token['priceUsd'])
        except (ValueError, TypeError):
            features['priceUsd'] = None
    
    if 'marketCap' in token:
        try:
            features['marketCap'] = float(token['marketCap'])
        except (ValueError, TypeError):
            features['marketCap'] = None
    
    if 'fdv' in token:
        try:
            features['fdv'] = float(token['fdv'])
        except (ValueError, TypeError):
            features['fdv'] = None
    
    if 'liquidity' in token:
        try:
            features['liquidity'] = float(token['liquidity']['usd'])
        except (ValueError, TypeError, KeyError):
            features['liquidity'] = None
    
    # Volume
    if 'volume' in token and 'h24' in token['volume']:
        try:
            features['volume_24h'] = float(token['volume']['h24'])
        except (ValueError, TypeError):
            features['volume_24h'] = None
    
    # Transactions
    if 'txns' in token:
        if 'h24' in token['txns']:
            try:
                features['txns_24h'] = int(token['txns']['h24']['buys']) + int(token['txns']['h24']['sells'])
            except (ValueError, TypeError, KeyError):
                features['txns_24h'] = None
        
        if 'm5' in token['txns']:
            try:
                features['txns_5m'] = int(token['txns']['m5']['buys']) + int(token['txns']['m5']['sells'])
            except (ValueError, TypeError, KeyError):
                features['txns_5m'] = None
    
    # Date de création
    if 'pairCreatedAt' in token:
        try:
            features['pairCreatedAt'] = int(token['pairCreatedAt'])
        except (ValueError, TypeError):
            features['pairCreatedAt'] = None
    
    return features

def apply_filter_combination(token_data, filter_criteria):
    """Applique une combinaison de filtres à un token"""
    features = extract_numeric_features(token_data)
    
    # Vérifier chaque critère du filtre
    for criteria in filter_criteria:
        field = criteria['field']
        filter_type = criteria['type']
        value = criteria['value']
        
        # Si la caractéristique n'est pas disponible, le token échoue
        if field not in features or features[field] is None:
            return False
        
        # Vérifier le critère
        if filter_type == 'min_threshold' and features[field] < value:
            return False
        elif filter_type == 'max_threshold' and features[field] > value:
            return False
    
    return True

def calculate_required_winrate(multiple):
    """Calcule le winrate requis pour être rentable avec un multiple donné"""
    required_winrate = 1 / (multiple + 1) * 100
    return required_winrate

def calculate_rentability(winrate, multiple):
    """Calcule la rentabilité avec un winrate et un multiple donnés"""
    loss_rate = 100 - winrate
    gain_per_trade = (winrate/100 * multiple) - (loss_rate/100 * 1)
    return gain_per_trade

def test_hybrid_strategy(new_data, success_data, filters):
    """Teste la stratégie hybride adaptative"""
    print("🧪 Test de la stratégie hybride adaptative...")
    
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    # Extraire les critères des filtres
    auto_criteria = filters['auto_optimized']['filter_criteria']
    ultra_criteria = filters['ultra_selective']['filter_criteria']
    precision_criteria = filters['high_precision']['filter_criteria']
    
    # Résultats par catégorie
    results = {
        'auto_only': {'tokens': [], 'wins': 0, 'multiples': []},
        'ultra_hybrid': {'tokens': [], 'wins': 0, 'multiples': []},
        'precision_hybrid': {'tokens': [], 'wins': 0, 'multiples': []},
        'all_filters': {'tokens': [], 'wins': 0, 'multiples': []}
    }
    
    total_tokens = len(new_data)
    
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue
        
        # Vérifier chaque filtre
        auto_match = apply_filter_combination(token, auto_criteria)
        ultra_match = apply_filter_combination(token, ultra_criteria)
        precision_match = apply_filter_combination(token, precision_criteria)
        
        # Classifier le token
        if auto_match and ultra_match and precision_match:
            # Tous les filtres
            results['all_filters']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['all_filters']['wins'] += 1
                results['all_filters']['multiples'].append(success_map[token_address])
        
        elif auto_match and precision_match:
            # Auto + Haute Précision
            results['precision_hybrid']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['precision_hybrid']['wins'] += 1
                results['precision_hybrid']['multiples'].append(success_map[token_address])
        
        elif auto_match and ultra_match:
            # Auto + Ultra-Sélectif
            results['ultra_hybrid']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['ultra_hybrid']['wins'] += 1
                results['ultra_hybrid']['multiples'].append(success_map[token_address])
        
        elif auto_match:
            # Auto-Optimisé seulement
            results['auto_only']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['auto_only']['wins'] += 1
                results['auto_only']['multiples'].append(success_map[token_address])
    
    return results, total_tokens

def analyze_hybrid_strategy():
    """Analyse la stratégie hybride adaptative"""
    print("🎯 STRATÉGIE HYBRIDE ADAPTATIVE")
    print("=" * 60)
    print("Objectif: Auto-Optimisé (base) + Filtres spéciaux (adaptatif)")
    
    # Charger les filtres et données
    filters = load_all_filters()
    success_data, new_data = load_clean_data()
    
    if not filters or not success_data or not new_data:
        print("❌ Impossible de charger les données nécessaires")
        return
    
    # Tester la stratégie hybride
    results, total_tokens = test_hybrid_strategy(new_data, success_data, filters)
    
    # Analyser les résultats
    analyze_hybrid_results(results, total_tokens)
    
    # Sauvegarder les résultats
    save_hybrid_analysis(results, total_tokens)
    
    return results

def analyze_hybrid_results(results, total_tokens):
    """Analyse et affiche les résultats de la stratégie hybride"""
    print(f"\n📊 ANALYSE DES RÉSULTATS HYBRIDES")
    print("=" * 80)
    
    # Multiples de sortie à analyser
    exit_targets = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    for target in exit_targets:
        print(f"\n🎯 OBJECTIF DE SORTIE: {target:.1f}x")
        print("-" * 80)
        print(f"{'Catégorie':<20} {'Tokens':<8} {'Wins':<6} {'Winrate':<9} {'Rentabilité':<12} {'Avg':<6} {'Stratégie'}")
        print("-" * 80)
        
        for category, data in results.items():
            if data['tokens']:
                tokens_count = len(data['tokens'])
                wins = data['wins']
                winrate = (wins / tokens_count * 100) if tokens_count > 0 else 0
                
                # Calculer les wins pour ce multiple
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0
                
                # Calculer la rentabilité
                required_winrate = calculate_required_winrate(target)
                rentability = calculate_rentability(target_winrate, target)
                
                # Multiple moyen pour les wins >= target
                target_multiples = [m for m in data['multiples'] if m >= target]
                avg_multiple = np.mean(target_multiples) if target_multiples else 0
                
                # Déterminer la stratégie recommandée
                if category == 'all_filters':
                    strategy = "🚀 MAXIMUM (2x + mise élevée)"
                    exit_multiple = 2.0
                elif category == 'precision_hybrid':
                    strategy = "🎯 HAUTE PRÉCISION (2x)"
                    exit_multiple = 2.0
                elif category == 'ultra_hybrid':
                    strategy = "⚡ ULTRA-SÉLECTIF (1.5x + mise modérée)"
                    exit_multiple = 1.5
                else:  # auto_only
                    strategy = "📊 STANDARD (1.5x + mise normale)"
                    exit_multiple = 1.5
                
                status = "✅ RENTABLE" if rentability > 0 else "❌ NON RENTABLE"
                print(f"{category:<20} {tokens_count:<8} {target_wins:<6} {target_winrate:<8.2f}% {rentability:<11.3f} {avg_multiple:<5.1f}x {strategy}")
    
    # Recommandations stratégiques
    print(f"\n💡 RECOMMANDATIONS STRATÉGIQUES")
    print("=" * 80)
    
    for category, data in results.items():
        if data['tokens']:
            tokens_count = len(data['tokens'])
            coverage = (tokens_count / total_tokens * 100)
            
            print(f"\n📋 {category.upper()}:")
            print(f"   📊 Tokens: {tokens_count} ({coverage:.2f}% de couverture)")
            print(f"   🏆 Wins totaux: {data['wins']}")
            print(f"   📈 Winrate global: {(data['wins'] / tokens_count * 100):.2f}%")
            
            if data['multiples']:
                avg_multiple = np.mean(data['multiples'])
                median_multiple = np.median(data['multiples'])
                print(f"   📊 Multiple moyen: {avg_multiple:.2f}x")
                print(f"   📊 Multiple médian: {median_multiple:.2f}x")
            
            # Recommandation de stratégie
            if category == 'all_filters':
                print(f"   🚀 STRATÉGIE: Mise maximale + Sortie à 2.0x")
                print(f"   💰 Allocation: 80-100% du capital disponible")
            elif category == 'precision_hybrid':
                print(f"   🎯 STRATÉGIE: Mise élevée + Sortie à 2.0x")
                print(f"   💰 Allocation: 60-80% du capital disponible")
            elif category == 'ultra_hybrid':
                print(f"   ⚡ STRATÉGIE: Mise modérée + Sortie à 1.5x")
                print(f"   💰 Allocation: 40-60% du capital disponible")
            else:  # auto_only
                print(f"   📊 STRATÉGIE: Mise normale + Sortie à 1.5x")
                print(f"   💰 Allocation: 20-40% du capital disponible")
    
    # Stratégie globale
    print(f"\n🏆 STRATÉGIE GLOBALE RECOMMANDÉE")
    print("=" * 80)
    
    total_hybrid_tokens = sum(len(data['tokens']) for data in results.values())
    total_hybrid_wins = sum(data['wins'] for data in results.values())
    total_hybrid_winrate = (total_hybrid_wins / total_hybrid_tokens * 100) if total_hybrid_tokens > 0 else 0
    
    print(f"📊 PERFORMANCE GLOBALE:")
    print(f"   📋 Tokens totaux: {total_hybrid_tokens}")
    print(f"   🏆 Wins totaux: {total_hybrid_wins}")
    print(f"   📈 Winrate global: {total_hybrid_winrate:.2f}%")
    print(f"   📊 Couverture: {(total_hybrid_tokens / total_tokens * 100):.2f}%")
    
    print(f"\n📋 IMPLÉMENTATION:")
    print(f"   🎯 Base: Auto-Optimisé (tous les tokens)")
    print(f"   🚀 Upgrade: Haute Précision (mise élevée + 2.0x)")
    print(f"   ⚡ Upgrade: Ultra-Sélectif (mise modérée + 1.5x)")
    print(f"   💎 Maximum: Tous les filtres (mise maximale + 2.0x)")
    
    print(f"\n💰 GESTION DU CAPITAL:")
    print(f"   📊 20-40%: Auto-Optimisé seulement")
    print(f"   ⚡ 40-60%: + Ultra-Sélectif")
    print(f"   🎯 60-80%: + Haute Précision")
    print(f"   🚀 80-100%: Tous les filtres")

def save_hybrid_analysis(results, total_tokens):
    """Sauvegarde l'analyse hybride"""
    print(f"\n💾 Sauvegarde de l'analyse hybride...")
    
    output = {
        'created_at': datetime.now().isoformat(),
        'objective': 'Stratégie hybride adaptative - Auto-Optimisé + Filtres spéciaux',
        'total_tokens': total_tokens,
        'results': results,
        'strategy_summary': {
            'auto_only': {
                'tokens': len(results['auto_only']['tokens']),
                'wins': results['auto_only']['wins'],
                'winrate': (results['auto_only']['wins'] / len(results['auto_only']['tokens']) * 100) if results['auto_only']['tokens'] else 0,
                'strategy': 'Standard (1.5x + mise normale)'
            },
            'ultra_hybrid': {
                'tokens': len(results['ultra_hybrid']['tokens']),
                'wins': results['ultra_hybrid']['wins'],
                'winrate': (results['ultra_hybrid']['wins'] / len(results['ultra_hybrid']['tokens']) * 100) if results['ultra_hybrid']['tokens'] else 0,
                'strategy': 'Ultra-Sélectif (1.5x + mise modérée)'
            },
            'precision_hybrid': {
                'tokens': len(results['precision_hybrid']['tokens']),
                'wins': results['precision_hybrid']['wins'],
                'winrate': (results['precision_hybrid']['wins'] / len(results['precision_hybrid']['tokens']) * 100) if results['precision_hybrid']['tokens'] else 0,
                'strategy': 'Haute Précision (2.0x + mise élevée)'
            },
            'all_filters': {
                'tokens': len(results['all_filters']['tokens']),
                'wins': results['all_filters']['wins'],
                'winrate': (results['all_filters']['wins'] / len(results['all_filters']['tokens']) * 100) if results['all_filters']['tokens'] else 0,
                'strategy': 'Maximum (2.0x + mise maximale)'
            }
        }
    }
    
    filename = f"hybrid_adaptive_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✅ Analyse hybride sauvegardée: {filename}")

def main():
    """Fonction principale"""
    results = analyze_hybrid_strategy()
    
    if results:
        print(f"\n🎯 STRATÉGIE HYBRIDE TERMINÉE!")
        print("=" * 60)
        print(f"📊 4 catégories de tokens analysées")
        print(f"✅ Stratégie adaptative recommandée")
        print(f"💡 Gestion du capital optimisée")

if __name__ == "__main__":
    main()




