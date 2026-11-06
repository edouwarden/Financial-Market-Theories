#!/usr/bin/env python3
"""
Filtre Ultra-Sélectif avec Données Nettoyées
Recalcul du filtre sans doublons pour des résultats précis
"""

import json
import pandas as pd
from datetime import datetime
import numpy as np

def load_clean_data():
    """Charge les données nettoyées"""
    print("📊 Chargement des données nettoyées...")
    
    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)
    
    # Utiliser le dataset nettoyé le plus récent
    import glob
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

def analyze_ultra_performers_clean(success_data, new_data):
    """Analyse les tokens ultra-performants avec données nettoyées"""
    print("\n🔍 Analyse des tokens ultra-performants (données nettoyées)...")
    
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    # Extraire les caractéristiques des tokens de succès
    success_features = []
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if token_address and token_address in success_map:
            features = extract_numeric_features(token)
            features['token_address'] = token_address
            features['multiplication_factor'] = success_map[token_address]
            success_features.append(features)
    
    df = pd.DataFrame(success_features)
    print(f"📈 {len(df)} tokens de succès avec caractéristiques extraites")
    
    # Analyser les percentiles de multiplication factor
    df_sorted = df.sort_values('multiplication_factor', ascending=False)
    
    # Top 1% (environ 48 tokens)
    top_1_percent = df_sorted.head(max(1, len(df_sorted) // 100))
    print(f"\n🏆 Top 1% ({len(top_1_percent)} tokens):")
    print(f"   Multiplication factor min: {top_1_percent['multiplication_factor'].min():.1f}")
    print(f"   Multiplication factor max: {top_1_percent['multiplication_factor'].max():.1f}")
    print(f"   Multiplication factor moyen: {top_1_percent['multiplication_factor'].mean():.1f}")
    
    # Top 0.1% (environ 5 tokens)
    top_01_percent = df_sorted.head(max(1, len(df_sorted) // 1000))
    print(f"\n👑 Top 0.1% ({len(top_01_percent)} tokens):")
    print(f"   Multiplication factor min: {top_01_percent['multiplication_factor'].min():.1f}")
    print(f"   Multiplication factor max: {top_01_percent['multiplication_factor'].max():.1f}")
    print(f"   Multiplication factor moyen: {top_01_percent['multiplication_factor'].mean():.1f}")
    
    return df, top_1_percent, top_01_percent

def create_ultra_selective_filters_clean(df, top_1_percent, top_01_percent):
    """Crée des filtres ultra-sélectifs basés sur les caractéristiques des meilleurs tokens"""
    print("\n🎯 Création de filtres ultra-sélectifs (données nettoyées)...")
    
    filters = []
    
    # Analyser chaque caractéristique pour les top 1%
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']
    
    for feature in numeric_features:
        if feature in top_1_percent.columns and not top_1_percent[feature].isna().all():
            # Statistiques des top 1%
            top_stats = top_1_percent[feature].describe()
            
            # Créer des filtres basés sur les percentiles des top 1%
            if not pd.isna(top_stats['25%']):
                filters.append({
                    'field': feature,
                    'type': 'min_threshold',
                    'value': top_stats['25%'],
                    'description': f"{feature} >= {top_stats['25%']:.6f} (25e percentile des top 1%)",
                    'percentile': 25
                })
            
            if not pd.isna(top_stats['75%']):
                filters.append({
                    'field': feature,
                    'type': 'max_threshold',
                    'value': top_stats['75%'],
                    'description': f"{feature} <= {top_stats['75%']:.6f} (75e percentile des top 1%)",
                    'percentile': 75
                })
    
    # Analyser les combinaisons de critères
    print(f"\n📋 {len(filters)} critères de filtrage créés")
    
    return filters

def test_ultra_filter_clean(new_data, success_data, filters, filter_name="Ultra-Sélectif Clean"):
    """Teste un filtre ultra-sélectif avec données nettoyées"""
    print(f"\n🧪 Test du filtre {filter_name}...")
    
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    filtered_tokens = []
    wins = 0
    
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue
        
        # Extraire les caractéristiques
        features = extract_numeric_features(token)
        
        # Appliquer tous les filtres
        passes_all_filters = True
        for filter_criteria in filters:
            field = filter_criteria['field']
            filter_type = filter_criteria['type']
            value = filter_criteria['value']
            
            if field not in features or features[field] is None:
                passes_all_filters = False
                break
            
            if filter_type == 'min_threshold' and features[field] < value:
                passes_all_filters = False
                break
            elif filter_type == 'max_threshold' and features[field] > value:
                passes_all_filters = False
                break
        
        if passes_all_filters:
            filtered_tokens.append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                wins += 1
    
    # Calculer les métriques
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0
    
    print(f"📊 Résultats du filtre {filter_name}:")
    print(f"   Tokens filtrés: {filtered_count:,}")
    print(f"   Wins: {wins:,}")
    print(f"   Winrate: {winrate:.2f}%")
    print(f"   Couverture: {coverage:.2f}%")
    print(f"   Total tokens: {total_tokens:,}")
    
    return {
        'filtered_count': filtered_count,
        'wins': wins,
        'winrate': winrate,
        'total_tokens': total_tokens,
        'coverage': coverage,
        'filtered_tokens': filtered_tokens
    }

def create_combined_ultra_filter_clean(df, top_1_percent):
    """Crée un filtre combiné ultra-sélectif avec données nettoyées"""
    print("\n🔧 Création d'un filtre combiné ultra-sélectif (données nettoyées)...")
    
    # Identifier les caractéristiques les plus discriminantes
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']
    
    best_filters = []
    
    for feature in numeric_features:
        if feature in top_1_percent.columns and not top_1_percent[feature].isna().all():
            # Utiliser le 50e percentile des top 1% comme seuil
            median_value = top_1_percent[feature].median()
            if not pd.isna(median_value):
                best_filters.append({
                    'field': feature,
                    'type': 'min_threshold',
                    'value': median_value,
                    'description': f"{feature} >= {median_value:.6f} (médiane des top 1%)"
                })
    
    return best_filters

def save_ultra_filter_clean(filter_config, results, filter_name):
    """Sauvegarde le filtre ultra-sélectif nettoyé"""
    output = {
        'filter_name': filter_name,
        'filter_criteria': filter_config,
        'results': results,
        'created_at': datetime.now().isoformat(),
        'description': f"Filtre ultra-sélectif avec données nettoyées - {filter_name}"
    }
    
    filename = f"{filter_name.lower().replace(' ', '_')}_clean_filter.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Filtre sauvegardé dans {filename}")
    return filename

def main():
    """Fonction principale"""
    print("🎯 FILTRE ULTRA-SÉLECTIF - Données Nettoyées")
    print("=" * 60)
    
    # Charger les données nettoyées
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return
    
    # Analyser les ultra-performants
    df, top_1_percent, top_01_percent = analyze_ultra_performers_clean(success_data, new_data)
    
    # Créer des filtres ultra-sélectifs
    filters_1_percent = create_ultra_selective_filters_clean(df, top_1_percent, top_01_percent)
    
    # Tester le filtre basé sur les top 1%
    results_1_percent = test_ultra_filter_clean(new_data, success_data, filters_1_percent, "Top 1% Clean")
    
    # Créer un filtre combiné plus strict
    combined_filters = create_combined_ultra_filter_clean(df, top_1_percent)
    results_combined = test_ultra_filter_clean(new_data, success_data, combined_filters, "Combiné Ultra Clean")
    
    # Sauvegarder le meilleur filtre
    if results_combined['winrate'] > results_1_percent['winrate']:
        best_results = results_combined
        best_filters = combined_filters
        best_name = "Combiné Ultra Clean"
    else:
        best_results = results_1_percent
        best_filters = filters_1_percent
        best_name = "Top 1% Clean"
    
    save_ultra_filter_clean(best_filters, best_results, best_name)
    
    # Résumé final
    print("\n" + "=" * 60)
    print("🎯 RÉSUMÉ FINAL - Filtre Ultra-Sélectif (Données Nettoyées)")
    print("=" * 60)
    print(f"🏆 Meilleur filtre: {best_name}")
    print(f"📊 Winrate: {best_results['winrate']:.2f}%")
    print(f"🎯 Couverture: {best_results['coverage']:.2f}%")
    print(f"📈 Tokens sélectionnés: {best_results['filtered_count']:,}")
    print(f"💰 Wins: {best_results['wins']:,}")
    
    if best_results['winrate'] >= 80:
        print("✅ EXCELLENT: Winrate très élevé!")
    elif best_results['winrate'] >= 70:
        print("🟡 BON: Winrate élevé")
    else:
        print("🔴 À AMÉLIORER: Winrate modéré")
    
    print("\n💡 Recommandation: Utilisez ce filtre pour des trades ultra-sélectifs")
    print("   avec des données propres et des résultats précis.")

if __name__ == "__main__":
    main()




