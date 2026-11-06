#!/usr/bin/env python3
"""
Script de test pour vérifier le bon fonctionnement du système d'optimisation
"""

import os
import json
import glob
import sys

def test_dependencies():
    """Teste si toutes les dépendances sont installées"""
    print("🔍 Test des dépendances...")
    
    required_packages = [
        'tensorflow', 'numpy', 'pandas', 'sklearn', 
        'matplotlib', 'seaborn', 'glob'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MANQUANT")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Packages manquants: {', '.join(missing_packages)}")
        print("💡 Lancez: python install_dependencies.py")
        return False
    
    print("✅ Toutes les dépendances sont installées")
    return True

def test_data_files():
    """Teste si les fichiers de données existent"""
    print("\n📁 Test des fichiers de données...")
    
    # Vérifier les données historiques
    historical_files = glob.glob('data/new_*.csv')
    if historical_files:
        print(f"✅ Données historiques trouvées: {len(historical_files)} fichiers")
    else:
        print("❌ Aucun fichier de données historiques trouvé (data/new_*.csv)")
        return False
    
    # Vérifier les données de succès
    success_files = glob.glob('data/success_*.csv')
    if success_files:
        print(f"✅ Données de succès trouvées: {len(success_files)} fichiers")
    else:
        print("❌ Aucun fichier de données de succès trouvé (data/success_*.csv)")
        return False
    
    return True

def test_data_loading():
    """Teste le chargement des données"""
    print("\n📥 Test du chargement des données...")
    
    try:
        # Test avec un petit échantillon
        from neural_filter_optimizer import NeuralFilterOptimizer
        
        optimizer = NeuralFilterOptimizer()
        optimizer.load_data()
        
        if len(optimizer.historical_data) > 0:
            print(f"✅ Données historiques chargées: {len(optimizer.historical_data)} tokens")
        else:
            print("❌ Aucune donnée historique chargée")
            return False
        
        if len(optimizer.success_data) > 0:
            print(f"✅ Données de succès chargées: {len(optimizer.success_data)} enregistrements")
        else:
            print("❌ Aucune donnée de succès chargée")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return False

def test_model_creation():
    """Teste la création d'un modèle simple"""
    print("\n🧠 Test de création de modèle...")
    
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers
        
        # Créer un modèle simple
        model = keras.Sequential([
            layers.Dense(64, activation='relu', input_shape=(13,)),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        
        print("✅ Modèle créé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du modèle: {e}")
        return False

def test_advanced_optimizer():
    """Teste l'optimiseur avancé"""
    print("\n🚀 Test de l'optimiseur avancé...")
    
    try:
        from advanced_neural_optimizer import AdvancedNeuralFilterOptimizer
        
        optimizer = AdvancedNeuralFilterOptimizer()
        print("✅ Optimiseur avancé importé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur avec l'optimiseur avancé: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🧪 Test du système d'optimisation de filtres")
    print("=" * 50)
    
    tests = [
        ("Dépendances", test_dependencies),
        ("Fichiers de données", test_data_files),
        ("Chargement des données", test_data_loading),
        ("Création de modèle", test_model_creation),
        ("Optimiseur avancé", test_advanced_optimizer)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"❌ Test '{test_name}' a échoué")
        except Exception as e:
            print(f"❌ Test '{test_name}' a généré une erreur: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Résumé des tests: {passed_tests}/{total_tests} réussis")
    
    if passed_tests == total_tests:
        print("🎉 Tous les tests sont passés! Le système est prêt.")
        print("\n🚀 Vous pouvez maintenant lancer l'optimiseur:")
        print("   python run_optimizer.py")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        print("\n💡 Solutions possibles:")
        print("   - Lancez: python install_dependencies.py")
        print("   - Vérifiez que vos données sont dans le dossier 'data/'")
        print("   - Vérifiez la version de Python (3.8+)")

if __name__ == "__main__":
    main()


