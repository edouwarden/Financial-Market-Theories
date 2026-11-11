#!/usr/bin/env python3
"""
Adaptive Hybrid Strategy with Transaction Fees
Incorporates the 2% fees into the profitability calculation
"""

import json
import pandas as pd
import numpy as np
import glob
from datetime import datetime

def load_all_filters():
    """Loads all available filters"""
    filters = {}

    # Load the ultra-selective filter
    ultra_files = glob.glob('combined_ultra_clean_*_filter.json')
    if ultra_files:
        latest_ultra = max(ultra_files)
        with open(latest_ultra, 'r') as f:
            filters['ultra_selective'] = json.load(f)
        print(f"✅ Ultra-selective filter loaded: {latest_ultra}")

    # Load the auto-optimized filter
    auto_files = glob.glob('best_auto_filter_*.json')
    if auto_files:
        latest_auto = max(auto_files)
        with open(latest_auto, 'r') as f:
            filters['auto_optimized'] = json.load(f)
        print(f"✅ Auto-optimized filter loaded: {latest_auto}")

    # Load the high-precision filter
    precision_files = glob.glob('best_high_precision_filter_*.json')
    if precision_files:
        latest_precision = max(precision_files)
        with open(latest_precision, 'r') as f:
            filters['high_precision'] = json.load(f)
        print(f"✅ High-precision filter loaded: {latest_precision}")

    return filters

def load_clean_data():
    """Loads the cleaned data"""
    print("📊 Loading data...")

    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)

    # Use the most recent cleaned dataset
    clean_files = glob.glob('data/raw/merged_new_data_clean_*.json')
    if clean_files:
        latest_clean_file = max(clean_files)
        with open(latest_clean_file, 'r') as f:
            new_data = json.load(f)
        print(f"✅ Cleaned dataset: {latest_clean_file}")
    else:
        print("❌ No cleaned dataset found")
        return None, None

    return success_data, new_data

def get_token_address_from_new_data(token):
    """Extracts the token address from new_data"""
    if 'baseToken' in token and 'address' in token['baseToken']:
        return token['baseToken']['address']
    elif 'token_address' in token:
        return token['token_address']
    elif 'address' in token:
        return token['address']
    return None

def extract_numeric_features(token):
    """Extracts the numeric features of a token"""
    features = {}

    # Price and market capitalization
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

    # Creation date
    if 'pairCreatedAt' in token:
        try:
            features['pairCreatedAt'] = int(token['pairCreatedAt'])
        except (ValueError, TypeError):
            features['pairCreatedAt'] = None

    return features

def apply_filter_combination(token_data, filter_criteria):
    """Applies a filter combination to a token"""
    features = extract_numeric_features(token_data)

    # Check each filter criterion
    for criteria in filter_criteria:
        field = criteria['field']
        filter_type = criteria['type']
        value = criteria['value']

        # If the feature is not available, the token fails
        if field not in features or features[field] is None:
            return False

        # Check the criterion
        if filter_type == 'min_threshold' and features[field] < value:
            return False
        elif filter_type == 'max_threshold' and features[field] > value:
            return False

    return True

def calculate_required_winrate_with_fees(multiple, fees_percent=2.0):
    """Calculates the winrate required to be profitable with fees"""
    # Entry and exit fees
    entry_fees = fees_percent / 100
    exit_fees = fees_percent / 100

    # To be profitable: (winrate * (multiple - exit_fees)) - (1 - winrate) - entry_fees > 0
    # winrate * (multiple - exit_fees) - 1 + winrate - entry_fees > 0
    # winrate * (multiple - exit_fees + 1) > 1 + entry_fees
    # winrate > (1 + entry_fees) / (multiple - exit_fees + 1)
    required_winrate = (1 + entry_fees) / (multiple - exit_fees + 1) * 100
    return required_winrate

def calculate_rentability_with_fees(winrate, multiple, fees_percent=2.0):
    """Calculates the profitability with transaction fees"""
    loss_rate = 100 - winrate
    entry_fees = fees_percent / 100
    exit_fees = fees_percent / 100

    # Net gain = (winrate * (multiple - exit_fees)) - (1 - winrate) - entry_fees
    gain_per_trade = (winrate/100 * (multiple - exit_fees)) - (loss_rate/100 * 1) - entry_fees
    return gain_per_trade

