#!/usr/bin/env python3
import json
import pandas as pd
from datetime import datetime
import numpy as np
from collections import defaultdict

def load_data():
    """Charge les données des fichiers JSON"""
    print("Chargement des données...")
    
    # Charger les données de succès (tokens qui ont atteint 50x ou plus)
    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)
    
    # Charger les données de découverte (tokens nouveaux)
    with open('data/raw/merged_new_data.json', 'r') as f:
        new_data = json.load(f)
    
    print(f"Données de succès chargées: {len(success_data)} entrées")
    print(f"Données de découverte chargées: {len(new_data)} entrées")
    
    return success_data, new_data

def analyze_success_patterns(success_data, new_data):
    """Analyse les patterns des tokens qui ont réussi"""
    print("\nAnalyse des patterns de succès...")
    
    # Créer un dictionnaire des tokens qui ont réussi (50x ou plus)
    successful_tokens = {}
    for entry in success_data:
        token_address = entry['token_address']
        multiplication_factor = entry['multiplication_factor_from_new_adding']
        if multiplication_factor >= 50:
            successful_tokens[token_address] = {
                'factor': multiplication_factor,
                'date': entry['multiplication_date']
            }
    
    print(f"Tokens avec 50x ou plus: {len(successful_tokens)}")
    
    # Trouver les données de découverte correspondantes
    discovery_data = {}
    for entry in new_data:
        token_address = entry.get('baseToken', {}).get('address', '')
        if token_address in successful_tokens:
            discovery_data[token_address] = {
                'success_info': successful_tokens[token_address],
                'discovery_info': entry
            }
    
    print(f"Tokens trouvés dans les données de découverte: {len(discovery_data)}")
    
    return discovery_data

def extract_features_safe(entry):
    """Extrait les caractéristiques de manière sécurisée"""
    try:
        return {
            'token_address': entry.get('baseToken', {}).get('address', ''),
            'symbol': entry.get('baseToken', {}).get('symbol', ''),
            'name': entry.get('baseToken', {}).get('name', ''),
            'dex_id': entry.get('dexId', ''),
            'price_usd': float(entry.get('priceUsd', 0)) if entry.get('priceUsd') else 0,
            'price_native': float(entry.get('priceNative', 0)) if entry.get('priceNative') else 0,
            'volume_h24': entry.get('volume', {}).get('h24', 0) if entry.get('volume') else 0,
            'volume_h6': entry.get('volume', {}).get('h6', 0) if entry.get('volume') else 0,
            'volume_h1': entry.get('volume', {}).get('h1', 0) if entry.get('volume') else 0,
            'volume_m5': entry.get('volume', {}).get('m5', 0) if entry.get('volume') else 0,
            'liquidity_usd': entry.get('liquidity', {}).get('usd', 0) if entry.get('liquidity') else 0,
            'liquidity_base': entry.get('liquidity', {}).get('base', 0) if entry.get('liquidity') else 0,
            'liquidity_quote': entry.get('liquidity', {}).get('quote', 0) if entry.get('liquidity') else 0,
            'fdv': entry.get('fdv', 0),
            'market_cap': entry.get('marketCap', 0),
            'txns_buys_m5': entry.get('txns', {}).get('m5', {}).get('buys', 0) if entry.get('txns') else 0,
            'txns_sells_m5': entry.get('txns', {}).get('m5', {}).get('sells', 0) if entry.get('txns') else 0,
            'txns_buys_h1': entry.get('txns', {}).get('h1', {}).get('buys', 0) if entry.get('txns') else 0,
            'txns_sells_h1': entry.get('txns', {}).get('h1', {}).get('sells', 0) if entry.get('txns') else 0,
            'price_change_m5': entry.get('priceChange', {}).get('m5', 0) if entry.get('priceChange') else 0,
            'price_change_h1': entry.get('priceChange', {}).get('h1', 0) if entry.get('priceChange') else 0,
            'price_change_h6': entry.get('priceChange', {}).get('h6', 0) if entry.get('priceChange') else 0,
            'price_change_h24': entry.get('priceChange', {}).get('h24', 0) if entry.get('priceChange') else 0,
            'labels': entry.get('labels', []),
            'source_date': entry.get('source_date', ''),
            'source_file': entry.get('source_file', '')
        }
    except Exception as e:
        print(f"Erreur lors de l'extraction des caractéristiques: {e}")
        return None

