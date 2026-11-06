#!/usr/bin/env python3
"""
Optimiseur de Filtres Haute Précision
Objectif: Couverture réduite + Winrate maximal
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

def analyze_success_patterns(new_data, success_data):
    """Analyse les patterns des tokens de succès pour créer des filtres précis"""
    print("\n📊 Analyse des patterns des tokens de succès...")
    
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
    
    # Analyser les tokens de succès
    success_df = df[df['is_success'] == True]
    failure_df = df[df['is_success'] == False]
    
    print(f"📈 Tokens de succès: {len(success_df)}")
    print(f"📉 Tokens d'échec: {len(failure_df)}")
    
    # Analyser chaque caractéristique
    feature_analysis = {}
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']
    
    for feature in numeric_features:
        if feature in df.columns and not df[feature].isna().all():
            # Statistiques des succès
            success_stats = success_df[feature].describe()
            failure_stats = failure_df[feature].describe()
            
            # Calculer les seuils optimaux pour discriminer
            if not success_stats.empty and not failure_stats.empty:
                # Utiliser les percentiles élevés des succès
                success_75 = success_stats['75%']
                success_90 = success_stats.quantile(0.90)
                success_95 = success_stats.quantile(0.95)
                
                # Utiliser les percentiles bas des échecs
                failure_25 = failure_stats['25%']
                failure_10 = failure_stats.quantile(0.10)
                failure_5 = failure_stats.quantile(0.05)
                
                feature_analysis[feature] = {
                    'success_stats': success_stats,
                    'failure_stats': failure_stats,
                    'success_75': success_75,
                    'success_90': success_90,
                    'success_95': success_95,
                    'failure_25': failure_25,
                    'failure_10': failure_10,
                    'failure_5': failure_5
                }
    
    return feature_analysis, df

def generate_high_precision_filters(feature_analysis):
    """Génère des filtres haute précision avec couverture réduite"""
    print("\n🎯 Génération de filtres haute précision...")
    
    filters = []
    
    # Filtres basés sur les percentiles élevés des succès
    for feature, analysis in feature_analysis.items():
        if not pd.isna(analysis['success_75']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_75'],
                'description': f"{feature} >= {analysis['success_75']:.2f} (75e percentile succès)"
            }])
        
        if not pd.isna(analysis['success_90']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_90'],
                'description': f"{feature} >= {analysis['success_90']:.2f} (90e percentile succès)"
            }])
        
        if not pd.isna(analysis['success_95']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_95'],
                'description': f"{feature} >= {analysis['success_95']:.2f} (95e percentile succès)"
            }])
    
    # Filtres combinés (2-3 critères) pour haute précision
    high_precision_combinations = [
        ('txns_5m', 'liquidity'),
        ('txns_5m', 'volume_24h'),
        ('liquidity', 'volume_24h'),
        ('txns_5m', 'liquidity', 'volume_24h'),
        ('marketCap', 'liquidity', 'txns_5m'),
        ('priceUsd', 'txns_5m', 'liquidity')
    ]
    
    for combination in high_precision_combinations:
        if len(combination) == 2:
            feature1, feature2 = combination
            if feature1 in feature_analysis and feature2 in feature_analysis:
                # Utiliser des seuils élevés pour chaque caractéristique
                for percentile in [75, 90, 95]:
                    if not pd.isna(feature_analysis[feature1][f'success_{percentile}']) and \
                       not pd.isna(feature_analysis[feature2][f'success_{percentile}']):
                        filters.append([
                            {
                                'field': feature1,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature1][f'success_{percentile}'],
                                'description': f"{feature1} >= {feature_analysis[feature1][f'success_{percentile}']:.2f} ({percentile}e percentile)"
                            },
                            {
                                'field': feature2,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature2][f'success_{percentile}'],
                                'description': f"{feature2} >= {feature_analysis[feature2][f'success_{percentile}']:.2f} ({percentile}e percentile)"
                            }
                        ])
        
        elif len(combination) == 3:
            feature1, feature2, feature3 = combination
            if all(f in feature_analysis for f in [feature1, feature2, feature3]):
                # Utiliser des seuils élevés pour les 3 caractéristiques
                for percentile in [75, 90]:
                    if all(not pd.isna(feature_analysis[f][f'success_{percentile}']) for f in [feature1, feature2, feature3]):
                        filters.append([
                            {
                                'field': feature1,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature1][f'success_{percentile}'],
                                'description': f"{feature1} >= {feature_analysis[feature1][f'success_{percentile}']:.2f} ({percentile}e percentile)"
                            },
                            {
                                'field': feature2,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature2][f'success_{percentile}'],
                                'description': f"{feature2} >= {feature_analysis[feature2][f'success_{percentile}']:.2f} ({percentile}e percentile)"
                            },
                            {
                                'field': feature3,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature3][f'success_{percentile}'],
                                'description': f"{feature3} >= {feature_analysis[feature3][f'success_{percentile}']:.2f} ({percentile}e percentile)"
                            }
                        ])
    
    # Filtres ultra-stricts (seuils très élevés)
    ultra_strict_filters = []
    for feature, analysis in feature_analysis.items():
        if not pd.isna(analysis['success_95']):
            # Seuil ultra-strict (95e percentile + 20%)
            ultra_strict_value = analysis['success_95'] * 1.2
            ultra_strict_filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': ultra_strict_value,
                'description': f"{feature} >= {ultra_strict_value:.2f} (ultra-strict)"
            }])
    
    filters.extend(ultra_strict_filters)
    
    print(f"📋 {len(filters)} filtres haute précision générés")
    
    return filters

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

def test_high_precision_filter(new_data, success_data, filter_combination, filter_name):
    """Teste un filtre haute précision"""
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
    
    # Score de précision (winrate élevé + couverture faible)
    precision_score = winrate * (1 - coverage/100) * 100
    
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
        'precision_score': precision_score,
        'win_multiples': win_multiples
    }

def optimize_high_precision_filters():
    """Fonction principale d'optimisation des filtres haute précision"""
    print("🎯 OPTIMISEUR DE FILTRES HAUTE PRÉCISION")
    print("=" * 60)
    print("Objectif: Couverture réduite + Winrate maximal")
    
    # Charger les données
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return
    
    # Analyser les patterns de succès
    feature_analysis, df = analyze_success_patterns(new_data, success_data)
    
    # Générer les filtres haute précision
    filter_combinations = generate_high_precision_filters(feature_analysis)
    
    print(f"\n🧪 Test de {len(filter_combinations)} filtres haute précision...")
    
    # Tester chaque combinaison
    results = []
    
    for i, combination in enumerate(filter_combinations, 1):
        if i % 20 == 0:
            print(f"   Progression: {i}/{len(filter_combinations)} ({i/len(filter_combinations)*100:.1f}%)")
        
        # Créer un nom pour le filtre
        filter_name = f"HighPrecision_{i:04d}"
        
        # Tester la combinaison
        result = test_high_precision_filter(new_data, success_data, combination, filter_name)
        results.append(result)
    
    print(f"\n✅ Test terminé - {len(results)} filtres évalués")
    
    # Analyser les résultats
    analyze_high_precision_results(results)
    
    # Sauvegarder les meilleurs filtres
    save_high_precision_filters(results)
    
    return results

