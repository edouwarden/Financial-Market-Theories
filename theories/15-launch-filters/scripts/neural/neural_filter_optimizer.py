import json
import numpy as np
import pandas as pd
import glob
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import seaborn as sns

class NeuralFilterOptimizer:
    def __init__(self):
        self.historical_data = {}
        self.success_data = {}
        self.scaler = StandardScaler()
        self.model = None
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
                        ratio_5m = buys_5m / sells_5m if sells_5m > 0 else 1000  # Cap infinity

                        buys_24h = int(pair.get('txns', {}).get('h24', {}).get('buys', 0))
                        sells_24h = int(pair.get('txns', {}).get('h24', {}).get('sells', 0))
                        ratio_24h = buys_24h / sells_24h if sells_24h > 0 else 1000

                        self.historical_data[token_address] = {
                            'tokenAddress': token_address,
                            'tokenName': pair.get('baseToken', {}).get('name', ''),
                            'tokenSymbol': pair.get('baseToken', {}).get('symbol', ''),
                            'buys_5m': buys_5m,
                            'sells_5m': sells_5m,
                            'ratio_5m': min(ratio_5m, 1000),  # Cap extreme values
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

    def prepare_training_data(self, target_multiplier=2.0):
        """Prepares the training data for the neural network"""
        print("🔄 Preparing training data...")

        X = []  # Features
        y = []  # Labels (1 if the token reaches the target multiple, 0 otherwise)

        for token_address, token_data in self.historical_data.items():
            # Extract the features
            features = [
                token_data['buys_5m'], token_data['sells_5m'], token_data['ratio_5m'],
                token_data['buys_24h'], token_data['sells_24h'], token_data['ratio_24h'],
                token_data['priceChange_5m'], token_data['liquidity'], token_data['priceUsd'],
                token_data['marketCap'], token_data['fdv'], token_data['pairCreatedAt'],
                token_data['volume_24h']
            ]

            # Check whether the token reached the target multiple
            success_info = self.success_data.get(token_address, {})
            achieved_multiplier = success_info.get('multiplier', 0)

            # Label: 1 if the token reached the target multiple, 0 otherwise
            label = 1 if achieved_multiplier >= target_multiplier else 0

            X.append(features)
            y.append(label)

        X = np.array(X)
        y = np.array(y)

        # Normalize the features
        X_scaled = self.scaler.fit_transform(X)

        print(f"📊 Prepared data: {len(X)} samples, {np.sum(y)} positives ({np.mean(y)*100:.1f}%)")

        return X_scaled, y

    def build_model(self, input_dim):
        """Builds the neural network"""
        model = keras.Sequential([
            layers.Dense(128, activation='relu', input_shape=(input_dim,)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.1),
            layers.Dense(1, activation='sigmoid')
        ])

        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )

        return model

    def train_model(self, X, y, epochs=100, batch_size=32):
        """Trains the model"""
        print("🧠 Training the neural network...")

        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Build the model
        self.model = self.build_model(X.shape[1])

        # Callbacks for training
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=10, restore_best_weights=True
        )

        # Training
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            callbacks=[early_stopping],
            verbose=1
        )

        # Evaluation
        y_pred = (self.model.predict(X_test) > 0.5).astype(int)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        print(f"📈 Test set results:")
        print(f"   Accuracy: {accuracy:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1-Score: {f1:.3f}")

        return history, (X_test, y_test, y_pred)

    def analyze_feature_importance(self, X, y):
        """Analyzes feature importance"""
        print("🔍 Analyzing feature importance...")

        # Train a simple model for the analysis
        from sklearn.ensemble import RandomForestClassifier

        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)

        # Feature importance
        importance = rf.feature_importances_
        feature_importance = list(zip(self.feature_names, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        print("📊 Feature importance:")
        for feature, imp in feature_importance:
            print(f"   {feature}: {imp:.3f}")

        return feature_importance

    def generate_optimal_filters(self, X, y, num_filters=50):
        """Generates optimal filters based on the model's predictions"""
        print("🎯 Generating optimal filters...")

        # Model predictions
        predictions = self.model.predict(X).flatten()

        # Create a DataFrame with the data and predictions
        df = pd.DataFrame(X, columns=self.feature_names)
        df['prediction'] = predictions
        df['actual'] = y

        # Sort by prediction (probability of success)
        df_sorted = df.sort_values('prediction', ascending=False)

        filters = []

        # Generate filters based on different thresholds
        thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]

        for threshold in thresholds:
            # Tokens with a high probability of success
            high_prob_tokens = df_sorted[df_sorted['prediction'] >= threshold]

            if len(high_prob_tokens) > 0:
                # Calculate the statistics for this filter
                trades = len(high_prob_tokens)
                wins = high_prob_tokens['actual'].sum()
                win_rate = wins / trades if trades > 0 else 0

                # Create the filter based on feature percentiles
                filter_rules = {}
                for feature in self.feature_names:
                    values = high_prob_tokens[feature]
                    if len(values) > 0:
                        filter_rules[f'{feature}_min'] = float(values.quantile(0.1))
                        filter_rules[f'{feature}_max'] = float(values.quantile(0.9))

                filters.append({
                    'threshold': threshold,
                    'trades': trades,
                    'wins': wins,
                    'win_rate': win_rate,
                    'rules': filter_rules
                })

        return filters

    def evaluate_filters(self, filters, target_multiplier=2.0):
        """Evaluates the generated filters according to your criteria"""
        print("🏆 Evaluating filters according to your criteria...")

        results = {
            'best_win_rate': [],
            'best_multiple': [],
            'best_retention': []
        }

        for filter_info in filters:
            trades = filter_info['trades']
            wins = filter_info['wins']
            win_rate = filter_info['win_rate']

            # Criterion 1: Good win rate (>90%) with at least 35 trades
            if win_rate >= 0.9 and trades >= 35:
                results['best_win_rate'].append(filter_info)

            # Criterion 2: Good final multiple (>100) with at least 3 winning trades
            # To do this, we must evaluate with target_multiplier=100
            if trades >= 3:  # The multiple will be checked later
                results['best_multiple'].append(filter_info)

            # Criterion 3: Good retention (win rate >=60%) with the maximum number of coins
            if win_rate >= 0.6:
                results['best_retention'].append(filter_info)

        # Sort the results
        results['best_win_rate'].sort(key=lambda x: (x['win_rate'], x['trades']), reverse=True)
        results['best_retention'].sort(key=lambda x: x['trades'], reverse=True)

        return results

    def save_results(self, results, filename='neural_optimizer_results.json'):
        """Saves the results"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to {filename}")

    def plot_results(self, history, test_results):
        """Displays the result charts"""
        X_test, y_test, y_pred = test_results

        # Training chart
        plt.figure(figsize=(15, 5))

        plt.subplot(1, 3, 1)
        plt.plot(history.history['accuracy'], label='Train Accuracy')
        plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
        plt.title('Accuracy during training')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.legend()

        plt.subplot(1, 3, 2)
        plt.plot(history.history['loss'], label='Train Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Loss during training')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()

        plt.subplot(1, 3, 3)
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Confusion matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')

        plt.tight_layout()
        plt.savefig('neural_optimizer_results.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """Main function"""
    print("🚀 Starting the neural network filter optimizer")

    # Create the optimizer
    optimizer = NeuralFilterOptimizer()

    # Load the data
    optimizer.load_data()

    # Prepare the training data
    X, y = optimizer.prepare_training_data(target_multiplier=2.0)

    # Analyze feature importance
    feature_importance = optimizer.analyze_feature_importance(X, y)

    # Train the model
    history, test_results = optimizer.train_model(X, y)

    # Generate optimal filters
    filters = optimizer.generate_optimal_filters(X, y)

    # Evaluate the filters
    results = optimizer.evaluate_filters(filters)

    # Display the results
    print("\n🏆 BEST FILTERS FOUND:")

    print("\n=== Best Win Rate (>90% with ≥35 trades):")
    for i, filter_info in enumerate(results['best_win_rate'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, Wins: {filter_info['wins']}")

    print("\n=== Best Retention (WR≥60% with max coins):")
    for i, filter_info in enumerate(results['best_retention'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, Wins: {filter_info['wins']}")

    # Save the results
    all_results = {
        'feature_importance': feature_importance,
        'filters': filters,
        'evaluations': results,
        'model_metrics': {
            'test_accuracy': float(accuracy_score(test_results[1], test_results[2])),
            'test_precision': float(precision_score(test_results[1], test_results[2])),
            'test_recall': float(recall_score(test_results[1], test_results[2])),
            'test_f1': float(f1_score(test_results[1], test_results[2]))
        }
    }

    optimizer.save_results(all_results)

    # Display the charts
    optimizer.plot_results(history, test_results)

    print("✅ Optimization complete!")

if __name__ == "__main__":
    main()