def create_practical_filter(successful_features, all_features):
    """Crée un filtre pratique basé sur l'analyse des tokens réussis"""
    print("\nCréation d'un filtre pratique...")
    
    # Convertir en DataFrame
    df_success = pd.DataFrame(successful_features)
    df_all = pd.DataFrame(all_features)
    
    print(f"Tokens réussis analysés: {len(df_success)}")
    print(f"Total tokens nouveaux: {len(df_all)}")
    
    # Analyser les caractéristiques des tokens réussis
    print("\nStatistiques des tokens réussis (50x+):")
    
    # Calculer les statistiques
    success_stats = {}
    for col in ['volume_h24', 'volume_h1', 'liquidity_usd', 'txns_buys_m5', 'txns_buys_h1', 
                'price_change_m5', 'price_change_h1', 'fdv', 'market_cap', 'price_usd']:
        if col in df_success.columns:
            success_stats[col] = {
                'mean': df_success[col].mean(),
                'median': df_success[col].median(),
                'q25': df_success[col].quantile(0.25),
                'q75': df_success[col].quantile(0.75),
                'min': df_success[col].min(),
                'max': df_success[col].max()
            }
            print(f"{col}:")
            print(f"  Moyenne: {success_stats[col]['mean']:.2f}")
            print(f"  Médiane: {success_stats[col]['median']:.2f}")
            print(f"  Q25: {success_stats[col]['q25']:.2f}")
            print(f"  Q75: {success_stats[col]['q75']:.2f}")
    
    # Créer un filtre pratique avec des seuils réalistes
    # Basé sur les percentiles inférieurs des tokens réussis
    filter_criteria = {
        # Volume - utiliser des seuils plus bas pour capturer plus de tokens
        'volume_h24_min': max(success_stats['volume_h24']['q25'] * 0.3, 5000),  # 30% du Q25
        'volume_h1_min': max(success_stats['volume_h1']['q25'] * 0.3, 2000),    # 30% du Q25
        
        # Transactions - seuils plus bas
        'txns_buys_m5_min': max(success_stats['txns_buys_m5']['q25'] * 0.2, 2),  # 20% du Q25
        'txns_buys_h1_min': max(success_stats['txns_buys_h1']['q25'] * 0.2, 10), # 20% du Q25
        
        # Changements de prix - seuils plus bas
        'price_change_m5_min': max(success_stats['price_change_m5']['q25'] * 0.1, 1),  # 10% du Q25
        'price_change_h1_min': max(success_stats['price_change_h1']['q25'] * 0.1, 10), # 10% du Q25
        
        # Liquidité et taille - seuils plus permissifs
        'liquidity_usd_min': max(success_stats['liquidity_usd']['q25'] * 0.1, 50),     # 10% du Q25
        'price_usd_max': min(success_stats['price_usd']['q75'] * 10, 0.01),           # 10x le Q75
        'fdv_max': min(success_stats['fdv']['q75'] * 5, 1000000),                     # 5x le Q75
        'market_cap_max': min(success_stats['market_cap']['q75'] * 5, 1000000),       # 5x le Q75
        
        # Critères supplémentaires - plus permissifs
        'buy_sell_ratio_min': 1.1,  # Légèrement plus d'achats que de ventes
        'volume_liquidity_ratio_min': 2,  # Volume modéré par rapport à la liquidité
    }
    
    return filter_criteria, df_success, df_all

def apply_practical_filter(df, filter_criteria):
    """Applique le filtre pratique"""
    filtered = df.copy()
    
    # Critères de base
    mask = (
        (filtered['volume_h24'] >= filter_criteria['volume_h24_min']) &
        (filtered['volume_h1'] >= filter_criteria['volume_h1_min']) &
        (filtered['txns_buys_m5'] >= filter_criteria['txns_buys_m5_min']) &
        (filtered['txns_buys_h1'] >= filter_criteria['txns_buys_h1_min']) &
        (filtered['price_change_m5'] >= filter_criteria['price_change_m5_min']) &
        (filtered['price_change_h1'] >= filter_criteria['price_change_h1_min']) &
        (filtered['liquidity_usd'] >= filter_criteria['liquidity_usd_min']) &
        (filtered['price_usd'] <= filter_criteria['price_usd_max']) &
        (filtered['fdv'] <= filter_criteria['fdv_max']) &
        (filtered['market_cap'] <= filter_criteria['market_cap_max'])
    )
    
    # Critères avancés - plus permissifs
    # Ratio achats/ventes
    buy_sell_ratio = np.where(
        (filtered['txns_sells_m5'] > 0) & (filtered['txns_buys_m5'] > 0),
        filtered['txns_buys_m5'] / filtered['txns_sells_m5'],
        999  # Si pas de ventes, ratio très élevé
    )
    mask &= (buy_sell_ratio >= filter_criteria['buy_sell_ratio_min'])
    
    # Ratio volume/liquidité
    volume_liquidity_ratio = np.where(
        filtered['liquidity_usd'] > 0,
        filtered['volume_h1'] / filtered['liquidity_usd'],
        0
    )
    mask &= (volume_liquidity_ratio >= filter_criteria['volume_liquidity_ratio_min'])
    
    return filtered[mask]