def analyze_high_precision_results(results):
    """Analyse et affiche les résultats des filtres haute précision"""
    print(f"\n📊 ANALYSE DES RÉSULTATS HAUTE PRÉCISION")
    print("=" * 60)
    
    # Filtrer les résultats valides (au moins 5 tokens sélectionnés)
    valid_results = [r for r in results if r['filtered_count'] >= 5]
    
    print(f"📋 Filtres valides: {len(valid_results)}/{len(results)}")
    
    if not valid_results:
        print("❌ Aucun filtre valide trouvé")
        return
    
    # Trier par différents critères
    by_winrate = sorted(valid_results, key=lambda x: x['winrate'], reverse=True)
    by_precision_score = sorted(valid_results, key=lambda x: x['precision_score'], reverse=True)
    by_coverage_low = sorted(valid_results, key=lambda x: x['coverage'])  # Couverture faible en premier
    
    # Afficher les meilleurs résultats par winrate
    print(f"\n🏆 TOP 10 PAR WINRATE:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Wins':<5} {'Filter'}")
    print("-" * 70)
    
    for i, result in enumerate(by_winrate[:10], 1):
        print(f"{i:<4} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['wins']:<5} {result['filter_name']}")
    
    # Afficher les meilleurs résultats par score de précision
    print(f"\n🏆 TOP 10 PAR SCORE DE PRÉCISION:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Score':<8} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Filter'}")
    print("-" * 70)
    
    for i, result in enumerate(by_precision_score[:10], 1):
        print(f"{i:<4} {result['precision_score']:<7.2f} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['filter_name']}")
    
    # Afficher les filtres avec couverture la plus faible
    print(f"\n🎯 TOP 10 COUVERTURE LA PLUS FAIBLE:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Coverage':<9} {'Winrate':<8} {'Avg':<6} {'Median':<7} {'Wins':<5} {'Filter'}")
    print("-" * 70)
    
    for i, result in enumerate(by_coverage_low[:10], 1):
        print(f"{i:<4} {result['coverage']:<8.2f}% {result['winrate']:<7.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['wins']:<5} {result['filter_name']}")
    
    # Statistiques générales
    print(f"\n📊 STATISTIQUES GÉNÉRALES:")
    print("-" * 60)
    print(f"Winrate moyen: {np.mean([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Winrate max: {max([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Couverture moyenne: {np.mean([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Couverture min: {min([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Multiple moyen moyen: {np.mean([r['avg_multiple'] for r in valid_results]):.2f}x")

