#!/usr/bin/env python3
"""
Optimiseur Automatique de Filtres
Teste automatiquement de nombreuses combinaisons de paramètres
et compare leurs performances
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import itertools
import glob
from collections import defaultdict

def load_clean_data():
    """Charge les données nettoyées"""
    print("📊 Chargement des données nettoyées...")
    
    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)
    
    # Utiliser le dataset nettoyé le plus récent
    clean_files = glob.glob('data/raw/merged_new_data_clean_*.json')
    if clean_files:
        latest_clean_file = max(clean_files)
        with open(latest_clean_file, 'r') as f:
            new_data = json.load(f)
        print(f"✅ Utilisation du dataset nettoyé: {latest_clean_file}")
    else:
        print("❌ Aucun dataset nettoyé trouvé")
        return None, None
    
    print(f"✅ {len(success_data)} tokens de succès chargés")
    print(f"✅ {len(new_data)} tokens découverts (nettoyés) chargés")
    
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

def analyze_feature_distributions(new_data, success_data):
    """Analyse les distributions des caractéristiques pour créer des seuils"""
    print("\n📊 Analyse des distributions des caractéristiques...")
    
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    # Extraire les caractéristiques de tous les tokens
    all_features = []
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if token_address:
            features = extract_numeric_features(token)
            features['token_address'] = token_address
            features['is_success'] = token_address in success_map and success_map[token_address] >= 1.5
            if token_address in success_map:
                features['multiplication_factor'] = success_map[token_address]
            all_features.append(features)
    
    df = pd.DataFrame(all_features)
    
    # Analyser chaque caractéristique
    feature_analysis = {}
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']
    
    for feature in numeric_features:
        if feature in df.columns and not df[feature].isna().all():
            # Statistiques générales
            stats = df[feature].describe()
            
            # Statistiques par succès/échec
            success_stats = df[df['is_success'] == True][feature].describe()
            failure_stats = df[df['is_success'] == False][feature].describe()
            
            feature_analysis[feature] = {
                'general': stats,
                'success': success_stats,
                'failure': failure_stats,
                'percentiles': [5, 10, 25, 50, 75, 90, 95]
            }
    
    return feature_analysis, df

def generate_filter_combinations(feature_analysis):
    """Génère des combinaisons de filtres à tester"""
    print("\n🎯 Génération des combinaisons de filtres...")
    
    # Définir les stratégies de filtrage
    filter_strategies = {
        'priceUsd': {
            'min_thresholds': [0.00001, 0.00005, 0.0001, 0.0005, 0.001],
            'max_thresholds': [0.001, 0.005, 0.01, 0.05, 0.1]
        },
        'marketCap': {
            'min_thresholds': [1000, 5000, 10000, 50000, 100000],
            'max_thresholds': [100000, 500000, 1000000, 5000000, 10000000]
        },
        'fdv': {
            'min_thresholds': [1000, 5000, 10000, 50000, 100000],
            'max_thresholds': [100000, 500000, 1000000, 5000000, 10000000]
        },
        'liquidity': {
            'min_thresholds': [1000, 5000, 10000, 25000, 50000],
            'max_thresholds': [50000, 100000, 250000, 500000, 1000000]
        },
        'volume_24h': {
            'min_thresholds': [1000, 5000, 10000, 25000, 50000],
            'max_thresholds': [50000, 100000, 250000, 500000, 1000000]
        },
        'txns_24h': {
            'min_thresholds': [10, 50, 100, 250, 500],
            'max_thresholds': [500, 1000, 2500, 5000, 10000]
        },
        'txns_5m': {
            'min_thresholds': [1, 5, 10, 25, 50],
            'max_thresholds': [50, 100, 250, 500, 1000]
        }
    }
    
    # Générer des combinaisons simples (1-2 critères)
    simple_combinations = []
    
    # Filtres à un seul critère
    for feature, strategies in filter_strategies.items():
        for min_threshold in strategies['min_thresholds']:
            simple_combinations.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': min_threshold,
                'description': f"{feature} >= {min_threshold}"
            }])
        
        for max_threshold in strategies['max_thresholds']:
            simple_combinations.append([{
                'field': feature,
                'type': 'max_threshold',
                'value': max_threshold,
                'description': f"{feature} <= {max_threshold}"
            }])
    
    # Filtres à deux critères (combinaisons populaires)
    popular_combinations = [
        ('txns_5m', 'liquidity'),
        ('txns_5m', 'volume_24h'),
        ('liquidity', 'volume_24h'),
        ('marketCap', 'liquidity'),
        ('priceUsd', 'txns_5m'),
        ('txns_24h', 'txns_5m')
    ]
    
    for feature1, feature2 in popular_combinations:
        if feature1 in filter_strategies and feature2 in filter_strategies:
            for min1 in filter_strategies[feature1]['min_thresholds'][:3]:  # Limiter pour éviter trop de combinaisons
                for min2 in filter_strategies[feature2]['min_thresholds'][:3]:
                    simple_combinations.append([
                        {
                            'field': feature1,
                            'type': 'min_threshold',
                            'value': min1,
                            'description': f"{feature1} >= {min1}"
                        },
                        {
                            'field': feature2,
                            'type': 'min_threshold',
                            'value': min2,
                            'description': f"{feature2} >= {min2}"
                        }
                    ])
    
    # Filtres basés sur les percentiles des tokens de succès
    percentile_combinations = []
    
    # Analyser les percentiles des tokens de succès pour chaque caractéristique
    for feature in ['txns_5m', 'liquidity', 'volume_24h', 'marketCap']:
        if feature in feature_analysis:
            percentiles = feature_analysis[feature]['success'].quantile([0.25, 0.5, 0.75])
            
            for percentile, value in percentiles.items():
                if not pd.isna(value):
                    percentile_combinations.append([{
                        'field': feature,
                        'type': 'min_threshold',
                        'value': value,
                        'description': f"{feature} >= {value:.2f} ({percentile*100:.0f}e percentile succès)"
                    }])
    
    all_combinations = simple_combinations + percentile_combinations
    
    print(f"📋 {len(all_combinations)} combinaisons de filtres générées")
    
    return all_combinations

def apply_filter_combination(token_data, filter_combination):
    """Applique une combinaison de filtres à un token"""
    features = extract_numeric_features(token_data)
    
    # Vérifier chaque critère du filtre
    for criteria in filter_combination:
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

def test_filter_combination(new_data, success_data, filter_combination, filter_name):
    """Teste une combinaison de filtres"""
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    filtered_tokens = []
    wins = 0
    win_multiples = []
    
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue
        
        # Appliquer le filtre
        if apply_filter_combination(token, filter_combination):
            filtered_tokens.append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                wins += 1
                win_multiples.append(success_map[token_address])
    
    # Calculer les métriques
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0
    
    # Statistiques des multiples gagnants
    avg_multiple = np.mean(win_multiples) if win_multiples else 0
    median_multiple = np.median(win_multiples) if win_multiples else 0
    
    return {
        'filter_name': filter_name,
        'filter_combination': filter_combination,
        'filtered_count': filtered_count,
        'wins': wins,
        'winrate': winrate,
        'coverage': coverage,
        'total_tokens': total_tokens,
        'avg_multiple': avg_multiple,
        'median_multiple': median_multiple,
        'win_multiples': win_multiples
    }

def optimize_filters():
    """Fonction principale d'optimisation des filtres"""
    print("🚀 OPTIMISEUR AUTOMATIQUE DE FILTRES")
    print("=" * 60)
    
    # Charger les données
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return
    
    # Analyser les distributions
    feature_analysis, df = analyze_feature_distributions(new_data, success_data)
    
    # Générer les combinaisons de filtres
    filter_combinations = generate_filter_combinations(feature_analysis)
    
    print(f"\n🧪 Test de {len(filter_combinations)} combinaisons de filtres...")
    
    # Tester chaque combinaison
    results = []
    
    for i, combination in enumerate(filter_combinations, 1):
        if i % 50 == 0:
            print(f"   Progression: {i}/{len(filter_combinations)} ({i/len(filter_combinations)*100:.1f}%)")
        
        # Créer un nom pour le filtre
        filter_name = f"Filter_{i:04d}"
        
        # Tester la combinaison
        result = test_filter_combination(new_data, success_data, combination, filter_name)
        results.append(result)
    
    print(f"\n✅ Test terminé - {len(results)} filtres évalués")
    
    # Analyser les résultats
    analyze_results(results)
    
    # Sauvegarder les meilleurs filtres
    save_best_filters(results)
    
    return results

