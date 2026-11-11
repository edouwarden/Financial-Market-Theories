#!/usr/bin/env python3
import json
import pandas as pd
from datetime import datetime
import numpy as np
from collections import defaultdict

def load_data():
    """Loads data from the JSON files"""
    print("Loading data...")

    # Load the success data (tokens that reached 50x or more)
    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)

    # Load the discovery data (new tokens)
    with open('data/raw/merged_new_data.json', 'r') as f:
        new_data = json.load(f)

    print(f"Success data loaded: {len(success_data)} entries")
    print(f"Discovery data loaded: {len(new_data)} entries")

    return success_data, new_data

def analyze_success_patterns(success_data, new_data):
    """Analyzes the patterns of tokens that succeeded"""
    print("\nAnalyzing success patterns...")

    # Create a dictionary of tokens that succeeded (50x or more)
    successful_tokens = {}
    for entry in success_data:
        token_address = entry['token_address']
        multiplication_factor = entry['multiplication_factor_from_new_adding']
        if multiplication_factor >= 50:
            successful_tokens[token_address] = {
                'factor': multiplication_factor,
                'date': entry['multiplication_date']
            }

    print(f"Tokens with 50x or more: {len(successful_tokens)}")

    # Find the corresponding discovery data
    discovery_data = {}
    for entry in new_data:
        token_address = entry.get('baseToken', {}).get('address', '')
        if token_address in successful_tokens:
            discovery_data[token_address] = {
                'success_info': successful_tokens[token_address],
                'discovery_info': entry
            }

    print(f"Tokens found in the discovery data: {len(discovery_data)}")

    return discovery_data

def extract_features_safe(entry):
    """Extracts the features safely"""
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
        print(f"Error while extracting features: {e}")
        return None

def create_practical_filter(successful_features, all_features):
    """Creates a practical filter based on the analysis of successful tokens"""
    print("\nCreating a practical filter...")

    # Convert to DataFrame
    df_success = pd.DataFrame(successful_features)
    df_all = pd.DataFrame(all_features)

    print(f"Successful tokens analyzed: {len(df_success)}")
    print(f"Total new tokens: {len(df_all)}")

    # Analyze the features of successful tokens
    print("\nStatistics of successful tokens (50x+):")

    # Calculate the statistics
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
            print(f"  Mean: {success_stats[col]['mean']:.2f}")
            print(f"  Median: {success_stats[col]['median']:.2f}")
            print(f"  Q25: {success_stats[col]['q25']:.2f}")
            print(f"  Q75: {success_stats[col]['q75']:.2f}")

    # Create a practical filter with realistic thresholds
    # Based on the lower percentiles of successful tokens
    filter_criteria = {
        # Volume - use lower thresholds to capture more tokens
        'volume_h24_min': max(success_stats['volume_h24']['q25'] * 0.3, 5000),  # 30% of Q25
        'volume_h1_min': max(success_stats['volume_h1']['q25'] * 0.3, 2000),    # 30% of Q25

        # Transactions - lower thresholds
        'txns_buys_m5_min': max(success_stats['txns_buys_m5']['q25'] * 0.2, 2),  # 20% of Q25
        'txns_buys_h1_min': max(success_stats['txns_buys_h1']['q25'] * 0.2, 10), # 20% of Q25

        # Price changes - lower thresholds
        'price_change_m5_min': max(success_stats['price_change_m5']['q25'] * 0.1, 1),  # 10% of Q25
        'price_change_h1_min': max(success_stats['price_change_h1']['q25'] * 0.1, 10), # 10% of Q25

        # Liquidity and size - more permissive thresholds
        'liquidity_usd_min': max(success_stats['liquidity_usd']['q25'] * 0.1, 50),     # 10% of Q25
        'price_usd_max': min(success_stats['price_usd']['q75'] * 10, 0.01),           # 10x Q75
        'fdv_max': min(success_stats['fdv']['q75'] * 5, 1000000),                     # 5x Q75
        'market_cap_max': min(success_stats['market_cap']['q75'] * 5, 1000000),       # 5x Q75

        # Additional criteria - more permissive
        'buy_sell_ratio_min': 1.1,  # Slightly more buys than sells
        'volume_liquidity_ratio_min': 2,  # Moderate volume relative to liquidity
    }

    return filter_criteria, df_success, df_all

def apply_practical_filter(df, filter_criteria):
    """Applies the practical filter"""
    filtered = df.copy()

    # Basic criteria
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

    # Advanced criteria - more permissive
    # Buy/sell ratio
    buy_sell_ratio = np.where(
        (filtered['txns_sells_m5'] > 0) & (filtered['txns_buys_m5'] > 0),
        filtered['txns_buys_m5'] / filtered['txns_sells_m5'],
        999  # If there are no sells, the ratio is very high
    )
    mask &= (buy_sell_ratio >= filter_criteria['buy_sell_ratio_min'])

    # Volume/liquidity ratio
    volume_liquidity_ratio = np.where(
        filtered['liquidity_usd'] > 0,
        filtered['volume_h1'] / filtered['liquidity_usd'],
        0
    )
    mask &= (volume_liquidity_ratio >= filter_criteria['volume_liquidity_ratio_min'])

    return filtered[mask]

def test_practical_filter(filter_criteria, df_success, df_all):
    """Tests the practical filter"""
    print("\nTesting the practical filter...")

    # Apply the filter
    filtered_all = apply_practical_filter(df_all, filter_criteria)
    filtered_success = apply_practical_filter(df_success, filter_criteria)

    # Calculate the metrics
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

    print(f"\nPractical filter results:")
    print(f"Filtered tokens: {total_filtered}")
    print(f"Successes among the filtered tokens: {success_filtered}")
    print(f"Total successes: {total_success}")
    print(f"Precision (Winrate): {winrate:.2f}%")
    print(f"Recall: {recall:.2f}")

    return {
        'total_filtered': total_filtered,
        'success_filtered': success_filtered,
        'total_success': total_success,
        'winrate': winrate,
        'recall': recall
    }

