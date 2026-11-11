#!/usr/bin/env python3
"""
Ultra-Selective Filter with Cleaned Data
Recalculates the filter without duplicates for precise results
"""

import json
import pandas as pd
from datetime import datetime
import numpy as np

def load_clean_data():
    """Loads the cleaned data"""
    print("📊 Loading cleaned data...")

    with open('data/sample/merged_success_data_filtered.json', 'r') as f:
        success_data = json.load(f)

    # Use the most recent cleaned dataset
    import glob
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

def analyze_ultra_performers_clean(success_data, new_data):
    """Analyzes ultra-performing tokens with cleaned data"""
    print("\n🔍 Analyzing ultra-performing tokens (cleaned data)...")

    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    # Extract the features of the success tokens
    success_features = []
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if token_address and token_address in success_map:
            features = extract_numeric_features(token)
            features['token_address'] = token_address
            features['multiplication_factor'] = success_map[token_address]
            success_features.append(features)

    df = pd.DataFrame(success_features)
    print(f"📈 {len(df)} success tokens with extracted features")

    # Analyze the multiplication factor percentiles
    df_sorted = df.sort_values('multiplication_factor', ascending=False)

    # Top 1% (about 48 tokens)
    top_1_percent = df_sorted.head(max(1, len(df_sorted) // 100))
    print(f"\n🏆 Top 1% ({len(top_1_percent)} tokens):")
    print(f"   Minimum multiplication factor: {top_1_percent['multiplication_factor'].min():.1f}")
    print(f"   Maximum multiplication factor: {top_1_percent['multiplication_factor'].max():.1f}")
    print(f"   Average multiplication factor: {top_1_percent['multiplication_factor'].mean():.1f}")

    # Top 0.1% (about 5 tokens)
    top_01_percent = df_sorted.head(max(1, len(df_sorted) // 1000))
    print(f"\n👑 Top 0.1% ({len(top_01_percent)} tokens):")
    print(f"   Minimum multiplication factor: {top_01_percent['multiplication_factor'].min():.1f}")
    print(f"   Maximum multiplication factor: {top_01_percent['multiplication_factor'].max():.1f}")
    print(f"   Average multiplication factor: {top_01_percent['multiplication_factor'].mean():.1f}")

    return df, top_1_percent, top_01_percent

def create_ultra_selective_filters_clean(df, top_1_percent, top_01_percent):
    """Creates ultra-selective filters based on the features of the best tokens"""
    print("\n🎯 Creating ultra-selective filters (cleaned data)...")

    filters = []

    # Analyze each feature for the top 1%
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']

    for feature in numeric_features:
        if feature in top_1_percent.columns and not top_1_percent[feature].isna().all():
            # Top 1% statistics
            top_stats = top_1_percent[feature].describe()

            # Create filters based on the top 1% percentiles
            if not pd.isna(top_stats['25%']):
                filters.append({
                    'field': feature,
                    'type': 'min_threshold',
                    'value': top_stats['25%'],
                    'description': f"{feature} >= {top_stats['25%']:.6f} (25th percentile of the top 1%)",
                    'percentile': 25
                })

            if not pd.isna(top_stats['75%']):
                filters.append({
                    'field': feature,
                    'type': 'max_threshold',
                    'value': top_stats['75%'],
                    'description': f"{feature} <= {top_stats['75%']:.6f} (75th percentile of the top 1%)",
                    'percentile': 75
                })

    # Analyze the criteria combinations
    print(f"\n📋 {len(filters)} filtering criteria created")

    return filters

def test_ultra_filter_clean(new_data, success_data, filters, filter_name="Ultra-Selective Clean"):
    """Tests an ultra-selective filter with cleaned data"""
    print(f"\n🧪 Testing the {filter_name} filter...")

    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    filtered_tokens = []
    wins = 0

    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue

        # Extract the features
        features = extract_numeric_features(token)

        # Apply all the filters
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

    # Calculate the metrics
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0

    print(f"📊 Results of the {filter_name} filter:")
    print(f"   Filtered tokens: {filtered_count:,}")
    print(f"   Wins: {wins:,}")
    print(f"   Winrate: {winrate:.2f}%")
    print(f"   Coverage: {coverage:.2f}%")
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
    """Creates a combined ultra-selective filter with cleaned data"""
    print("\n🔧 Creating a combined ultra-selective filter (cleaned data)...")

    # Identify the most discriminating features
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']

    best_filters = []

    for feature in numeric_features:
        if feature in top_1_percent.columns and not top_1_percent[feature].isna().all():
            # Use the 50th percentile of the top 1% as the threshold
            median_value = top_1_percent[feature].median()
            if not pd.isna(median_value):
                best_filters.append({
                    'field': feature,
                    'type': 'min_threshold',
                    'value': median_value,
                    'description': f"{feature} >= {median_value:.6f} (median of the top 1%)"
                })

    return best_filters

def save_ultra_filter_clean(filter_config, results, filter_name):
    """Saves the cleaned ultra-selective filter"""
    output = {
        'filter_name': filter_name,
        'filter_criteria': filter_config,
        'results': results,
        'created_at': datetime.now().isoformat(),
        'description': f"Ultra-selective filter with cleaned data - {filter_name}"
    }

    filename = f"{filter_name.lower().replace(' ', '_')}_clean_filter.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Filter saved to {filename}")
    return filename

def main():
    """Main function"""
    print("🎯 ULTRA-SELECTIVE FILTER - Cleaned Data")
    print("=" * 60)

    # Load the cleaned data
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return

    # Analyze the ultra-performers
    df, top_1_percent, top_01_percent = analyze_ultra_performers_clean(success_data, new_data)

    # Create ultra-selective filters
    filters_1_percent = create_ultra_selective_filters_clean(df, top_1_percent, top_01_percent)

    # Test the filter based on the top 1%
    results_1_percent = test_ultra_filter_clean(new_data, success_data, filters_1_percent, "Top 1% Clean")

    # Create a stricter combined filter
    combined_filters = create_combined_ultra_filter_clean(df, top_1_percent)
    results_combined = test_ultra_filter_clean(new_data, success_data, combined_filters, "Combined Ultra Clean")

    # Save the best filter
    if results_combined['winrate'] > results_1_percent['winrate']:
        best_results = results_combined
        best_filters = combined_filters
        best_name = "Combined Ultra Clean"
    else:
        best_results = results_1_percent
        best_filters = filters_1_percent
        best_name = "Top 1% Clean"

    save_ultra_filter_clean(best_filters, best_results, best_name)

    # Final summary
    print("\n" + "=" * 60)
    print("🎯 FINAL SUMMARY - Ultra-Selective Filter (Cleaned Data)")
    print("=" * 60)
    print(f"🏆 Best filter: {best_name}")
    print(f"📊 Winrate: {best_results['winrate']:.2f}%")
    print(f"🎯 Coverage: {best_results['coverage']:.2f}%")
    print(f"📈 Selected tokens: {best_results['filtered_count']:,}")
    print(f"💰 Wins: {best_results['wins']:,}")

    if best_results['winrate'] >= 80:
        print("✅ EXCELLENT: Very high winrate!")
    elif best_results['winrate'] >= 70:
        print("🟡 GOOD: High winrate")
    else:
        print("🔴 NEEDS IMPROVEMENT: Moderate winrate")

    print("\n💡 Recommendation: Use this filter for ultra-selective trades")
    print("   with clean data and precise results.")

if __name__ == "__main__":
    main()
