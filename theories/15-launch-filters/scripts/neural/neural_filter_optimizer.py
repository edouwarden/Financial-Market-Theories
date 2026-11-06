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
        """Charge les données historiques et de succès"""
        print("📥 Chargement des données...")
        
        # Charger les données historiques
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
                            
                        # Calculer les ratios
                        buys_5m = int(pair.get('txns', {}).get('m5', {}).get('buys', 0))
                        sells_5m = int(pair.get('txns', {}).get('m5', {}).get('sells', 0))
                        ratio_5m = buys_5m / sells_5m if sells_5m > 0 else 1000  # Limiter l'infini
                        
                        buys_24h = int(pair.get('txns', {}).get('h24', {}).get('buys', 0))
                        sells_24h = int(pair.get('txns', {}).get('h24', {}).get('sells', 0))
                        ratio_24h = buys_24h / sells_24h if sells_24h > 0 else 1000
                        
                        self.historical_data[token_address] = {
                            'tokenAddress': token_address,
                            'tokenName': pair.get('baseToken', {}).get('name', ''),
                            'tokenSymbol': pair.get('baseToken', {}).get('symbol', ''),
                            'buys_5m': buys_5m,
                            'sells_5m': sells_5m,
                            'ratio_5m': min(ratio_5m, 1000),  # Limiter les valeurs extrêmes
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
        
        # Charger les données de succès
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
        
        print(f"✅ Chargé {len(self.historical_data)} snapshots de tokens et {len(self.success_data)} enregistrements de succès")
    
    def prepare_training_data(self, target_multiplier=2.0):
        """Prépare les données d'entraînement pour le réseau neuronal"""
        print("🔄 Préparation des données d'entraînement...")
        
        X = []  # Features
        y = []  # Labels (1 si le token atteint le multiple cible, 0 sinon)
        
        for token_address, token_data in self.historical_data.items():
            # Extraire les features
            features = [
                token_data['buys_5m'], token_data['sells_5m'], token_data['ratio_5m'],
                token_data['buys_24h'], token_data['sells_24h'], token_data['ratio_24h'],
                token_data['priceChange_5m'], token_data['liquidity'], token_data['priceUsd'],
                token_data['marketCap'], token_data['fdv'], token_data['pairCreatedAt'],
                token_data['volume_24h']
            ]
            
            # Vérifier si le token a atteint le multiple cible
            success_info = self.success_data.get(token_address, {})
            achieved_multiplier = success_info.get('multiplier', 0)
            
            # Label: 1 si le token a atteint le multiple cible, 0 sinon
            label = 1 if achieved_multiplier >= target_multiplier else 0
            
            X.append(features)
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        # Normaliser les features
        X_scaled = self.scaler.fit_transform(X)
        
        print(f"📊 Données préparées: {len(X)} échantillons, {np.sum(y)} positifs ({np.mean(y)*100:.1f}%)")
        
        return X_scaled, y
    
    def build_model(self, input_dim):
        """Construit le réseau neuronal"""
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
        """Entraîne le modèle"""
        print("🧠 Entraînement du réseau neuronal...")
        
        # Diviser les données
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Construire le modèle
        self.model = self.build_model(X.shape[1])
        
        # Callbacks pour l'entraînement
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=10, restore_best_weights=True
        )
        
        # Entraînement
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            callbacks=[early_stopping],
            verbose=1
        )
        
        # Évaluation
        y_pred = (self.model.predict(X_test) > 0.5).astype(int)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        print(f"📈 Résultats sur le test set:")
        print(f"   Accuracy: {accuracy:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1-Score: {f1:.3f}")
        
        return history, (X_test, y_test, y_pred)
    
    def analyze_feature_importance(self, X, y):
        """Analyse l'importance des features"""
        print("🔍 Analyse de l'importance des features...")
        
        # Entraîner un modèle simple pour l'analyse
        from sklearn.ensemble import RandomForestClassifier
        
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # Importance des features
        importance = rf.feature_importances_
        feature_importance = list(zip(self.feature_names, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        print("📊 Importance des features:")
        for feature, imp in feature_importance:
            print(f"   {feature}: {imp:.3f}")
        
        return feature_importance
    
    def generate_optimal_filters(self, X, y, num_filters=50):
        """Génère des filtres optimaux basés sur les prédictions du modèle"""
        print("🎯 Génération de filtres optimaux...")
        
        # Prédictions du modèle
        predictions = self.model.predict(X).flatten()
        
        # Créer un DataFrame avec les données et prédictions
        df = pd.DataFrame(X, columns=self.feature_names)
        df['prediction'] = predictions
        df['actual'] = y
        
        # Trier par prédiction (probabilité de succès)
        df_sorted = df.sort_values('prediction', ascending=False)
        
        filters = []
        
        # Générer des filtres basés sur différents seuils
        thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
        
        for threshold in thresholds:
            # Tokens avec haute probabilité de succès
            high_prob_tokens = df_sorted[df_sorted['prediction'] >= threshold]
            
            if len(high_prob_tokens) > 0:
                # Calculer les statistiques pour ce filtre
                trades = len(high_prob_tokens)
                wins = high_prob_tokens['actual'].sum()
                win_rate = wins / trades if trades > 0 else 0
                
                # Créer le filtre basé sur les percentiles des features
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
        """Évalue les filtres générés selon vos critères"""
        print("🏆 Évaluation des filtres selon vos critères...")
        
        results = {
            'best_win_rate': [],
            'best_multiple': [],
            'best_retention': []
        }
        
        for filter_info in filters:
            trades = filter_info['trades']
            wins = filter_info['wins']
            win_rate = filter_info['win_rate']
            
            # Critère 1: Bon win rate (>90%) avec au moins 35 trades
            if win_rate >= 0.9 and trades >= 35:
                results['best_win_rate'].append(filter_info)
            
            # Critère 2: Bon multiple final (>100) avec au moins 3 trades gagnants
            # Pour cela, on doit évaluer avec target_multiplier=100
            if trades >= 3:  # On vérifiera le multiple plus tard
                results['best_multiple'].append(filter_info)
            
            # Critère 3: Bonne retention (win rate >=60%) avec maximum de coins
            if win_rate >= 0.6:
                results['best_retention'].append(filter_info)
        
        # Trier les résultats
        results['best_win_rate'].sort(key=lambda x: (x['win_rate'], x['trades']), reverse=True)
        results['best_retention'].sort(key=lambda x: x['trades'], reverse=True)
        
        return results
    
    def save_results(self, results, filename='neural_optimizer_results.json'):
        """Sauvegarde les résultats"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Résultats sauvegardés dans {filename}")
    
    def plot_results(self, history, test_results):
        """Affiche les graphiques des résultats"""
        X_test, y_test, y_pred = test_results
        
        # Graphique de l'entraînement
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.plot(history.history['accuracy'], label='Train Accuracy')
        plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
        plt.title('Accuracy pendant l\'entraînement')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.legend()
        
        plt.subplot(1, 3, 2)
        plt.plot(history.history['loss'], label='Train Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Loss pendant l\'entraînement')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        plt.subplot(1, 3, 3)
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Matrice de confusion')
        plt.xlabel('Prédit')
        plt.ylabel('Réel')
        
        plt.tight_layout()
        plt.savefig('neural_optimizer_results.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """Fonction principale"""
    print("🚀 Démarrage de l'optimiseur de filtres par réseau neuronal")
    
    # Créer l'optimiseur
    optimizer = NeuralFilterOptimizer()
    
    # Charger les données
    optimizer.load_data()
    
    # Préparer les données d'entraînement
    X, y = optimizer.prepare_training_data(target_multiplier=2.0)
    
    # Analyser l'importance des features
    feature_importance = optimizer.analyze_feature_importance(X, y)
    
    # Entraîner le modèle
    history, test_results = optimizer.train_model(X, y)
    
    # Générer des filtres optimaux
    filters = optimizer.generate_optimal_filters(X, y)
    
    # Évaluer les filtres
    results = optimizer.evaluate_filters(filters)
    
    # Afficher les résultats
    print("\n🏆 MEILLEURS FILTRES TROUVÉS:")
    
    print("\n=== Meilleur Win Rate (>90% avec ≥35 trades):")
    for i, filter_info in enumerate(results['best_win_rate'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, Wins: {filter_info['wins']}")
    
    print("\n=== Meilleure Retention (WR≥60% avec max coins):")
    for i, filter_info in enumerate(results['best_retention'][:10]):
        print(f"{i+1}. WR: {filter_info['win_rate']:.1%}, Trades: {filter_info['trades']}, Wins: {filter_info['wins']}")
    
    # Sauvegarder les résultats
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
    
    # Afficher les graphiques
    optimizer.plot_results(history, test_results)
    
    print("✅ Optimisation terminée!")

if __name__ == "__main__":
    main()