def analyze_results(results):
    """Analyse et affiche les résultats"""
    print(f"\n📊 ANALYSE DES RÉSULTATS")
    print("=" * 60)
    
    # Filtrer les résultats valides (au moins 10 tokens sélectionnés)
    valid_results = [r for r in results if r['filtered_count'] >= 10]
    
    print(f"📋 Filtres valides: {len(valid_results)}/{len(results)}")
    
    if not valid_results:
        print("❌ Aucun filtre valide trouvé")
        return
    
    # Trier par différents critères
    by_winrate = sorted(valid_results, key=lambda x: x['winrate'], reverse=True)
    by_coverage = sorted(valid_results, key=lambda x: x['coverage'], reverse=True)
    by_avg_multiple = sorted(valid_results, key=lambda x: x['avg_multiple'], reverse=True)
    by_median_multiple = sorted(valid_results, key=lambda x: x['median_multiple'], reverse=True)
    
    # Score composite (winrate * avg_multiple * coverage)
    for result in valid_results:
        result['composite_score'] = result['winrate'] * result['avg_multiple'] * result['coverage'] / 10000
    
    by_composite = sorted(valid_results, key=lambda x: x['composite_score'], reverse=True)
    
    # Afficher les meilleurs résultats
    print(f"\n🏆 TOP 10 PAR WINRATE:")
    print("-" * 60)
    print(f"{'Rank':<4} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Wins':<5} {'Filter'}")
    print("-" * 60)
    
    for i, result in enumerate(by_winrate[:10], 1):
        print(f"{i:<4} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['wins']:<5} {result['filter_name']}")
    
    print(f"\n🏆 TOP 10 PAR SCORE COMPOSITE:")
    print("-" * 60)
    print(f"{'Rank':<4} {'Score':<8} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Filter'}")
    print("-" * 60)
    
    for i, result in enumerate(by_composite[:10], 1):
        print(f"{i:<4} {result['composite_score']:<7.2f} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['filter_name']}")
    
    # Statistiques générales
    print(f"\n📊 STATISTIQUES GÉNÉRALES:")
    print("-" * 60)
    print(f"Winrate moyen: {np.mean([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Winrate médian: {np.median([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Winrate max: {max([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Winrate min: {min([r['winrate'] for r in valid_results]):.2f}%")
    
    print(f"\nCouverture moyenne: {np.mean([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Couverture médiane: {np.median([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Couverture max: {max([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Couverture min: {min([r['coverage'] for r in valid_results]):.2f}%")
    
    print(f"\nMultiple moyen moyen: {np.mean([r['avg_multiple'] for r in valid_results]):.2f}x")
    print(f"Multiple médian moyen: {np.mean([r['median_multiple'] for r in valid_results]):.2f}x")