def test_practical_filter(filter_criteria, df_success, df_all):
    """Teste le filtre pratique"""
    print("\nTest du filtre pratique...")
    
    # Appliquer le filtre
    filtered_all = apply_practical_filter(df_all, filter_criteria)
    filtered_success = apply_practical_filter(df_success, filter_criteria)
    
    # Calculer les métriques
    total_filtered = len(filtered_all)
    success_filtered = len(filtered_success)
    total_success = len(df_success)
    
    if total_filtered > 0:
        precision = success_filtered / total_filtered
        recall = success_filtered / total_success
        winrate = precision * 100
    else:
        precision = 0
        recall = 0
        winrate = 0
    
    print(f"\nRésultats du filtre pratique:")
    print(f"Tokens filtrés: {total_filtered}")
    print(f"Succès dans les tokens filtrés: {success_filtered}")
    print(f"Total succès: {total_success}")
    print(f"Précision (Winrate): {winrate:.2f}%")
    print(f"Rappel: {recall:.2f}")
    
    return {
        'total_filtered': total_filtered,
        'success_filtered': success_filtered,
        'total_success': total_success,
        'winrate': winrate,
        'recall': recall
    }

def optimize_practical_filter(filter_criteria, df_success, df_all, target_winrate=90):
    """Optimise le filtre pratique pour atteindre le winrate cible"""
    print(f"\nOptimisation pour un winrate de {target_winrate}%...")
    
    current_result = test_practical_filter(filter_criteria, df_success, df_all)
    
    if current_result['winrate'] >= target_winrate:
        print(f"Le filtre actuel atteint déjà un winrate de {current_result['winrate']:.2f}%")
        return filter_criteria
    
    # Si aucun token n'est filtré, assouplir les critères
    if current_result['total_filtered'] == 0:
        print("Aucun token filtré. Assouplissement des critères...")
        relaxed_criteria = filter_criteria.copy()
        
        # Réduire les seuils de 50%
        for key in ['volume_h24_min', 'volume_h1_min', 'txns_buys_m5_min', 'txns_buys_h1_min', 
                   'price_change_m5_min', 'price_change_h1_min', 'liquidity_usd_min']:
            if key in relaxed_criteria:
                relaxed_criteria[key] *= 0.5
        
        # Augmenter les seuils maximaux
        for key in ['price_usd_max', 'fdv_max', 'market_cap_max']:
            if key in relaxed_criteria:
                relaxed_criteria[key] *= 2
        
        # Réduire les ratios
        relaxed_criteria['buy_sell_ratio_min'] *= 0.8
        relaxed_criteria['volume_liquidity_ratio_min'] *= 0.5
        
        relaxed_result = test_practical_filter(relaxed_criteria, df_success, df_all)
        
        if relaxed_result['total_filtered'] > 0:
            return relaxed_criteria
        else:
            # Si toujours aucun token, créer un filtre très basique
            print("Création d'un filtre très basique...")
            basic_criteria = {
                'volume_h24_min': 1000,
                'volume_h1_min': 500,
                'txns_buys_m5_min': 1,
                'txns_buys_h1_min': 5,
                'price_change_m5_min': 0,
                'price_change_h1_min': 5,
                'liquidity_usd_min': 10,
                'price_usd_max': 0.1,
                'fdv_max': 10000000,
                'market_cap_max': 10000000,
                'buy_sell_ratio_min': 1.0,
                'volume_liquidity_ratio_min': 1
            }
            return basic_criteria
    
    # Si des tokens sont filtrés mais winrate trop faible, ajuster progressivement
    optimized_criteria = filter_criteria.copy()
    
    # Ajuster les seuils pour améliorer le winrate
    adjustments = {
        'volume_h24_min': 1.2,
        'volume_h1_min': 1.2,
        'txns_buys_m5_min': 1.3,
        'txns_buys_h1_min': 1.2,
        'price_change_m5_min': 1.2,
        'price_change_h1_min': 1.1,
        'liquidity_usd_min': 1.2,
        'buy_sell_ratio_min': 1.1,
        'volume_liquidity_ratio_min': 1.2
    }
    
    for key, factor in adjustments.items():
        if key in optimized_criteria:
            optimized_criteria[key] *= factor
    
    # Tester le filtre optimisé
    optimized_result = test_practical_filter(optimized_criteria, df_success, df_all)
    
    print(f"Winrate après optimisation: {optimized_result['winrate']:.2f}%")
    
    return optimized_criteria

