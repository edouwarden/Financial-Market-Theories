#!/usr/bin/env python3
"""
Stratégie Hybride Adaptative avec Frais de Transaction
Intègre les frais de 2% dans le calcul de rentabilité
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

def calculate_required_winrate_with_fees(multiple, fees_percent=2.0):
    """Calcule le winrate requis pour être rentable avec frais"""
    # Frais d'entrée et de sortie
    entry_fees = fees_percent / 100
    exit_fees = fees_percent / 100
    
    # Pour être rentable: (winrate * (multiple - exit_fees)) - (1 - winrate) - entry_fees > 0
    # winrate * (multiple - exit_fees) - 1 + winrate - entry_fees > 0
    # winrate * (multiple - exit_fees + 1) > 1 + entry_fees
    # winrate > (1 + entry_fees) / (multiple - exit_fees + 1)
    required_winrate = (1 + entry_fees) / (multiple - exit_fees + 1) * 100
    return required_winrate

def calculate_rentability_with_fees(winrate, multiple, fees_percent=2.0):
    """Calcule la rentabilité avec frais de transaction"""
    loss_rate = 100 - winrate
    entry_fees = fees_percent / 100
    exit_fees = fees_percent / 100
    
    # Gain net = (winrate * (multiple - exit_fees)) - (1 - winrate) - entry_fees
    gain_per_trade = (winrate/100 * (multiple - exit_fees)) - (loss_rate/100 * 1) - entry_fees
    return gain_per_trade

def test_hybrid_strategy_with_fees(new_data, success_data, filters):
    """Teste la stratégie hybride avec frais de transaction"""
    print("🧪 Test de la stratégie hybride avec frais de 2%...")
    
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

def analyze_hybrid_strategy_with_fees():
    """Analyse la stratégie hybride avec frais de transaction"""
    print("🎯 STRATÉGIE HYBRIDE AVEC FRAIS DE TRANSACTION")
    print("=" * 60)
    print("Objectif: Analyser la rentabilité avec frais de 2%")
    
    # Charger les filtres et données
    filters = load_all_filters()
    success_data, new_data = load_clean_data()
    
    if not filters or not success_data or not new_data:
        print("❌ Impossible de charger les données nécessaires")
        return
    
    # Tester la stratégie hybride
    results, total_tokens = test_hybrid_strategy_with_fees(new_data, success_data, filters)
    
    # Analyser les résultats avec frais
    analyze_hybrid_results_with_fees(results, total_tokens)
    
    # Sauvegarder les résultats
    save_hybrid_analysis_with_fees(results, total_tokens)
    
    return results

def analyze_hybrid_results_with_fees(results, total_tokens):
    """Analyse et affiche les résultats avec frais de transaction"""
    print(f"\n📊 ANALYSE AVEC FRAIS DE 2%")
    print("=" * 80)
    
    # Multiples de sortie à analyser
    exit_targets = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    for target in exit_targets:
        print(f"\n🎯 OBJECTIF DE SORTIE: {target:.1f}x")
        print("-" * 80)
        print(f"{'Catégorie':<20} {'Tokens':<8} {'Wins':<6} {'Winrate':<9} {'Requis':<8} {'Rentabilité':<12} {'Stratégie'}")
        print("-" * 80)
        
        for category, data in results.items():
            if data['tokens']:
                tokens_count = len(data['tokens'])
                wins = data['wins']
                winrate = (wins / tokens_count * 100) if tokens_count > 0 else 0
                
                # Calculer les wins pour ce multiple
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0
                
                # Calculer la rentabilité avec frais
                required_winrate = calculate_required_winrate_with_fees(target, 2.0)
                rentability = calculate_rentability_with_fees(target_winrate, target, 2.0)
                
                # Déterminer la stratégie recommandée
                if category == 'all_filters':
                    strategy = "🚀 MAXIMUM (2x + mise élevée)"
                elif category == 'precision_hybrid':
                    strategy = "🎯 HAUTE PRÉCISION (2x)"
                elif category == 'ultra_hybrid':
                    strategy = "⚡ ULTRA-SÉLECTIF (1.5x + mise modérée)"
                else:  # auto_only
                    strategy = "📊 STANDARD (1.5x + mise normale)"
                
                status = "✅ RENTABLE" if rentability > 0 else "❌ NON RENTABLE"
                print(f"{category:<20} {tokens_count:<8} {target_wins:<6} {target_winrate:<8.2f}% {required_winrate:<7.2f}% {rentability:<11.3f} {strategy}")
    
    # Comparaison avec/sans frais
    print(f"\n📊 COMPARAISON AVEC/SANS FRAIS")
    print("=" * 80)
    
    comparison_targets = [1.5, 2.0, 2.5, 3.0]
    
    for target in comparison_targets:
        print(f"\n🎯 Multiple {target:.1f}x:")
        print(f"{'Catégorie':<20} {'Sans Frais':<12} {'Avec Frais':<12} {'Différence':<12}")
        print("-" * 60)
        
        for category, data in results.items():
            if data['tokens']:
                tokens_count = len(data['tokens'])
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0
                
                # Rentabilité sans frais
                rentability_no_fees = calculate_rentability_with_fees(target_winrate, target, 0.0)
                
                # Rentabilité avec frais
                rentability_with_fees = calculate_rentability_with_fees(target_winrate, target, 2.0)
                
                # Différence
                difference = rentability_with_fees - rentability_no_fees
                
                print(f"{category:<20} {rentability_no_fees:<11.3f} {rentability_with_fees:<11.3f} {difference:<11.3f}")
    
    # Recommandations stratégiques avec frais
    print(f"\n💡 RECOMMANDATIONS AVEC FRAIS DE 2%")
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
            
            # Analyser la rentabilité avec frais pour différents multiples
            print(f"   💰 RENTABILITÉ AVEC FRAIS:")
            for target in [1.5, 2.0, 2.5, 3.0]:
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0
                required_winrate = calculate_required_winrate_with_fees(target, 2.0)
                rentability = calculate_rentability_with_fees(target_winrate, target, 2.0)
                
                status = "✅ RENTABLE" if rentability > 0 else "❌ NON RENTABLE"
                print(f"     {target:.1f}x: {target_winrate:.1f}% vs {required_winrate:.1f}% requis → {rentability:.3f} ({status})")
            
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
    
    # Impact des frais sur la stratégie globale
    print(f"\n⚠️  IMPACT DES FRAIS SUR LA STRATÉGIE")
    print("=" * 80)
    
    print(f"📊 FRAIS DE TRANSACTION:")
    print(f"   💸 Frais d'entrée: 2%")
    print(f"   💸 Frais de sortie: 2%")
    print(f"   💸 Total par trade: 4% (entrée + sortie)")
    
    print(f"\n📈 SEUILS DE RENTABILITÉ AVEC FRAIS:")
    for target in [1.5, 2.0, 2.5, 3.0]:
        required = calculate_required_winrate_with_fees(target, 2.0)
        print(f"   {target:.1f}x: {required:.1f}% de winrate requis")
    
    print(f"\n💡 RECOMMANDATIONS ADAPTÉES:")
    print(f"   🎯 Augmenter les objectifs de sortie pour compenser les frais")
    print(f"   📊 Privilégier les stratégies à haute qualité (moins de trades)")
    print(f"   💰 Optimiser la taille des positions pour maximiser le ROI")

def save_hybrid_analysis_with_fees(results, total_tokens):
    """Sauvegarde l'analyse hybride avec frais"""
    print(f"\n💾 Sauvegarde de l'analyse avec frais...")
    
    output = {
        'created_at': datetime.now().isoformat(),
        'objective': 'Stratégie hybride adaptative avec frais de transaction de 2%',
        'fees_percent': 2.0,
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
    
    filename = f"hybrid_strategy_with_fees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✅ Analyse avec frais sauvegardée: {filename}")

def main():
    """Fonction principale"""
    results = analyze_hybrid_strategy_with_fees()
    
    if results:
        print(f"\n🎯 ANALYSE AVEC FRAIS TERMINÉE!")
        print("=" * 60)
        print(f"📊 Impact des frais de 2% analysé")
        print(f"✅ Recommandations adaptées générées")
        print(f"💡 Stratégie optimisée pour les frais")

if __name__ == "__main__":
    main()