def optimize_practical_filter(filter_criteria, df_success, df_all, target_winrate=90):
    """Optimizes the practical filter to reach the target winrate"""
    print(f"\nOptimizing for a {target_winrate}% winrate...")

    current_result = test_practical_filter(filter_criteria, df_success, df_all)

    if current_result['winrate'] >= target_winrate:
        print(f"The current filter already reaches a winrate of {current_result['winrate']:.2f}%")
        return filter_criteria

    # If no token is filtered, loosen the criteria
    if current_result['total_filtered'] == 0:
        print("No token filtered. Loosening the criteria...")
        relaxed_criteria = filter_criteria.copy()

        # Reduce the thresholds by 50%
        for key in ['volume_h24_min', 'volume_h1_min', 'txns_buys_m5_min', 'txns_buys_h1_min',
                   'price_change_m5_min', 'price_change_h1_min', 'liquidity_usd_min']:
            if key in relaxed_criteria:
                relaxed_criteria[key] *= 0.5

        # Increase the maximum thresholds
        for key in ['price_usd_max', 'fdv_max', 'market_cap_max']:
            if key in relaxed_criteria:
                relaxed_criteria[key] *= 2

        # Reduce the ratios
        relaxed_criteria['buy_sell_ratio_min'] *= 0.8
        relaxed_criteria['volume_liquidity_ratio_min'] *= 0.5

        relaxed_result = test_practical_filter(relaxed_criteria, df_success, df_all)

        if relaxed_result['total_filtered'] > 0:
            return relaxed_criteria
        else:
            # If there is still no token, create a very basic filter
            print("Creating a very basic filter...")
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

    # If tokens are filtered but the winrate is too low, adjust gradually
    optimized_criteria = filter_criteria.copy()

    # Adjust the thresholds to improve the winrate
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

    # Test the optimized filter
    optimized_result = test_practical_filter(optimized_criteria, df_success, df_all)

    print(f"Winrate after optimization: {optimized_result['winrate']:.2f}%")

    return optimized_criteria

def save_practical_filter(filter_criteria, results):
    """Saves the practical filter"""
    print("\nSaving the practical filter...")

    filter_data = {
        'filter_criteria': filter_criteria,
        'results': results,
        'description': 'Practical filter to identify tokens with 50x+ potential',
        'target_winrate': 90,
        'created_date': datetime.now().isoformat(),
        'usage_instructions': {
            'volume_h24_min': 'Minimum 24h volume in USD',
            'volume_h1_min': 'Minimum 1h volume in USD',
            'txns_buys_m5_min': 'Minimum number of buys over 5 minutes',
            'txns_buys_h1_min': 'Minimum number of buys over 1h',
            'price_change_m5_min': 'Minimum price change over 5 minutes (%)',
            'price_change_h1_min': 'Minimum price change over 1h (%)',
            'liquidity_usd_min': 'Minimum liquidity in USD',
            'price_usd_max': 'Maximum price in USD',
            'fdv_max': 'Maximum FDV',
            'market_cap_max': 'Maximum market cap',
            'buy_sell_ratio_min': 'Minimum buys/sells ratio',
            'volume_liquidity_ratio_min': 'Minimum volume/liquidity ratio'
        },
        'application_guide': {
            'step1': 'Apply this filter to newly discovered tokens',
            'step2': 'Tokens that pass the filter have high 50x+ potential',
            'step3': 'Monitor these tokens for entry opportunities',
            'step4': 'The filter captures about {:.1f}% of successful tokens'.format(results.get('recall', 0) * 100)
        }
    }

    with open('practical_token_filter.json', 'w') as f:
        json.dump(filter_data, f, indent=2)

    print("Practical filter saved to 'practical_token_filter.json'")

def main():
    """Main function"""
    print("=== Creating a practical filter for tokens with 50x+ potential ===\n")

    # Load the data
    success_data, new_data = load_data()

    # Analyze the success patterns
    discovery_data = analyze_success_patterns(success_data, new_data)

    # Extract the features
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

    # Create the practical filter
    filter_criteria, df_success, df_all = create_practical_filter(successful_features, all_features)

    # Test the initial filter
    initial_results = test_practical_filter(filter_criteria, df_success, df_all)

    # Optimize the filter
    optimized_criteria = optimize_practical_filter(filter_criteria, df_success, df_all, target_winrate=90)

    # Test the optimized filter
    final_results = test_practical_filter(optimized_criteria, df_success, df_all)

    # Save the filter
    save_practical_filter(optimized_criteria, final_results)

    print("\n=== Summary ===")
    print(f"Practical filter created with a winrate of {final_results['winrate']:.2f}%")
    print(f"Filtered tokens: {final_results['total_filtered']}")
    print(f"Successes captured: {final_results['success_filtered']}/{final_results['total_success']}")
    print(f"Recall: {final_results['recall']:.2f} ({final_results['recall']*100:.1f}% of successes captured)")

    if final_results['total_filtered'] > 0:
        print(f"\nThe filter identifies {final_results['total_filtered']} tokens out of {len(df_all)} total tokens")
        print(f"Among these {final_results['total_filtered']} tokens, {final_results['success_filtered']} reached 50x+")
        print(f"Success rate: {final_results['winrate']:.2f}%")
    else:
        print("\nThe filter is too strict and captures no token.")
        print("Consider adjusting the criteria manually according to your needs.")

if __name__ == "__main__":
    main()
