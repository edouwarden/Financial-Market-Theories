#!/usr/bin/env python3
"""
Script for applying the created performance filter
Uses the optimal filter to evaluate new tokens
"""

import json
import sys
from datetime import datetime

def load_performance_filter():
    """Loads the optimal performance filter"""
    try:
        with open('performance_filter.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ performance_filter.json file not found")
        print("Run final_filter_analysis.py first to create the filter")
        return None

def extract_txns_5m(token_data):
    """Extracts the 5-minute transaction count from a token"""
    try:
        if 'txns' in token_data and 'm5' in token_data['txns']:
            txns = token_data['txns']['m5']
            return int(txns.get('buys', 0)) + int(txns.get('sells', 0))
        return 0
    except:
        return 0

def apply_performance_filter(token_data, filter_config):
    """
    Applies the performance filter to a token

    Args:
        token_data: Token data (dict)
        filter_config: Filter configuration (dict)

    Returns:
        dict: Evaluation result with details
    """
    if not filter_config or 'filter_criteria' not in filter_config:
        return {
            'passed': False,
            'reason': 'Invalid filter configuration'
        }

    criteria = filter_config['filter_criteria'][0]  # First criterion

    # Extract the value of the required field
    field = criteria['field']
    threshold = criteria['value']

    if field == 'txns_5m':
        value = extract_txns_5m(token_data)
    else:
        return {
            'passed': False,
            'reason': f'Field {field} not supported'
        }

    # Apply the criterion
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
    Evaluates a token with the performance filter

    Args:
        token_data: Token data (dict)

    Returns:
        dict: Evaluation result
    """
    # Load the filter
    filter_config = load_performance_filter()
    if not filter_config:
        return None

    # Apply the filter
    result = apply_performance_filter(token_data, filter_config)

    # Add additional information
    if result['passed']:
        result['recommendation'] = '✅ RECOMMENDED TOKEN'
        result['confidence'] = 'High (based on top performers patterns)'
    else:
        result['recommendation'] = '❌ TOKEN NOT RECOMMENDED'
        result['confidence'] = 'Moderate (criterion not met)'

    return result

def print_evaluation_result(result):
    """Displays the evaluation result in a formatted way"""
    if not result:
        print("❌ Unable to evaluate the token")
        return

    print("\n" + "="*60)
    print("TOKEN EVALUATION")
    print("="*60)

    print(f"🎯 {result['recommendation']}")
    print(f"📊 Confidence: {result['confidence']}")

    print(f"\n📈 Filter details:")
    print(f"   - Criterion: {result['description']}")
    print(f"   - Current value: {result['value']}")
    print(f"   - Required threshold: {result['threshold']}")
    print(f"   - Type: {result['type']}")

    if result['passed']:
        print(f"\n✅ The token MEETS the filter criterion")
        print(f"   → Recommended for investment")
    else:
        print(f"\n❌ The token DOES NOT MEET the filter criterion")
        print(f"   → Not recommended according to this filter")

def example_usage():
    """Example of using the filter"""
    print("🔍 FILTER USAGE EXAMPLE")
    print("="*60)

    # Example token
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

    print("Example token:")
    print(f"   - Name: {example_token['baseToken']['name']}")
    print(f"   - Symbol: {example_token['baseToken']['symbol']}")
    print(f"   - 5min transactions: {extract_txns_5m(example_token)}")

    # Evaluate the token
    result = evaluate_token(example_token)
    print_evaluation_result(result)

def batch_evaluate_tokens(tokens_data):
    """
    Evaluates a batch of tokens

    Args:
        tokens_data: List of tokens to evaluate

    Returns:
        dict: Evaluation results
    """
    print(f"\n🔍 EVALUATING {len(tokens_data)} TOKENS")
    print("="*60)

    results = {
        'total': len(tokens_data),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    for i, token in enumerate(tokens_data, 1):
        print(f"\n[{i}/{len(tokens_data)}] Evaluating token...")

        result = evaluate_token(token)
        if result:
            results['details'].append(result)
            if result['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1

    # Display the summary
    print(f"\n📊 EVALUATION SUMMARY:")
    print(f"   - Total evaluated: {results['total']}")
    print(f"   - Recommended tokens: {results['passed']}")
    print(f"   - Non-recommended tokens: {results['failed']}")
    print(f"   - Recommendation rate: {results['passed']/results['total']*100:.2f}%")

    return results

def main():
    """Main function"""
    print("🎯 APPLYING THE PERFORMANCE FILTER")
    print("="*60)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "example":
            example_usage()
        elif command == "evaluate" and len(sys.argv) > 2:
            # Evaluate a specific token (JSON file)
            try:
                with open(sys.argv[2], 'r') as f:
                    token_data = json.load(f)
                result = evaluate_token(token_data)
                print_evaluation_result(result)
            except FileNotFoundError:
                print(f"❌ File {sys.argv[2]} not found")
            except json.JSONDecodeError:
                print(f"❌ File {sys.argv[2]} is not valid JSON")
        else:
            print("❌ Invalid command")
            print_usage()
    else:
        print_usage()

def print_usage():
    """Displays usage help"""
    print("\n📖 USAGE:")
    print("   python3 apply_filter.py example")
    print("   python3 apply_filter.py evaluate <token_file.json>")
    print("\n📝 Examples:")
    print("   python3 apply_filter.py example")
    print("   python3 apply_filter.py evaluate token_data.json")

if __name__ == "__main__":
    main()
