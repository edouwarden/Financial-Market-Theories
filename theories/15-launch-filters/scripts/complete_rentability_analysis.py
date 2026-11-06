#!/usr/bin/env python3
"""
Analyse Complète de Rentabilité - Tous les Multiples
Analyse la rentabilité de tous les multiples de sortie sur les 3 stratégies
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

def test_filter_with_all_multiples(new_data, success_data, filter_criteria, filter_name):
    """Teste un filtre avec tous les multiples de sortie"""
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    filtered_tokens = []
    win_multiples = []
    
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue
        
        # Appliquer le filtre
        if apply_filter_combination(token, filter_criteria):
            filtered_tokens.append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                win_multiples.append(success_map[token_address])
    
    # Calculer les métriques de base
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0
    
    # Multiples à tester (1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 9, 10, 15, 20, 50, 100)
    multiple_targets = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 15.0, 20.0, 50.0, 100.0]
    
    results = {}
    for target in multiple_targets:
        wins = sum(1 for multiple in win_multiples if multiple >= target)
        winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0
        
        # Calculer les multiples moyens et médians pour les wins >= target
        target_wins = [m for m in win_multiples if m >= target]
        avg_multiple = np.mean(target_wins) if target_wins else 0
        median_multiple = np.median(target_wins) if target_wins else 0
        
        # Calculer le winrate requis et la rentabilité
        required_winrate = calculate_required_winrate(target)
        rentability = calculate_rentability(winrate, target)
        is_profitable = rentability > 0
        
        # Score de rentabilité (basé sur l'excédent de winrate)
        winrate_excess = winrate - required_winrate
        profitability_score = winrate_excess * avg_multiple * (coverage / 100)
        
        results[target] = {
            'target': target,
            'wins': wins,
            'winrate': winrate,
            'required_winrate': required_winrate,
            'winrate_excess': winrate_excess,
            'rentability': rentability,
            'is_profitable': is_profitable,
            'avg_multiple': avg_multiple,
            'median_multiple': median_multiple,
            'profitability_score': profitability_score,
            'filtered_count': filtered_count,
            'coverage': coverage
        }
    
    return results

def analyze_all_strategies():
    """Analyse toutes les stratégies avec tous les multiples"""
    print("🎯 ANALYSE COMPLÈTE DE RENTABILITÉ")
    print("=" * 60)
    print("Objectif: Analyser la rentabilité de tous les multiples sur les 3 stratégies")
    
    # Charger les filtres et données
    filters = load_all_filters()
    success_data, new_data = load_clean_data()
    
    if not filters or not success_data or not new_data:
        print("❌ Impossible de charger les données nécessaires")
        return
    
    print(f"\n📊 Analyse de {len(filters)} stratégies...")
    
    all_results = {}
    
    # Tester chaque filtre
    for filter_name, filter_data in filters.items():
        print(f"\n🧪 Test de la stratégie: {filter_name}")
        
        if filter_name == 'ultra_selective':
            filter_criteria = filter_data['filter_criteria']
            display_name = "Ultra-Sélectif (16 critères)"
        elif filter_name == 'auto_optimized':
            filter_criteria = filter_data['filter_criteria']
            display_name = "Auto-Optimisé"
        elif filter_name == 'high_precision':
            filter_criteria = filter_data['filter_criteria']
            display_name = "Haute Précision"
        else:
            continue
        
        results = test_filter_with_all_multiples(new_data, success_data, filter_criteria, filter_name)
        all_results[display_name] = results
    
    # Analyser et afficher les résultats
    analyze_complete_results(all_results)
    
    # Sauvegarder les résultats
    save_complete_analysis(all_results)
    
    return all_results

def analyze_complete_results(all_results):
    """Analyse et affiche les résultats complets"""
    print(f"\n📊 ANALYSE COMPLÈTE DES RÉSULTATS")
    print("=" * 100)
    
    # Multiples à afficher
    display_multiples = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 50.0, 100.0]
    
    for target in display_multiples:
        print(f"\n🎯 MULTIPLE DE SORTIE: {target:.1f}x")
        print("-" * 100)
        print(f"{'Stratégie':<25} {'Winrate':<8} {'Requis':<8} {'Rentabilité':<12} {'Avg':<6} {'Median':<7} {'Rentable?'}")
        print("-" * 100)
        
        # Trier par rentabilité
        target_results = []
        for strategy_name, results in all_results.items():
            if target in results:
                result = results[target]
                target_results.append((strategy_name, result))
        
        # Trier par rentabilité décroissante
        target_results.sort(key=lambda x: x[1]['rentability'], reverse=True)
        
        for strategy_name, result in target_results:
            status = "✅ OUI" if result['is_profitable'] else "❌ NON"
            print(f"{strategy_name:<25} {result['winrate']:<7.2f}% {result['required_winrate']:<7.2f}% {result['rentability']:<11.3f} {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {status}")
    
    # Recommandations par stratégie
    print(f"\n💡 RECOMMANDATIONS PAR STRATÉGIE")
    print("=" * 100)
    
    for strategy_name, results in all_results.items():
        print(f"\n📋 {strategy_name}:")
        
        # Trouver les multiples rentables
        profitable_multiples = {k: v for k, v in results.items() if v['is_profitable']}
        
        if profitable_multiples:
            # Trouver le meilleur multiple (rentabilité maximale)
            best_multiple = max(profitable_multiples.items(), key=lambda x: x[1]['rentability'])
            target, best_result = best_multiple
            
            print(f"   🏆 Meilleur multiple: {target:.1f}x")
            print(f"   📊 Winrate: {best_result['winrate']:.1f}%")
            print(f"   💰 Rentabilité: +{best_result['rentability']:.3f} par trade")
            print(f"   📈 Multiple moyen: {best_result['avg_multiple']:.1f}x")
            print(f"   📊 Couverture: {best_result['coverage']:.1f}%")
            
            # Recommandation
            if best_result['winrate'] >= 60:
                print(f"   ✅ EXCELLENT: Allocation élevée recommandée")
            elif best_result['winrate'] >= 50:
                print(f"   🟡 BON: Allocation modérée recommandée")
            else:
                print(f"   🔴 MODÉRÉ: Allocation conservatrice recommandée")
        else:
            print(f"   ❌ Aucun multiple rentable trouvé")
    
    # Recommandation globale
    print(f"\n🏆 RECOMMANDATION GLOBALE")
    print("=" * 100)
    
    # Trouver la meilleure combinaison stratégie/multiple
    best_global = None
    best_global_rentability = 0
    
    for strategy_name, results in all_results.items():
        for target, result in results.items():
            if result['is_profitable'] and result['rentability'] > best_global_rentability:
                best_global_rentability = result['rentability']
                best_global = (strategy_name, target, result)
    
    if best_global:
        strategy_name, target, result = best_global
        print(f"🎯 CONFIGURATION OPTIMALE:")
        print(f"   📋 Stratégie: {strategy_name}")
        print(f"   🎯 Multiple de sortie: {target:.1f}x")
        print(f"   📊 Winrate: {result['winrate']:.1f}%")
        print(f"   💰 Rentabilité: +{result['rentability']:.3f} par trade")
        print(f"   📈 Multiple moyen: {result['avg_multiple']:.1f}x")
        print(f"   📊 Couverture: {result['coverage']:.1f}%")
        
        # Stratégie d'implémentation
        print(f"\n📋 STRATÉGIE D'IMPLÉMENTATION:")
        print(f"   🎯 Utilisez la stratégie: {strategy_name}")
        print(f"   📈 Objectif de sortie: {target:.1f}x")
        print(f"   💰 Allocation: {'Élevée' if result['winrate'] >= 60 else 'Modérée' if result['winrate'] >= 50 else 'Conservatrice'}")
        print(f"   ⏰ Fréquence: {'Rare' if result['coverage'] <= 5 else 'Modérée' if result['coverage'] <= 15 else 'Élevée'}")

def save_complete_analysis(all_results):
    """Sauvegarde l'analyse complète"""
    print(f"\n💾 Sauvegarde de l'analyse complète...")
    
    # Trouver la meilleure combinaison
    best_global = None
    best_global_rentability = 0
    
    for strategy_name, results in all_results.items():
        for target, result in results.items():
            if result['is_profitable'] and result['rentability'] > best_global_rentability:
                best_global_rentability = result['rentability']
                best_global = (strategy_name, target, result)
    
    output = {
        'created_at': datetime.now().isoformat(),
        'objective': 'Analyse complète de rentabilité - Tous les multiples sur les 3 stratégies',
        'strategies_analyzed': list(all_results.keys()),
        'best_combination': best_global,
        'all_results': all_results
    }
    
    filename = f"complete_rentability_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✅ Analyse complète sauvegardée: {filename}")

def main():
    """Fonction principale"""
    results = analyze_all_strategies()
    
    if results:
        print(f"\n🎯 ANALYSE COMPLÈTE TERMINÉE!")
        print("=" * 60)
        print(f"📊 {len(results)} stratégies analysées")
        print(f"📈 Multiples de 1.5x à 100x testés")
        print(f"✅ Recommandations optimales générées")

if __name__ == "__main__":
    main()