def save_best_filters(results):
    """Sauvegarde les meilleurs filtres"""
    print(f"\n💾 Sauvegarde des meilleurs filtres...")
    
    # Filtrer les résultats valides
    valid_results = [r for r in results if r['filtered_count'] >= 10]
    
    if not valid_results:
        print("❌ Aucun filtre valide à sauvegarder")
        return
    
    # Calculer le score composite
    for result in valid_results:
        result['composite_score'] = result['winrate'] * result['avg_multiple'] * result['coverage'] / 10000
    
    # Trier par score composite
    best_results = sorted(valid_results, key=lambda x: x['composite_score'], reverse=True)
    
    # Sauvegarder les top 20
    output = {
        'created_at': datetime.now().isoformat(),
        'total_filters_tested': len(results),
        'valid_filters': len(valid_results),
        'best_filters': []
    }
    
    for i, result in enumerate(best_results[:20], 1):
        filter_info = {
            'rank': i,
            'filter_name': result['filter_name'],
            'filter_criteria': result['filter_combination'],
            'results': {
                'filtered_count': result['filtered_count'],
                'wins': result['wins'],
                'winrate': result['winrate'],
                'coverage': result['coverage'],
                'avg_multiple': result['avg_multiple'],
                'median_multiple': result['median_multiple'],
                'composite_score': result['composite_score']
            }
        }
        output['best_filters'].append(filter_info)
    
    # Sauvegarder
    filename = f"auto_optimized_filters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Meilleurs filtres sauvegardés: {filename}")
    
    # Sauvegarder aussi le meilleur filtre séparément
    if best_results:
        best_filter = best_results[0]
        best_filter_output = {
            'filter_name': f"Best_Auto_Filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'filter_criteria': best_filter['filter_combination'],
            'results': {
                'filtered_count': best_filter['filtered_count'],
                'wins': best_filter['wins'],
                'winrate': best_filter['winrate'],
                'coverage': best_filter['coverage'],
                'avg_multiple': best_filter['avg_multiple'],
                'median_multiple': best_filter['median_multiple'],
                'composite_score': best_filter['composite_score']
            },
            'created_at': datetime.now().isoformat(),
            'description': f"Meilleur filtre auto-optimisé - Score: {best_filter['composite_score']:.2f}"
        }
        
        best_filename = f"best_auto_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(best_filename, 'w') as f:
            json.dump(best_filter_output, f, indent=2)
        
        print(f"✅ Meilleur filtre sauvegardé: {best_filename}")
        print(f"🏆 Meilleur filtre: {best_filter['filter_name']}")
        print(f"   Winrate: {best_filter['winrate']:.2f}%")
        print(f"   Couverture: {best_filter['coverage']:.2f}%")
        print(f"   Multiple moyen: {best_filter['avg_multiple']:.2f}x")
        print(f"   Score composite: {best_filter['composite_score']:.2f}")

def main():
    """Fonction principale"""
    results = optimize_filters()
    
    if results:
        print(f"\n🎯 OPTIMISATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 60)
        print(f"📊 {len(results)} filtres testés")
        print(f"✅ Meilleurs filtres sauvegardés")
        print(f"💡 Consultez les fichiers JSON pour les détails complets")

if __name__ == "__main__":
    main()




