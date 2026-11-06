#!/usr/bin/env python3
"""
Script d'application du filtre de performance créé
Utilise le filtre optimal pour évaluer de nouveaux tokens
"""

import json
import sys
from datetime import datetime

def load_performance_filter():
    """Charge le filtre de performance optimal"""
    try:
        with open('performance_filter.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Fichier performance_filter.json non trouvé")
        print("Exécutez d'abord final_filter_analysis.py pour créer le filtre")
        return None

def extract_txns_5m(token_data):
    """Extrait le nombre de transactions 5 minutes d'un token"""
    try:
        if 'txns' in token_data and 'm5' in token_data['txns']:
            txns = token_data['txns']['m5']
            return int(txns.get('buys', 0)) + int(txns.get('sells', 0))
        return 0
    except:
        return 0

def apply_performance_filter(token_data, filter_config):
    """
    Applique le filtre de performance à un token
    
    Args:
        token_data: Données du token (dict)
        filter_config: Configuration du filtre (dict)
    
    Returns:
        dict: Résultat de l'évaluation avec détails
    """
    if not filter_config or 'filter_criteria' not in filter_config:
        return {
            'passed': False,
            'reason': 'Configuration de filtre invalide'
        }
    
    criteria = filter_config['filter_criteria'][0]  # Premier critère
    
    # Extraire la valeur du champ requis
    field = criteria['field']
    threshold = criteria['value']
    
    if field == 'txns_5m':
        value = extract_txns_5m(token_data)
    else:
        return {
            'passed': False,
            'reason': f'Champ {field} non supporté'
        }
    
    # Appliquer le critère
    passed = False
    if criteria['type'] == 'min_threshold':
        passed = value >= threshold
    elif criteria['type'] == 'max_threshold':
        passed = value <= threshold
    
    return {
        'passed': passed,
        'field': field,
        'value': value,
        'threshold': threshold,
        'type': criteria['type'],
        'description': criteria['description']
    }

def evaluate_token(token_data):
    """
    Évalue un token avec le filtre de performance
    
    Args:
        token_data: Données du token (dict)
    
    Returns:
        dict: Résultat de l'évaluation
    """
    # Charger le filtre
    filter_config = load_performance_filter()
    if not filter_config:
        return None
    
    # Appliquer le filtre
    result = apply_performance_filter(token_data, filter_config)
    
    # Ajouter des informations supplémentaires
    if result['passed']:
        result['recommendation'] = '✅ TOKEN RECOMMANDÉ'
        result['confidence'] = 'Élevée (basé sur les patterns des top performants)'
    else:
        result['recommendation'] = '❌ TOKEN NON RECOMMANDÉ'
        result['confidence'] = 'Modérée (critère non satisfait)'
    
    return result

def print_evaluation_result(result):
    """Affiche le résultat de l'évaluation de manière formatée"""
    if not result:
        print("❌ Impossible d'évaluer le token")
        return
    
    print("\n" + "="*60)
    print("ÉVALUATION DU TOKEN")
    print("="*60)
    
    print(f"🎯 {result['recommendation']}")
    print(f"📊 Confiance: {result['confidence']}")
    
    print(f"\n📈 Détails du filtre:")
    print(f"   - Critère: {result['description']}")
    print(f"   - Valeur actuelle: {result['value']}")
    print(f"   - Seuil requis: {result['threshold']}")
    print(f"   - Type: {result['type']}")
    
    if result['passed']:
        print(f"\n✅ Le token SATISFAIT le critère de filtre")
        print(f"   → Recommandé pour l'investissement")
    else:
        print(f"\n❌ Le token NE SATISFAIT PAS le critère de filtre")
        print(f"   → Non recommandé selon ce filtre")

def example_usage():
    """Exemple d'utilisation du filtre"""
    print("🔍 EXEMPLE D'UTILISATION DU FILTRE")
    print("="*60)
    
    # Exemple de token
    example_token = {
        "baseToken": {
            "address": "example_token_address",
            "name": "Example Token",
            "symbol": "EXT"
        },
        "txns": {
            "m5": {
                "buys": 15,
                "sells": 8
            }
        },
        "priceUsd": "0.0001",
        "marketCap": 50000
    }
    
    print("Token d'exemple:")
    print(f"   - Nom: {example_token['baseToken']['name']}")
    print(f"   - Symbol: {example_token['baseToken']['symbol']}")
    print(f"   - Transactions 5min: {extract_txns_5m(example_token)}")
    
    # Évaluer le token
    result = evaluate_token(example_token)
    print_evaluation_result(result)

def batch_evaluate_tokens(tokens_data):
    """
    Évalue un lot de tokens
    
    Args:
        tokens_data: Liste de tokens à évaluer
    
    Returns:
        dict: Résultats de l'évaluation
    """
    print(f"\n🔍 ÉVALUATION DE {len(tokens_data)} TOKENS")
    print("="*60)
    
    results = {
        'total': len(tokens_data),
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    for i, token in enumerate(tokens_data, 1):
        print(f"\n[{i}/{len(tokens_data)}] Évaluation du token...")
        
        result = evaluate_token(token)
        if result:
            results['details'].append(result)
            if result['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1
    
    # Afficher le résumé
    print(f"\n📊 RÉSUMÉ DE L'ÉVALUATION:")
    print(f"   - Total évalué: {results['total']}")
    print(f"   - Tokens recommandés: {results['passed']}")
    print(f"   - Tokens non recommandés: {results['failed']}")
    print(f"   - Taux de recommandation: {results['passed']/results['total']*100:.2f}%")
    
    return results

def main():
    """Fonction principale"""
    print("🎯 APPLICATION DU FILTRE DE PERFORMANCE")
    print("="*60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "example":
            example_usage()
        elif command == "evaluate" and len(sys.argv) > 2:
            # Évaluer un token spécifique (fichier JSON)
            try:
                with open(sys.argv[2], 'r') as f:
                    token_data = json.load(f)
                result = evaluate_token(token_data)
                print_evaluation_result(result)
            except FileNotFoundError:
                print(f"❌ Fichier {sys.argv[2]} non trouvé")
            except json.JSONDecodeError:
                print(f"❌ Fichier {sys.argv[2]} n'est pas un JSON valide")
        else:
            print("❌ Commande invalide")
            print_usage()
    else:
        print_usage()

def print_usage():
    """Affiche l'aide d'utilisation"""
    print("\n📖 UTILISATION:")
    print("   python3 apply_filter.py example")
    print("   python3 apply_filter.py evaluate <fichier_token.json>")
    print("\n📝 Exemples:")
    print("   python3 apply_filter.py example")
    print("   python3 apply_filter.py evaluate token_data.json")

if __name__ == "__main__":
    main()