def save_practical_filter(filter_criteria, results):
    """Sauvegarde le filtre pratique"""
    print("\nSauvegarde du filtre pratique...")
    
    filter_data = {
        'filter_criteria': filter_criteria,
        'results': results,
        'description': 'Filtre pratique pour identifier les tokens avec potentiel 50x+',
        'target_winrate': 90,
        'created_date': datetime.now().isoformat(),
        'usage_instructions': {
            'volume_h24_min': 'Volume minimum sur 24h en USD',
            'volume_h1_min': 'Volume minimum sur 1h en USD',
            'txns_buys_m5_min': 'Nombre minimum d\'achats sur 5 minutes',
            'txns_buys_h1_min': 'Nombre minimum d\'achats sur 1h',
            'price_change_m5_min': 'Changement de prix minimum sur 5 minutes (%)',
            'price_change_h1_min': 'Changement de prix minimum sur 1h (%)',
            'liquidity_usd_min': 'Liquidité minimum en USD',
            'price_usd_max': 'Prix maximum en USD',
            'fdv_max': 'FDV maximum',
            'market_cap_max': 'Market cap maximum',
            'buy_sell_ratio_min': 'Ratio minimum achats/ventes',
            'volume_liquidity_ratio_min': 'Ratio minimum volume/liquidité'
        },
        'application_guide': {
            'step1': 'Appliquer ce filtre sur les nouveaux tokens découverts',
            'step2': 'Les tokens qui passent le filtre ont un potentiel élevé pour 50x+',
            'step3': 'Surveiller ces tokens pour les opportunités d\'entrée',
            'step4': 'Le filtre capture environ {:.1f}% des tokens réussis'.format(results.get('recall', 0) * 100)
        }
    }
    
    with open('practical_token_filter.json', 'w') as f:
        json.dump(filter_data, f, indent=2)
    
    print("Filtre pratique sauvegardé dans 'practical_token_filter.json'")

def main():
    """Fonction principale"""
    print("=== Création d'un filtre pratique pour tokens avec potentiel 50x+ ===\n")
    
    # Charger les données
    success_data, new_data = load_data()
    
    # Analyser les patterns de succès
    discovery_data = analyze_success_patterns(success_data, new_data)
    
    # Extraire les caractéristiques
    successful_features = []
    for token_address, data in discovery_data.items():
        feature = extract_features_safe(data['discovery_info'])
        if feature:
            feature['success_factor'] = data['success_info']['factor']
            feature['success_date'] = data['success_info']['date']
            successful_features.append(feature)
    
    all_features = []
    for entry in new_data:
        feature = extract_features_safe(entry)
        if feature:
            all_features.append(feature)
    
    # Créer le filtre pratique
    filter_criteria, df_success, df_all = create_practical_filter(successful_features, all_features)
    
    # Tester le filtre initial
    initial_results = test_practical_filter(filter_criteria, df_success, df_all)
    
    # Optimiser le filtre
    optimized_criteria = optimize_practical_filter(filter_criteria, df_success, df_all, target_winrate=90)
    
    # Tester le filtre optimisé
    final_results = test_practical_filter(optimized_criteria, df_success, df_all)
    
    # Sauvegarder le filtre
    save_practical_filter(optimized_criteria, final_results)
    
    print("\n=== Résumé ===")
    print(f"Filtre pratique créé avec un winrate de {final_results['winrate']:.2f}%")
    print(f"Tokens filtrés: {final_results['total_filtered']}")
    print(f"Succès capturés: {final_results['success_filtered']}/{final_results['total_success']}")
    print(f"Rappel: {final_results['recall']:.2f} ({final_results['recall']*100:.1f}% des succès capturés)")
    
    if final_results['total_filtered'] > 0:
        print(f"\nLe filtre identifie {final_results['total_filtered']} tokens sur {len(df_all)} tokens totaux")
        print(f"Parmi ces {final_results['total_filtered']} tokens, {final_results['success_filtered']} ont atteint 50x+")
        print(f"Taux de succès: {final_results['winrate']:.2f}%")
    else:
        print("\nLe filtre est trop strict et ne capture aucun token.")
        print("Considérez ajuster manuellement les critères selon vos besoins.")

if __name__ == "__main__":
    main()




