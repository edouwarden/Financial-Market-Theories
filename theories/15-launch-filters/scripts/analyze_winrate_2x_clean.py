#!/usr/bin/env python3
"""
Winrate Analysis with a 2x Target - Cleaned Data
Winrate calculation for the ultra-selective filter using clean data
"""

import json
import pandas as pd
import numpy as np
import glob

def load_clean_data():
    """Loads the cleaned data"""
    print("📊 Loading cleaned data...")

    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)

    # Use the most recent cleaned dataset
    clean_files = glob.glob('data/raw/merged_new_data_clean_*.json')
    if clean_files:
        latest_clean_file = max(clean_files)
        with open(latest_clean_file, 'r') as f:
            new_data = json.load(f)
        print(f"✅ Using cleaned dataset: {latest_clean_file}")
    else:
        print("❌ No cleaned dataset found")
        return None, None

    print(f"✅ {len(success_data)} success tokens loaded")
    print(f"✅ {len(new_data)} discovered tokens (cleaned) loaded")

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

def load_ultra_filter_clean():
    """Loads the cleaned ultra-selective filter"""
    try:
        # Look for the most recent cleaned filter
        clean_filter_files = glob.glob('*_clean_filter.json')
        if clean_filter_files:
            latest_filter_file = max(clean_filter_files)
            with open(latest_filter_file, 'r') as f:
                return json.load(f)
        else:
            print("❌ No cleaned filter found")
            return None
    except FileNotFoundError:
        print("❌ Cleaned filter file not found")
        return None

def apply_ultra_filter_clean(token_data, filter_config):
    """Applies the cleaned ultra-selective filter to a token"""
    features = extract_numeric_features(token_data)

    # Check each filter criterion
    for criteria in filter_config['filter_criteria']:
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

