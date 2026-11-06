#!/usr/bin/env python3
"""
Analyse du Winrate avec Objectif 2x - Données Nettoyées
Calcul du winrate du filtre ultra-sélectif avec données propres
"""

import json
import pandas as pd
import numpy as np
import glob

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

def load_ultra_filter_clean():
    """Charge le filtre ultra-sélectif nettoyé"""
    try:
        # Chercher le filtre nettoyé le plus récent
        clean_filter_files = glob.glob('*_clean_filter.json')
        if clean_filter_files:
            latest_filter_file = max(clean_filter_files)
            with open(latest_filter_file, 'r') as f:
                return json.load(f)
        else:
            print("❌ Aucun filtre nettoyé trouvé")
            return None
    except FileNotFoundError:
        print("❌ Fichier de filtre nettoyé non trouvé")
        return None

def apply_ultra_filter_clean(token_data, filter_config):
    """Applique le filtre ultra-sélectif nettoyé à un token"""
    features = extract_numeric_features(token_data)
    
    # Vérifier chaque critère du filtre
    for criteria in filter_config['filter_criteria']:
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

def analyze_winrate_with_different_targets_clean():
    """Analyse le winrate avec différents objectifs de multiple (données nettoyées)"""
    print("🎯 ANALYSE DU WINRATE AVEC DIFFÉRENTS OBJECTIFS - DONNÉES NETTOYÉES")
    print("=" * 70)
    
    # Charger les données nettoyées
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return
    
    # Charger le filtre nettoyé
    filter_config = load_ultra_filter_clean()
    if not filter_config:
        return
    
    # Créer un mapping des tokens de succès
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']
    
    print(f"\n📊 Analyse de {len(new_data)} tokens découverts (nettoyés)...")
    
    # Appliquer le filtre et collecter les résultats
    selected_tokens = []
    all_tokens = []
    
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue
        
        # Vérifier si le token passe le filtre
        passes_filter = apply_ultra_filter_clean(token, filter_config)
        
        all_tokens.append({
            'address': token_address,
            'passes_filter': passes_filter
        })
        
        if passes_filter:
            selected_tokens.append(token_address)
    
    print(f"✅ {len(selected_tokens)} tokens sélectionnés par le filtre")
    print(f"❌ {len(all_tokens) - len(selected_tokens)} tokens rejetés")
    
    # Analyser avec différents seuils
    targets = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 7.5, 10.0]
    
    print(f"\n📊 WINRATE PAR OBJECTIF DE MULTIPLE (DONNÉES NETTOYÉES)")
    print("=" * 70)
    print(f"{'Objectif':<8} {'Wins':<6} {'Winrate':<10} {'Amélioration':<12} {'Baseline':<10}")
    print("-" * 70)
    
    # Calculer le baseline (sans filtre)
    baseline_results = {}
    for target in targets:
        wins_baseline = sum(1 for addr in success_map.values() if addr >= target)
        total_baseline = len(success_map)
        winrate_baseline = (wins_baseline / total_baseline * 100) if total_baseline > 0 else 0
        baseline_results[target] = winrate_baseline
    
    # Calculer les résultats avec filtre
    filter_results = {}
    for target in targets:
        wins_filter = 0
        for token_address in selected_tokens:
            if token_address in success_map and success_map[token_address] >= target:
                wins_filter += 1
        
        winrate_filter = (wins_filter / len(selected_tokens) * 100) if len(selected_tokens) > 0 else 0
        improvement = winrate_filter - baseline_results[target]
        
        filter_results[target] = {
            'wins': wins_filter,
            'winrate': winrate_filter,
            'improvement': improvement
        }
        
        print(f"{target}x{'':<7} {wins_filter:<6} {winrate_filter:<9.2f}% {improvement:+<11.2f}% {baseline_results[target]:<9.2f}%")
    
    # Analyse détaillée pour l'objectif 2x
    target_2x = 2.0
    result_2x = filter_results[target_2x]
    baseline_2x = baseline_results[target_2x]
    
    print(f"\n🎯 ANALYSE DÉTAILLÉE - OBJECTIF {target_2x}x (DONNÉES NETTOYÉES)")
    print("=" * 70)
    print(f"📊 Tokens sélectionnés: {len(selected_tokens)}")
    print(f"🏆 Wins ({target_2x}x+): {result_2x['wins']}")
    print(f"📈 Winrate: {result_2x['winrate']:.2f}%")
    print(f"📊 Baseline (sans filtre): {baseline_2x:.2f}%")
    print(f"📈 Amélioration: {result_2x['improvement']:+.2f}%")
    
    # Distribution des multiples pour les tokens sélectionnés
    selected_multiples = []
    for token_address in selected_tokens:
        if token_address in success_map:
            selected_multiples.append(success_map[token_address])
    
    if selected_multiples:
        print(f"\n📊 STATISTIQUES DES TOKENS SÉLECTIONNÉS (NETTOYÉS)")
        print("=" * 70)
        print(f"📈 Multiple moyen: {np.mean(selected_multiples):.2f}x")
        print(f"📊 Multiple médian: {np.median(selected_multiples):.2f}x")
        print(f"📉 Multiple minimum: {np.min(selected_multiples):.2f}x")
        print(f"📈 Multiple maximum: {np.max(selected_multiples):.2f}x")
        
        # Distribution autour de l'objectif 2x
        print(f"\n📊 DISTRIBUTION AUTOUR DE L'OBJECTIF {target_2x}x")
        print("=" * 70)
        ranges = [
            (1.5, 2.0, f"1.5x - {target_2x}x"),
            (2.0, 2.5, f"{target_2x}x - 2.5x"),
            (2.5, 3.0, "2.5x - 3.0x"),
            (3.0, 5.0, "3.0x - 5.0x"),
            (5.0, 10.0, "5.0x - 10.0x"),
            (10.0, float('inf'), "10.0x+")
        ]
        
        for min_val, max_val, label in ranges:
            count = sum(1 for mf in selected_multiples if min_val <= mf < max_val)
            percentage = (count / len(selected_multiples)) * 100
            print(f"   {label}: {count} tokens ({percentage:.1f}%)")
    
    # Comparaison avec l'ensemble
    all_winners = []
    for token in all_tokens:
        if token['address'] in success_map:
            multiplication_factor = success_map[token['address']]
            if multiplication_factor >= 1.5:
                all_winners.append(multiplication_factor)
    
    if all_winners and selected_multiples:
        print(f"\n📊 COMPARAISON AVEC L'ENSEMBLE (DONNÉES NETTOYÉES)")
        print("=" * 70)
        print(f"📈 Multiple moyen (tous les tokens): {np.mean(all_winners):.2f}x")
        print(f"📈 Multiple moyen (tokens sélectionnés): {np.mean(selected_multiples):.2f}x")
        print(f"📊 Amélioration: {np.mean(selected_multiples) - np.mean(all_winners):.2f}x")
        
        print(f"\n📊 Multiple médian (tous les tokens): {np.median(all_winners):.2f}x")
        print(f"📊 Multiple médian (tokens sélectionnés): {np.median(selected_multiples):.2f}x")
        print(f"📈 Amélioration: {np.median(selected_multiples) - np.median(all_winners):.2f}x")
    
    # Recommandations
    print(f"\n💡 RECOMMANDATIONS (DONNÉES NETTOYÉES)")
    print("=" * 70)
    
    if result_2x['winrate'] >= 50:
        print("✅ EXCELLENT: Winrate très élevé pour l'objectif 2x!")
        print("   Vous pouvez trader avec confiance sur cet objectif.")
    elif result_2x['winrate'] >= 40:
        print("🟡 BON: Winrate élevé pour l'objectif 2x")
        print("   Objectif réaliste avec une bonne probabilité de succès.")
    elif result_2x['winrate'] >= 30:
        print("🟡 MODÉRÉ: Winrate correct pour l'objectif 2x")
        print("   Objectif atteignable mais nécessite une gestion du risque.")
    else:
        print("🔴 FAIBLE: Winrate bas pour l'objectif 2x")
        print("   Considérez un objectif plus bas ou améliorez le filtre.")
    
    if result_2x['improvement'] > 0:
        print(f"📈 Le filtre améliore le winrate de {result_2x['improvement']:+.2f}%")
    else:
        print(f"📉 Le filtre réduit le winrate de {abs(result_2x['improvement']):.2f}%")
    
    # Comparaison avec d'autres objectifs
    best_target = max(filter_results.keys(), key=lambda x: filter_results[x]['winrate'])
    best_winrate = filter_results[best_target]['winrate']
    
    print(f"\n🏆 MEILLEUR OBJECTIF: {best_target}x avec {best_winrate:.2f}% de winrate")
    
    if best_target != target_2x:
        print(f"💡 Considérez l'objectif {best_target}x pour maximiser vos chances de succès.")
    
    # Comparaison avec les anciens résultats (avec doublons)
    print(f"\n📊 COMPARAISON AVEC LES RÉSULTATS PRÉCÉDENTS (AVEC DOUBLONS)")
    print("=" * 70)
    print(f"🔴 Ancien winrate (avec doublons): 51.69%")
    print(f"✅ Nouveau winrate (sans doublons): {result_2x['winrate']:.2f}%")
    print(f"📈 Différence: {result_2x['winrate'] - 51.69:+.2f}%")
    
    if result_2x['winrate'] > 51.69:
        print("✅ AMÉLIORATION: Les données nettoyées donnent de meilleurs résultats!")
    elif result_2x['winrate'] < 51.69:
        print("📉 DIMINUTION: Les données nettoyées révèlent des résultats plus réalistes.")
    else:
        print("🟡 STABLE: Les résultats sont similaires.")

def main():
    """Fonction principale"""
    analyze_winrate_with_different_targets_clean()

if __name__ == "__main__":
    main()