def test_hybrid_strategy_with_fees(new_data, success_data, filters):
    """Tests the hybrid strategy with transaction fees"""
    print("🧪 Testing the hybrid strategy with 2% fees...")

    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    # Extract the filter criteria
    auto_criteria = filters['auto_optimized']['filter_criteria']
    ultra_criteria = filters['ultra_selective']['filter_criteria']
    precision_criteria = filters['high_precision']['filter_criteria']

    # Results by category
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

        # Check each filter
        auto_match = apply_filter_combination(token, auto_criteria)
        ultra_match = apply_filter_combination(token, ultra_criteria)
        precision_match = apply_filter_combination(token, precision_criteria)

        # Classify the token
        if auto_match and ultra_match and precision_match:
            # All filters
            results['all_filters']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['all_filters']['wins'] += 1
                results['all_filters']['multiples'].append(success_map[token_address])

        elif auto_match and precision_match:
            # Auto + High Precision
            results['precision_hybrid']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['precision_hybrid']['wins'] += 1
                results['precision_hybrid']['multiples'].append(success_map[token_address])

        elif auto_match and ultra_match:
            # Auto + Ultra-Selective
            results['ultra_hybrid']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['ultra_hybrid']['wins'] += 1
                results['ultra_hybrid']['multiples'].append(success_map[token_address])

        elif auto_match:
            # Auto-Optimized only
            results['auto_only']['tokens'].append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                results['auto_only']['wins'] += 1
                results['auto_only']['multiples'].append(success_map[token_address])

    return results, total_tokens

def analyze_hybrid_strategy_with_fees():
    """Analyzes the hybrid strategy with transaction fees"""
    print("🎯 HYBRID STRATEGY WITH TRANSACTION FEES")
    print("=" * 60)
    print("Objective: Analyze profitability with 2% fees")

    # Load the filters and data
    filters = load_all_filters()
    success_data, new_data = load_clean_data()

    if not filters or not success_data or not new_data:
        print("❌ Unable to load the required data")
        return

    # Test the hybrid strategy
    results, total_tokens = test_hybrid_strategy_with_fees(new_data, success_data, filters)

    # Analyze the results with fees
    analyze_hybrid_results_with_fees(results, total_tokens)

    # Save the results
    save_hybrid_analysis_with_fees(results, total_tokens)

    return results

def analyze_hybrid_results_with_fees(results, total_tokens):
    """Analyzes and displays the results with transaction fees"""
    print(f"\n📊 ANALYSIS WITH 2% FEES")
    print("=" * 80)

    # Exit multiples to analyze
    exit_targets = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

    for target in exit_targets:
        print(f"\n🎯 EXIT TARGET: {target:.1f}x")
        print("-" * 80)
        print(f"{'Category':<20} {'Tokens':<8} {'Wins':<6} {'Winrate':<9} {'Required':<8} {'Profitability':<12} {'Strategy'}")
        print("-" * 80)

        for category, data in results.items():
            if data['tokens']:
                tokens_count = len(data['tokens'])
                wins = data['wins']
                winrate = (wins / tokens_count * 100) if tokens_count > 0 else 0

                # Calculate the wins for this multiple
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0

                # Calculate the profitability with fees
                required_winrate = calculate_required_winrate_with_fees(target, 2.0)
                rentability = calculate_rentability_with_fees(target_winrate, target, 2.0)

                # Determine the recommended strategy
                if category == 'all_filters':
                    strategy = "🚀 MAXIMUM (2x + high stake)"
                elif category == 'precision_hybrid':
                    strategy = "🎯 HIGH PRECISION (2x)"
                elif category == 'ultra_hybrid':
                    strategy = "⚡ ULTRA-SELECTIVE (1.5x + moderate stake)"
                else:  # auto_only
                    strategy = "📊 STANDARD (1.5x + normal stake)"

                status = "✅ PROFITABLE" if rentability > 0 else "❌ NOT PROFITABLE"
                print(f"{category:<20} {tokens_count:<8} {target_wins:<6} {target_winrate:<8.2f}% {required_winrate:<7.2f}% {rentability:<11.3f} {strategy}")

    # Comparison with/without fees
    print(f"\n📊 COMPARISON WITH/WITHOUT FEES")
    print("=" * 80)

    comparison_targets = [1.5, 2.0, 2.5, 3.0]

    for target in comparison_targets:
        print(f"\n🎯 Multiple {target:.1f}x:")
        print(f"{'Category':<20} {'Without Fees':<12} {'With Fees':<12} {'Difference':<12}")
        print("-" * 60)

        for category, data in results.items():
            if data['tokens']:
                tokens_count = len(data['tokens'])
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0

                # Profitability without fees
                rentability_no_fees = calculate_rentability_with_fees(target_winrate, target, 0.0)

                # Profitability with fees
                rentability_with_fees = calculate_rentability_with_fees(target_winrate, target, 2.0)

                # Difference
                difference = rentability_with_fees - rentability_no_fees

                print(f"{category:<20} {rentability_no_fees:<11.3f} {rentability_with_fees:<11.3f} {difference:<11.3f}")

    # Strategic recommendations with fees
    print(f"\n💡 RECOMMENDATIONS WITH 2% FEES")
    print("=" * 80)

    for category, data in results.items():
        if data['tokens']:
            tokens_count = len(data['tokens'])
            coverage = (tokens_count / total_tokens * 100)

            print(f"\n📋 {category.upper()}:")
            print(f"   📊 Tokens: {tokens_count} ({coverage:.2f}% coverage)")
            print(f"   🏆 Total wins: {data['wins']}")
            print(f"   📈 Overall winrate: {(data['wins'] / tokens_count * 100):.2f}%")

            if data['multiples']:
                avg_multiple = np.mean(data['multiples'])
                median_multiple = np.median(data['multiples'])
                print(f"   📊 Average multiple: {avg_multiple:.2f}x")
                print(f"   📊 Median multiple: {median_multiple:.2f}x")

            # Analyze the profitability with fees for different multiples
            print(f"   💰 PROFITABILITY WITH FEES:")
            for target in [1.5, 2.0, 2.5, 3.0]:
                target_wins = sum(1 for m in data['multiples'] if m >= target)
                target_winrate = (target_wins / tokens_count * 100) if tokens_count > 0 else 0
                required_winrate = calculate_required_winrate_with_fees(target, 2.0)
                rentability = calculate_rentability_with_fees(target_winrate, target, 2.0)

                status = "✅ PROFITABLE" if rentability > 0 else "❌ NOT PROFITABLE"
                print(f"     {target:.1f}x: {target_winrate:.1f}% vs {required_winrate:.1f}% required → {rentability:.3f} ({status})")

            # Strategy recommendation
            if category == 'all_filters':
                print(f"   🚀 STRATEGY: Maximum stake + Exit at 2.0x")
                print(f"   💰 Allocation: 80-100% of available capital")
            elif category == 'precision_hybrid':
                print(f"   🎯 STRATEGY: High stake + Exit at 2.0x")
                print(f"   💰 Allocation: 60-80% of available capital")
            elif category == 'ultra_hybrid':
                print(f"   ⚡ STRATEGY: Moderate stake + Exit at 1.5x")
                print(f"   💰 Allocation: 40-60% of available capital")
            else:  # auto_only
                print(f"   📊 STRATEGY: Normal stake + Exit at 1.5x")
                print(f"   💰 Allocation: 20-40% of available capital")

    # Impact of fees on the overall strategy
    print(f"\n⚠️  IMPACT OF FEES ON THE STRATEGY")
    print("=" * 80)

    print(f"📊 TRANSACTION FEES:")
    print(f"   💸 Entry fees: 2%")
    print(f"   💸 Exit fees: 2%")
    print(f"   💸 Total per trade: 4% (entry + exit)")

    print(f"\n📈 PROFITABILITY THRESHOLDS WITH FEES:")
    for target in [1.5, 2.0, 2.5, 3.0]:
        required = calculate_required_winrate_with_fees(target, 2.0)
        print(f"   {target:.1f}x: {required:.1f}% winrate required")

    print(f"\n💡 ADAPTED RECOMMENDATIONS:")
    print(f"   🎯 Increase the exit targets to offset the fees")
    print(f"   📊 Favor high-quality strategies (fewer trades)")
    print(f"   💰 Optimize position sizing to maximize ROI")

