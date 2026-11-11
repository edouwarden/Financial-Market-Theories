#!/usr/bin/env python3
"""
Complete Profitability Analysis - All Multiples
Analyzes the profitability of all exit multiples across the 3 strategies
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

def calculate_required_winrate(multiple):
    """Calculates the winrate required to be profitable with a given multiple"""
    required_winrate = 1 / (multiple + 1) * 100
    return required_winrate

def calculate_rentability(winrate, multiple):
    """Calculates the profitability for a given winrate and multiple"""
    loss_rate = 100 - winrate
    gain_per_trade = (winrate/100 * multiple) - (loss_rate/100 * 1)
    return gain_per_trade

def test_filter_with_all_multiples(new_data, success_data, filter_criteria, filter_name):
    """Tests a filter with all exit multiples"""
    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    filtered_tokens = []
    win_multiples = []

    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue

        # Apply the filter
        if apply_filter_combination(token, filter_criteria):
            filtered_tokens.append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                win_multiples.append(success_map[token_address])

    # Calculate the base metrics
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0

    # Multiples to test (1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 9, 10, 15, 20, 50, 100)
    multiple_targets = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 15.0, 20.0, 50.0, 100.0]

    results = {}
    for target in multiple_targets:
        wins = sum(1 for multiple in win_multiples if multiple >= target)
        winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0

        # Calculate the average and median multiples for wins >= target
        target_wins = [m for m in win_multiples if m >= target]
        avg_multiple = np.mean(target_wins) if target_wins else 0
        median_multiple = np.median(target_wins) if target_wins else 0

        # Calculate the required winrate and profitability
        required_winrate = calculate_required_winrate(target)
        rentability = calculate_rentability(winrate, target)
        is_profitable = rentability > 0

        # Profitability score (based on the winrate surplus)
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
    """Analyzes all strategies with all multiples"""
    print("🎯 COMPLETE PROFITABILITY ANALYSIS")
    print("=" * 60)
    print("Objective: Analyze the profitability of all multiples across the 3 strategies")

    # Load the filters and data
    filters = load_all_filters()
    success_data, new_data = load_clean_data()

    if not filters or not success_data or not new_data:
        print("❌ Unable to load the required data")
        return

    print(f"\n📊 Analyzing {len(filters)} strategies...")

    all_results = {}

    # Test each filter
    for filter_name, filter_data in filters.items():
        print(f"\n🧪 Testing strategy: {filter_name}")

        if filter_name == 'ultra_selective':
            filter_criteria = filter_data['filter_criteria']
            display_name = "Ultra-Selective (16 criteria)"
        elif filter_name == 'auto_optimized':
            filter_criteria = filter_data['filter_criteria']
            display_name = "Auto-Optimized"
        elif filter_name == 'high_precision':
            filter_criteria = filter_data['filter_criteria']
            display_name = "High Precision"
        else:
            continue

        results = test_filter_with_all_multiples(new_data, success_data, filter_criteria, filter_name)
        all_results[display_name] = results

    # Analyze and display the results
    analyze_complete_results(all_results)

    # Save the results
    save_complete_analysis(all_results)

    return all_results

def analyze_complete_results(all_results):
    """Analyzes and displays the complete results"""
    print(f"\n📊 COMPLETE RESULTS ANALYSIS")
    print("=" * 100)

    # Multiples to display
    display_multiples = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 50.0, 100.0]

    for target in display_multiples:
        print(f"\n🎯 EXIT MULTIPLE: {target:.1f}x")
        print("-" * 100)
        print(f"{'Strategy':<25} {'Winrate':<8} {'Required':<8} {'Profitability':<12} {'Avg':<6} {'Median':<7} {'Profitable?'}")
        print("-" * 100)

        # Sort by profitability
        target_results = []
        for strategy_name, results in all_results.items():
            if target in results:
                result = results[target]
                target_results.append((strategy_name, result))

        # Sort by decreasing profitability
        target_results.sort(key=lambda x: x[1]['rentability'], reverse=True)

        for strategy_name, result in target_results:
            status = "✅ YES" if result['is_profitable'] else "❌ NO"
            print(f"{strategy_name:<25} {result['winrate']:<7.2f}% {result['required_winrate']:<7.2f}% {result['rentability']:<11.3f} {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {status}")

    # Recommendations by strategy
    print(f"\n💡 RECOMMENDATIONS BY STRATEGY")
    print("=" * 100)

    for strategy_name, results in all_results.items():
        print(f"\n📋 {strategy_name}:")

        # Find the profitable multiples
        profitable_multiples = {k: v for k, v in results.items() if v['is_profitable']}

        if profitable_multiples:
            # Find the best multiple (maximum profitability)
            best_multiple = max(profitable_multiples.items(), key=lambda x: x[1]['rentability'])
            target, best_result = best_multiple

            print(f"   🏆 Best multiple: {target:.1f}x")
            print(f"   📊 Winrate: {best_result['winrate']:.1f}%")
            print(f"   💰 Profitability: +{best_result['rentability']:.3f} per trade")
            print(f"   📈 Average multiple: {best_result['avg_multiple']:.1f}x")
            print(f"   📊 Coverage: {best_result['coverage']:.1f}%")

            # Recommendation
            if best_result['winrate'] >= 60:
                print(f"   ✅ EXCELLENT: High allocation recommended")
            elif best_result['winrate'] >= 50:
                print(f"   🟡 GOOD: Moderate allocation recommended")
            else:
                print(f"   🔴 MODERATE: Conservative allocation recommended")
        else:
            print(f"   ❌ No profitable multiple found")

    # Overall recommendation
    print(f"\n🏆 OVERALL RECOMMENDATION")
    print("=" * 100)

    # Find the best strategy/multiple combination
    best_global = None
    best_global_rentability = 0

    for strategy_name, results in all_results.items():
        for target, result in results.items():
            if result['is_profitable'] and result['rentability'] > best_global_rentability:
                best_global_rentability = result['rentability']
                best_global = (strategy_name, target, result)

    if best_global:
        strategy_name, target, result = best_global
        print(f"🎯 OPTIMAL CONFIGURATION:")
        print(f"   📋 Strategy: {strategy_name}")
        print(f"   🎯 Exit multiple: {target:.1f}x")
        print(f"   📊 Winrate: {result['winrate']:.1f}%")
        print(f"   💰 Profitability: +{result['rentability']:.3f} per trade")
        print(f"   📈 Average multiple: {result['avg_multiple']:.1f}x")
        print(f"   📊 Coverage: {result['coverage']:.1f}%")

        # Implementation strategy
        print(f"\n📋 IMPLEMENTATION STRATEGY:")
        print(f"   🎯 Use the strategy: {strategy_name}")
        print(f"   📈 Exit target: {target:.1f}x")
        print(f"   💰 Allocation: {'High' if result['winrate'] >= 60 else 'Moderate' if result['winrate'] >= 50 else 'Conservative'}")
        print(f"   ⏰ Frequency: {'Rare' if result['coverage'] <= 5 else 'Moderate' if result['coverage'] <= 15 else 'High'}")

def save_complete_analysis(all_results):
    """Saves the complete analysis"""
    print(f"\n💾 Saving the complete analysis...")

    # Find the best combination
    best_global = None
    best_global_rentability = 0

    for strategy_name, results in all_results.items():
        for target, result in results.items():
            if result['is_profitable'] and result['rentability'] > best_global_rentability:
                best_global_rentability = result['rentability']
                best_global = (strategy_name, target, result)

    output = {
        'created_at': datetime.now().isoformat(),
        'objective': 'Complete profitability analysis - All multiples across the 3 strategies',
        'strategies_analyzed': list(all_results.keys()),
        'best_combination': best_global,
        'all_results': all_results
    }

    filename = f"complete_rentability_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"✅ Complete analysis saved: {filename}")

def main():
    """Main function"""
    results = analyze_all_strategies()

    if results:
        print(f"\n🎯 COMPLETE ANALYSIS FINISHED!")
        print("=" * 60)
        print(f"📊 {len(results)} strategies analyzed")
        print(f"📈 Multiples from 1.5x to 100x tested")
        print(f"✅ Optimal recommendations generated")

if __name__ == "__main__":
    main()