def analyze_winrate_with_different_targets_clean():
    """Analyzes the winrate with different multiple targets (cleaned data)"""
    print("🎯 WINRATE ANALYSIS WITH DIFFERENT TARGETS - CLEANED DATA")
    print("=" * 70)

    # Load the cleaned data
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return

    # Load the cleaned filter
    filter_config = load_ultra_filter_clean()
    if not filter_config:
        return

    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    print(f"\n📊 Analyzing {len(new_data)} discovered tokens (cleaned)...")

    # Apply the filter and collect the results
    selected_tokens = []
    all_tokens = []

    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue

        # Check whether the token passes the filter
        passes_filter = apply_ultra_filter_clean(token, filter_config)

        all_tokens.append({
            'address': token_address,
            'passes_filter': passes_filter
        })

        if passes_filter:
            selected_tokens.append(token_address)

    print(f"✅ {len(selected_tokens)} tokens selected by the filter")
    print(f"❌ {len(all_tokens) - len(selected_tokens)} tokens rejected")

    # Analyze with different thresholds
    targets = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 7.5, 10.0]

    print(f"\n📊 WINRATE BY MULTIPLE TARGET (CLEANED DATA)")
    print("=" * 70)
    print(f"{'Target':<8} {'Wins':<6} {'Winrate':<10} {'Improvement':<12} {'Baseline':<10}")
    print("-" * 70)

    # Calculate the baseline (without filter)
    baseline_results = {}
    for target in targets:
        wins_baseline = sum(1 for addr in success_map.values() if addr >= target)
        total_baseline = len(success_map)
        winrate_baseline = (wins_baseline / total_baseline * 100) if total_baseline > 0 else 0
        baseline_results[target] = winrate_baseline

    # Calculate the filtered results
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

    # Detailed analysis for the 2x target
    target_2x = 2.0
    result_2x = filter_results[target_2x]
    baseline_2x = baseline_results[target_2x]

    print(f"\n🎯 DETAILED ANALYSIS - {target_2x}x TARGET (CLEANED DATA)")
    print("=" * 70)
    print(f"📊 Selected tokens: {len(selected_tokens)}")
    print(f"🏆 Wins ({target_2x}x+): {result_2x['wins']}")
    print(f"📈 Winrate: {result_2x['winrate']:.2f}%")
    print(f"📊 Baseline (without filter): {baseline_2x:.2f}%")
    print(f"📈 Improvement: {result_2x['improvement']:+.2f}%")

    # Distribution of multiples for the selected tokens
    selected_multiples = []
    for token_address in selected_tokens:
        if token_address in success_map:
            selected_multiples.append(success_map[token_address])

    if selected_multiples:
        print(f"\n📊 STATISTICS OF SELECTED TOKENS (CLEANED)")
        print("=" * 70)
        print(f"📈 Average multiple: {np.mean(selected_multiples):.2f}x")
        print(f"📊 Median multiple: {np.median(selected_multiples):.2f}x")
        print(f"📉 Minimum multiple: {np.min(selected_multiples):.2f}x")
        print(f"📈 Maximum multiple: {np.max(selected_multiples):.2f}x")

        # Distribution around the 2x target
        print(f"\n📊 DISTRIBUTION AROUND THE {target_2x}x TARGET")
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

    # Comparison with the whole set
    all_winners = []
    for token in all_tokens:
        if token['address'] in success_map:
            multiplication_factor = success_map[token['address']]
            if multiplication_factor >= 1.5:
                all_winners.append(multiplication_factor)

    if all_winners and selected_multiples:
        print(f"\n📊 COMPARISON WITH THE WHOLE SET (CLEANED DATA)")
        print("=" * 70)
        print(f"📈 Average multiple (all tokens): {np.mean(all_winners):.2f}x")
        print(f"📈 Average multiple (selected tokens): {np.mean(selected_multiples):.2f}x")
        print(f"📊 Improvement: {np.mean(selected_multiples) - np.mean(all_winners):.2f}x")

        print(f"\n📊 Median multiple (all tokens): {np.median(all_winners):.2f}x")
        print(f"📊 Median multiple (selected tokens): {np.median(selected_multiples):.2f}x")
        print(f"📈 Improvement: {np.median(selected_multiples) - np.median(all_winners):.2f}x")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS (CLEANED DATA)")
    print("=" * 70)

    if result_2x['winrate'] >= 50:
        print("✅ EXCELLENT: Very high winrate for the 2x target!")
        print("   You can trade with confidence on this target.")
    elif result_2x['winrate'] >= 40:
        print("🟡 GOOD: High winrate for the 2x target")
        print("   Realistic target with a good probability of success.")
    elif result_2x['winrate'] >= 30:
        print("🟡 MODERATE: Correct winrate for the 2x target")
        print("   Achievable target but requires risk management.")
    else:
        print("🔴 LOW: Low winrate for the 2x target")
        print("   Consider a lower target or improve the filter.")

    if result_2x['improvement'] > 0:
        print(f"📈 The filter improves the winrate by {result_2x['improvement']:+.2f}%")
    else:
        print(f"📉 The filter reduces the winrate by {abs(result_2x['improvement']):.2f}%")

    # Comparison with other targets
    best_target = max(filter_results.keys(), key=lambda x: filter_results[x]['winrate'])
    best_winrate = filter_results[best_target]['winrate']

    print(f"\n🏆 BEST TARGET: {best_target}x with a {best_winrate:.2f}% winrate")

    if best_target != target_2x:
        print(f"💡 Consider the {best_target}x target to maximize your chances of success.")

    # Comparison with the previous results (with duplicates)
    print(f"\n📊 COMPARISON WITH PREVIOUS RESULTS (WITH DUPLICATES)")
    print("=" * 70)
    print(f"🔴 Old winrate (with duplicates): 51.69%")
    print(f"✅ New winrate (without duplicates): {result_2x['winrate']:.2f}%")
    print(f"📈 Difference: {result_2x['winrate'] - 51.69:+.2f}%")

    if result_2x['winrate'] > 51.69:
        print("✅ IMPROVEMENT: The cleaned data gives better results!")
    elif result_2x['winrate'] < 51.69:
        print("📉 DECREASE: The cleaned data reveals more realistic results.")
    else:
        print("🟡 STABLE: The results are similar.")

def main():
    """Main function"""
    analyze_winrate_with_different_targets_clean()

if __name__ == "__main__":
    main()
