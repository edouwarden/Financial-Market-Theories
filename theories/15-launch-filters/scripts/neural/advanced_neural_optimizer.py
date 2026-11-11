import json
import numpy as np
import pandas as pd
import glob
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import seaborn as sns

class AdvancedNeuralFilterOptimizer:
    def __init__(self):
        self.historical_data = {}
        self.success_data = {}
        self.scaler = StandardScaler()
        self.models = {}  # One model per criterion
        self.feature_names = [
            'buys_5m', 'sells_5m', 'ratio_5m', 'buys_24h', 'sells_24h', 'ratio_24h',
            'priceChange_5m', 'liquidity', 'priceUsd', 'marketCap', 'fdv',
            'pairCreatedAt', 'volume_24h'
        ]

    def load_data(self):
        """Loads the historical and success data"""
        print("📥 Loading data...")

        # Load the historical data
        data_files = glob.glob('data/new_*.csv')
        for file in data_files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if not isinstance(data, list) or len(data) == 0:
                            continue

                        pair = data[0]
                        token_address = pair.get('baseToken', {}).get('address')
                        if not token_address:
                            continue

                        # Calculate the ratios
                        buys_5m = int(pair.get('txns', {}).get('m5', {}).get('buys', 0))
                        sells_5m = int(pair.get('txns', {}).get('m5', {}).get('sells', 0))
                        ratio_5m = buys_5m / sells_5m if sells_5m > 0 else 1000

                        buys_24h = int(pair.get('txns', {}).get('h24', {}).get('buys', 0))
                        sells_24h = int(pair.get('txns', {}).get('h24', {}).get('sells', 0))
                        ratio_24h = buys_24h / sells_24h if sells_24h > 0 else 1000

                        self.historical_data[token_address] = {
                            'tokenAddress': token_address,
                            'tokenName': pair.get('baseToken', {}).get('name', ''),
                            'tokenSymbol': pair.get('baseToken', {}).get('symbol', ''),
                            'buys_5m': buys_5m,
                            'sells_5m': sells_5m,
                            'ratio_5m': min(ratio_5m, 1000),
                            'buys_24h': buys_24h,
                            'sells_24h': sells_24h,
                            'ratio_24h': min(ratio_24h, 1000),
                            'priceChange_5m': float(pair.get('priceChange', {}).get('m5', 0)),
                            'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                            'priceUsd': float(pair.get('priceUsd', 0)),
                            'marketCap': float(pair.get('marketCap', 0)),
                            'fdv': float(pair.get('fdv', 0)),
                            'pairCreatedAt': int(pair.get('pairCreatedAt', 0)),
                            'volume_24h': float(pair.get('volume', {}).get('h24', 0))
                        }
                    except Exception as e:
                        continue

        # Load the success data
        success_files = glob.glob('data/success_*.csv')
        for file in success_files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            timestamp, token_address, token_name, multiplier = parts[:4]
                            self.success_data[token_address] = {
                                'timestamp': datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp(),
                                'multiplier': float(multiplier)
                            }
                    except Exception as e:
                        continue

        print(f"✅ Loaded {len(self.historical_data)} token snapshots and {len(self.success_data)} success records")

    def prepare_training_data_for_criteria(self, criteria_type):
        """Prepares the training data according to the specific criterion"""
        print(f"🔄 Preparing data for criterion: {criteria_type}")

        X = []
        y = []

        for token_address, token_data in self.historical_data.items():
            features = [
                token_data['buys_5m'], token_data['sells_5m'], token_data['ratio_5m'],
                token_data['buys_24h'], token_data['sells_24h'], token_data['ratio_24h'],
                token_data['priceChange_5m'], token_data['liquidity'], token_data['priceUsd'],
                token_data['marketCap'], token_data['fdv'], token_data['pairCreatedAt'],
                token_data['volume_24h']
            ]

            success_info = self.success_data.get(token_address, {})
            achieved_multiplier = success_info.get('multiplier', 0)

            # Define the labels according to the criterion
            if criteria_type == 'win_rate':
                # Criterion 1: Win rate > 90% with at least 35 trades
                label = 1 if achieved_multiplier >= 2.0 else 0
            elif criteria_type == 'high_multiple':
                # Criterion 2: Multiple > 100 with at least 3 winning trades
                label = 1 if achieved_multiplier >= 100.0 else 0
            elif criteria_type == 'retention':
                # Criterion 3: Win rate >= 60% with the maximum number of coins
                label = 1 if achieved_multiplier >= 2.0 else 0
            else:
                label = 0

            X.append(features)
            y.append(label)

        X = np.array(X)
        y = np.array(y)

        # Normalize the features
        X_scaled = self.scaler.fit_transform(X)

        positive_ratio = np.mean(y) * 100
        print(f"📊 Criterion '{criteria_type}': {len(X)} samples, {np.sum(y)} positives ({positive_ratio:.1f}%)")

        return X_scaled, y

    def build_model(self, input_dim, criteria_type):
        """Builds a model optimized for the criterion"""
        if criteria_type == 'win_rate':
            # Model for high precision (win rate > 90%)
            model = keras.Sequential([
                layers.Dense(256, activation='relu', input_shape=(input_dim,)),
                layers.BatchNormalization(),
                layers.Dropout(0.4),
                layers.Dense(128, activation='relu'),
                layers.BatchNormalization(),
                layers.Dropout(0.3),
                layers.Dense(64, activation='relu'),
                layers.Dropout(0.2),
                layers.Dense(1, activation='sigmoid')
            ])
        elif criteria_type == 'high_multiple':
            # Model to detect large gains (multiple > 100)
            model = keras.Sequential([
                layers.Dense(512, activation='relu', input_shape=(input_dim,)),
                layers.BatchNormalization(),
                layers.Dropout(0.5),
                layers.Dense(256, activation='relu'),
                layers.BatchNormalization(),
                layers.Dropout(0.4),
                layers.Dense(128, activation='relu'),
                layers.Dropout(0.3),
                layers.Dense(64, activation='relu'),
                layers.Dropout(0.2),
                layers.Dense(1, activation='sigmoid')
            ])
        else:  # retention
            # Balanced model for retention
            model = keras.Sequential([
                layers.Dense(128, activation='relu', input_shape=(input_dim,)),
                layers.BatchNormalization(),
                layers.Dropout(0.3),
                layers.Dense(64, activation='relu'),
                layers.BatchNormalization(),
                layers.Dropout(0.2),
                layers.Dense(32, activation='relu'),
                layers.Dropout(0.1),
                layers.Dense(1, activation='sigmoid')
            ])

        # Optimizer and metrics adapted to the criterion
        if criteria_type == 'win_rate':
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='binary_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )
        elif criteria_type == 'high_multiple':
            # For large gains, precision is favored
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.0005),
                loss='binary_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )
        else:
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='binary_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )

        return model

    def train_models(self):
        """Trains the models for each criterion"""
        print("🧠 Training the models for each criterion...")

        criteria_types = ['win_rate', 'high_multiple', 'retention']
        results = {}

        for criteria in criteria_types:
            print(f"\n--- Training for criterion: {criteria} ---")

            # Prepare the data
            X, y = self.prepare_training_data_for_criteria(criteria)

            # Split the data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Build and train the model
            model = self.build_model(X.shape[1], criteria)
            self.models[criteria] = model

            # Callbacks
            early_stopping = keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=15, restore_best_weights=True
            )

            # Training
            history = model.fit(
                X_train, y_train,
                epochs=200,
                batch_size=32,
                validation_data=(X_test, y_test),
                callbacks=[early_stopping],
                verbose=1
            )

            # Evaluation
            y_pred = (model.predict(X_test) > 0.5).astype(int)
            metrics = {
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'precision': float(precision_score(y_test, y_pred, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, zero_division=0))
            }

            results[criteria] = {
                'history': history,
                'test_data': (X_test, y_test, y_pred),
                'metrics': metrics
            }

            print(f"📈 Metrics for {criteria}:")
            for metric, value in metrics.items():
                print(f"   {metric}: {value:.3f}")

        return results

    def generate_optimal_filters(self):
        """Generates optimal filters for each criterion"""
        print("🎯 Generating optimal filters for each criterion...")

        all_filters = {}

        for criteria, model in self.models.items():
            print(f"\n--- Generating filters for: {criteria} ---")

            # Prepare all the data
            X, y = self.prepare_training_data_for_criteria(criteria)

            # Model predictions
            predictions = model.predict(X).flatten()

            # Create DataFrame
            df = pd.DataFrame(X, columns=self.feature_names)
            df['prediction'] = predictions
            df['actual'] = y

            # Sort by prediction
            df_sorted = df.sort_values('prediction', ascending=False)

            filters = []

            # Generate filters with different thresholds
            if criteria == 'win_rate':
                thresholds = [0.95, 0.9, 0.85, 0.8]
            elif criteria == 'high_multiple':
                thresholds = [0.8, 0.7, 0.6, 0.5]
            else:  # retention
                thresholds = [0.7, 0.6, 0.5, 0.4]

            for threshold in thresholds:
                high_prob_tokens = df_sorted[df_sorted['prediction'] >= threshold]

                if len(high_prob_tokens) > 0:
                    trades = len(high_prob_tokens)
                    wins = high_prob_tokens['actual'].sum()
                    win_rate = wins / trades if trades > 0 else 0

                    # Create the filter rules
                    filter_rules = {}
                    for feature in self.feature_names:
                        values = high_prob_tokens[feature]
                        if len(values) > 0:
                            # Use percentiles for more robust rules
                            filter_rules[f'{feature}_min'] = float(values.quantile(0.05))
                            filter_rules[f'{feature}_max'] = float(values.quantile(0.95))

                    filters.append({
                        'threshold': threshold,
                        'trades': trades,
                        'wins': wins,
                        'win_rate': win_rate,
                        'rules': filter_rules,
                        'avg_prediction': float(high_prob_tokens['prediction'].mean())
                    })

            all_filters[criteria] = filters

        return all_filters

    def evaluate_filters_advanced(self, filters):
        """Evaluates the filters according to your specific criteria"""
        print("🏆 Advanced filter evaluation...")

        results = {
            'best_win_rate': [],
            'best_multiple': [],
            'best_retention': []
        }

        # Evaluate the win rate filters
        for filter_info in filters.get('win_rate', []):
            if filter_info['win_rate'] >= 0.9 and filter_info['trades'] >= 35:
                results['best_win_rate'].append(filter_info)

        # Evaluate the high multiple filters
        for filter_info in filters.get('high_multiple', []):
            if filter_info['wins'] >= 3 and filter_info['win_rate'] >= 0.01:
                results['best_multiple'].append(filter_info)

        # Evaluate the retention filters
        for filter_info in filters.get('retention', []):
            if filter_info['win_rate'] >= 0.6:
                results['best_retention'].append(filter_info)

        # Sort the results
        results['best_win_rate'].sort(key=lambda x: (x['win_rate'], x['trades']), reverse=True)
        results['best_multiple'].sort(key=lambda x: (x['win_rate'], x['wins']), reverse=True)
        results['best_retention'].sort(key=lambda x: x['trades'], reverse=True)

        return results

    def save_results(self, results, filename='advanced_neural_results.json'):
        """Saves the results"""
        # Convert non-serializable objects
        serializable_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                serializable_results[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (np.ndarray, pd.DataFrame)):
                        serializable_results[key][sub_key] = sub_value.tolist()
                    else:
                        serializable_results[key][sub_key] = sub_value
            else:
                serializable_results[key] = value

        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        print(f"💾 Results saved to {filename}")

    def plot_comprehensive_results(self, training_results, filters):
        """Displays comprehensive result charts"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))

        criteria = ['win_rate', 'high_multiple', 'retention']

        for i, criteria_type in enumerate(criteria):
            # Training charts
            history = training_results[criteria_type]['history']

            # Accuracy
            axes[0, i].plot(history.history['accuracy'], label='Train')
            axes[0, i].plot(history.history['val_accuracy'], label='Validation')
            axes[0, i].set_title(f'Accuracy - {criteria_type}')
            axes[0, i].set_xlabel('Epoch')
            axes[0, i].set_ylabel('Accuracy')
            axes[0, i].legend()

            # Loss
            axes[1, i].plot(history.history['loss'], label='Train')
            axes[1, i].plot(history.history['val_loss'], label='Validation')
            axes[1, i].set_title(f'Loss - {criteria_type}')
            axes[1, i].set_xlabel('Epoch')
            axes[1, i].set_ylabel('Loss')
            axes[1, i].legend()

        plt.tight_layout()
        plt.savefig('advanced_neural_results.png', dpi=300, bbox_inches='tight')
        plt.show()

        # Filter chart
        self.plot_filter_comparison(filters)

    def plot_filter_comparison(self, filters):
        """Displays a comparison chart of the filters"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        criteria = ['win_rate', 'high_multiple', 'retention']

        for i, criteria_type in enumerate(criteria):
            filter_list = filters.get(criteria_type, [])

            if filter_list:
                trades = [f['trades'] for f in filter_list]
                win_rates = [f['win_rate'] * 100 for f in filter_list]
                thresholds = [f['threshold'] for f in filter_list]

                scatter = axes[i].scatter(trades, win_rates, c=thresholds, cmap='viridis', s=100)
                axes[i].set_xlabel('Number of trades')
                axes[i].set_ylabel('Win Rate (%)')
                axes[i].set_title(f'Filters - {criteria_type}')
                axes[i].grid(True, alpha=0.3)

                # Add colorbar
                plt.colorbar(scatter, ax=axes[i], label='Prediction threshold')

        plt.tight_layout()
        plt.savefig('filter_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """Main function"""
    print("🚀 Starting the advanced neural network filter optimizer")

    # Create the optimizer
    optimizer = AdvancedNeuralFilterOptimizer()

    # Load the data
    optimizer.load_data()

    # Train the models
    training_results = optimizer.train_models()

    # Generate the optimal filters
    filters = optimizer.generate_optimal_filters()

    # Evaluate the filters
    evaluations = optimizer.evaluate_filters_advanced(filters)

    # Display the results
    print("\n🏆 BEST FILTERS FOUND:")

    print("\n=== Best Win Rate (>90% with ≥35 trades):")
    for i, filter_info in enumerate(evaluations['best_win_rate'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, "
              f"Wins: {filter_info['wins']}, Threshold: {filter_info['threshold']:.2f}")

    print("\n=== Best Multiple (>100 with ≥3 wins):")
    for i, filter_info in enumerate(evaluations['best_multiple'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, "
              f"Wins: {filter_info['wins']}, Threshold: {filter_info['threshold']:.2f}")

    print("\n=== Best Retention (WR≥60% with max coins):")
    for i, filter_info in enumerate(evaluations['best_retention'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, "
              f"Wins: {filter_info['wins']}, Threshold: {filter_info['threshold']:.2f}")

    # Save the results
    all_results = {
        'training_results': training_results,
        'filters': filters,
        'evaluations': evaluations
    }

    optimizer.save_results(all_results)

    # Display the charts
    optimizer.plot_comprehensive_results(training_results, filters)

    print("✅ Advanced optimization complete!")

if __name__ == "__main__":
    main()
