#!/usr/bin/env python3
"""
High-Precision Filter Optimizer
Objective: Reduced coverage + Maximum winrate
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import itertools
import glob
from collections import defaultdict

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

def analyze_success_patterns(new_data, success_data):
    """Analyzes the patterns of success tokens to create precise filters"""
    print("\n📊 Analyzing success token patterns...")

    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    # Extract the features of all tokens
    all_features = []
    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if token_address:
            features = extract_numeric_features(token)
            features['token_address'] = token_address
            features['is_success'] = token_address in success_map and success_map[token_address] >= 1.5
            if token_address in success_map:
                features['multiplication_factor'] = success_map[token_address]
            all_features.append(features)

    df = pd.DataFrame(all_features)

    # Analyze the success tokens
    success_df = df[df['is_success'] == True]
    failure_df = df[df['is_success'] == False]

    print(f"📈 Success tokens: {len(success_df)}")
    print(f"📉 Failure tokens: {len(failure_df)}")

    # Analyze each feature
    feature_analysis = {}
    numeric_features = ['priceUsd', 'marketCap', 'fdv', 'liquidity', 'volume_24h', 'txns_24h', 'txns_5m', 'pairCreatedAt']

    for feature in numeric_features:
        if feature in df.columns and not df[feature].isna().all():
            # Success statistics
            success_stats = success_df[feature].describe()
            failure_stats = failure_df[feature].describe()

            # Calculate the optimal thresholds for discrimination
            if not success_stats.empty and not failure_stats.empty:
                # Use the high percentiles of successes
                success_75 = success_stats['75%']
                success_90 = success_stats.quantile(0.90)
                success_95 = success_stats.quantile(0.95)

                # Use the low percentiles of failures
                failure_25 = failure_stats['25%']
                failure_10 = failure_stats.quantile(0.10)
                failure_5 = failure_stats.quantile(0.05)

                feature_analysis[feature] = {
                    'success_stats': success_stats,
                    'failure_stats': failure_stats,
                    'success_75': success_75,
                    'success_90': success_90,
                    'success_95': success_95,
                    'failure_25': failure_25,
                    'failure_10': failure_10,
                    'failure_5': failure_5
                }

    return feature_analysis, df

def generate_high_precision_filters(feature_analysis):
    """Generates high-precision filters with reduced coverage"""
    print("\n🎯 Generating high-precision filters...")

    filters = []

    # Filters based on the high percentiles of successes
    for feature, analysis in feature_analysis.items():
        if not pd.isna(analysis['success_75']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_75'],
                'description': f"{feature} >= {analysis['success_75']:.2f} (75th success percentile)"
            }])

        if not pd.isna(analysis['success_90']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_90'],
                'description': f"{feature} >= {analysis['success_90']:.2f} (90th success percentile)"
            }])

        if not pd.isna(analysis['success_95']):
            filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': analysis['success_95'],
                'description': f"{feature} >= {analysis['success_95']:.2f} (95th success percentile)"
            }])

    # Combined filters (2-3 criteria) for high precision
    high_precision_combinations = [
        ('txns_5m', 'liquidity'),
        ('txns_5m', 'volume_24h'),
        ('liquidity', 'volume_24h'),
        ('txns_5m', 'liquidity', 'volume_24h'),
        ('marketCap', 'liquidity', 'txns_5m'),
        ('priceUsd', 'txns_5m', 'liquidity')
    ]

    for combination in high_precision_combinations:
        if len(combination) == 2:
            feature1, feature2 = combination
            if feature1 in feature_analysis and feature2 in feature_analysis:
                # Use high thresholds for each feature
                for percentile in [75, 90, 95]:
                    if not pd.isna(feature_analysis[feature1][f'success_{percentile}']) and \
                       not pd.isna(feature_analysis[feature2][f'success_{percentile}']):
                        filters.append([
                            {
                                'field': feature1,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature1][f'success_{percentile}'],
                                'description': f"{feature1} >= {feature_analysis[feature1][f'success_{percentile}']:.2f} ({percentile}th percentile)"
                            },
                            {
                                'field': feature2,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature2][f'success_{percentile}'],
                                'description': f"{feature2} >= {feature_analysis[feature2][f'success_{percentile}']:.2f} ({percentile}th percentile)"
                            }
                        ])

        elif len(combination) == 3:
            feature1, feature2, feature3 = combination
            if all(f in feature_analysis for f in [feature1, feature2, feature3]):
                # Use high thresholds for all 3 features
                for percentile in [75, 90]:
                    if all(not pd.isna(feature_analysis[f][f'success_{percentile}']) for f in [feature1, feature2, feature3]):
                        filters.append([
                            {
                                'field': feature1,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature1][f'success_{percentile}'],
                                'description': f"{feature1} >= {feature_analysis[feature1][f'success_{percentile}']:.2f} ({percentile}th percentile)"
                            },
                            {
                                'field': feature2,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature2][f'success_{percentile}'],
                                'description': f"{feature2} >= {feature_analysis[feature2][f'success_{percentile}']:.2f} ({percentile}th percentile)"
                            },
                            {
                                'field': feature3,
                                'type': 'min_threshold',
                                'value': feature_analysis[feature3][f'success_{percentile}'],
                                'description': f"{feature3} >= {feature_analysis[feature3][f'success_{percentile}']:.2f} ({percentile}th percentile)"
                            }
                        ])

    # Ultra-strict filters (very high thresholds)
    ultra_strict_filters = []
    for feature, analysis in feature_analysis.items():
        if not pd.isna(analysis['success_95']):
            # Ultra-strict threshold (95th percentile + 20%)
            ultra_strict_value = analysis['success_95'] * 1.2
            ultra_strict_filters.append([{
                'field': feature,
                'type': 'min_threshold',
                'value': ultra_strict_value,
                'description': f"{feature} >= {ultra_strict_value:.2f} (ultra-strict)"
            }])

    filters.extend(ultra_strict_filters)

    print(f"📋 {len(filters)} high-precision filters generated")

    return filters

def apply_filter_combination(token_data, filter_combination):
    """Applies a filter combination to a token"""
    features = extract_numeric_features(token_data)

    # Check each filter criterion
    for criteria in filter_combination:
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

def test_high_precision_filter(new_data, success_data, filter_combination, filter_name):
    """Tests a high-precision filter"""
    # Create a mapping of success tokens
    success_map = {}
    for token in success_data:
        success_map[token['token_address']] = token['multiplication_factor_from_new_adding']

    filtered_tokens = []
    wins = 0
    win_multiples = []

    for token in new_data:
        token_address = get_token_address_from_new_data(token)
        if not token_address:
            continue

        # Apply the filter
        if apply_filter_combination(token, filter_combination):
            filtered_tokens.append(token_address)
            if token_address in success_map and success_map[token_address] >= 1.5:
                wins += 1
                win_multiples.append(success_map[token_address])

    # Calculate the metrics
    total_tokens = len(new_data)
    filtered_count = len(filtered_tokens)
    winrate = (wins / filtered_count * 100) if filtered_count > 0 else 0
    coverage = (filtered_count / total_tokens * 100) if total_tokens > 0 else 0

    # Statistics for the winning multiples
    avg_multiple = np.mean(win_multiples) if win_multiples else 0
    median_multiple = np.median(win_multiples) if win_multiples else 0

    # Precision score (high winrate + low coverage)
    precision_score = winrate * (1 - coverage/100) * 100

    return {
        'filter_name': filter_name,
        'filter_combination': filter_combination,
        'filtered_count': filtered_count,
        'wins': wins,
        'winrate': winrate,
        'coverage': coverage,
        'total_tokens': total_tokens,
        'avg_multiple': avg_multiple,
        'median_multiple': median_multiple,
        'precision_score': precision_score,
        'win_multiples': win_multiples
    }

def optimize_high_precision_filters():
    """Main high-precision filter optimization function"""
    print("🎯 HIGH-PRECISION FILTER OPTIMIZER")
    print("=" * 60)
    print("Objective: Reduced coverage + Maximum winrate")

    # Load the data
    success_data, new_data = load_clean_data()
    if not success_data or not new_data:
        return

    # Analyze the success patterns
    feature_analysis, df = analyze_success_patterns(new_data, success_data)

    # Generate the high-precision filters
    filter_combinations = generate_high_precision_filters(feature_analysis)

    print(f"\n🧪 Testing {len(filter_combinations)} high-precision filters...")

    # Test each combination
    results = []

    for i, combination in enumerate(filter_combinations, 1):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(filter_combinations)} ({i/len(filter_combinations)*100:.1f}%)")

        # Create a name for the filter
        filter_name = f"HighPrecision_{i:04d}"

        # Test the combination
        result = test_high_precision_filter(new_data, success_data, combination, filter_name)
        results.append(result)

    print(f"\n✅ Test complete - {len(results)} filters evaluated")

    # Analyze the results
    analyze_high_precision_results(results)

    # Save the best filters
    save_high_precision_filters(results)

    return results

def analyze_high_precision_results(results):
    """Analyzes and displays the high-precision filter results"""
    print(f"\n📊 HIGH-PRECISION RESULTS ANALYSIS")
    print("=" * 60)

    # Filter the valid results (at least 5 selected tokens)
    valid_results = [r for r in results if r['filtered_count'] >= 5]

    print(f"📋 Valid filters: {len(valid_results)}/{len(results)}")

    if not valid_results:
        print("❌ No valid filter found")
        return

    # Sort by different criteria
    by_winrate = sorted(valid_results, key=lambda x: x['winrate'], reverse=True)
    by_precision_score = sorted(valid_results, key=lambda x: x['precision_score'], reverse=True)
    by_coverage_low = sorted(valid_results, key=lambda x: x['coverage'])  # Lowest coverage first

    # Display the best results by winrate
    print(f"\n🏆 TOP 10 BY WINRATE:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Wins':<5} {'Filter'}")
    print("-" * 70)

    for i, result in enumerate(by_winrate[:10], 1):
        print(f"{i:<4} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['wins']:<5} {result['filter_name']}")

    # Display the best results by precision score
    print(f"\n🏆 TOP 10 BY PRECISION SCORE:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Score':<8} {'Winrate':<8} {'Coverage':<9} {'Avg':<6} {'Median':<7} {'Filter'}")
    print("-" * 70)

    for i, result in enumerate(by_precision_score[:10], 1):
        print(f"{i:<4} {result['precision_score']:<7.2f} {result['winrate']:<7.2f}% {result['coverage']:<8.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['filter_name']}")

    # Display the filters with the lowest coverage
    print(f"\n🎯 TOP 10 LOWEST COVERAGE:")
    print("-" * 70)
    print(f"{'Rank':<4} {'Coverage':<9} {'Winrate':<8} {'Avg':<6} {'Median':<7} {'Wins':<5} {'Filter'}")
    print("-" * 70)

    for i, result in enumerate(by_coverage_low[:10], 1):
        print(f"{i:<4} {result['coverage']:<8.2f}% {result['winrate']:<7.2f}% {result['avg_multiple']:<5.1f}x {result['median_multiple']:<6.1f}x {result['wins']:<5} {result['filter_name']}")

    # General statistics
    print(f"\n📊 GENERAL STATISTICS:")
    print("-" * 60)
    print(f"Average winrate: {np.mean([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Max winrate: {max([r['winrate'] for r in valid_results]):.2f}%")
    print(f"Average coverage: {np.mean([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Min coverage: {min([r['coverage'] for r in valid_results]):.2f}%")
    print(f"Average mean multiple: {np.mean([r['avg_multiple'] for r in valid_results]):.2f}x")

def save_high_precision_filters(results):
    """Saves the best high-precision filters"""
    print(f"\n💾 Saving the best high-precision filters...")

    # Filter the valid results
    valid_results = [r for r in results if r['filtered_count'] >= 5]

    if not valid_results:
        print("❌ No valid filter to save")
        return

    # Sort by precision score
    best_results = sorted(valid_results, key=lambda x: x['precision_score'], reverse=True)

    # Save the top 20
    output = {
        'created_at': datetime.now().isoformat(),
        'total_filters_tested': len(results),
        'valid_filters': len(valid_results),
        'objective': 'High precision - Reduced coverage + Maximum winrate',
        'best_filters': []
    }

    for i, result in enumerate(best_results[:20], 1):
        filter_info = {
            'rank': i,
            'filter_name': result['filter_name'],
            'filter_criteria': result['filter_combination'],
            'results': {
                'filtered_count': result['filtered_count'],
                'wins': result['wins'],
                'winrate': result['winrate'],
                'coverage': result['coverage'],
                'avg_multiple': result['avg_multiple'],
                'median_multiple': result['median_multiple'],
                'precision_score': result['precision_score']
            }
        }
        output['best_filters'].append(filter_info)

    # Save
    filename = f"high_precision_filters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Best high-precision filters saved: {filename}")

    # Also save the best filter separately
    if best_results:
        best_filter = best_results[0]
        best_filter_output = {
            'filter_name': f"Best_High_Precision_Filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'filter_criteria': best_filter['filter_combination'],
            'results': {
                'filtered_count': best_filter['filtered_count'],
                'wins': best_filter['wins'],
                'winrate': best_filter['winrate'],
                'coverage': best_filter['coverage'],
                'avg_multiple': best_filter['avg_multiple'],
                'median_multiple': best_filter['median_multiple'],
                'precision_score': best_filter['precision_score']
            },
            'created_at': datetime.now().isoformat(),
            'description': f"Best high-precision filter - Score: {best_filter['precision_score']:.2f}"
        }

        best_filename = f"best_high_precision_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(best_filename, 'w') as f:
            json.dump(best_filter_output, f, indent=2)

        print(f"✅ Best high-precision filter saved: {best_filename}")
        print(f"🏆 Best filter: {best_filter['filter_name']}")
        print(f"   Winrate: {best_filter['winrate']:.2f}%")
        print(f"   Coverage: {best_filter['coverage']:.2f}%")
        print(f"   Average multiple: {best_filter['avg_multiple']:.2f}x")
        print(f"   Precision score: {best_filter['precision_score']:.2f}")

def main():
    """Main function"""
    results = optimize_high_precision_filters()

    if results:
        print(f"\n🎯 HIGH-PRECISION OPTIMIZATION FINISHED!")
        print("=" * 60)
        print(f"📊 {len(results)} filters tested")
        print(f"✅ Best high-precision filters saved")
        print(f"💡 Objective achieved: Reduced coverage + Maximum winrate")

if __name__ == "__main__":
    main()