def save_high_precision_filters(results):
    """Sauvegarde les meilleurs filtres haute précision"""
    print(f"\n💾 Sauvegarde des meilleurs filtres haute précision...")
    
    # Filtrer les résultats valides
    valid_results = [r for r in results if r['filtered_count'] >= 5]
    
    if not valid_results:
        print("❌ Aucun filtre valide à sauvegarder")
        return
    
    # Trier par score de précision
    best_results = sorted(valid_results, key=lambda x: x['precision_score'], reverse=True)
    
    # Sauvegarder les top 20
    output = {
        'created_at': datetime.now().isoformat(),
        'total_filters_tested': len(results),
        'valid_filters': len(valid_results),
        'objective': 'Haute précision - Couverture réduite + Winrate maximal',
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
                'precision_score': result['precision_score']
            }
        }
        output['best_filters'].append(filter_info)
    
    # Sauvegarder
    filename = f"high_precision_filters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Meilleurs filtres haute précision sauvegardés: {filename}")
    
    # Sauvegarder aussi le meilleur filtre séparément
    if best_results:
        best_filter = best_results[0]
        best_filter_output = {
            'filter_name': f"Best_High_Precision_Filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'filter_criteria': best_filter['filter_combination'],
            'results': {
                'filtered_count': best_filter['filtered_count'],
                'wins': best_filter['wins'],
                'winrate': best_filter['winrate'],
                'coverage': best_filter['coverage'],
                'avg_multiple': best_filter['avg_multiple'],
                'median_multiple': best_filter['median_multiple'],
                'precision_score': best_filter['precision_score']
            },
            'created_at': datetime.now().isoformat(),
            'description': f"Meilleur filtre haute précision - Score: {best_filter['precision_score']:.2f}"
        }
        
        best_filename = f"best_high_precision_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(best_filename, 'w') as f:
            json.dump(best_filter_output, f, indent=2)
        
        print(f"✅ Meilleur filtre haute précision sauvegardé: {best_filename}")
        print(f"🏆 Meilleur filtre: {best_filter['filter_name']}")
        print(f"   Winrate: {best_filter['winrate']:.2f}%")
        print(f"   Couverture: {best_filter['coverage']:.2f}%")
        print(f"   Multiple moyen: {best_filter['avg_multiple']:.2f}x")
        print(f"   Score de précision: {best_filter['precision_score']:.2f}")

def main():
    """Fonction principale"""
    results = optimize_high_precision_filters()
    
    if results:
        print(f"\n🎯 OPTIMISATION HAUTE PRÉCISION TERMINÉE!")
        print("=" * 60)
        print(f"📊 {len(results)} filtres testés")
        print(f"✅ Meilleurs filtres haute précision sauvegardés")
        print(f"💡 Objectif atteint: Couverture réduite + Winrate maximal")

if __name__ == "__main__":
    main()