def save_hybrid_analysis_with_fees(results, total_tokens):
    """Saves the hybrid analysis with fees"""
    print(f"\n💾 Saving the analysis with fees...")

    output = {
        'created_at': datetime.now().isoformat(),
        'objective': 'Adaptive hybrid strategy with 2% transaction fees',
        'fees_percent': 2.0,
        'total_tokens': total_tokens,
        'results': results,
        'strategy_summary': {
            'auto_only': {
                'tokens': len(results['auto_only']['tokens']),
                'wins': results['auto_only']['wins'],
                'winrate': (results['auto_only']['wins'] / len(results['auto_only']['tokens']) * 100) if results['auto_only']['tokens'] else 0,
                'strategy': 'Standard (1.5x + normal stake)'
            },
            'ultra_hybrid': {
                'tokens': len(results['ultra_hybrid']['tokens']),
                'wins': results['ultra_hybrid']['wins'],
                'winrate': (results['ultra_hybrid']['wins'] / len(results['ultra_hybrid']['tokens']) * 100) if results['ultra_hybrid']['tokens'] else 0,
                'strategy': 'Ultra-Selective (1.5x + moderate stake)'
            },
            'precision_hybrid': {
                'tokens': len(results['precision_hybrid']['tokens']),
                'wins': results['precision_hybrid']['wins'],
                'winrate': (results['precision_hybrid']['wins'] / len(results['precision_hybrid']['tokens']) * 100) if results['precision_hybrid']['tokens'] else 0,
                'strategy': 'High Precision (2.0x + high stake)'
            },
            'all_filters': {
                'tokens': len(results['all_filters']['tokens']),
                'wins': results['all_filters']['wins'],
                'winrate': (results['all_filters']['wins'] / len(results['all_filters']['tokens']) * 100) if results['all_filters']['tokens'] else 0,
                'strategy': 'Maximum (2.0x + maximum stake)'
            }
        }
    }

    filename = f"hybrid_strategy_with_fees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"✅ Analysis with fees saved: {filename}")

def main():
    """Main function"""
    results = analyze_hybrid_strategy_with_fees()

    if results:
        print(f"\n🎯 ANALYSIS WITH FEES FINISHED!")
        print("=" * 60)
        print(f"📊 Impact of 2% fees analyzed")
        print(f"✅ Adapted recommendations generated")
        print(f"💡 Strategy optimized for fees")

if __name__ == "__main__":
    main()
